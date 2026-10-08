"""Fixed six-cell prospective comparison with authenticated shared beta rows."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np

from latent_landscapes import adjusted_background_likelihood as likelihood
from latent_landscapes import arc2b_campaign as prey
from latent_landscapes import arc2c_likelihood as joint
from latent_landscapes import known_nuisance_calibration as legacy
from latent_landscapes import misspecification_generator as old_generator
from latent_landscapes import model_adequacy_campaign as adequacy
from latent_landscapes import prospective_background_generator as generator
from latent_landscapes.adjusted_background_pilot import BETAS, EFFECTS, sha256
from latent_landscapes.goal011 import benchmark

REGISTRATION = Path("docs/goals/053-prospective-background/registration-2026-09-27.md")
PILOT_CONTRACT = "b5d0374987d1b4ace007a8e8d7af8bb3a6317f5fd82024b5a8779c8b644ff365"
PILOT_EVIDENCE = "d923a768ae60f542ac1f001da1cc7477d30861f30eb23d5e5bcd70e0421027b5"
TIMING_BETAS = (-2, -1.75, -1.5, -1.25, -1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.6, 0.75, 1, 1.5, 2)
TIMING_INDICES = tuple(int(np.argmin(np.abs(np.asarray(BETAS) - b))) for b in TIMING_BETAS)
SCORE_NAMES = ("latent_training", "latent_holdout_joint", "oracle_training", "oracle_holdout")
TOLERANCE = 1e-10
ASSEMBLY_ALLOWANCE_SECONDS = 2_400
AUDIT_ONLY_ROOT = 2026092799
OBSERVATION_KEYS = (
    "effects",
    "betas",
    "cell_ids",
    "replicate_indices",
    "truth_h",
    "truth_beta",
    "opaque_ids",
    "site_ids",
    "site_cluster_ids",
    "site_splits",
    "training_mask",
    "site_A",
    "map_A",
    "true_arrival",
    "true_extirpation",
    "true_hazards",
    "predator_counts",
    "prey_counts",
    "oracle_history_indices",
)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def worker_identity() -> dict[str, str]:
    """Return the execution identity that timing qualification binds."""

    return {
        "host": platform.node(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "numpy": np.__version__,
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    encoded = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with temp.open("w", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(path)
    _fsync_directory(path.parent)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def source_hashes(repository: Path) -> dict[str, str]:
    paths = [
        *sorted((repository / "src").rglob("*.py")),
        *sorted((repository / "tests").glob("test_prospective_background*.py")),
        repository / "scripts/run_prospective_background.py",
        repository / "scripts/synthesize_prospective_background.py",
        repository / REGISTRATION,
        repository / "pyproject.toml",
        repository / "uv.lock",
    ]
    return {str(p.relative_to(repository)): sha256(p) for p in paths}


def read_committed(
    path: Path, identity: str
) -> tuple[dict[str, np.ndarray], dict[str, Any]] | None:
    receipt = path.with_suffix(".json")
    if not path.exists() or not receipt.exists():
        for item in (
            path,
            receipt,
            path.with_name(path.name + ".tmp"),
            receipt.with_name(receipt.name + ".tmp"),
        ):
            if item.exists():
                item.rename(item.with_name(item.name + f".uncommitted-{time.time_ns()}"))
        return None
    record = json.loads(receipt.read_text(encoding="utf-8"))
    if record.get("identity") != identity or sha256(path) != record.get("sha256"):
        raise ValueError(f"cached identity or checksum changed: {path}")
    with np.load(path, allow_pickle=False) as data:
        return {name: data[name] for name in data.files}, record


def commit_npz(path: Path, values: dict[str, np.ndarray], record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    started = time.perf_counter()
    with temp.open("wb") as handle:
        np.savez_compressed(handle, **cast(Any, values))
        handle.flush()
        os.fsync(handle.fileno())
    record["sha256"] = sha256(temp)
    temp.replace(path)
    _fsync_directory(path.parent)
    record["serialization_seconds"] = time.perf_counter() - started
    write_json(path.with_suffix(".json"), record)


def validate_row(values: dict[str, np.ndarray], n: int, m: int) -> None:
    shapes: dict[str, tuple[int, ...]] = {
        name: (n if name.startswith("latent") else m, len(EFFECTS)) for name in SCORE_NAMES
    }
    shapes.update(latent_holdout_predator=(n,), h1_error=(), reference_error=())
    if set(values) != set(shapes):
        raise ValueError("row schema changed")
    for name, value in values.items():
        if value.shape != shapes[name] or value.dtype != np.float64 or not np.isfinite(value).all():
            raise ValueError(f"row values changed: {name}")
    if max(float(values["h1_error"]), float(values["reference_error"])) > TOLERANCE:
        raise ValueError("row numerical control failed")


def _require_record(record: dict[str, Any], **expected: Any) -> None:
    for name, value in expected.items():
        if record.get(name) != value:
            raise ValueError(f"cache metadata changed: {name}")
    if not isinstance(record.get("sha256"), str) or len(record["sha256"]) != 64:
        raise ValueError("cache metadata lacks an authenticated checksum")


def validate_observations(
    values: dict[str, np.ndarray],
    record: dict[str, Any],
    identity: str,
    count: int,
    setup: Any,
) -> None:
    """Authenticate observation array schema, ordering, and phase metadata."""

    histories = 6 * count
    expected = set(OBSERVATION_KEYS)
    if set(values) != expected:
        raise ValueError("observation schema changed")
    shapes: dict[str, tuple[int, ...]] = {
        "effects": (len(EFFECTS),),
        "betas": (len(BETAS),),
        "cell_ids": (histories,),
        "replicate_indices": (histories,),
        "truth_h": (histories,),
        "truth_beta": (histories,),
        "opaque_ids": (histories,),
        "site_ids": (160,),
        "site_cluster_ids": (160,),
        "site_splits": (160,),
        "training_mask": (160,),
        "site_A": (160,),
        "map_A": setup.exposure_score.shape,
        "true_arrival": (histories, 160),
        "true_extirpation": (histories, 160),
        "true_hazards": (histories, 160),
        "predator_counts": (histories, 160, 6),
        "prey_counts": (histories, 160, 6),
        "oracle_history_indices": (4 * min(250, count),),
    }
    for name, shape in shapes.items():
        value = values[name]
        if value.shape != shape:
            raise ValueError(f"observation shape changed: {name}")
        if name != "truth_beta" and value.dtype.kind in "fiu" and not np.isfinite(value).all():
            raise ValueError(f"observation values are non-finite: {name}")
    if values["effects"].dtype != np.float64 or values["betas"].dtype != np.float64:
        raise ValueError("observation grids changed dtype")
    if not np.array_equal(values["effects"], np.asarray(EFFECTS)) or not np.array_equal(
        values["betas"], np.asarray(BETAS)
    ):
        raise ValueError("observation grids changed")
    expected_cells = np.tile(np.asarray(generator.CELL_IDS), count)
    if not np.array_equal(values["cell_ids"], expected_cells):
        raise ValueError("cell ordering changed")
    if not np.array_equal(values["replicate_indices"], np.repeat(np.arange(count), 6)):
        raise ValueError("replicate ordering changed")
    if not np.array_equal(values["site_ids"], np.asarray(setup.site_ids)):
        raise ValueError("site ordering changed")
    if not np.array_equal(values["site_cluster_ids"], np.asarray(setup.site_cluster_ids)):
        raise ValueError("site cluster ordering changed")
    if not np.array_equal(values["site_splits"], np.asarray(setup.site_splits)):
        raise ValueError("site split ordering changed")
    expected_training = np.asarray([split == "training" for split in setup.site_splits])
    if not np.array_equal(values["training_mask"], expected_training):
        raise ValueError("training split changed")
    expected_h = np.tile(np.asarray(generator.TRUTH_H), count)
    expected_beta = np.tile(np.asarray(generator.TRUTH_BETA), count)
    if not np.array_equal(values["truth_h"], expected_h) or not np.array_equal(
        values["truth_beta"], expected_beta, equal_nan=True
    ):
        raise ValueError("truth metadata changed")
    if len(set(map(str, values["opaque_ids"]))) != histories:
        raise ValueError("opaque identities are not unique")
    if (
        not np.isin(values["predator_counts"], (0, 1, 2)).all()
        or not np.isin(values["prey_counts"], (0, 1, 2)).all()
    ):
        raise ValueError("invalid detection counts")
    if not np.array_equal(
        values["oracle_history_indices"],
        np.asarray([6 * block + cell for block in range(min(250, count)) for cell in range(4)]),
    ):
        raise ValueError("oracle subset ordering changed")
    _require_record(record, identity=identity, blocks=count, histories=histories)
    if record.get("phase") not in {"timing", "production"}:
        raise ValueError("observation phase metadata changed")
    if not isinstance(record.get("seeds"), list) or len(record["seeds"]) != count:
        raise ValueError("observation seed metadata changed")
    for name in ("generation_seconds", "cache_io_seconds", "serialization_seconds"):
        if name not in record or not isinstance(record[name], (int, float)) or record[name] < 0:
            raise ValueError(f"observation timing metadata changed: {name}")
    root = generator.TIMING_ROOT if record["phase"] == "timing" else generator.PRODUCTION_ROOT
    expected_seeds = [
        asdict(seed)
        for seed in generator.spawn_generator_seeds(root, cast(Any, record["phase"]), count)
    ]
    if record["seeds"] != expected_seeds:
        raise ValueError("observation seed ordering changed")


def validate_integration_cache(
    values: dict[str, np.ndarray], record: dict[str, Any], identity: str, index: int
) -> None:
    if set(values) != {"category_mass", "survival_moments"}:
        raise ValueError("integration cache schema changed")
    if values["category_mass"].shape != (1, 160, 7) or values["survival_moments"].shape != (
        len(EFFECTS),
        160,
        7,
        7,
    ):
        raise ValueError("integration cache shape changed")
    if any(
        value.dtype != np.float64 or not np.isfinite(value).all() or (value < 0).any()
        for value in values.values()
    ):
        raise ValueError("invalid integration cache")
    _require_record(record, identity=identity, index=index, beta=float(BETAS[index]))


def validate_row_record(record: dict[str, Any], identity: str, phase_id: str, index: int) -> None:
    _require_record(
        record, identity=identity, phase_fingerprint=phase_id, index=index, beta=float(BETAS[index])
    )
    for name in (
        "reference_error",
        "h1_error",
        "construction_seconds",
        "scoring_seconds",
        "serialization_seconds",
        "reference_seconds",
        "cache_io_seconds",
        "integration_serialization_seconds",
    ):
        if name not in record or not isinstance(record[name], (int, float)) or record[name] < 0:
            raise ValueError(f"row timing metadata changed: {name}")


def validate_output_hashes(directory: Path, expected: dict[str, str]) -> None:
    """Verify every timing artifact before allowing production continuation."""

    observed = {
        str(path.relative_to(directory)): sha256(path)
        for path in directory.rglob("*")
        if path.is_file()
        and path.name != "run_summary.json"
        and ".tmp" not in path.name
        and ".uncommitted" not in path.name
    }
    if observed != expected:
        raise ValueError("timing output hashes changed")


def seed_controls() -> dict[str, Any]:
    streams: dict[str, set[int]] = {}
    for phase, root, count in [
        ("production", generator.PRODUCTION_ROOT, generator.PRODUCTION_REPLICATES),
        ("timing", generator.TIMING_ROOT, generator.TIMING_REPLICATES),
        ("bootstrap", generator.BOOTSTRAP_ROOT, generator.BOOTSTRAP_REPLICATES),
        ("smoke", generator.SMOKE_ROOT, generator.SMOKE_REPLICATES),
    ]:
        seeds = generator.spawn_generator_seeds(root, cast(Any, phase), count)
        stream_values = {s for record in seeds for s in record.stream_seeds}
        streams[phase] = stream_values
        if len(streams[phase]) != 7 * count:
            raise ValueError("within-phase seed collision")
    previous: set[int] = set()
    for root, phase, count in [
        (old_generator.PRODUCTION_ROOT, "production", 1000),
        (old_generator.TIMING_ROOT, "timing", 16),
        (old_generator.SMOKE_ROOT, "smoke", 2),
    ]:
        previous.update(
            s
            for record in old_generator.spawn_generator_seeds(root, cast(Any, phase), count)
            for s in record.stream_seeds
        )
    config = adequacy.production_config("timing")
    for root, phase, count in [
        (config.original_calibration_root, "calibration", 999),
        (config.original_evaluation_root, "evaluation", 1000),
        (config.fresh_calibration_root, "calibration", 999),
        (config.fresh_evaluation_root, "evaluation", 1000),
    ]:
        for record in adequacy.spawn_phase_seeds(root, phase, count):
            previous.update(
                (
                    record.process_seed,
                    record.predator_detection_seed,
                    record.prey_seed,
                    record.prey_detection_seed,
                )
            )
    previous.update(legacy._expected_archived_bank_seeds(131072))
    execution_roots = {
        generator.PRODUCTION_ROOT,
        generator.TIMING_ROOT,
        generator.BOOTSTRAP_ROOT,
        generator.SMOKE_ROOT,
        old_generator.PRODUCTION_ROOT,
        old_generator.TIMING_ROOT,
        old_generator.SMOKE_ROOT,
        old_generator.BOOTSTRAP_ROOT,
        config.original_calibration_root,
        config.original_evaluation_root,
        config.fresh_calibration_root,
        config.fresh_evaluation_root,
        config.bank_root,
    }
    registered_roots = execution_roots | {AUDIT_ONLY_ROOT}
    if len(registered_roots) != 14:
        raise ValueError("registered seed roots are not distinct")
    for phase, stream_values in streams.items():
        if not stream_values.isdisjoint(previous):
            raise ValueError(f"previous-campaign/bank seed collision: {phase}")
        for other, other_values in streams.items():
            if phase != other and not stream_values.isdisjoint(other_values):
                raise ValueError("phase seed collision")
    return {
        "phase_seed_counts": {key: len(value) for key, value in streams.items()},
        "previous_and_bank_seed_count": len(previous),
        "all_disjoint": True,
        "previous_roots": [
            old_generator.PRODUCTION_ROOT,
            old_generator.TIMING_ROOT,
            old_generator.SMOKE_ROOT,
            old_generator.BOOTSTRAP_ROOT,
        ],
        "bootstrap_root_reserved": generator.BOOTSTRAP_ROOT
        not in {
            generator.PRODUCTION_ROOT,
            generator.TIMING_ROOT,
            generator.SMOKE_ROOT,
        },
        "audit_root_reserved": AUDIT_ONLY_ROOT not in execution_roots,
        "root_identifiers_distinct": len(registered_roots) == 14,
    }


def histories_from_arrays(data: dict[str, np.ndarray]) -> tuple[tuple[Any, ...], ...]:
    ids = data["site_ids"]
    clusters = data["site_cluster_ids"]
    splits = data["site_splits"]
    predator = data["predator_counts"]
    prey_counts = data["prey_counts"]
    if predator.shape != prey_counts.shape or predator.shape[1:] != (160, 6):
        raise ValueError("observation dimensions changed")
    if not np.isin(predator, (0, 1, 2)).all() or not np.isin(prey_counts, (0, 1, 2)).all():
        raise ValueError("invalid detection counts")
    return tuple(
        tuple(
            legacy.AnalystHistory(
                str(ids[j]),
                str(clusters[j]),
                str(splits[j]),
                tuple(map(int, predator[i, j])),
                tuple(map(int, prey_counts[i, j])),
                0.65,
            )
            for j in range(160)
        )
        for i in range(len(predator))
    )


def prepare_observations(
    output: Path, phase: str, identity: str, fixed: Any, setup: Any
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    if phase not in {"timing", "production"}:
        raise ValueError("invalid observation phase")
    count = 20 if phase == "timing" else 1000
    root = generator.TIMING_ROOT if phase == "timing" else generator.PRODUCTION_ROOT
    seeds = generator.spawn_generator_seeds(root, cast(Any, phase), count)
    seed_records = [asdict(s) for s in seeds]
    identity = fingerprint({"core": identity, "phase": phase, "seeds": seed_records})
    path = output / "observations.npz"
    cache_started = time.perf_counter()
    cached = read_committed(path, identity)
    cache_seconds = time.perf_counter() - cache_started
    if cached is not None:
        validate_observations(cached[0], cached[1], identity, count, setup)
        cached[1]["cache_io_seconds"] = cache_seconds
        return cached
    started = time.perf_counter()
    cells: list[Any] = []
    for block, seed in enumerate(seeds):
        cells.extend(generator.generate_replicate(fixed, setup, seed))
        if (block + 1) % 50 == 0:
            print(f"{phase}: generated {block + 1}/{count} paired blocks", flush=True)
    values: dict[str, np.ndarray] = {
        "effects": np.asarray(EFFECTS),
        "betas": np.asarray(BETAS),
        "cell_ids": np.asarray([c.cell.cell_id for c in cells]),
        "replicate_indices": np.repeat(np.arange(count), 6),
        "truth_h": np.tile(np.asarray([1.0, 3.0, 1.0, 3.0, 1.0, 3.0]), count),
        "truth_beta": np.tile(np.asarray([0.0, 0.0, 0.6, 0.6, np.nan, np.nan]), count),
        "opaque_ids": np.asarray([c.dataset.opaque_id for c in cells]),
        "site_ids": np.asarray(setup.site_ids),
        "site_cluster_ids": np.asarray(setup.site_cluster_ids),
        "site_splits": np.asarray(setup.site_splits),
        "training_mask": np.asarray([s == "training" for s in setup.site_splits]),
        "site_A": setup.exposure_score[setup.site_rows, setup.site_cols],
        "map_A": setup.exposure_score,
        "true_arrival": np.stack([c.latent_truth.arrival for c in cells]),
        "true_extirpation": np.stack([c.latent_truth.prey_extirpation for c in cells]),
        "true_hazards": np.stack([c.latent_truth.background_hazard for c in cells]),
        "predator_counts": np.asarray(
            [[h.predator_detection_counts for h in c.dataset.histories] for c in cells],
            dtype=np.uint8,
        ),
        "prey_counts": np.asarray(
            [[h.prey_detection_counts for h in c.dataset.histories] for c in cells], dtype=np.uint8
        ),
        "oracle_history_indices": np.asarray(
            [6 * b + c for b in range(min(250, count)) for c in range(4)]
        ),
    }
    if (
        tuple(values["cell_ids"]) != tuple(generator.CELL_IDS) * count
        or len(set(values["opaque_ids"])) != 6 * count
    ):
        raise ValueError("generator cell order or identities changed")
    record = {
        "identity": identity,
        "phase": phase,
        "blocks": count,
        "histories": len(cells),
        "generation_seconds": time.perf_counter() - started,
        "cache_io_seconds": cache_seconds,
        "seeds": seed_records,
        "diagnostics": [asdict(c.diagnostics) for c in cells],
    }
    commit_npz(path, values, record)
    validate_observations(values, record, identity, count, setup)
    print(f"{phase}: observations committed in {record['generation_seconds']:.1f}s", flush=True)
    return values, record


def get_integration_timed(
    root: Path, index: int, core: str, prepared: Any, data: dict[str, np.ndarray]
) -> tuple[Any, float, float, dict[str, Any]]:
    identity = fingerprint({"core": core, "beta_index": index, "beta": BETAS[index]})
    path = root / "integrations" / f"{index:03d}.npz"
    cache_started = time.perf_counter()
    cached = read_committed(path, identity)
    cache_seconds = time.perf_counter() - cache_started
    seconds = 0.0
    if cached is None:
        started = time.perf_counter()
        hazards = likelihood.normalized_hazards(BETAS[index], data["map_A"], data["site_A"])
        integration = likelihood.build_integration(prepared, EFFECTS, hazards)
        seconds = time.perf_counter() - started
        values = {
            "category_mass": integration.category_mass,
            "survival_moments": integration.survival_moments[0],
        }
        record = {"identity": identity, "index": index, "beta": BETAS[index]}
        commit_npz(path, values, record)
    else:
        values, record = cached
    validate_integration_cache(values, record, identity, index)
    if not np.array_equal(values["category_mass"][0], prepared.category_mass):
        raise ValueError("integration category weights changed")
    result = joint.BridgeIntegration(
        (1.0,),
        EFFECTS,
        prepared.site_ids,
        values["category_mass"],
        (values["survival_moments"],),
        prepared.bank_checksum,
    )
    return result, seconds, cache_seconds, record


def get_integration(
    root: Path, index: int, core: str, prepared: Any, data: dict[str, np.ndarray]
) -> tuple[Any, float]:
    """Return one cached integration and its construction time."""

    integration, construction, _, _ = get_integration_timed(root, index, core, prepared, data)
    return integration, construction


def score_panel(
    histories: tuple[tuple[Any, ...], ...],
    integration: Any,
    data: dict[str, np.ndarray],
    index: int,
) -> dict[str, np.ndarray]:
    n = len(histories)
    oracle_ids = data["oracle_history_indices"]
    m = len(oracle_ids)
    oracle_positions = {int(row): i for i, row in enumerate(oracle_ids)}
    values: dict[str, np.ndarray] = {
        name: np.empty((n if name.startswith("latent") else m, len(EFFECTS)))
        for name in SCORE_NAMES
    }
    values["latent_holdout_predator"] = np.empty(n)
    hazards = likelihood.normalized_hazards(BETAS[index], data["map_A"], data["site_A"])
    h1_error = 0.0
    for i, history in enumerate(histories):
        train, held, pred = joint.evaluate_dataset(cast(Any, history), integration)
        values["latent_training"][i] = train[0]
        values["latent_holdout_joint"][i] = held[0]
        values["latent_holdout_predator"][i] = pred[0]
        if i in oracle_positions:
            position = oracle_positions[i]
            otr, oh = likelihood.oracle_evaluate_dataset(
                history, data["true_arrival"][i], EFFECTS, hazards, site_ids=integration.site_ids
            )
            values["oracle_training"][position] = otr
            values["oracle_holdout"][position] = oh
            emissions = prey._predator_category_probabilities(cast(Any, history), 0.65)
            margin = np.einsum("sc,sc->s", integration.category_mass[0], emissions)
            training_predator = np.log(margin[data["training_mask"]]).sum()
            h1_error = max(
                h1_error,
                abs(train[0, 0] - training_predator - otr[0]),
                abs(held[0, 0] - pred[0] - oh[0]),
            )
    values["h1_error"] = np.asarray(h1_error)
    return values


def reference_check(
    integration: Any, index: int, reference: dict[str, np.ndarray], setup: Any
) -> float:
    """Reproduce all 24 frozen Goal052 scores at this beta, without refitting."""
    data = dict(
        reference,
        site_cluster_ids=np.asarray(setup.site_cluster_ids),
        site_splits=np.asarray(setup.site_splits),
        oracle_history_indices=np.arange(24),
    )
    values = score_panel(histories_from_arrays(data), integration, data, index)
    errors = [
        float(np.max(np.abs(values[name] - reference[name][:, index, :]))) for name in SCORE_NAMES
    ]
    errors.extend(
        [
            float(values["h1_error"]),
            float(
                np.max(
                    np.abs(values["latent_holdout_predator"] - reference["latent_holdout_predator"])
                )
            ),
        ]
    )
    if max(errors) > TOLERANCE:
        raise RuntimeError(
            f"Goal052 full-bank reference failed at beta index {index}: {max(errors)}"
        )
    return max(errors)


def run_phase(
    *,
    root: Path,
    phase: str,
    bank_cache: Path,
    pilot_output: Path,
    wrapper: Path,
    workers: int = 16,
) -> dict[str, Any]:
    if phase not in ("timing", "production") or not 1 <= workers <= 32:
        raise ValueError("invalid phase or worker count")
    started = time.perf_counter()
    repository = Path(__file__).resolve().parents[2]
    output = root / phase / "output"
    output.mkdir(parents=True, exist_ok=True)
    if (output / "run_summary.json").exists():
        raise ValueError("completed phase cannot be restarted")
    if (
        sha256(pilot_output / "run_contract.json") != PILOT_CONTRACT
        or sha256(pilot_output / "evidence.npz") != PILOT_EVIDENCE
    ):
        raise ValueError("Goal052 reference identity changed")
    previous = json.loads((pilot_output / "run_contract.json").read_text())
    for name, digest in previous["source_hashes"].items():
        if sha256(repository / name) != digest:
            raise ValueError(f"frozen source changed: {name}")
    sources = source_hashes(repository)
    wrapper_hash = sha256(wrapper)
    fixed = benchmark.build_fixed_inputs()
    setup = old_generator.build_generator_setup(fixed)
    bank, provenance = adequacy._load_bank(
        adequacy.production_config("timing"), bank_cache, setup.site_ids
    )
    prepared = likelihood.prepare_bank(bank, setup.site_ids)
    control = seed_controls()
    contract = {
        "workflow": "goal053_six_cell_prospective_v1",
        "source_hashes": sources,
        "wrapper_sha256": wrapper_hash,
        "goal052_contract_sha256": PILOT_CONTRACT,
        "goal052_evidence_sha256": PILOT_EVIDENCE,
        "bank": provenance,
        "effects": EFFECTS,
        "betas": BETAS,
        "alpha": 1.0,
        "seed_controls": control,
        "worker_identity": worker_identity(),
    }
    core = fingerprint(contract)
    contract["fingerprint"] = core
    if (root / "run_contract.json").exists():
        if json.loads((root / "run_contract.json").read_text()) != json.loads(json.dumps(contract)):
            raise ValueError("run contract changed; prior timing/cache invalid")
    else:
        write_json(root / "run_contract.json", contract)
    if phase == "production":
        timing_path = root / "timing" / "output" / "run_summary.json"
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        budget = json.loads((root / "production-budget.json").read_text(encoding="utf-8"))
        if (
            timing.get("fingerprint") != core
            or budget.get("fingerprint") != core
            or budget.get("workers") != workers
            or timing.get("workers") != workers
            or timing.get("worker_identity") != worker_identity()
            or budget.get("timing_summary_sha256") != sha256(timing_path)
            or not timing.get("controls_passed")
            or not timing.get("source_identity_unchanged")
            or not isinstance(timing.get("output_sha256"), dict)
        ):
            raise ValueError("production lacks current timing/budget qualification")
        validate_output_hashes(timing_path.parent, timing["output_sha256"])
    with np.load(pilot_output / "evidence.npz", allow_pickle=False) as loaded:
        reference = {name: loaded[name] for name in loaded.files}
    data, observation_record = prepare_observations(output, phase, core, fixed, setup)
    histories = histories_from_arrays(data)
    n = len(histories)
    m = len(data["oracle_history_indices"])
    if n != (120 if phase == "timing" else 6000) or m != (80 if phase == "timing" else 1000):
        raise ValueError("fixed panel dimensions changed")
    phase_id = fingerprint(
        {"core": core, "phase": phase, "observations_sha256": observation_record["sha256"]}
    )
    indices = TIMING_INDICES if phase == "timing" else tuple(range(81))
    print(
        f"{phase}: inputs and source verified; scoring {len(indices)} beta rows for {n} histories",
        flush=True,
    )

    def compute_row(index: int) -> dict[str, Any]:
        identity = fingerprint({"phase": phase_id, "index": index, "beta": BETAS[index]})
        path = output / "rows" / f"{index:03d}.npz"
        cache_started = time.perf_counter()
        cached = read_committed(path, identity)
        cache_seconds = time.perf_counter() - cache_started
        if cached is not None:
            values, record = cached
            validate_row(values, n, m)
            validate_row_record(record, identity, phase_id, index)
            record["cache_io_seconds"] = cache_seconds
            return record
        integration, construction, integration_cache_seconds, integration_record = (
            get_integration_timed(root, index, core, prepared, data)
        )
        reference_started = time.perf_counter()
        reference_error = reference_check(integration, index, reference, setup)
        reference_seconds = time.perf_counter() - reference_started
        began = time.perf_counter()
        values = score_panel(histories, integration, data, index)
        values["reference_error"] = np.asarray(reference_error)
        validate_row(values, n, m)
        scoring = time.perf_counter() - began
        record = {
            "identity": identity,
            "phase_fingerprint": phase_id,
            "index": index,
            "beta": BETAS[index],
            "construction_seconds": construction,
            "cache_io_seconds": cache_seconds + integration_cache_seconds,
            "integration_serialization_seconds": integration_record.get(
                "serialization_seconds", 0.0
            ),
            "reference_seconds": reference_seconds,
            "scoring_seconds": scoring,
            "h1_error": float(values["h1_error"]),
            "reference_error": reference_error,
        }
        commit_npz(path, values, record)
        validate_row_record(record, identity, phase_id, index)
        print(
            f"{phase}: beta {BETAS[index]:+.2f} complete; "
            f"build {construction:.2f}s score {scoring:.2f}s",
            flush=True,
        )
        return record

    records = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for future in as_completed([executor.submit(compute_row, index) for index in indices]):
            records.append(future.result())
    records.sort(key=lambda x: x["index"])
    assembly_seconds = 0.0
    if phase == "production":
        assembly_started = time.perf_counter()
        outputs = {
            name: np.lib.format.open_memmap(
                output / (name + ".tmp.npy"),
                mode="w+",
                dtype=np.float64,
                shape=(n if name.startswith("latent") else m, 81, 181),
            )
            for name in SCORE_NAMES
        }
        predator = None
        for index in indices:
            identity = fingerprint({"phase": phase_id, "index": index, "beta": BETAS[index]})
            cached = read_committed(output / "rows" / f"{index:03d}.npz", identity)
            if cached is None:
                raise ValueError("row missing during assembly")
            values, record = cached
            validate_row(values, n, m)
            validate_row_record(record, identity, phase_id, index)
            for name in SCORE_NAMES:
                outputs[name][:, index, :] = values[name]
            if predator is None:
                predator = values["latent_holdout_predator"]
            elif not np.array_equal(predator, values["latent_holdout_predator"]):
                raise ValueError("predator marginal changed across beta")
        for name, value in outputs.items():
            value.flush()
            (output / (name + ".tmp.npy")).replace(output / (name + ".npy"))
        del outputs
        final_data = dict(data, latent_holdout_predator=cast(np.ndarray, predator))
        commit_npz(
            output / "evidence.npz", final_data, {"identity": phase_id, "metadata_only": True}
        )
        assembly_seconds = time.perf_counter() - assembly_started
    if source_hashes(repository) != sources or sha256(wrapper) != wrapper_hash:
        raise RuntimeError("source or wrapper changed during phase")
    summary = {
        "phase": phase,
        "fingerprint": core,
        "phase_fingerprint": phase_id,
        "finished_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": time.perf_counter() - started,
        "histories": n,
        "oracle_histories": m,
        "rows": len(records),
        "workers": workers,
        "worker_identity": worker_identity(),
        "controls_passed": True,
        "observation_sha256": observation_record["sha256"],
        "generation_seconds": observation_record["generation_seconds"],
        "observation_cache_io_seconds": observation_record.get("cache_io_seconds", 0.0),
        "observation_serialization_seconds": observation_record.get("serialization_seconds", 0.0),
        "reference_replay_seconds": sum(r.get("reference_seconds", 0.0) for r in records),
        "integration_cache_io_seconds": sum(r.get("cache_io_seconds", 0.0) for r in records),
        "integration_construction_seconds": sum(
            r.get("construction_seconds", 0.0) for r in records
        ),
        "integration_serialization_seconds": sum(
            r.get("integration_serialization_seconds", 0.0) for r in records
        ),
        "scoring_seconds": sum(r.get("scoring_seconds", 0.0) for r in records),
        "serialization_seconds": sum(r.get("serialization_seconds", 0.0) for r in records),
        "assembly_seconds": assembly_seconds,
        "row_receipts": records,
        "source_identity_unchanged": True,
    }
    if phase == "timing":
        per_history = max(
            (
                r.get("reference_seconds", 0.0)
                + r.get("scoring_seconds", 0.0)
                + r.get("serialization_seconds", 0.0)
            )
            / n
            for r in records
        )
        per_row_cache = max(r.get("cache_io_seconds", 0.0) for r in records)
        per_row_integration_serialization = max(
            r.get("integration_serialization_seconds", 0.0) for r in records
        )
        projected = (
            1.5
            * (
                (
                    observation_record["generation_seconds"]
                    + observation_record.get("cache_io_seconds", 0.0)
                    + observation_record.get("serialization_seconds", 0.0)
                )
                / 20
                * 1000
                + math.ceil(81 / workers)
                * (
                    max(r.get("construction_seconds", 0.0) for r in records)
                    + max(r.get("reference_seconds", 0.0) for r in records)
                    + per_row_cache
                    + per_row_integration_serialization
                    + per_history * 6000
                )
            )
            + ASSEMBLY_ALLOWANCE_SECONDS
        )
        summary["projection"] = {
            "complete_production_seconds": projected,
            "safety_factor": 1.5,
            "assembly_allowance_seconds": ASSEMBLY_ALLOWANCE_SECONDS,
            "synthesis_verification_reserve_seconds": ASSEMBLY_ALLOWANCE_SECONDS,
            "slowest_score_serialization_seconds_per_history": per_history,
            "slowest_row_cache_io_seconds": per_row_cache,
            "slowest_integration_serialization_seconds": per_row_integration_serialization,
        }
    paths = [
        p
        for p in output.rglob("*")
        if p.is_file() and ".tmp" not in p.name and ".uncommitted" not in p.name
    ]
    summary["output_sha256"] = {str(p.relative_to(output)): sha256(p) for p in paths}
    write_json(output / "run_summary.json", summary)
    print(f"{phase}: complete in {summary['elapsed_seconds']:.1f}s", flush=True)
    return summary
