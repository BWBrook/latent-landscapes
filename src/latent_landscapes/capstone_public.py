"""Goal 059 public capstone inputs, histories, and arrival-bank construction."""

from __future__ import annotations

import hashlib
import json
import math
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes import preinvasion_campaign as pre_campaign
from latent_landscapes.arc3_design import build_sampling_pair, sampling_checks
from latent_landscapes.arc3_landscapes import build_landscape, describe_landscape
from latent_landscapes.goal001.spread import passable_edges
from latent_landscapes.goal006.spread import compute_contrast_spread, sample_edge_shock_vector
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.misspecification_generator import build_generator_setup

ROOT_SEED = 2026100403
NAMESPACE = 59
MAP_STAGE = 1
SAMPLING_STAGE = 2
BANK_STAGE = 3
BANK_SIZE = 131072
CHUNK_SIZE = 256
STREAM_NAMES = (*pre_campaign.STREAM_NAMES, "background_field")
PREY_TIMES = pre_campaign.PREY_TIMES
PREDATOR_TIMES = pre_campaign.PREDATOR_TIMES


@dataclass(frozen=True, slots=True)
class GeneralTruth:
    index: int
    effect: float
    mean_hazard: float
    beta: float
    detection_sd: float
    background: str = "exact"


@dataclass(frozen=True, slots=True)
class PublicInputs:
    fixed: FixedInputs
    setup: Any
    metadata: dict[str, Any]


def _u64_seed(root: int, stage: int, index: int, *, namespace: int = NAMESPACE) -> int:
    return int(
        np.random.SeedSequence([root, namespace, stage, index]).generate_state(1, dtype=np.uint64)[
            0
        ]
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _array_sha(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, allow_nan=False, indent=2) + "\n")
    temporary.replace(path)


def _make_fixed(map_seed: int, sampling_seed: int) -> FixedInputs:
    landscape = build_landscape("connected", map_seed)
    design, _balanced = build_sampling_pair(landscape, sampling_seed)
    counts = {
        split: sum(site.split == split for site in design.sites)
        for split in ("training", "holdout")
    }
    checks = sampling_checks(landscape, (design, _balanced))
    invariants = {
        "landscape_shape": landscape.shape == (72, 84),
        "landscape_counts": int(landscape.passable.sum()) == 5225
        and int((~landscape.passable).sum()) == 823,
        "graph_edge_count": len(passable_edges(landscape)) > 0,
        "site_count": len(design.sites) == 160,
        "training_sites": counts["training"] == 120,
        "holdout_sites": counts["holdout"] == 40,
        "cluster_count": len(design.clusters) == 32,
        "cluster_isolation": all(
            len({s.split for s in design.sites if s.cluster_id == c.cluster_id}) == 1
            for c in design.clusters
        ),
        **{f"sampling_{key}": value for key, value in checks.items()},
    }
    if not all(invariants.values()):
        raise ValueError("public map/design structural invariants failed")
    return FixedInputs(landscape, design, invariants)


def _fixed_arrays(fixed: FixedInputs) -> dict[str, np.ndarray]:
    landscape = fixed.landscape
    sites = tuple(sorted(fixed.design.sites, key=lambda x: x.site_id))
    return {
        "passable": landscape.passable,
        "source_reachable": landscape.source_reachable,
        "habitat_class": landscape.habitat_class,
        "quality": landscape.quality,
        "patch_id": landscape.patch_id,
        "corridor_id": landscape.corridor_id,
        "source_zone": landscape.source_zone,
        "water_neighbor_count": landscape.water_neighbor_count,
        "access_network": fixed.design.network,
        "site_ids": np.asarray([s.site_id for s in sites]),
        "site_rows": np.asarray([s.row for s in sites], dtype=np.int64),
        "site_cols": np.asarray([s.col for s in sites], dtype=np.int64),
        "site_splits": np.asarray([s.split for s in sites], dtype="U16"),
        "site_clusters": np.asarray([s.cluster_id for s in sites], dtype="U32"),
        "site_strata": np.asarray([s.stratum_index for s in sites], dtype=np.int64),
        "site_center_rows": np.asarray([s.center_row for s in sites], dtype=np.int64),
        "site_center_cols": np.asarray([s.center_col for s in sites], dtype=np.int64),
    }


def _array_hashes(fixed: FixedInputs) -> dict[str, str]:
    return {name: _array_sha(value) for name, value in _fixed_arrays(fixed).items()}


def freeze_public_inputs(output: Path, *, root: int, attempts: int = 100) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("refusing to replace frozen public inputs")
    if type(root) is not int or root < 0 or not 1 <= attempts <= 100:
        raise ValueError("invalid root or structural attempt bound")
    output.mkdir(parents=True)
    ledger = [
        {
            "attempt": attempt,
            "map_seed": _u64_seed(root, MAP_STAGE, attempt),
            "sampling_seed": _u64_seed(root, SAMPLING_STAGE, attempt),
        }
        for attempt in range(attempts)
    ]
    _write_json(
        output / "seed_ledger.json",
        {
            "root": root,
            "namespace": NAMESPACE,
            "map_stage": MAP_STAGE,
            "sampling_stage": SAMPLING_STAGE,
            "candidates": ledger,
        },
    )
    failures: list[dict[str, Any]] = []
    for candidate in ledger:
        map_seed, sampling_seed = candidate["map_seed"], candidate["sampling_seed"]
        try:
            fixed = _make_fixed(map_seed, sampling_seed)
        except (ValueError, RuntimeError) as error:
            failures.append({**candidate, "error_type": type(error).__name__, "error": str(error)})
            _write_json(output / "failed_attempts.json", failures)
            continue
        # Persist structural acceptance and the actual map/design before any
        # exposure/field/certificate operation. Numerical failure is terminal.
        np.savez_compressed(output / "public_inputs.npz", **_fixed_arrays(fixed))  # type: ignore[arg-type]
        metadata = {
            "schema_version": "goal059-public-v1",
            "root": root,
            "namespace": NAMESPACE,
            **candidate,
            "state": "structurally_frozen",
            "array_sha256": _array_hashes(fixed),
            "invariants": fixed.invariants,
            "landscape_description": describe_landscape(fixed.landscape),
            "failed_attempts": failures,
            "seed_ledger_sha256": _sha(output / "seed_ledger.json"),
            "public_inputs_sha256": _sha(output / "public_inputs.npz"),
        }
        _write_json(output / "accepted_candidate.json", metadata)
        _write_json(output / "failed_attempts.json", failures)
        try:
            setup = build_generator_setup(fixed)
            site_a = setup.exposure_score[setup.site_rows, setup.site_cols]
            np.savez_compressed(
                output / "exposure.npz",
                map_a=setup.exposure_score,
                site_a=site_a,
                accepted_mask=setup.accepted_mask,
            )
            certificate = pre_campaign.hazard_box_certificate(setup.exposure_score, site_a)
            field = setup.field_sampler
            metadata.update(
                hazard_certificate=certificate,
                exposure_sha256=_sha(output / "exposure.npz"),
                map_a_sha256=_array_sha(setup.exposure_score),
                site_a_sha256=_array_sha(site_a),
                field_checks={
                    "field_shape": list(field.field_shape),
                    "embedding_shape": list(field.embedding_shape),
                    "minimum_eigenvalue": field.minimum_eigenvalue,
                    "reconstruction_max_abs_error": field.reconstruction_max_abs_error,
                },
            )
            if (
                not certificate["passes"]
                or field.field_shape != (72, 84)
                or field.embedding_shape != (142, 166)
                or field.minimum_eigenvalue <= 0
                or field.reconstruction_max_abs_error > 1e-12
            ):
                raise RuntimeError("accepted public map failed hazard or fixed-field certificate")
        except Exception as error:
            metadata.update(
                state="qualification_failed", error_type=type(error).__name__, error=str(error)
            )
            _write_json(output / "public_inputs.json", metadata)
            raise
        metadata["state"] = "qualified"
        _write_json(output / "public_inputs.json", metadata)
        return metadata
    _write_json(output / "failed_attempts.json", failures)
    raise RuntimeError("no public map attempt passed")


def load_public_inputs(path: Path) -> PublicInputs:
    metadata = json.loads((path / "public_inputs.json").read_text(encoding="utf-8"))
    if metadata.get("state") != "qualified":
        raise ValueError("public map numerical qualification did not pass")
    fixed = _make_fixed(int(metadata["map_seed"]), int(metadata["sampling_seed"]))
    setup = build_generator_setup(fixed)
    expected = metadata["array_sha256"]
    actual = _array_hashes(fixed)
    if actual != expected:
        raise ValueError("public input array hash mismatch")
    if _sha(path / "public_inputs.npz") != metadata["public_inputs_sha256"]:
        raise ValueError("public input artifact hash mismatch")
    if (
        _sha(path / "exposure.npz") != metadata["exposure_sha256"]
        or _array_sha(setup.exposure_score) != metadata["map_a_sha256"]
        or _array_sha(setup.exposure_score[setup.site_rows, setup.site_cols])
        != metadata["site_a_sha256"]
        or _sha(path / "seed_ledger.json") != metadata["seed_ledger_sha256"]
    ):
        raise ValueError("public exposure or seed ledger identity mismatch")
    return PublicInputs(fixed, setup, metadata)


def generate_exact_history(
    fixed: FixedInputs, setup: Any, truth: GeneralTruth, seeds: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    if truth.background != "exact":
        raise ValueError("generate_exact_history requires background='exact'")
    open_truth = pre_campaign.OpenTruth(
        truth.index, truth.effect, truth.mean_hazard, truth.beta, truth.detection_sd
    )
    return pre_campaign.generate_open_history(fixed, setup, open_truth, seeds)


def _b100_hazard(setup: Any, rng: np.random.Generator, mean_hazard: float) -> NDArray[np.float64]:
    gaussian = setup.field_sampler.sample(rng)
    if not np.asarray(setup.accepted_mask).all():
        raise ValueError("capstone normalization requires every map cell")
    z = 0.7 * setup.exposure_score + math.sqrt(0.51) * gaussian
    sigma = math.sqrt(math.log(2.0))
    raw = np.exp(sigma * z)
    return np.asarray(mean_hazard * raw / float(raw.mean()), dtype=np.float64)


def generate_b100_history(
    fixed: FixedInputs, setup: Any, truth: GeneralTruth, seeds: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    if truth.background != "B100-A":
        raise ValueError("generate_b100_history requires background='B100-A'")
    streams = seeds["streams"]
    spread = compute_contrast_spread(
        fixed.landscape,
        1.0,
        edge_shocks=sample_edge_shock_vector(
            fixed.landscape, np.random.default_rng(streams["spread"])
        ),
        rho=1.0,
    )
    arrivals = np.asarray(spread.arrival[setup.site_rows, setup.site_cols], dtype=np.float64)
    hazards_map = _b100_hazard(
        setup, np.random.default_rng(streams["background_field"]), truth.mean_hazard
    )
    site_hazard = hazards_map[setup.site_rows, setup.site_cols]
    thresholds = np.random.default_rng(streams["prey_loss"]).exponential(size=len(site_hazard))
    losses = pre_campaign.loss_times(arrivals, site_hazard, truth.effect, thresholds)
    if truth.detection_sd == 0:
        detection = np.full(len(site_hazard), 0.65)
    else:
        concentration = 0.65 * 0.35 / truth.detection_sd**2 - 1.0
        if concentration <= 0:
            raise ValueError("detection dispersion is outside the Beta domain")
        detection = np.random.default_rng(streams["site_detection"]).beta(
            0.65 * concentration, 0.35 * concentration, size=len(site_hazard)
        )
    predator_alive = arrivals[:, None] <= PREDATOR_TIMES[None, :]
    prey_alive = losses[:, None] > PREY_TIMES[None, :]
    predator = (
        (
            np.random.default_rng(streams["predator_visits"]).random(
                (len(site_hazard), len(PREDATOR_TIMES), 2)
            )
            < 0.65
        ).sum(axis=2)
        * predator_alive
    ).astype(np.int8)
    prey = (
        (
            np.random.default_rng(streams["prey_visits"]).random(
                (len(site_hazard), len(PREY_TIMES), 2)
            )
            < detection[:, None, None]
        ).sum(axis=2)
        * prey_alive
    ).astype(np.int8)
    observations = {"index": truth.index, "predator_counts": predator, "prey_counts": prey}
    evaluator = {
        "truth": asdict(truth),
        "seeds": seeds,
        "arrival": arrivals,
        "loss": losses,
        "site_hazard": site_hazard,
        "map_hazard": hazards_map,
        "site_detection": detection,
        "prey_alive": prey_alive,
    }
    return observations, evaluator


_BANK_FIXED: FixedInputs | None = None


def _bank_init(fixed: FixedInputs) -> None:
    global _BANK_FIXED
    _BANK_FIXED = fixed


def _bank_chunk(task: tuple[int, tuple[int, ...]]) -> tuple[int, np.ndarray, str]:
    if _BANK_FIXED is None:
        raise RuntimeError("bank worker not initialized")
    offset, seeds = task
    values = np.asarray(arc2b._generate_bank(_BANK_FIXED, seeds), dtype=np.float64)
    return offset, values, _array_sha(values)


def build_arrival_bank(
    public: PublicInputs,
    output: Path,
    *,
    root: int,
    workers: int = 1,
    bank_size: int = BANK_SIZE,
    chunk_size: int = CHUNK_SIZE,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("refusing to replace arrival bank")
    if workers < 1 or workers > 32 or bank_size < 1 or chunk_size < 1:
        raise ValueError("invalid bank execution bounds")
    if root != public.metadata["root"]:
        raise ValueError("bank root must match public input root")
    output.mkdir(parents=True)
    site_ids = tuple(sorted(public.setup.site_ids))
    seeds = tuple(_u64_seed(root, BANK_STAGE, index) for index in range(bank_size))
    ledger = np.asarray(seeds, dtype=np.uint64)
    np.savez_compressed(
        output / "seed_ledger.npz",
        seeds=ledger,
        root=np.uint64(root),
        namespace=np.uint64(NAMESPACE),
        stage=np.uint64(BANK_STAGE),
    )
    started_receipt = {
        "schema_version": "goal059-arrival-bank-v1",
        "root": root,
        "namespace": NAMESPACE,
        "stage": BANK_STAGE,
        "bank_size": bank_size,
        "site_ids": list(site_ids),
        "ledger_sha256": _array_sha(ledger),
        "ledger_file_sha256": _sha(output / "seed_ledger.npz"),
        "public_input_array_sha256": _array_hashes(public.fixed),
        "map_a_sha256": _array_sha(public.setup.exposure_score),
        "workers": workers,
        "chunk_size": chunk_size,
        "seed_rule": "SeedSequence([root,59,3,row]).generate_state(1,dtype=uint64)[0]",
    }
    _write_json(output / "started.json", started_receipt)
    arrivals = np.empty((bank_size, len(site_ids)), dtype=np.float64)
    tasks = [
        (offset, seeds[offset : offset + chunk_size]) for offset in range(0, bank_size, chunk_size)
    ]
    receipts: list[dict[str, Any]] = []
    started = time.perf_counter()
    with ProcessPoolExecutor(
        max_workers=workers, initializer=_bank_init, initargs=(public.fixed,)
    ) as pool:
        iterator = iter(tasks)
        pending = {
            pool.submit(_bank_chunk, task): task
            for task in [next(iterator, None) for _ in range(workers)]
            if task is not None
        }
        while pending:
            done, _pending_left = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                task = pending.pop(future)
                try:
                    offset, values, checksum = future.result()
                    if offset != task[0] or values.shape != (len(task[1]), len(site_ids)):
                        raise ValueError("bank chunk address or shape mismatch")
                    if not np.isfinite(values).all() or (values < 0).any():
                        np.savez_compressed(
                            output / f"invalid-chunk-{offset:08d}.npz", arrivals=values
                        )
                        raise ValueError("bank chunk has invalid arrivals")
                except Exception as error:
                    _write_json(
                        output / "failed_chunk.json",
                        {
                            "offset": task[0],
                            "rows": len(task[1]),
                            "error": str(error),
                            "completed_chunks": receipts,
                        },
                    )
                    for remaining in pending:
                        remaining.cancel()
                    raise
                arrivals[offset : offset + len(values)] = values
                chunk_path = output / f"chunk-{offset:08d}.npz"
                np.savez_compressed(
                    chunk_path,
                    offset=np.int64(offset),
                    seeds=np.asarray(task[1], dtype=np.uint64),
                    arrivals=values,
                )
                receipts.append(
                    {
                        "offset": offset,
                        "rows": len(values),
                        "seed_sha256": _array_sha(np.asarray(task[1], dtype=np.uint64)),
                        "chunk_sha256": checksum,
                        "file_sha256": _sha(chunk_path),
                    }
                )
                _write_json(
                    output / "progress.json",
                    {
                        "completed_rows": sum(r["rows"] for r in receipts),
                        "elapsed_seconds": time.perf_counter() - started,
                        "chunks": sorted(receipts, key=lambda x: x["offset"]),
                    },
                )
                next_task = next(iterator, None)
                if next_task is not None:
                    pending[pool.submit(_bank_chunk, next_task)] = next_task
    if not np.isfinite(arrivals).all() or (arrivals < 0).any():
        raise RuntimeError("arrival bank contains invalid values")
    np.save(output / "arrivals.npy", arrivals)
    manifest = {
        **started_receipt,
        "array_shape": list(arrivals.shape),
        "array_sha256": _array_sha(arrivals),
        "arrivals_file_sha256": _sha(output / "arrivals.npy"),
        "started_receipt_sha256": _sha(output / "started.json"),
        "chunks": sorted(receipts, key=lambda x: x["offset"]),
        "elapsed_seconds": time.perf_counter() - started,
    }
    _write_json(output / "manifest.json", manifest)
    return manifest
