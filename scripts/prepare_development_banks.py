"""Generate independent arrival banks on the frozen arm-C public geometries."""

from __future__ import annotations

import argparse
import json
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np

from latent_landscapes import capstone_public as cap
from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.development_challenge_data import (
    C_NAMESPACE,
    C_ROOT,
    load_master_public,
    sha256,
)

ROOT = Path(__file__).resolve().parents[1]
ROLE_SIZE = 131072


def seeds_for_map(map_index: int, start: int, count: int) -> np.ndarray:
    if map_index not in range(3) or start < 0 or count < 1:
        raise ValueError("invalid bank seed address")
    return np.array(
        [
            int(
                np.random.SeedSequence([C_ROOT, C_NAMESPACE, 2, map_index, row]).generate_state(
                    1, dtype=np.uint64
                )[0]
            )
            for row in range(start, start + count)
        ],
        dtype=np.uint64,
    )


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def generate(
    public_dir: Path,
    output: Path,
    *,
    manifest: Path,
    source_root: Path,
    role: str,
    bank_size: int,
    workers: int,
) -> dict[str, Any]:
    if role not in {"B0", "A"} or workers < 1 or not 1 <= bank_size <= ROLE_SIZE:
        raise ValueError("invalid bank settings")
    if output.exists():
        raise FileExistsError(output)
    public = load_master_public(public_dir, expected_manifest=manifest, source_root=source_root)
    ids = tuple(sorted(site.site_id for site in public.fixed.design.sites))
    start = 0 if role == "B0" else ROLE_SIZE
    seeds = seeds_for_map(public.metadata["map_index"], start, bank_size)
    all_seeds = np.concatenate(
        [
            seeds_for_map(public.metadata["map_index"], offset, bank_size)
            for offset in (0, ROLE_SIZE)
        ]
    )
    if len(np.unique(all_seeds)) != len(all_seeds):
        raise ValueError("bank seed collision")
    paths = [
        Path(__file__),
        manifest,
        *sorted((ROOT / "src/latent_landscapes").rglob("*.py")),
        *(
            public_dir / name
            for name in ("public_inputs.json", "public_inputs.npz", "exposure.npz", "design.json")
        ),
    ]
    identities = {str(p.resolve()): sha256(p) for p in paths}
    output.mkdir(parents=True)
    np.savez_compressed(
        output / "seed_ledger.npz", row_addresses=np.arange(start, start + bank_size), seeds=seeds
    )
    started = {
        "schema": "development-master-arrival-bank-v1",
        "role": role,
        "map_index": public.metadata["map_index"],
        "archetype": public.metadata["archetype"],
        "bank_size": bank_size,
        "site_ids": ids,
        "row_start": start,
        "row_stop_exclusive": start + bank_size,
        "source_input_sha256": identities,
        "seed_rule": (
            "SeedSequence([2026110107,711,2,map_index,row]).generate_state(1,dtype=uint64)[0]"
        ),
        "seed_ledger_sha256": sha256(output / "seed_ledger.npz"),
        "workers": workers,
    }
    write(output / "started.json", started)
    arrivals = np.lib.format.open_memmap(
        output / "arrivals.npy", mode="w+", dtype=np.float64, shape=(bank_size, len(ids))
    )
    chunk_size = 256
    tasks = [
        (offset, tuple(map(int, seeds[offset : offset + chunk_size])))
        for offset in range(0, bank_size, chunk_size)
    ]
    began = time.perf_counter()
    completed = 0
    chunks: list[dict[str, Any]] = []
    try:
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=multiprocessing.get_context("spawn"),
            initializer=cap._bank_init,
            initargs=(public.fixed,),
        ) as pool:
            futures = {pool.submit(cap._bank_chunk, task): task for task in tasks}
            for future in as_completed(futures):
                offset, values, checksum = future.result()
                task = futures[future]
                if offset != task[0] or values.shape != (len(task[1]), len(ids)):
                    raise ValueError("arrival chunk shape/address mismatch")
                if (
                    not np.isfinite(values).all()
                    or (values < 0).any()
                    or cap._array_sha(values) != checksum
                ):
                    raise ValueError("invalid arrival chunk")
                arrivals[offset : offset + len(values)] = values
                arrivals.flush()
                completed += len(values)
                chunks.append({"offset": offset, "rows": len(values), "array_sha256": checksum})
                write(
                    output / "progress.json",
                    {"completed_rows": completed, "elapsed_seconds": time.perf_counter() - began},
                )
        bank = likelihood.compress_bank(arrivals, ids, series_order=192)
        np.savez_compressed(
            output / "compressed.npz",
            site_ids=np.asarray(ids),
            bank_size=bank.bank_size,
            category_counts=bank.category_counts,
            category_mass=bank.category_mass,
            power_moments=bank.power_moments,
            bank_checksum=bank.bank_checksum,
            series_order=192,
        )
        for path, expected in identities.items():
            if sha256(Path(path)) != expected:
                raise RuntimeError(f"source/input drift: {path}")
        result = {
            **started,
            "state": "complete",
            "elapsed_seconds": time.perf_counter() - began,
            "raw": str((output / "arrivals.npy").resolve()),
            "compressed": str((output / "compressed.npz").resolve()),
            "raw_sha256": sha256(output / "arrivals.npy"),
            "compressed_sha256": sha256(output / "compressed.npz"),
            "raw_array_sha256": cap._array_sha(arrivals),
            "chunks": sorted(chunks, key=lambda x: x["offset"]),
        }
        write(output / "manifest.json", result)
        return result
    except Exception as error:
        write(
            output / "failure.json",
            {"completed_rows": completed, "type": type(error).__name__, "message": str(error)},
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--role", choices=("B0", "A"), required=True)
    parser.add_argument("--bank-size", type=int, default=131072)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    result = generate(
        args.public_dir,
        args.output_dir,
        manifest=args.manifest,
        source_root=args.source_root,
        role=args.role,
        bank_size=args.bank_size,
        workers=args.workers,
    )
    print(json.dumps({"state": result["state"], "seconds": result["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
