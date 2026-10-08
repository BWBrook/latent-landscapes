#!/usr/bin/env python3
"""Reconstruct the registered Goal 047 Stage A decision from reduced arrays."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

ALPHAS = ("025", "050", "100")
BANKS = ("half0", "half1", "combined")


def width_summary(cal: np.ndarray, drops: np.ndarray, effects: np.ndarray) -> dict:
    if cal.shape != (2, 250) or drops.shape != (2, 250, len(effects)):
        raise ValueError("Expected both designs, 250 calibration and 250 evaluation histories")
    if not np.isfinite(cal).all() or not np.isfinite(drops).all():
        raise ValueError("Nonfinite likelihood quantities")
    cutoff = np.sort(cal, axis=1)[:, 238]
    mask = drops <= cutoff[:, None, None]
    if not mask.any(axis=2).all():
        raise ValueError("Empty calibrated support")
    lower = mask.argmax(axis=2)
    upper = len(effects) - 1 - mask[:, :, ::-1].argmax(axis=2)
    components = mask[:, :, 0].astype(int) + np.sum(~mask[:, :, :-1] & mask[:, :, 1:], axis=2)
    widths = np.log(effects[upper] / effects[lower])
    covered = mask[:, :, 0].sum(axis=1)
    return dict(
        cutoff=cutoff,
        lower=lower,
        upper=upper,
        components=components,
        boundary=np.stack((mask[:, :, 0], mask[:, :, -1])),
        covered=covered,
        excluded=250 - covered,
        mean_width_contrast=float(np.mean(widths[1] - widths[0])),
    )


def compare_width(a: dict, b: dict) -> dict:
    movement = {
        "cutoff_lr": float(np.max(np.abs(a["cutoff"] - b["cutoff"]))),
        "component_changes": int(np.count_nonzero(a["components"] != b["components"])),
        "boundary_changes": int(np.count_nonzero(a["boundary"] != b["boundary"])),
        "endpoint_cells": int(max(np.max(np.abs(a[x] - b[x])) for x in ("lower", "upper"))),
        "coverage_count": int(np.max(np.abs(a["covered"] - b["covered"]))),
        "exclusion_count": int(np.max(np.abs(a["excluded"] - b["excluded"]))),
        "coverage_contrast_count": int(abs(np.diff(a["covered"])[0] - np.diff(b["covered"])[0])),
        "exclusion_contrast_count": int(abs(np.diff(a["excluded"])[0] - np.diff(b["excluded"])[0])),
        "mean_log_width_contrast": abs(a["mean_width_contrast"] - b["mean_width_contrast"]),
    }
    limits = dict(
        cutoff_lr=0.5,
        component_changes=0,
        boundary_changes=0,
        endpoint_cells=1,
        coverage_count=1,
        exclusion_count=1,
        coverage_contrast_count=1,
        exclusion_contrast_count=1,
        mean_log_width_contrast=0.01,
    )
    failed = [key for key, value in movement.items() if value > limits[key] + 1e-12]
    return dict(movement=movement, failed=failed, passed=not failed)


def tail_summary(surface: np.ndarray, rhos: np.ndarray, effects: np.ndarray) -> dict:
    if surface.shape != (3, len(rhos), len(effects)) or not np.isfinite(surface).all():
        raise ValueError("Expected three finite corridor likelihood surfaces")
    rho_raw = surface.max(axis=2)
    effect_raw = surface.max(axis=1)
    maximum = surface.max(axis=(1, 2))
    rho_index = rho_raw.argmax(axis=1)
    effect_index = effect_raw.argmax(axis=1)
    return dict(
        rho_raw=rho_raw,
        maximum=maximum,
        rho_lr=2 * (maximum[:, None] - rho_raw),
        effect_lr=2 * (maximum[:, None] - effect_raw),
        rho_mle=rhos[rho_index],
        effect_index=effect_index,
        window_inconclusive=np.any(rho_raw[:, (0, 1, len(rhos) - 1)] == maximum[:, None], axis=1),
    )


def compare_tail(a: dict, b: dict) -> dict:
    cases = []
    for case in range(3):
        movement = dict(
            effect_mle_cells=int(abs(a["effect_index"][case] - b["effect_index"][case])),
            rho_mle_log=float(abs(np.log(a["rho_mle"][case] / b["rho_mle"][case]))),
            generating_rho_lr=float(abs(a["rho_lr"][case, 0] - b["rho_lr"][case, 0])),
        )
        for kind in ("rho", "effect"):
            left, right = a[f"{kind}_lr"][case], b[f"{kind}_lr"][case]
            core = (left <= 10) | (right <= 10)
            movement[f"{kind}_core_lr"] = float(np.max(np.abs(left[core] - right[core])))
        limits = dict(
            effect_mle_cells=1,
            rho_mle_log=0.027726,
            generating_rho_lr=0.5,
            rho_core_lr=0.5,
            effect_core_lr=0.5,
        )
        failed = [key for key, value in movement.items() if value > limits[key] + 1e-12]
        cases.append(
            dict(
                effect_truth=(1, 3, 5)[case],
                movement=movement,
                failed=failed,
                passed=not failed,
                raw_profile_max_abs=float(np.max(np.abs(a["rho_raw"][case] - b["rho_raw"][case]))),
                raw_maximum_shift=float(b["maximum"][case] - a["maximum"][case]),
            )
        )
    return dict(cases=cases, passed=all(case["passed"] for case in cases))


def evaluate(arrays: dict[str, np.ndarray]) -> dict:
    effects, rhos = arrays["effects"], arrays["corridor_rhos"]
    if len(effects) != 181 or not np.allclose(effects, np.linspace(1, 10, 181), rtol=0, atol=1e-12):
        raise ValueError("Stage A requires the registered H181 grid")
    expected_rhos = (
        1.0,
        1.0570180405613805,
        1.0717734625362931,
        1.0867348625260582,
        1.1019051158766109,
        1.11728713807222,
        1.1328838852957988,
        1.148698354997035,
    )
    if not np.allclose(rhos, expected_rhos, rtol=0, atol=1e-12):
        raise ValueError("Stage A requires the registered eight rho nodes")
    widths, tails = {}, {}
    for bank, alpha in itertools.product(BANKS, ALPHAS):
        label = f"{bank}_alpha{alpha}"
        widths[label] = width_summary(
            arrays[f"connected_{label}_calibration_effect_lr"],
            arrays[f"connected_{label}_validation_effect_drops"],
            effects,
        )
        tails[label] = tail_summary(arrays[f"corridor_{label}_training_joint"], rhos, effects)

    def compare(left: str, right: str) -> dict:
        width, tail = (
            compare_width(widths[left], widths[right]),
            compare_tail(tails[left], tails[right]),
        )
        return dict(
            left=left,
            right=right,
            width=width,
            tail=tail,
            passed=width["passed"] and tail["passed"],
        )

    sensitivity = [
        compare(f"{bank}_alpha{a}", f"{bank}_alpha{b}")
        for bank in BANKS
        for a, b in itertools.combinations(ALPHAS, 2)
    ]
    same_alpha_halves = [compare(f"half0_alpha{a}", f"half1_alpha{a}") for a in ALPHAS]
    matched_weight = [
        compare(f"{half}_alpha{a}", f"combined_alpha{b}")
        for half in ("half0", "half1")
        for a, b in (("025", "050"), ("050", "100"))
    ]
    inconclusive = [label for label, result in tails.items() if result["window_inconclusive"].any()]
    failed = any(not result["passed"] for result in sensitivity)
    # A limited window cannot supply a definitive profile-based method verdict.
    status = (
        "inconclusive_window"
        if inconclusive
        else "pseudocount_sensitive"
        if failed
        else "stage_a_pass_continue_registered_stage_b"
    )
    summaries = {
        label: dict(
            cutoffs=result["cutoff"].tolist(),
            coverage_counts=result["covered"].tolist(),
            mean_log_width_contrast=result["mean_width_contrast"],
        )
        for label, result in widths.items()
    }
    return dict(
        stage="A",
        status=status,
        scientific_acceptance=False,
        same_bank_alpha_comparisons=sensitivity,
        equal_k_half_comparisons=same_alpha_halves,
        matched_relative_weight_comparisons=matched_weight,
        inconclusive_window_labels=inconclusive,
        width_summaries=summaries,
    )


def verify_run(arrays_path: Path, report_path: Path) -> dict:
    report = json.loads(report_path.read_text())
    if report.get("completion_status") != "complete":
        raise ValueError("Runner did not complete technical verification")
    errors = report.get("technical_replay_max_abs", {})
    expected = {
        f"{kind}_{bank}" for kind in ("connected", "corridor") for bank in ("half0", "combined")
    }
    if set(errors) != expected or any(
        not np.isfinite(error) or error < 0 or error > 1e-9 for error in errors.values()
    ):
        raise ValueError("Required frozen-output replay gates did not pass")
    with arrays_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != report.get("arrays_sha256"):
        raise ValueError("Runner report does not bind supplied arrays")
    with np.load(arrays_path, allow_pickle=False) as data:
        if sorted(data.files) != report.get("array_keys"):
            raise ValueError("Runner array inventory differs")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arrays", type=Path)
    parser.add_argument("--runner-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    report = verify_run(args.arrays, args.runner_report)
    with np.load(args.arrays, allow_pickle=False) as data:
        result = evaluate(dict(data))
    with args.arrays.open("rb") as stream:
        result["arrays_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    result["technical_replay_max_abs"] = report["technical_replay_max_abs"]
    result["runner_report_sha256"] = hashlib.sha256(args.runner_report.read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
