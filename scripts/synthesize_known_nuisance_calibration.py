#!/usr/bin/env python3
"""Verify frozen Goal 049 scores, then evaluate the registered paired synthesis."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from latent_landscapes.known_nuisance_synthesis import VARIANTS, write_synthesis


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary_path = args.input_dir / "run_summary.json"
    summary = json.loads(summary_path.read_text())
    config = summary["config"]
    if summary["outcome"] != "production_scores_complete" or config["mode"] != "production":
        raise ValueError("Scientific synthesis requires completed registered production")
    if tuple(summary["variant_ids"]) != VARIANTS:
        raise ValueError("Unrecognized variant ordering")
    if (
        config["calibration_replicates"],
        config["evaluation_replicates"],
        config["calibration_rank"],
    ) != (999, 1000, 950):
        raise ValueError("Replication differs from registration")
    frozen = json.loads((args.input_dir / "frozen_scores.json").read_text())
    if frozen["files"] != summary["score_file_sha256"] or frozen["truth_joined"] is not False:
        raise ValueError("Frozen score manifest and completion disagree")
    for name, digest in frozen["files"].items():
        if sha256(args.input_dir / name) != digest:
            raise ValueError(f"Frozen file changed: {name}")
    if not summary.get("paired_across_truths", False):
        raise ValueError("Receipt must certify common-random-number pairing across truths")
    effects = np.asarray(config["effects"], dtype=float)
    truths = np.asarray(config["evaluation_truths"], dtype=float)
    ids = np.load(args.input_dir / "evaluation_opaque_ids.npy", allow_pickle=False)
    sidecar = json.loads((args.input_dir / "evaluation_truth_sidecar.json").read_text())
    for t, h in enumerate(truths):
        if any(sidecar[str(identifier)] != h for identifier in ids[t]):
            raise ValueError("Evaluator sidecar disagrees with frozen IDs")
    calibration = []
    evaluation = []
    holdout = []
    for variant in VARIANTS:
        curves = np.load(args.input_dir / f"calibration_profiles_{variant}.npy", mmap_mode="r")
        if curves.shape != (181, 999, 181):
            raise ValueError("Calibration shape differs from full-grid contract")
        calibration.append(np.stack([curves[i, :, i] for i in range(len(effects))]))
        evaluation.append(np.load(args.input_dir / f"evaluation_profiles_{variant}.npy"))
        holdout.append(np.load(args.input_dir / f"evaluation_holdout_loglikelihood_{variant}.npy"))
    result = write_synthesis(
        args.output_dir,
        np.stack(calibration),
        np.stack(evaluation),
        effects,
        truths,
        list(VARIANTS),
        950,
        holdout=np.stack(holdout),
        paired_across_truths=True,
        draws=2000,
        seed=2026092003,
    )
    source = (
        Path(__file__).resolve().parents[1] / "src/latent_landscapes/known_nuisance_synthesis.py"
    )
    (args.output_dir / "receipt.json").write_text(
        json.dumps(
            {
                "input_summary_sha256": sha256(summary_path),
                "frozen_scores_sha256": sha256(args.input_dir / "frozen_scores.json"),
                "evaluation_truth_sidecar_sha256": sha256(
                    args.input_dir / "evaluation_truth_sidecar.json"
                ),
                "script_sha256": sha256(Path(__file__)),
                "synthesis_source_sha256": sha256(source),
                "outputs": {
                    p.name: sha256(p) for p in sorted(args.output_dir.iterdir()) if p.is_file()
                },
                "source_scope": "Known nuisance, fixed grid; all input score hashes verified",
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
