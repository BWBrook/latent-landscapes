#!/usr/bin/env python3
"""Freeze, qualify, or run the Goal 058 effect-reference micro pilot."""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from latent_landscapes import preinvasion_effect_reference as effect


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("freeze", "qualify", "run"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--freeze", type=Path)
    p.add_argument("--qualification", type=Path)
    p.add_argument("--bank-directory", type=Path, default=Path("/data/codex/scratch/goal045-full-bank-reference128-20260907-e8c08f1/bank_cache"))
    p.add_argument("--root", type=int, default=effect.ROOT_SEED)
    p.add_argument("--workers", type=int, default=1)
    args = p.parse_args()
    if args.mode == "freeze":
        if args.output.exists():
            raise FileExistsError("refusing to replace freeze")
        args.output.mkdir(parents=True)
        ledger = effect.seed_ledger(root=args.root)
        np.savez_compressed(args.output / "seed_ledger.npz", ledger=ledger)
        meta = effect.validate_seed_ledger(ledger, root=args.root)
        meta["schema_version"] = effect.SCHEMA_VERSION
        meta["full_grid_size"] = len(effect.full_grid_metadata())
        meta["full_grid"] = effect.full_grid_metadata()
        (args.output / "freeze.json").write_text(json.dumps(meta, sort_keys=True) + "\n", encoding="utf-8")
        return 0
    if args.mode == "qualify":
        effect.qualify(args.output, bank_directory=args.bank_directory)
        return 0
    if args.freeze is None or args.qualification is None:
        raise ValueError("run requires --freeze and --qualification")
    if not (args.freeze / "freeze.json").exists():
        raise FileNotFoundError("freeze metadata is missing")
    qualification = json.loads((args.qualification / "qualification.json").read_text(encoding="utf-8"))
    if qualification.get("status") != "qualified":
        raise ValueError("qualification is not successful")
    if args.output.exists():
        raise FileExistsError("refusing to resume or replace an existing run")
    with np.load(args.freeze / "seed_ledger.npz", allow_pickle=False) as z:
        ledger = z["ledger"]
    metadata = json.loads((args.freeze / "freeze.json").read_text(encoding="utf-8"))
    effect.validate_seed_ledger(ledger, root=args.root, expected_hash=metadata["sha256"])
    effect.run_reference_micro(
        args.output,
        bank_directory=args.bank_directory,
        root=args.root,
        workers=args.workers,
        frozen_ledger=ledger,
        freeze_metadata=metadata,
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
