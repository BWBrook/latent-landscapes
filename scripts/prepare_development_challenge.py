"""Freeze and prepare development-panel data without starting any fits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from latent_landscapes.development_challenge_data import (
    freeze_panel_manifest,
    generate_arm_c_case,
    materialize_archived_panel,
    prepare_master_public,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze", help="freeze identities without loading outcomes")
    freeze.add_argument("--archive-root", type=Path, required=True)
    freeze.add_argument("--public-dir", type=Path, required=True)
    freeze.add_argument(
        "--banks", type=Path, required=True, help="JSON B0/A raw/compressed path maps"
    )
    freeze.add_argument("--selector-receipt", type=Path, required=True)
    freeze.add_argument("--source-root", type=Path, required=True)
    freeze.add_argument("--output", type=Path, required=True)
    archived = commands.add_parser("materialize", help="write training-only archived A/B inputs")
    archived.add_argument("--manifest", type=Path, required=True)
    archived.add_argument("--output", type=Path, required=True)
    master = commands.add_parser("master-public", help="prepare outcome-free 300-site geometry")
    master.add_argument("--manifest", type=Path, required=True)
    master.add_argument("--map-index", type=int, choices=range(3), required=True)
    master.add_argument("--source-root", type=Path, required=True)
    master.add_argument("--output", type=Path, required=True)
    generate = commands.add_parser(
        "generate-c", help="generate one training-only arm-C input and reporting evaluator"
    )
    generate.add_argument("--manifest", type=Path, required=True)
    generate.add_argument("--dataset-id", required=True)
    generate.add_argument("--public-dir", type=Path, required=True)
    generate.add_argument("--source-root", type=Path, required=True)
    generate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "freeze":
        bank_paths = json.loads(args.banks.read_text())
        banks = {
            role: {key: Path(value) for key, value in spec.items()}
            for role, spec in bank_paths.items()
        }
        result = freeze_panel_manifest(
            args.archive_root,
            args.public_dir,
            banks,
            args.selector_receipt,
            args.output,
            source_root=args.source_root,
        )
    elif args.command == "materialize":
        result = materialize_archived_panel(args.manifest, args.output)
    elif args.command == "master-public":
        result = prepare_master_public(
            args.manifest, args.map_index, args.output, source_root=args.source_root
        )
    else:
        result = generate_arm_c_case(
            args.manifest,
            args.dataset_id,
            args.public_dir,
            args.output,
            source_root=args.source_root,
        )
    print(
        json.dumps(
            {
                "state": result["state"],
                "output": str(args.output),
                "datasets": len(result.get("datasets", [])),
            }
        )
    )


if __name__ == "__main__":
    main()
