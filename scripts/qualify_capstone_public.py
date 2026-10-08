#!/usr/bin/env python3
"""Run the bounded, preregistered Goal 059 numerical qualification."""

from __future__ import annotations

import argparse
from pathlib import Path

from latent_landscapes.capstone_qualification import generate_public_panel, qualify, run_panel


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--public-inputs-dir", "--public-inputs", dest="public_inputs_dir", type=Path, required=True
    )
    parser.add_argument("--bank-dir", dest="bank_dir", type=Path)
    parser.add_argument("--qualification-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--panel-dir",
        type=Path,
        help="released observations directory; when supplied, run the 8-history panel",
    )
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--generate-panel", type=Path)
    parser.add_argument("--root", type=int)
    args = parser.parse_args()
    if args.generate_panel is not None:
        if args.qualification_dir is None or args.root is None:
            parser.error("--generate-panel requires --qualification-dir and --root")
        generate_public_panel(
            args.public_inputs_dir,
            args.qualification_dir,
            args.generate_panel,
            root=args.root,
        )
    elif args.panel_dir is None:
        if args.bank_dir is None:
            parser.error("qualification requires --bank-dir")
        qualify(args.public_inputs_dir, args.bank_dir, args.output, workers=args.workers)
    else:
        if args.bank_dir is None:
            parser.error("panel analysis requires --bank-dir")
        run_panel(
            args.public_inputs_dir,
            args.bank_dir,
            args.panel_dir,
            args.output,
            workers=args.workers,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
