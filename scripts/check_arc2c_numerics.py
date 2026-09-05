#!/usr/bin/env python3
"""Check all four timing histories against a doubled bank and local grid refinement."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

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
from latent_landscapes.arc2c_synthesis import load_campaign_bundle
from latent_landscapes.goal011.benchmark import build_fixed_inputs

FloatArray = NDArray[np.float64]


def local_effect_grid(grid: FloatArray, index: int) -> tuple[float, ...]:
    """Retain the known-speed MLE and its adjacent effect half-steps."""
    values = {float(grid[index])}
    for neighbour in (index - 1, index + 1):
        if 0 <= neighbour < len(grid):
            values.add(float((grid[index] + grid[neighbour]) / 2))
    return tuple(sorted(values))


def profile_change(old: FloatArray, new: FloatArray, *, new_maximum: float | None = None) -> float:
    """Compare LR at common nodes in the union of the two near-support regions."""
    old_drop = 2 * (old.max() - old)
    new_drop = 2 * ((new.max() if new_maximum is None else new_maximum) - new)
    near_support = (old_drop <= 10) | (new_drop <= 10)
    return float(np.max(np.abs(new_drop[near_support] - old_drop[near_support])))


def refined_rho_grid(
    grid: FloatArray, old: FloatArray, doubled: FloatArray, truths: tuple[float, ...]
) -> tuple[float, ...]:
    """Refine supported original nodes and neighbours without bridging separate windows."""
    old_rho, doubled_rho = old.max(axis=-1), doubled.max(axis=-1)
    old_drop = 2 * (old_rho.max(axis=-1, keepdims=True) - old_rho)
    doubled_drop = 2 * (doubled_rho.max(axis=-1, keepdims=True) - doubled_rho)
    support = ((old_drop <= 10) | (doubled_drop <= 10)).reshape(-1, len(grid)).any(axis=0)
    selected = set(map(int, np.flatnonzero(support)))
    for index in tuple(selected):
        selected.update(
            neighbour for neighbour in (index - 1, index + 1) if 0 <= neighbour < len(grid)
        )
    selected.update(int(np.flatnonzero(grid == truth)[0]) for truth in truths)
    values = {float(grid[index]) for index in selected}
    values.update(
        float(np.sqrt(grid[index] * grid[index + 1])) for index in selected if index + 1 in selected
    )
    return tuple(sorted(values))


def merge_midpoints(
    rhos: FloatArray, baseline: FloatArray, fine_rhos: FloatArray, refined: FloatArray
) -> tuple[FloatArray, FloatArray]:
    """Preserve every baseline row and insert only the newly evaluated midpoints."""
    inserted = ~np.isin(fine_rhos, rhos)
    merged_rhos = np.concatenate((rhos, fine_rhos[inserted]))
    order = np.argsort(merged_rhos)
    merged = np.concatenate((baseline, refined[..., inserted, :]), axis=-2)
    return merged_rhos[order], merged[..., order, :]


def rho_mle_within_original_interval(grid: FloatArray, old_index: int, new_rho: float) -> bool:
    return bool(grid[max(0, old_index - 1)] <= new_rho <= grid[min(len(grid) - 1, old_index + 1)])


def truth_lrs(joint: FloatArray, true_rho: int, true_effect: int) -> FloatArray:
    known = joint[true_rho]
    return np.asarray(
        (
            2 * (known.max() - known[true_effect]),
            2 * (joint.max() - joint[:, true_effect].max()),
            2 * (joint.max() - joint[true_rho].max()),
        ),
        dtype=np.float64,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timing-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = timing_config()
    bundle = load_campaign_bundle(args.timing_dir)
    run = bundle.run_summary
    bank = np.load(args.timing_dir / "base_arrivals.npy", allow_pickle=False)
    if (
        bundle.config != config
        or run["mode"] != "timing"
        or run["bank_checksum"] != hashlib.sha256(bank.tobytes(order="C")).hexdigest()
        or run["profile_bundle_sha256"] != bundle.profile_sha256
        or not all(run["invariants"].values())
    ):
        raise ValueError("canary requires the complete frozen timing bank and profiles")
    seeds = spawn_seed_manifest(replace(config, bank_size=2 * config.bank_size))
    fixed = build_fixed_inputs()
    history_seeds = (*seeds.calibration[:2], *seeds.validation[:2])
    histories = tuple(paired_histories(fixed, seed) for seed in history_seeds)
    sites = tuple(row.site_id for row in histories[0][0])
    if bank.shape != (config.bank_size, len(sites)) or not np.isfinite(bank).all():
        raise ValueError("timing bank has invalid dimensions or nonfinite arrivals")
    # Axes are timing history (calibration 0/1, validation 0/1), case, rho, effect.
    reference = np.concatenate(
        (bundle.profiles["calibration_train_joint"], bundle.profiles["validation_train_joint"]),
        axis=1,
    ).swapaxes(0, 1)
    print("Generating the second half of the nested 8192-draw bank", flush=True)
    extra = arc2b._generate_bank(fixed, seeds.bank_seeds[config.bank_size :])
    integration = build_joint_integration(
        np.concatenate((bank, extra)), sites, config.rhos, config.effects
    )
    doubled = np.stack(
        [
            np.stack([evaluate_dataset(records, integration)[0] for records in block])
            for block in histories
        ]
    )
    del integration, extra
    print("Doubled-bank surfaces ready for all four histories", flush=True)
    rhos, effects = np.asarray(config.rhos), np.asarray(config.effects)
    fine_rhos = np.asarray(
        refined_rho_grid(rhos, reference, doubled, tuple(truth.rho for truth in TRUTHS))
    )
    refined_integration = build_joint_integration(bank, sites, tuple(fine_rhos), config.effects)
    refined_subset = np.stack(
        [
            np.stack([evaluate_dataset(records, refined_integration)[0] for records in block])
            for block in histories
        ]
    )
    del refined_integration
    retained = np.isin(fine_rhos, rhos)
    if not np.allclose(
        refined_subset[..., retained, :],
        reference[..., np.searchsorted(rhos, fine_rhos[retained]), :],
        rtol=0.0,
        atol=1e-9,
    ):
        raise ValueError("replayed timing histories disagree at retained candidate nodes")
    merged_rhos, refined = merge_midpoints(rhos, reference, fine_rhos, refined_subset)
    common = np.searchsorted(merged_rhos, rhos)
    rows: list[dict[str, Any]] = []
    known_effect_canaries: dict[str, FloatArray] = {}
    for history_index, (seed, block) in enumerate(zip(history_seeds, histories, strict=True)):
        for case_index, (truth, records) in enumerate(zip(TRUTHS, block, strict=True)):
            baseline = reference[history_index, case_index]
            doubled_joint = doubled[history_index, case_index]
            refined_joint = refined[history_index, case_index]
            true_rho = config.rhos.index(truth.rho)
            true_effect = config.effects.index(truth.effect)
            old_r, old_h = np.unravel_index(np.argmax(baseline), baseline.shape)
            new_r, new_h = np.unravel_index(np.argmax(doubled_joint), doubled_joint.shape)
            old_known = int(np.argmax(baseline[true_rho]))
            new_known = int(np.argmax(doubled_joint[true_rho]))
            bank_effect_change = float(
                max(
                    abs(np.log(effects[new_h] / effects[old_h])),
                    abs(np.log(effects[new_known] / effects[old_known])),
                )
            )
            bank_rho_change = float(abs(np.log(rhos[new_r] / rhos[old_r])))
            bank_profile_changes = (
                profile_change(baseline[true_rho], doubled_joint[true_rho]),
                profile_change(baseline.max(axis=0), doubled_joint.max(axis=0)),
                profile_change(baseline.max(axis=1), doubled_joint.max(axis=1)),
            )
            bank_truth_change = np.abs(
                truth_lrs(baseline, true_rho, true_effect)
                - truth_lrs(doubled_joint, true_rho, true_effect)
            )
            refined_true_rho = int(common[true_rho])
            grid_truth_change = np.abs(
                truth_lrs(baseline, true_rho, true_effect)
                - truth_lrs(refined_joint, refined_true_rho, true_effect)
            )
            grid_effect_change = profile_change(baseline.max(axis=0), refined_joint.max(axis=0))
            grid_rho_change = profile_change(
                baseline.max(axis=1),
                refined_joint[common].max(axis=1),
                new_maximum=float(refined_joint.max()),
            )
            refinement_gain = float(refined_joint.max() - baseline.max())
            refined_r = int(np.argmax(refined_joint.max(axis=1)))
            rho_within_interval = rho_mle_within_original_interval(
                rhos, int(old_r), float(merged_rhos[refined_r])
            )
            fine_effects = local_effect_grid(effects, old_known)
            known_integration = build_joint_integration(bank, sites, (truth.rho,), fine_effects)
            known_joint = evaluate_dataset(records, known_integration)[0]
            known_refinement_gain = float(max(0.0, known_joint.max() - baseline[true_rho].max()))
            key = f"{seed.phase}_{seed.index}_{truth.condition_id}"
            known_effect_canaries[f"{key}_effects"] = np.asarray(fine_effects)
            known_effect_canaries[f"{key}_known_joint"] = known_joint
            row = {
                "phase": seed.phase,
                "dataset_index": seed.index,
                "condition_id": truth.condition_id,
                "bank_effect_max_abs_log_mle_change": bank_effect_change,
                "bank_rho_abs_log_mle_change": bank_rho_change,
                "bank_known_effect_profile_lr_change_within_10": bank_profile_changes[0],
                "bank_estimated_effect_profile_lr_change_within_10": bank_profile_changes[1],
                "bank_spread_profile_lr_change_within_10": bank_profile_changes[2],
                "bank_truth_lr_changes": dict(
                    zip(
                        ("known_effect", "estimated_effect", "spread"),
                        bank_truth_change.tolist(),
                        strict=True,
                    )
                ),
                "grid_estimated_effect_profile_lr_change_within_10": grid_effect_change,
                "grid_spread_profile_lr_change_within_10": grid_rho_change,
                "grid_truth_lr_changes": dict(
                    zip(
                        ("known_effect", "estimated_effect", "spread"),
                        grid_truth_change.tolist(),
                        strict=True,
                    )
                ),
                "local_refinement_max_log_likelihood_gain": refinement_gain,
                "grid_rho_abs_log_mle_change": float(
                    abs(np.log(merged_rhos[refined_r] / rhos[old_r]))
                ),
                "grid_rho_mle_within_one_original_interval": rho_within_interval,
                "known_local_refinement_log_likelihood_gain": known_refinement_gain,
                "within_numerical_review_limits": bool(
                    bank_effect_change <= 0.05
                    and bank_rho_change <= 0.06
                    and max(bank_profile_changes) <= 0.5
                    and bank_truth_change.max() <= 0.5
                    and max(grid_effect_change, grid_rho_change, grid_truth_change.max()) <= 0.5
                    and max(refinement_gain, known_refinement_gain) <= 0.25
                    and rho_within_interval
                ),
            }
            rows.append(row)
            print(json.dumps(row), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    profile_path = args.output.with_suffix(".npz")
    np.savez_compressed(
        profile_path,
        allow_pickle=False,
        rhos=rhos,
        refined_rhos=merged_rhos,
        refinement_subset_rhos=fine_rhos,
        effects=effects,
        phases=np.asarray([seed.phase for seed in history_seeds]),
        dataset_indices=np.asarray([seed.index for seed in history_seeds]),
        condition_ids=np.asarray([truth.condition_id for truth in TRUTHS]),
        current_joint=reference,
        doubled_joint=doubled,
        refined_joint=refined,
        **known_effect_canaries,
    )
    payload = {
        "scope": (
            "first two calibration and first two evaluation histories across six truths; "
            "numerical diagnosis only"
        ),
        "bank_sizes": [config.bank_size, 2 * config.bank_size],
        "review_limits": {
            "bank_effect_abs_log_mle_change": 0.05,
            "bank_rho_abs_log_mle_change": 0.06,
            "profile_lr_change_on_union_within_10": 0.5,
            "truth_lr_change": 0.5,
            "local_refinement_log_likelihood_gain": 0.25,
            "grid_rho_mle_movement_original_intervals": 1,
        },
        "conditions": rows,
        "timing_source_commit": run["source_commit"],
        "timing_profile_sha256": bundle.profile_sha256,
        "canary_profiles": profile_path.name,
        "canary_profile_sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
        "all_within_review_limits": all(row["within_numerical_review_limits"] for row in rows),
        "limitation": "four paired histories; final bootstrap intervals condition on the bank",
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
