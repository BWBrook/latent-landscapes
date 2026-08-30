#!/usr/bin/env python3
"""Freeze or run the Goal 041 nested Arc 2A prospective validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.goal039 import current_git_commit
from latent_landscapes.goal041 import (
    DEFAULT_FROZEN_PREDICTIONS,
    DEFAULT_OUTPUT_DIR,
    freeze_prospective_predictions,
    load_frozen_predictions,
    production_config,
    run_goal041,
    smoke_config,
    summarize_for_cli,
    write_review_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze-predictions", action="store_true")
    mode.add_argument("--reduced-smoke", action="store_true")
    mode.add_argument("--production", action="store_true")
    parser.add_argument("--goal040-dir", type=Path)
    parser.add_argument("--frozen-predictions", type=Path, default=DEFAULT_FROZEN_PREDICTIONS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--workers", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.freeze_predictions:
            if args.goal040_dir is None:
                raise ValueError("--goal040-dir is required when freezing predictions")
            rows = freeze_prospective_predictions(
                args.goal040_dir,
                args.frozen_predictions,
            )
            print(f"Froze {len(rows)} Goal 041 predictions to {args.frozen_predictions}")
            return 0
        predictions = load_frozen_predictions(args.frozen_predictions)
        config = smoke_config() if args.reduced_smoke else production_config()
        result = run_goal041(
            config,
            predictions,
            workers=args.workers,
            source_commit=current_git_commit(),
        )
        if result.outcome == "implementation_blocked":
            raise RuntimeError(result.outcome)
        written = write_review_bundle(result, args.output_dir)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Goal 041 failed: {error}", file=sys.stderr)
        return 1
    print(summarize_for_cli(result), end="")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
