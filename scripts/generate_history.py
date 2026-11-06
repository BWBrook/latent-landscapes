"""Generate one biological history on a prepared Sprint 1 map for one monitoring arm.

``--map-dir`` is ``artifacts/sprint1/maps/<role>/<archetype>-<i>`` from
``prepare_experiment_maps.py``.  The history address keys every random stream, so the
same address on the same map gives the same biology under any background or arm.
Analyst arrays (``observations.npz``) and evaluator arrays (``evaluator.npz``, with
``receipt.json`` holding truth, seeds and hashes) are written separately.

``--build-bank`` instead builds the independent arrival bank for the map (raw
``arrivals.npy`` and ``compressed.npz``), the wrapper that
``prepare_development_banks.py`` cannot provide for the new maps.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import fields
from pathlib import Path
from typing import Any

import numpy as np

from latent_landscapes import capstone_public as cap
from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.background_family import (
    BACKGROUNDS,
    FamilySurfaces,
    family_stream_seeds,
    generate_family_history,
)
from latent_landscapes.development_challenge_data import (
    PREY_TIMES,
    sha256,
    training_observation_arrays,
)
from latent_landscapes.goal001.design import Cluster, DesignSite, EligibleCentre, SamplingDesign
from latent_landscapes.goal001.landscape import Landscape
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.misspecification_generator import GeneratorSetup, build_field_sampler
from latent_landscapes.preinvasion_campaign import OpenTruth

ROOT_SEED = 2026110501
BANK_NAMESPACE = 4
MAP_FILES = ("public_inputs.npz", "exposure.npz", "surfaces.npz", "design.json", "record.json")
ARM_SITES = {"A": 120, "B": 120, "C": 260}
CHUNK = 256


def _npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as source:
        return {name: source[name] for name in source.files}


def load_map(
    map_dir: Path,
) -> tuple[FixedInputs, GeneratorSetup, FamilySurfaces, dict[str, Any], dict[str, np.ndarray]]:
    record = json.loads((map_dir / "record.json").read_text())
    if record.get("status") != "ok":
        raise ValueError(f"map is not a completed map: {map_dir}")
    public, exposure = _npz(map_dir / "public_inputs.npz"), _npz(map_dir / "exposure.npz")
    surfaces = _npz(map_dir / "surfaces.npz")
    design = json.loads((map_dir / "design.json").read_text())
    landscape = Landscape(**{field.name: public[field.name] for field in fields(Landscape)})
    sampling = SamplingDesign(
        public["access_network"],
        tuple(EligibleCentre(**row) for row in design["eligible_centres"]),
        tuple(Cluster(**row) for row in design["clusters"]),
        tuple(DesignSite(**row) for row in design["sites"]),
    )
    fixed = FixedInputs(landscape, sampling, {"prepared_map_loaded": True})
    setup = GeneratorSetup(
        tuple(map(str, public["site_ids"])),
        public["site_rows"],
        public["site_cols"],
        tuple(map(str, public["site_splits"])),
        tuple(map(str, public["site_clusters"])),
        exposure["accepted_mask"],
        exposure["map_a"],
        record["unreachable_tie_count"],
        record["unreachable_tie_exposure_score"],
        build_field_sampler(landscape.shape),
    )
    family_surfaces = FamilySurfaces(surfaces["T"], surfaces["W"], record["surface_diagnostics"])
    return fixed, setup, family_surfaces, record, public


def arm_arrays(
    full: dict[str, np.ndarray],
    public: dict[str, np.ndarray],
    record: dict[str, Any],
    arm: str,
) -> dict[str, np.ndarray]:
    """Analyst arrays for one arm; A and B restrict training to the 120 baseline sites."""
    ids = np.asarray(public["site_ids"]).astype(str)
    baseline = set(record["baseline_site_ids"])
    view = dict(public)
    if arm in ("A", "B"):
        view["site_splits"] = np.where(np.isin(ids, list(baseline)), "training", "holdout")
    mask = np.asarray(view["site_splits"]).astype(str) == "training"
    source = {**full, "site_ids": ids, "training_mask": mask}
    arrays = training_observation_arrays(
        source,
        view,
        arm=arm,
        baseline_site_ids=record["baseline_site_ids"] if arm == "C" else None,
    )
    chosen = set(map(str, arrays["site_ids"]))
    if len(chosen) != ARM_SITES[arm] or chosen & set(record["holdout_site_ids"]):
        raise ValueError("arm site count or holdout separation violated")
    if arm == "C":
        network = arrays["predator_observed"].any(axis=1)
        if chosen != set(record["c_site_ids"]) or int(network.sum()) != len(baseline):
            raise ValueError("C training or predator-network sites do not match the design")
    elif chosen != baseline:
        raise ValueError("A/B training sites differ from the baseline design")
    if arm != "A" and arrays["prey_observed"][:, np.asarray(PREY_TIMES) <= 0].any():
        raise ValueError("prey observed at or before day 0 outside arm A")
    return arrays


def parse_address(text: str) -> tuple[int, ...]:
    address = tuple(int(part) for part in text.split(","))
    if not address:
        raise ValueError("address must hold at least one integer")
    return address


def generate(args: argparse.Namespace) -> dict[str, Any]:
    if args.background not in BACKGROUNDS:
        raise ValueError(f"unknown background {args.background!r}")
    fixed, setup, surfaces, record, public = load_map(args.map_dir)
    address = parse_address(args.address)
    seeds = {"address": list(address), "streams": family_stream_seeds(address)}
    truth = OpenTruth(
        index=0, effect=args.h, mean_hazard=args.mu, beta=0.0, detection_sd=args.detection_sd
    )
    observations, evaluator = generate_family_history(
        fixed, setup, truth, seeds, args.background, surfaces
    )
    full = {key: observations[key] for key in ("prey_counts", "predator_counts")}
    analyst = arm_arrays(full, public, record, args.arm)
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    np.savez_compressed(args.output_dir / "observations.npz", **analyst)  # type: ignore[arg-type]
    arrays = {key: value for key, value in evaluator.items() if isinstance(value, np.ndarray)}
    np.savez_compressed(args.output_dir / "evaluator.npz", **arrays)  # type: ignore[arg-type]
    receipt = {
        "schema": "sprint1-history-v1",
        "map_dir": str(args.map_dir.resolve()),
        "map": {k: record[k] for k in ("role", "archetype", "map_index", "seeds")},
        "arm": args.arm,
        "training_site_count": len(analyst["site_ids"]),
        "address": list(address),
        "seeds": seeds,
        "background": args.background,
        "truth": {
            "h": args.h,
            "mu": args.mu,
            "detection_sd": args.detection_sd,
            "trend_gamma": evaluator["trend_gamma"],
            "opaque_id": observations["opaque_id"],
        },
        "files": {
            name: sha256(args.output_dir / name) for name in ("observations.npz", "evaluator.npz")
        },
        "file_roles": {
            "analyst": ["observations.npz"],
            "reporting_only": ["evaluator.npz", "receipt.json"],
        },
        "map_input_sha256": {name: sha256(args.map_dir / name) for name in MAP_FILES},
    }
    (args.output_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    return receipt


def bank_seeds(record: dict[str, Any], count: int, replicate: int) -> np.ndarray:
    if count < 1 or replicate < 0:
        raise ValueError("bank size must be positive and replicate nonnegative")
    key = [ROOT_SEED, BANK_NAMESPACE, *record["spawn_key"], replicate]
    return np.array(
        [
            int(np.random.SeedSequence([*key, row]).generate_state(1, dtype=np.uint64)[0])
            for row in range(count)
        ],
        dtype=np.uint64,
    )


def verify_independent_banks(left_path: Path, right_path: Path) -> None:
    left, right = (json.loads(p.read_text()) for p in (left_path, right_path))
    if left["map_input_sha256"] != right["map_input_sha256"]:
        raise ValueError("bank comparison requires the identical map inputs")
    if left["bank_size"] != right["bank_size"]:
        raise ValueError("independent bank comparison requires equal bank sizes")
    if left["series_order"] != 192 or right["series_order"] != 192:
        raise ValueError("independent banks must use the frozen series order 192")
    if left["bank_replicate"] == right["bank_replicate"]:
        raise ValueError("bank comparison repeats the same replicate")
    seeds = []
    for bank in (left, right):
        if bank["schema"] != "sprint2-map-arrival-bank-v1":
            raise ValueError("bank does not have the frozen replicate identity")
        current = bank_seeds(bank["map"], bank["bank_size"], bank["bank_replicate"])
        if hashlib.sha256(current.astype("<u8").tobytes()).hexdigest() != bank["seed_sha256"]:
            raise ValueError("bank seed identity does not reconstruct")
        for key in ("raw", "compressed"):
            if sha256(Path(bank[key])) != bank[f"{key}_sha256"]:
                raise ValueError("bank file hash differs from its manifest")
        seeds.append(current)
    if np.intersect1d(*seeds).size:
        raise ValueError("independent banks share simulation seeds")
    if any(left[f"{key}_sha256"] == right[f"{key}_sha256"] for key in ("raw", "compressed")):
        raise ValueError("independent bank comparison has identical payloads")


def build_bank(args: argparse.Namespace) -> dict[str, Any]:
    fixed, setup, _surfaces, record, _public = load_map(args.map_dir)
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    ids = tuple(setup.site_ids)
    seeds = bank_seeds(record, args.bank_size, args.bank_replicate)
    if len(np.unique(seeds)) != len(seeds):
        raise ValueError("bank seed collision")
    arrivals = np.lib.format.open_memmap(
        args.output_dir / "arrivals.npy",
        mode="w+",
        dtype=np.float64,
        shape=(args.bank_size, len(ids)),
    )
    tasks = [
        (offset, tuple(int(s) for s in seeds[offset : offset + CHUNK]))
        for offset in range(0, args.bank_size, CHUNK)
    ]
    began = time.perf_counter()
    with ProcessPoolExecutor(
        max_workers=args.workers,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=cap._bank_init,
        initargs=(fixed,),
    ) as pool:
        futures = {pool.submit(cap._bank_chunk, task): task for task in tasks}
        for future in as_completed(futures):
            offset, values, checksum = future.result()
            if (
                values.shape != (len(futures[future][1]), len(ids))
                or cap._array_sha(values) != checksum
            ):
                raise ValueError("arrival chunk shape or checksum mismatch")
            if not np.isfinite(values).all() or (values < 0).any():
                raise ValueError("invalid arrival chunk")
            arrivals[offset : offset + len(values)] = values
    arrivals.flush()
    bank = likelihood.compress_bank(arrivals, ids, series_order=192)
    np.savez_compressed(
        args.output_dir / "compressed.npz",
        site_ids=np.asarray(ids),
        bank_size=bank.bank_size,
        category_counts=bank.category_counts,
        category_mass=bank.category_mass,
        power_moments=bank.power_moments,
        bank_checksum=bank.bank_checksum,
        series_order=192,
    )
    manifest = {
        "schema": "sprint2-map-arrival-bank-v1",
        "map_dir": str(args.map_dir.resolve()),
        "map": {k: record[k] for k in ("role", "archetype", "map_index", "spawn_key")},
        "bank_size": args.bank_size,
        "series_order": 192,
        "bank_replicate": args.bank_replicate,
        "seed_sha256": hashlib.sha256(seeds.astype("<u8").tobytes()).hexdigest(),
        "site_ids_sha256": hashlib.sha256("\n".join(ids).encode()).hexdigest(),
        "seed_rule": f"SeedSequence([{ROOT_SEED}, {BANK_NAMESPACE}, *spawn_key, replicate, row])",
        "elapsed_seconds": time.perf_counter() - began,
        "workers": args.workers,
        "raw_sha256": sha256(args.output_dir / "arrivals.npy"),
        "compressed_sha256": sha256(args.output_dir / "compressed.npz"),
        "raw": str((args.output_dir / "arrivals.npy").resolve()),
        "compressed": str((args.output_dir / "compressed.npz").resolve()),
        "map_input_sha256": {name: sha256(args.map_dir / name) for name in MAP_FILES},
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--build-bank", action="store_true")
    parser.add_argument("--bank-size", type=int, default=131072)
    parser.add_argument("--bank-replicate", type=int)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--address")
    parser.add_argument("--background", choices=sorted(BACKGROUNDS))
    parser.add_argument("--mu", type=float)
    parser.add_argument("--h", type=float)
    parser.add_argument("--detection-sd", type=float, default=0.2)
    parser.add_argument("--arm", choices=sorted(ARM_SITES))
    args = parser.parse_args()
    if args.build_bank:
        if args.bank_replicate is None:
            parser.error("bank generation requires an explicit --bank-replicate")
        manifest = build_bank(args)
        print(
            json.dumps({"bank_size": manifest["bank_size"], "seconds": manifest["elapsed_seconds"]})
        )
        return 0
    missing = [n for n in ("address", "background", "mu", "h", "arm") if getattr(args, n) is None]
    if missing:
        parser.error(f"history generation requires: {', '.join(missing)}")
    receipt = generate(args)
    print(
        json.dumps(
            {"opaque_id": receipt["truth"]["opaque_id"], "sites": receipt["training_site_count"]}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
