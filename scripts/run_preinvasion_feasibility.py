"""Run one named qualification or the registered open Goal 056 panel."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from latent_landscapes.preinvasion_campaign import write_json
from latent_landscapes.preinvasion_execution import qualify, run_panel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("qualify", "panel"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bank-directory", type=Path)
    parser.add_argument("--qualification", type=Path)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    try:
        if args.phase == "qualify":
            if args.bank_directory is None:
                parser.error("qualify requires --bank-directory")
            result = qualify(repository, args.bank_directory, args.output)
            print(
                json.dumps(
                    {"passed": result["passed"], "elapsed_seconds": result["elapsed_seconds"]}
                )
            )
            if not result["passed"]:
                raise SystemExit(1)
        else:
            if args.qualification is None:
                parser.error("panel requires --qualification")
            result = run_panel(repository, args.qualification, args.output, workers=args.workers)
            print(
                json.dumps(
                    {"status": result["status"], "elapsed_seconds": result["elapsed_seconds"]}
                )
            )
            if result["status"] != "panel_completed_pending_scientific_audit":
                raise SystemExit(2)
    except Exception as error:
        # Refusal to overwrite an old attempt must not itself alter that attempt.
        if not isinstance(error, FileExistsError):
            write_json(
                args.output / "failed.json",
                {
                    "phase": args.phase,
                    "created_utc": datetime.now(UTC).isoformat(),
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            )
        raise


if __name__ == "__main__":
    main()
