"""Generate disjoint arrival rows and derive independently compressed A/B/AB banks."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path
from typing import Any

import numpy as np

from latent_landscapes import capstone_public as cap
from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.goal007.benchmark import FixedInputs

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = ("public_inputs.json", "public_inputs.npz", "exposure.npz", "seed_ledger.json")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _identities(paths: list[Path]) -> dict[str, str]:
    return {str(path.resolve()): _sha(path) for path in paths}


def _verify(identities: dict[str, str]) -> None:
    for name, expected in identities.items():
        if _sha(Path(name)) != expected:
            raise ValueError(f"identity changed: {name}")


def _source_identities() -> dict[str, str]:
    return _identities([Path(__file__), *sorted((ROOT / "src/latent_landscapes").rglob("*.py"))])


def _write(path: Path, value: Any) -> None:
    cap._write_json(path, value)


def row_seeds(root: int, row_start: int, bank_size: int) -> np.ndarray:
    if root < 0 or row_start < 0 or bank_size < 1:
        raise ValueError("root and row_start must be nonnegative, bank_size positive")
    return np.asarray(
        [
            cap._u64_seed(root, cap.BANK_STAGE, row)
            for row in range(row_start, row_start + bank_size)
        ],
        dtype=np.uint64,
    )


def load_arrival_inputs(input_dir: Path) -> tuple[FixedInputs, dict[str, Any]]:
    metadata = json.loads((input_dir / "public_inputs.json").read_text())
    root = metadata.get("root")
    attempt = metadata.get("attempt")
    if (
        metadata.get("schema_version") != "goal059-public-v1"
        or metadata.get("state") != "qualified"
        or metadata.get("namespace") != cap.NAMESPACE
        or type(root) is not int
        or root < 0
        or type(attempt) is not int
        or not 0 <= attempt < 100
    ):
        raise ValueError("invalid qualified public metadata or seed namespace")
    _verify(
        {
            str(input_dir / name): metadata[key]
            for name, key in (
                ("public_inputs.npz", "public_inputs_sha256"),
                ("exposure.npz", "exposure_sha256"),
                ("seed_ledger.json", "seed_ledger_sha256"),
            )
        }
    )
    ledger = json.loads((input_dir / "seed_ledger.json").read_text())
    candidates = ledger.get("candidates", [])
    if (
        ledger.get("root") != root
        or ledger.get("namespace") != cap.NAMESPACE
        or ledger.get("map_stage") != cap.MAP_STAGE
        or ledger.get("sampling_stage") != cap.SAMPLING_STAGE
        or not isinstance(candidates, list)
        or not attempt < len(candidates) <= 100
    ):
        raise ValueError("public seed ledger metadata mismatch")
    for index, candidate in enumerate(candidates):
        expected = {
            "attempt": index,
            "map_seed": cap._u64_seed(root, cap.MAP_STAGE, index),
            "sampling_seed": cap._u64_seed(root, cap.SAMPLING_STAGE, index),
        }
        if candidate != expected:
            raise ValueError("public seed ledger violates the frozen seed rule")
    accepted = candidates[attempt]
    if any(metadata.get(key) != value for key, value in accepted.items()):
        raise ValueError("accepted public seeds disagree with the seed ledger")
    fixed = cap._make_fixed(metadata["map_seed"], metadata["sampling_seed"])
    if cap._array_hashes(fixed) != metadata["array_sha256"]:
        raise ValueError("public fixed-array hash mismatch")
    expected_arrays = cap._fixed_arrays(fixed)
    with np.load(input_dir / "public_inputs.npz", allow_pickle=False) as frozen:
        if set(frozen.files) != set(expected_arrays):
            raise ValueError("public fixed-array keys mismatch")
        for name, expected_array in expected_arrays.items():
            actual = frozen[name]
            if (
                actual.dtype != expected_array.dtype
                or actual.shape != expected_array.shape
                or not np.array_equal(actual, expected_array)
            ):
                raise ValueError(f"public fixed-array identity mismatch: {name}")
    return fixed, metadata


def generate_bank(
    input_dir: Path,
    output_dir: Path,
    *,
    row_start: int,
    bank_size: int,
    workers: int = 1,
    chunk_size: int = 256,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError("refusing to replace arrival-bank output; resume is not supported")
    if not 1 <= workers <= 32 or chunk_size < 1 or row_start < 0 or bank_size < 1:
        raise ValueError("invalid generation dimensions or worker count")
    inputs = _identities([input_dir / name for name in PUBLIC_FILES])
    sources = _source_identities()
    fixed, metadata = load_arrival_inputs(input_dir)
    _verify(inputs)
    root = int(metadata["root"])
    site_ids = tuple(sorted(site.site_id for site in fixed.design.sites))
    seeds = row_seeds(root, row_start, bank_size)
    if len(np.unique(seeds)) != bank_size:
        raise ValueError("seed collision within requested row addresses")
    output_dir.mkdir(parents=True)
    np.savez_compressed(
        output_dir / "seed_ledger.npz",
        row_addresses=np.arange(row_start, row_start + bank_size, dtype=np.uint64),
        seeds=seeds,
        root=np.uint64(root),
        namespace=np.uint64(cap.NAMESPACE),
        stage=np.uint64(cap.BANK_STAGE),
    )
    started = {
        "schema": "profile-sensitivity-bank-v1",
        "root": root,
        "row_start": row_start,
        "row_stop_exclusive": row_start + bank_size,
        "bank_size": bank_size,
        "site_ids": list(site_ids),
        "seed_rule": "SeedSequence([root,59,3,row]).generate_state(1,dtype=uint64)[0]",
        "workers": workers,
        "chunk_size": chunk_size,
        "source_sha256": sources,
        "input_sha256": inputs,
        "ledger_sha256": _sha(output_dir / "seed_ledger.npz"),
        "seed_array_sha256": cap._array_sha(seeds),
        "resume_supported": False,
        "public_input_loader": "arrival-only-frozen-v1",
        "exposure_used_for_arrivals": False,
    }
    _write(output_dir / "started.json", started)
    arrivals = np.lib.format.open_memmap(
        output_dir / "arrivals.npy",
        mode="w+",
        dtype=np.float64,
        shape=(bank_size, len(site_ids)),
    )
    tasks = [
        (offset, tuple(int(seed) for seed in seeds[offset : offset + chunk_size]))
        for offset in range(0, bank_size, chunk_size)
    ]
    receipts: list[dict[str, Any]] = []
    began = time.perf_counter()

    def retain(task: tuple[int, tuple[int, ...]], result: tuple[int, np.ndarray, str]) -> None:
        offset, values, checksum = result
        if offset != task[0] or values.shape != (len(task[1]), len(site_ids)):
            raise ValueError("bank chunk address or shape mismatch")
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError("bank chunk has invalid arrivals")
        if cap._array_sha(values) != checksum:
            raise ValueError("bank chunk checksum mismatch")
        path = output_dir / f"chunk-{offset:08d}.npz"
        np.savez_compressed(
            path,
            offset=np.int64(offset),
            row_start=np.int64(row_start + offset),
            seeds=np.asarray(task[1], dtype=np.uint64),
            arrivals=values,
        )
        arrivals[offset : offset + len(values)] = values
        arrivals.flush()
        receipts.append(
            {
                "offset": offset,
                "row_start": row_start + offset,
                "rows": len(values),
                "array_sha256": checksum,
                "seed_sha256": cap._array_sha(np.asarray(task[1], dtype=np.uint64)),
                "path": path.name,
                "file_sha256": _sha(path),
            }
        )
        _write(
            output_dir / "progress.json",
            {
                "completed_rows": sum(row["rows"] for row in receipts),
                "elapsed_seconds": time.perf_counter() - began,
                "chunks": sorted(receipts, key=lambda row: row["offset"]),
            },
        )

    try:
        if workers == 1:
            cap._bank_init(fixed)
            for task in tasks:
                retain(task, cap._bank_chunk(task))
        else:
            with ProcessPoolExecutor(
                max_workers=workers,
                mp_context=multiprocessing.get_context("spawn"),
                initializer=cap._bank_init,
                initargs=(fixed,),
            ) as pool:
                iterator = iter(tasks)
                pending = {
                    pool.submit(cap._bank_chunk, task): task
                    for task in [next(iterator, None) for _ in range(workers)]
                    if task is not None
                }
                while pending:
                    done, _ = wait(pending, return_when=FIRST_COMPLETED)
                    for future in done:
                        task = pending.pop(future)
                        retain(task, future.result())
                        next_task = next(iterator, None)
                        if next_task is not None:
                            pending[pool.submit(cap._bank_chunk, next_task)] = next_task
        _verify(inputs)
        _verify(sources)
        manifest = {
            **started,
            "state": "complete",
            "array_shape": list(arrivals.shape),
            "array_sha256": cap._array_sha(arrivals),
            "arrivals_file_sha256": _sha(output_dir / "arrivals.npy"),
            "started_sha256": _sha(output_dir / "started.json"),
            "chunks": sorted(receipts, key=lambda row: row["offset"]),
            "elapsed_seconds": time.perf_counter() - began,
        }
        _write(output_dir / "manifest.json", manifest)
        return manifest
    except Exception as error:
        _write(
            output_dir / "failure.json",
            {
                "error_type": type(error).__name__,
                "error": str(error),
                "completed_rows": sum(row["rows"] for row in receipts),
            },
        )
        raise


def derive_banks(bank_dir: Path, output_dir: Path, *, half_size: int) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError("refusing to replace derived-bank output")
    manifest_path = bank_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("state") != "complete" or manifest["bank_size"] != 2 * half_size:
        raise ValueError("derivation requires one completed bank of exactly twice half_size")
    if half_size < 1:
        raise ValueError("half_size must be positive")
    _verify(
        {
            str(bank_dir / "arrivals.npy"): manifest["arrivals_file_sha256"],
            str(bank_dir / "seed_ledger.npz"): manifest["ledger_sha256"],
        }
    )
    raw = np.load(bank_dir / "arrivals.npy", mmap_mode="r", allow_pickle=False)
    ids = tuple(manifest["site_ids"])
    if raw.shape != (2 * half_size, len(ids)) or cap._array_sha(raw) != manifest["array_sha256"]:
        raise ValueError("raw bank shape or checksum mismatch")
    sources = _source_identities()
    inputs = _identities([manifest_path, bank_dir / "arrivals.npy", bank_dir / "seed_ledger.npz"])
    output_dir.mkdir(parents=True)
    products = {}
    for name, lower, upper in (
        ("A", 0, half_size),
        ("B", half_size, 2 * half_size),
        ("AB", 0, 2 * half_size),
    ):
        path = output_dir / name
        path.mkdir()
        values = np.asarray(raw[lower:upper])
        bank = likelihood.compress_bank(values, ids, series_order=192)
        np.save(path / "arrivals.npy", values)
        np.savez_compressed(
            path / "compressed.npz",
            site_ids=np.asarray(ids),
            bank_size=bank.bank_size,
            category_counts=bank.category_counts,
            category_mass=bank.category_mass,
            power_moments=bank.power_moments,
            bank_checksum=bank.bank_checksum,
            series_order=192,
            max_x=40.0,
        )
        products[name] = {
            "bank_size": bank.bank_size,
            "row_start": manifest["row_start"] + lower,
            "row_stop_exclusive": manifest["row_start"] + upper,
            "site_ids": list(ids),
            "bank_checksum": bank.bank_checksum,
            "raw_path": str((path / "arrivals.npy").resolve()),
            "raw_sha256": _sha(path / "arrivals.npy"),
            "compressed_path": str((path / "compressed.npz").resolve()),
            "compressed_sha256": _sha(path / "compressed.npz"),
            "series_order": 192,
            "max_x": 40.0,
            "pseudo_arrivals_per_category": 1,
            "normalization_denominator": bank.bank_size + 7,
        }
        _write(path / "manifest.json", products[name])
        _write(output_dir / "progress.json", {"completed_products": list(products)})
    _verify(inputs)
    _verify(sources)
    result = {
        "schema": "profile-sensitivity-derived-banks-v1",
        "state": "complete",
        "source_sha256": sources,
        "input_sha256": inputs,
        "products": products,
    }
    _write(output_dir / "manifest.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate")
    generate.add_argument("--input-dir", type=Path, required=True)
    generate.add_argument("--output-dir", type=Path, required=True)
    generate.add_argument("--row-start", type=int, required=True)
    generate.add_argument("--bank-size", type=int, required=True)
    generate.add_argument("--workers", type=int, default=1)
    generate.add_argument("--chunk-size", type=int, default=256)
    derive = commands.add_parser("derive")
    derive.add_argument("--bank-dir", type=Path, required=True)
    derive.add_argument("--output-dir", type=Path, required=True)
    derive.add_argument("--half-size", type=int, required=True)
    args = parser.parse_args()
    if args.command == "generate":
        result = generate_bank(
            args.input_dir,
            args.output_dir,
            row_start=args.row_start,
            bank_size=args.bank_size,
            workers=args.workers,
            chunk_size=args.chunk_size,
        )
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in (
                        "state",
                        "row_start",
                        "row_stop_exclusive",
                        "bank_size",
                        "elapsed_seconds",
                    )
                }
            )
        )
    else:
        result = derive_banks(args.bank_dir, args.output_dir, half_size=args.half_size)
        print(json.dumps({"state": result["state"], "products": list(result["products"])}))


if __name__ == "__main__":
    main()
