#!/usr/bin/env python3
"""Compare the first evaluation histories against a doubled bank and local grid refinement."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes.arc2c_campaign import spawn_seed_manifest
from latent_landscapes.arc2c_design import TRUTHS, timing_config
from latent_landscapes.arc2c_likelihood import (
    build_joint_integration,
    evaluate_dataset,
    paired_histories,
)
from latent_landscapes.goal011.benchmark import build_fixed_inputs


def local_grid(
    grid: NDArray[np.float64], indices: tuple[int, ...], *, log: bool
) -> tuple[float, ...]:
    values: set[float] = set()
    for index in indices:
        values.add(float(grid[index]))
        for neighbour in (index - 1, index + 1):
            if 0 <= neighbour < len(grid):
                midpoint = (
                    np.sqrt(grid[index] * grid[neighbour])
                    if log
                    else (grid[index] + grid[neighbour]) / 2
                )
                values.add(float(midpoint))
    return tuple(sorted(values))


def profile_change(old: NDArray[np.float64], new: NDArray[np.float64]) -> float:
    old_drop = 2 * (old.max() - old)
    new_drop = 2 * (new.max() - new)
    near_support = old_drop <= 10
    return float(np.max(np.abs(new_drop[near_support] - old_drop[near_support])))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timing-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = timing_config()
    seeds = spawn_seed_manifest(replace(config, bank_size=2 * config.bank_size))
    fixed = build_fixed_inputs()
    histories = paired_histories(fixed, seeds.validation[0])
    sites = tuple(row.site_id for row in histories[0])
    bank = np.load(args.timing_dir / "base_arrivals.npy", allow_pickle=False)
    run = json.loads((args.timing_dir / "run_summary.json").read_text())
    if (
        bank.shape != (config.bank_size, len(sites))
        or run["config"] != json.loads(json.dumps(asdict(config)))
        or run["bank_checksum"] != hashlib.sha256(bank.tobytes(order="C")).hexdigest()
        or not all(run["invariants"].values())
    ):
        raise ValueError("canary requires the complete frozen timing bank")
    if (
        run["profile_bundle_sha256"]
        != hashlib.sha256((args.timing_dir / "profiles.npz").read_bytes()).hexdigest()
    ):
        raise ValueError("timing profiles do not match the recorded source run")
    with np.load(args.timing_dir / "profiles.npz", allow_pickle=False) as profiles:
        reference = profiles["representative_train_joint"]
    print("Generating the second half of the nested 8192-draw bank", flush=True)
    extra = arc2b._generate_bank(fixed, seeds.bank_seeds[config.bank_size :])
    integration = build_joint_integration(
        np.concatenate((bank, extra)), sites, config.rhos, config.effects
    )
    print("Doubled-bank integration ready", flush=True)
    rhos, effects = np.asarray(config.rhos), np.asarray(config.effects)
    rows = []
    for truth, records, baseline in zip(TRUTHS, histories, reference, strict=True):
        doubled = evaluate_dataset(records, integration)[0]
        true_rho = int(np.flatnonzero(rhos == truth.rho)[0])
        old_r, old_h = np.unravel_index(np.argmax(baseline), baseline.shape)
        new_r, new_h = np.unravel_index(np.argmax(doubled), doubled.shape)
        old_known = int(np.argmax(baseline[true_rho]))
        new_known = int(np.argmax(doubled[true_rho]))
        bank_effect_change = float(
            max(
                abs(np.log(effects[new_h] / effects[old_h])),
                abs(np.log(effects[new_known] / effects[old_known])),
            )
        )
        bank_rho_change = float(abs(np.log(rhos[new_r] / rhos[old_r])))
        bank_profile_changes = (
            profile_change(baseline[true_rho], doubled[true_rho]),
            profile_change(baseline.max(axis=0), doubled.max(axis=0)),
            profile_change(baseline.max(axis=1), doubled.max(axis=1)),
        )
        fine_rhos = local_grid(rhos, (int(old_r), true_rho), log=True)
        fine_effects = local_grid(effects, (int(old_h), old_known), log=False)
        refined = build_joint_integration(bank, sites, fine_rhos, fine_effects)
        refined_joint = evaluate_dataset(records, refined)[0]
        refinement_gain = float(refined_joint.max() - baseline.max())
        known_refinement_gain = float(
            refined_joint[fine_rhos.index(truth.rho)].max() - baseline[true_rho].max()
        )
        row = {
            "condition_id": truth.condition_id,
            "bank_effect_max_abs_log_mle_change": bank_effect_change,
            "bank_rho_abs_log_mle_change": bank_rho_change,
            "bank_known_effect_profile_lr_change_within_10": bank_profile_changes[0],
            "bank_estimated_effect_profile_lr_change_within_10": bank_profile_changes[1],
            "bank_spread_profile_lr_change_within_10": bank_profile_changes[2],
            "local_refinement_max_log_likelihood_gain": refinement_gain,
            "known_local_refinement_log_likelihood_gain": known_refinement_gain,
            "within_numerical_review_limits": bool(
                bank_effect_change <= 0.05
                and bank_rho_change <= 0.06
                and max(bank_profile_changes) <= 0.5
                and max(refinement_gain, known_refinement_gain) <= 0.25
            ),
        }
        rows.append(row)
        print(json.dumps(row), flush=True)
    payload = {
        "scope": "first evaluation history across six truths; numerical diagnosis only",
        "bank_sizes": [config.bank_size, 2 * config.bank_size],
        "review_limits": {
            "bank_effect_abs_log_mle_change": 0.05,
            "bank_rho_abs_log_mle_change": 0.06,
            "bank_profile_lr_change_within_10": 0.5,
            "local_refinement_log_likelihood_gain": 0.25,
        },
        "conditions": rows,
        "timing_source_commit": run["source_commit"],
        "timing_profile_sha256": run["profile_bundle_sha256"],
        "all_within_review_limits": all(row["within_numerical_review_limits"] for row in rows),
        "limitation": "one paired history; final bootstrap intervals condition on the bank",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
