#!/usr/bin/env python3
"""Run the Goal 013 weak-contrast sampling-design intervention."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from latent_landscapes.goal013 import artifacts, benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--goal009-evidence-dir",
        type=Path,
        help="Authenticated Goal 009 scientific-pack directory.",
    )
    parser.add_argument(
        "--goal012-evidence-dir",
        type=Path,
        help="Authenticated Goal 012 review-pack directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Goal 013 review-pack output directory.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        help="Production worker count; the frozen campaign requires exactly 4.",
    )
    parser.add_argument(
        "--compute-provenance-json",
        type=Path,
        help="Portable compute-provenance JSON object for production.",
    )
    parser.add_argument(
        "--reduced-smoke",
        action="store_true",
        help="Run the fixed local non-scientific reduced configuration.",
    )
    return parser.parse_args()


def _load_json_object(path: Path) -> dict[str, object]:
    def reject_nonfinite(value: str) -> None:
        raise ValueError(f"non-finite JSON token: {value}")

    payload = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_nonfinite,
    )
    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        raise ValueError("compute provenance must be a JSON object")
    return payload


def _reduced_inputs(
    args: argparse.Namespace,
) -> tuple[benchmark.Goal013Config, int, dict[str, object]]:
    if args.output_dir is None:
        raise ValueError("reduced smoke requires explicit --output-dir")
    if any(
        value is not None
        for value in (
            args.goal009_evidence_dir,
            args.goal012_evidence_dir,
            args.workers,
            args.compute_provenance_json,
        )
    ):
        raise ValueError("reduced smoke accepts only --output-dir and --reduced-smoke")
    provenance: dict[str, object] = {
        "provenance_mode": "test",
        "run_id": "goal013-reduced-smoke",
        "host_id": "local-test-host",
    }
    return benchmark.smoke_config(), 1, provenance


def _production_inputs(
    args: argparse.Namespace,
) -> tuple[
    benchmark.Goal013Config,
    int,
    dict[str, object],
    Path,
    Path,
]:
    missing = [
        option
        for option, value in (
            ("--goal009-evidence-dir", args.goal009_evidence_dir),
            ("--goal012-evidence-dir", args.goal012_evidence_dir),
            ("--output-dir", args.output_dir),
            ("--workers", args.workers),
            ("--compute-provenance-json", args.compute_provenance_json),
        )
        if value is None
    ]
    if missing:
        raise ValueError("production campaign requires explicit " + ", ".join(missing))
    if args.workers != 4:
        raise ValueError("production campaign requires exactly --workers 4")
    assert args.compute_provenance_json is not None
    assert args.goal009_evidence_dir is not None
    assert args.goal012_evidence_dir is not None
    provenance = _load_json_object(args.compute_provenance_json)
    return (
        benchmark.DEFAULT_CONFIG,
        4,
        provenance,
        args.goal009_evidence_dir,
        args.goal012_evidence_dir,
    )


def main() -> int:
    args = parse_args()
    try:
        if args.reduced_smoke:
            config, workers, provenance = _reduced_inputs(args)
            artifacts.validate_pre_campaign_provenance(
                provenance,
                workers=workers,
            )
            result = benchmark.run_campaign(config, workers=workers)
        else:
            (
                config,
                workers,
                provenance,
                goal009_evidence_dir,
                goal012_evidence_dir,
            ) = _production_inputs(args)
            artifacts.validate_pre_campaign_provenance(
                provenance,
                workers=workers,
            )
            result = benchmark.run_campaign(
                config,
                workers=workers,
                goal009_evidence_dir=goal009_evidence_dir,
                goal012_evidence_dir=goal012_evidence_dir,
            )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(
            f"Goal 013 campaign did not start or complete: {error}; no review pack was accepted.",
            file=sys.stderr,
        )
        return 1
    if result.outcome == "implementation_blocked":
        print(
            "Goal 013 completed with implementation_blocked; no review pack was written.",
            file=sys.stderr,
        )
        return 1
    assert args.output_dir is not None
    try:
        written = artifacts.write_review_bundle(
            result,
            args.output_dir,
            provenance,
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(
            f"Goal 013 review pack failed validation: {error}; "
            "no accepted scientific claim was made.",
            file=sys.stderr,
        )
        return 1
    mode = "reduced smoke" if args.reduced_smoke else "production campaign"
    print(f"Goal 013 {mode} complete")
    print(f"Outcome: {result.outcome}")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
