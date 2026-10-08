"""Goal 051 paired misspecification screen runner.

The generator owns the scientific departures.  This module owns the frozen
analyst, paired replicate execution, provenance, and resumable shard format.
Evaluator joins are deliberately downstream of ``frozen_scores.json``.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import platform
import socket
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import known_nuisance_calibration as legacy
from latent_landscapes import model_adequacy_campaign as adequacy
from latent_landscapes.goal011 import benchmark as goal011

RunMode = Literal["smoke", "timing", "production"]
FloatArray = NDArray[np.float64]
Progress = Callable[[str], None]

EFFECT_GRID = tuple(float(x) for x in np.linspace(1.0, 10.0, 181))
TRUTHS = (1.0, 3.0, 5.0)
CELL_COUNT = 17
PRODUCTION_ROOT = 2026092301
TIMING_ROOT = 2026092302
SMOKE_ROOT = 2026092303
BOOTSTRAP_ROOT = 2026092304
ARCHIVED_BANK_ROOT = 20260905
ORIGINAL_ROOTS = (2026092001, 2026092002, 2026092004, 2026092005)
DEFAULT_OUTPUT_DIR = Path("artifacts/goal051_misspecification_screen")
DEFAULT_EXECUTION_ROOT = Path("artifacts/goal051_execution")
DEFAULT_REFERENCE_DIR = Path("artifacts/goal050_execution")
DEFAULT_REGISTRATION_PATH = Path(
    "docs/goals/051-misspecification-screen/registration-2026-09-23.md"
)
PREPARATION_SECONDS = 1200.0
SYNTHESIS_SECONDS = 1800.0
MAX_SECONDS = 14_400.0
GOAL050_DETECTOR_SHA256 = "0fd2f1e43d1de74fb2ee0ebfe18e45f8c463e3cd0c3aebbb19c8bca86b6beeb6"
GOAL050_CALIBRATION_SHA256 = "91c1cd83b78cf7ebe070e6652d3cccdd8235c4e34715e1af4a680b8eedba80e9"
GOAL050_SYNTHESIS_RECEIPT_SHA256 = (
    "3a8ed36fbe71084b297ef0e6f4ca63aeea861fff39b1930408cdf13f70cbea4c"
)


def _generator() -> Any:
    return importlib.import_module("latent_landscapes.misspecification_generator")


def _cell_specs() -> tuple[Any, ...]:
    specs = tuple(_generator().CELL_SPECS)
    if len(specs) != CELL_COUNT:
        raise ValueError("Goal 051 generator must expose exactly 17 ordered CELL_SPECS")
    return specs


def _cell_id(spec: Any) -> str:
    value = getattr(spec, "cell_id", None)
    if value is None and isinstance(spec, Mapping):
        value = spec.get("cell_id")
    if not isinstance(value, str) or not value:
        raise ValueError("every Goal 051 cell must have a non-empty cell_id")
    return value


def _cell_truth(spec: Any) -> float:
    value = getattr(spec, "truth_h", None)
    if value is None and isinstance(spec, Mapping):
        value = spec.get("truth_h")
    result = float(cast(float, value))
    if not math.isfinite(result):
        raise ValueError("cell truths must be finite")
    return result


@dataclass(frozen=True, slots=True)
class CampaignConfig:
    mode: RunMode
    effects: tuple[float, ...]
    truths: tuple[float, ...] = TRUTHS
    replicates: int = 1_000
    bank_size: int = 131_072
    campaign_root: int = PRODUCTION_ROOT
    bank_root: int = ARCHIVED_BANK_ROOT
    bootstrap_root: int = BOOTSTRAP_ROOT

    def __post_init__(self) -> None:
        effects = np.asarray(self.effects, dtype=np.float64)
        truths = np.asarray(self.truths, dtype=np.float64)
        if effects.ndim != 1 or len(effects) < 2 or not np.isfinite(effects).all():
            raise ValueError("effects must be a finite one-dimensional grid")
        if np.any(np.diff(effects) <= 0) or effects[0] != 1.0:
            raise ValueError("effects must be strictly increasing and start at 1")
        if truths.ndim != 1 or not len(truths) or not np.isfinite(truths).all():
            raise ValueError("truths must be a non-empty finite vector")
        if any(not np.any(np.isclose(effects, value, rtol=0, atol=1e-12)) for value in truths):
            raise ValueError("every registered truth must occur on the effect grid")
        if self.replicates <= 0 or self.bank_size <= 0:
            raise ValueError("replicates and bank_size must be positive")
        if self.mode not in ("smoke", "timing", "production"):
            raise ValueError("invalid campaign mode")
        expected_root = {
            "production": PRODUCTION_ROOT,
            "timing": TIMING_ROOT,
            "smoke": SMOKE_ROOT,
        }[self.mode]
        if self.campaign_root != expected_root:
            raise ValueError("campaign root does not match the registered mode")
        if self.mode != "smoke" and (self.effects != EFFECT_GRID or self.truths != TRUTHS):
            raise ValueError(
                "timing and production require the registered 181-node grid and truths"
            )
        if self.mode == "production" and (self.replicates, self.bank_size) != (1_000, 131_072):
            raise ValueError("production requires 1000 paired replicates and K=131072")
        if self.mode == "timing" and (self.replicates, self.bank_size) != (16, 131_072):
            raise ValueError("timing requires 16 complete paired replicates and K=131072")
        if self.mode == "smoke" and self.replicates not in (1, 2):
            raise ValueError("smoke permits one or two paired replicates")
        if self.mode == "smoke" and self.bank_size >= 131_072:
            raise ValueError("smoke must use a small bank")
        roots = (self.campaign_root, self.bank_root, self.bootstrap_root, *ORIGINAL_ROOTS)
        if len(set(roots)) != len(roots):
            raise ValueError("campaign, bank, bootstrap, and original roots must be distinct")


def production_config() -> CampaignConfig:
    return CampaignConfig("production", EFFECT_GRID, TRUTHS, 1_000, 131_072)


def timing_config() -> CampaignConfig:
    return CampaignConfig("timing", EFFECT_GRID, TRUTHS, 16, 131_072, TIMING_ROOT)


def smoke_config(*, replicates: int = 1, bank_size: int = 16) -> CampaignConfig:
    return CampaignConfig("smoke", (1.0, 3.0, 5.0), TRUTHS, replicates, bank_size, SMOKE_ROOT)


def _file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _json_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _array_sha256(value: NDArray[Any]) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _seed_dict(seed: Any) -> dict[str, Any]:
    value = asdict(cast(Any, seed)) if is_dataclass(seed) else vars(seed)
    return cast(dict[str, Any], value)


def _seed_fingerprint(seed: Any) -> str:
    return _json_sha256(_seed_dict(seed))


def _seed_values(seed: Any) -> set[int]:
    result: set[int] = set()
    for name, value in _seed_dict(seed).items():
        if "seed" in name and isinstance(value, (int, np.integer)):
            result.add(int(value))
    return result


def _spawn_seeds(config: CampaignConfig) -> tuple[Any, ...]:
    generator = _generator()
    phase = config.mode
    seeds = tuple(generator.spawn_generator_seeds(config.campaign_root, phase, config.replicates))
    if len(seeds) != config.replicates:
        raise ValueError("generator returned the wrong number of paired replicate seeds")
    return seeds


def _seed_controls(
    config: CampaignConfig, seeds: Sequence[Any], bank_provenance: Mapping[str, Any]
) -> dict[str, bool]:
    values = [_seed_values(seed) for seed in seeds]
    all_values = set().union(*values) if values else set()
    generator = _generator()
    campaign_sets: dict[str, set[int]] = {}
    for mode, root, count in (
        ("production", PRODUCTION_ROOT, 1_000),
        ("timing", TIMING_ROOT, 16),
        ("smoke", SMOKE_ROOT, 2),
    ):
        campaign_sets[mode] = set().union(
            *(_seed_values(seed) for seed in generator.spawn_generator_seeds(root, mode, count))
        )
    cross_mode_disjoint = all(
        campaign_sets[first].isdisjoint(campaign_sets[second])
        for index, first in enumerate(campaign_sets)
        for second in list(campaign_sets)[index + 1 :]
    )
    original_values: set[int] = set()
    for root, phase in zip(
        ORIGINAL_ROOTS, ("calibration", "evaluation", "calibration", "evaluation"), strict=True
    ):
        count = 2 if config.mode == "smoke" else 999 if phase == "calibration" else 1_000
        for original_seed in adequacy.spawn_phase_seeds(root, phase, count):
            original_values.update(_seed_values(original_seed))
    bank_values = set(legacy._expected_archived_bank_seeds(131_072))
    controls = {
        "campaign_seed_streams_nonempty": bool(all_values),
        "within_replicate_streams_distinct": all(len(row) == 7 for row in values),
        "replicate_seed_blocks_distinct": len(all_values) == sum(len(row) for row in values),
        "all_registered_campaign_modes_disjoint": cross_mode_disjoint,
        "campaign_vs_original_streams_disjoint": all_values.isdisjoint(original_values),
        "campaign_vs_archived_bank_streams_disjoint": all_values.isdisjoint(bank_values),
        "bank_provenance_present": bool(bank_provenance.get("bank_checksum")),
        "bootstrap_root_reserved": config.bootstrap_root
        not in {config.campaign_root, config.bank_root},
    }
    if not all(controls.values()):
        raise RuntimeError(f"registered seed controls failed: {controls}")
    return controls


def _load_bank(
    config: CampaignConfig, bank_cache_dir: Path | None, site_ids: tuple[str, ...]
) -> tuple[FloatArray, dict[str, Any]]:
    if config.mode == "smoke":
        return legacy.load_verified_bank(
            Path("."),
            legacy.smoke_config(
                low_bank_size=min(8, config.bank_size), high_bank_size=config.bank_size
            ),
            site_ids,
        )
    if bank_cache_dir is None:
        raise ValueError("timing and production require --bank-cache")
    return adequacy._load_bank(adequacy.production_config("timing"), bank_cache_dir, site_ids)


def _source_hashes(
    registration_path: Path,
    reference_paths: Sequence[Path] = (),
    *,
    execution_root: Path | None = None,
    include_execution_helpers: bool = False,
) -> dict[str, str]:
    repository = Path(__file__).resolve().parents[2]
    module_paths = [*sorted((repository / "src").rglob("*.py"))]
    paths = [
        *module_paths,
        repository / "scripts" / "run_misspecification.py",
        repository / "scripts" / "synthesize_misspecification.py",
        repository / "pyproject.toml",
        repository / "uv.lock",
        registration_path.resolve(),
        repository / "docs" / "goals" / "050-model-adequacy" / "next-screen-proposal.md",
        *reference_paths,
    ]
    if include_execution_helpers:
        if execution_root is None:
            raise ValueError("full campaign modes require an execution helper root")
        paths.extend(
            execution_root / name
            for name in ("run-bounded.sh", "run-synthesis.sh", "prepare-production-budget.py")
        )
    result: dict[str, str] = {}
    for path in paths:
        if not path.is_file():
            raise ValueError(f"source-bound file is missing: {path}")
        try:
            name = str(path.resolve().relative_to(repository))
        except ValueError:
            name = str(path.resolve())
        result[name] = _file_sha256(path)
    return result


def _load_frozen_references(reference_dir: Path | None, *, smoke: bool) -> dict[str, Any]:
    if smoke:
        return {"kind": "smoke_without_reference", "files": {}}
    if reference_dir is None:
        raise ValueError("timing and production require Goal 050 reference artifacts")
    detector = reference_dir / "detector_values.npz"
    if not detector.is_file():
        detector = reference_dir / "synthesis" / "detector_values.npz"
    calibration = reference_dir / "production" / "output" / "calibration.npz"
    if not calibration.is_file():
        calibration = reference_dir / "production/output/calibration.npz"
    if not calibration.is_file() and reference_dir.name == "synthesis":
        calibration = reference_dir.parent / "production" / "output" / "calibration.npz"
    if not detector.is_file() or not calibration.is_file():
        raise ValueError(
            "reference directory must contain "
            "synthesis/detector_values.npz and production/output/calibration.npz"
        )
    goal050_root = detector.parent.parent
    synthesis_receipt = goal050_root / "synthesis" / "receipt.json"
    production_summary = goal050_root / "production" / "output" / "run_summary.json"
    production_contract = goal050_root / "production" / "output" / "run_contract.json"
    if (
        not synthesis_receipt.is_file()
        or not production_summary.is_file()
        or not production_contract.is_file()
    ):
        raise ValueError(
            "Goal 050 synthesis receipt and production summary are required frozen inputs"
        )
    if _file_sha256(synthesis_receipt) != GOAL050_SYNTHESIS_RECEIPT_SHA256:
        raise ValueError("Goal 050 synthesis receipt hash differs from the registered pin")
    receipt = json.loads(synthesis_receipt.read_text(encoding="utf-8"))
    production = json.loads(production_summary.read_text(encoding="utf-8"))
    contract = json.loads(production_contract.read_text(encoding="utf-8"))
    if (
        receipt.get("input_run_summary_sha256") != _file_sha256(production_summary)
        or receipt.get("input_run_contract_sha256") != _file_sha256(production_contract)
        or production.get("outcome") != "production_complete"
        or production.get("workflow") != "goal050-model-adequacy"
        or production.get("run_fingerprint") != contract.get("run_fingerprint")
        or not isinstance(production.get("original_manifest"), dict)
        or production["original_manifest"].get("run_summary", {}).get("outcome")
        != "production_scores_complete"
    ):
        raise ValueError("Goal 050 production summary/contract/reference chain is not registered")
    detector_hash = _file_sha256(detector)
    calibration_hash = _file_sha256(calibration)
    if detector_hash != GOAL050_DETECTOR_SHA256 or calibration_hash != GOAL050_CALIBRATION_SHA256:
        raise ValueError("Goal 050 reference artifact hash differs from the registered pin")
    with np.load(detector, allow_pickle=False) as values:
        arrays = {name: np.asarray(values[name]) for name in values.files}
    required = {"original_effect_cutoffs", "original_c99_cutoffs"}
    if not required.issubset(arrays) or any(
        array.dtype.kind not in "fciub" for array in arrays.values()
    ):
        raise ValueError("Goal 050 detector_values.npz lacks the registered numeric cutoffs")
    if any(array.dtype.kind in "fc" and not np.isfinite(array).all() for array in arrays.values()):
        raise ValueError("Goal 050 detector arrays contain non-finite values")
    with np.load(calibration, allow_pickle=False) as values:
        if "prey_score" not in values:
            raise ValueError("Goal 050 calibration.npz lacks prey_score reference rows")
        scores = np.asarray(values["prey_score"])
    if (
        scores.shape != (181, 999)
        or scores.dtype != np.dtype("float64")
        or not np.isfinite(scores).all()
    ):
        raise ValueError("Goal 050 reference prey scores do not have the registered 181x999 schema")
    return {
        "detector_path": str(detector.resolve()),
        "detector_sha256": detector_hash,
        "calibration_path": str(calibration.resolve()),
        "calibration_sha256": calibration_hash,
        "synthesis_receipt_path": str(synthesis_receipt.resolve()),
        "synthesis_receipt_sha256": GOAL050_SYNTHESIS_RECEIPT_SHA256,
        "production_summary_path": str(production_summary.resolve()),
        "production_summary_sha256": _file_sha256(production_summary),
        "production_contract_sha256": _file_sha256(production_contract),
        "detector_arrays": {
            name: {
                "shape": list(array.shape),
                "dtype": str(array.dtype),
                "sha256": _array_sha256(array),
            }
            for name, array in arrays.items()
        },
        "reference_scores": {
            "key": "prey_score",
            "shape": list(scores.shape),
            "dtype": str(scores.dtype),
            "sha256": _array_sha256(scores),
        },
    }


def _normalise_generated(
    generated: Sequence[Any], specs: Sequence[Any]
) -> tuple[tuple[Any, ...], dict[str, FloatArray]]:
    if len(generated) != len(specs):
        raise ValueError("generator returned a non-17-cell replicate")
    expected = tuple(_cell_id(spec) for spec in specs)
    seen: list[str] = []
    datasets: list[Any] = []
    diagnostics: dict[str, FloatArray] = {}
    for row in generated:
        cell = getattr(row, "cell", None)
        dataset = getattr(row, "dataset", None)
        if cell is None or dataset is None:
            raise ValueError("GeneratedCell must expose cell and dataset")
        identifier = _cell_id(cell)
        seen.append(identifier)
        datasets.append(dataset)
        diagnostic_value = getattr(row, "diagnostics", {}) or {}
        if is_dataclass(diagnostic_value):
            diagnostic_value = asdict(cast(Any, diagnostic_value))
        for name, value in dict(diagnostic_value).items():
            if isinstance(value, (int, float, np.integer, np.floating)):
                diagnostics.setdefault(name, np.full(len(specs), np.nan, dtype=np.float64))
                diagnostics[name][len(seen) - 1] = float(value)
    if tuple(seen) != expected:
        raise ValueError("generator cell order/identifiers differ from frozen CELL_SPECS")
    return tuple(datasets), diagnostics


def _score_replicate(
    fixed: Any,
    setup: Any,
    seed: Any,
    integration: Any,
    specs: Sequence[Any],
    effects: tuple[float, ...],
) -> dict[str, Any]:
    generated = _generator().generate_replicate(fixed, setup, seed)
    datasets, diagnostics = _normalise_generated(generated, specs)
    n = len(specs)
    profiles = np.empty((n, len(effects)), dtype=np.float64)
    holdout = np.empty_like(profiles)
    prey = np.empty(n, dtype=np.float64)
    predator = np.empty(n, dtype=np.float64)
    mle = np.empty(n, dtype=np.int64)
    opaque = np.empty(n, dtype="<U64")
    for index, dataset in enumerate(datasets):
        prey[index], predator[index], mle[index], profiles[index], holdout[index] = (
            adequacy._score_dataset(dataset, integration)
        )
        opaque[index] = dataset.opaque_id
    if len(set(opaque.tolist())) != n:
        raise ValueError("opaque IDs must be unique within every paired replicate")
    return {
        "profiles": profiles,
        "holdout_joint": holdout,
        "prey_score": prey,
        "predator_score": predator,
        "mle_index": mle,
        "opaque_ids": opaque,
        "diagnostics": diagnostics,
    }


def _payload_digest(payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    for name in (
        "profiles",
        "holdout_joint",
        "prey_score",
        "predator_score",
        "mle_index",
        "opaque_ids",
    ):
        digest.update(name.encode())
        digest.update(np.ascontiguousarray(payload[name]).tobytes())
    return digest.hexdigest()


def _diagnostics_digest(diagnostics: Mapping[str, FloatArray]) -> str:
    digest = hashlib.sha256()
    for name in sorted(diagnostics):
        digest.update(name.encode())
        digest.update(np.ascontiguousarray(diagnostics[name]).tobytes())
    return digest.hexdigest()


def validate_production_budget(
    path: Path,
    *,
    config: CampaignConfig,
    source_hashes: Mapping[str, str],
    input_hash: str,
    workers: int,
) -> dict[str, Any]:
    if config.mode != "production":
        raise ValueError("production budget applies only to production")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict):
        raise ValueError("production budget must be a JSON object")
    timing_path = Path(str(receipt.get("timing_summary_path", "")))
    if not timing_path.is_file() or _file_sha256(timing_path) != receipt.get(
        "timing_summary_sha256"
    ):
        raise ValueError("budget does not bind a timing summary")
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    projection = timing.get("timing_projection", {})
    total = float(receipt.get("total_projected_seconds", math.nan))
    remaining = float(receipt.get("remaining_budget_seconds", math.nan))
    timeout = float(receipt.get("production_timeout_seconds", math.nan))
    preparation = float(receipt.get("preparation_seconds", PREPARATION_SECONDS))
    timing_seconds = float(
        receipt.get("timing_seconds", timing.get("timings", {}).get("total", math.nan))
    )
    workload = float(
        receipt.get(
            "production_workload_seconds",
            projection.get("production_workload_seconds_conservative", math.nan),
        )
    )
    reserve = float(receipt.get("synthesis_seconds_reserved", SYNTHESIS_SECONDS))
    grace = float(receipt.get("grace_seconds", 30.0))
    helper_root = path.parent
    helper_paths = {
        "bounded_wrapper_sha256": helper_root / "run-bounded.sh",
        "synthesis_wrapper_sha256": helper_root / "run-synthesis.sh",
        "budget_preparer_sha256": helper_root / "prepare-production-budget.py",
    }
    helper_hashes_match = all(
        helper.is_file() and _file_sha256(helper) == receipt.get(field)
        for field, helper in helper_paths.items()
    )
    finite_budget = all(
        math.isfinite(value)
        for value in (
            total,
            remaining,
            timeout,
            preparation,
            timing_seconds,
            workload,
            reserve,
            grace,
        )
    )
    expected_total = preparation + timing_seconds + workload + reserve + grace
    expected_remaining = MAX_SECONDS - preparation - timing_seconds
    if (
        timing.get("outcome") != "timing_complete"
        or timing.get("source_hashes") != dict(source_hashes)
        or timing.get("input_hash") != input_hash
        or timing.get("workers") != workers
        or _json_sha256(timing.get("config", {}))
        != _json_sha256(cast(Any, asdict(timing_config())))
        or float(projection.get("scoring_projection_factor", 0)) < 1.5
        or not finite_budget
        or preparation != PREPARATION_SECONDS
        or reserve < SYNTHESIS_SECONDS
        or grace < 30.0
        or not helper_hashes_match
        or receipt.get("within_4h") is not True
        or timing_seconds < float(timing.get("timings", {}).get("total", math.inf))
        or workload < float(projection.get("production_workload_seconds_conservative", math.inf))
        or abs(total - expected_total) > 1e-6 * max(1.0, expected_total)
        or abs(remaining - expected_remaining) > 1e-6 * max(1.0, expected_remaining)
        or total > MAX_SECONDS
        or remaining <= 0
        or timeout <= 0
        or timeout < math.ceil(workload)
        or workload + reserve + grace > remaining
        or timeout > remaining - reserve - grace
    ):
        raise ValueError("timing/source/input/config/workers evidence does not support production")
    return receipt


def run_campaign(
    config: CampaignConfig,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    bank_cache_dir: Path | None = None,
    registration_path: Path = DEFAULT_REGISTRATION_PATH,
    reference_dir: Path | None = DEFAULT_REFERENCE_DIR,
    execution_root: Path | None = DEFAULT_EXECUTION_ROOT,
    budget_receipt_path: Path | None = None,
    workers: int = 8,
    progress: Progress | None = print,
) -> dict[str, Any]:
    run_started = time.perf_counter()
    if not 1 <= workers <= 8:
        raise ValueError("workers must lie between 1 and 8")
    completed = output_dir / "run_summary.json"
    if completed.is_file():
        try:
            if (
                json.loads(completed.read_text(encoding="utf-8"))
                .get("outcome", "")
                .endswith(("complete", "smoke"))
            ):
                raise ValueError("output directory already contains a completed campaign")
        except json.JSONDecodeError as error:
            raise ValueError("completed output summary is invalid") from error
    output_dir.mkdir(parents=True, exist_ok=True)
    specs = _cell_specs()
    cell_ids = tuple(_cell_id(spec) for spec in specs)
    truths = tuple(_cell_truth(spec) for spec in specs)
    if len(set(cell_ids)) != CELL_COUNT:
        raise ValueError("cell IDs must be unique")
    fixed = goal011.build_fixed_inputs()
    site_ids = tuple(
        site.site_id for site in sorted(fixed.design.sites, key=lambda site: site.site_id)
    )
    references = _load_frozen_references(reference_dir, smoke=config.mode == "smoke")
    reference_paths = [
        Path(references[name])
        for name in ("detector_path", "calibration_path")
        if name in references
    ]
    source_hashes = _source_hashes(
        registration_path,
        reference_paths,
        execution_root=execution_root,
        include_execution_helpers=config.mode != "smoke",
    )
    bank, bank_provenance = _load_bank(config, bank_cache_dir, site_ids)
    input_hash = _json_sha256({"bank": bank_provenance, "references": references})
    if config.mode == "production":
        if budget_receipt_path is None:
            raise ValueError("production requires a bound production budget receipt")
        validate_production_budget(
            budget_receipt_path,
            config=config,
            source_hashes=source_hashes,
            input_hash=input_hash,
            workers=workers,
        )
    elif budget_receipt_path is not None:
        raise ValueError("budget receipts apply only to production")
    seeds = _spawn_seeds(config)
    seed_controls = _seed_controls(config, seeds, bank_provenance)
    setup_started = time.perf_counter()
    setup = _generator().build_generator_setup(fixed)
    setup_seconds = time.perf_counter() - setup_started
    if progress is not None:
        progress(f"Goal 051 field setup complete ({setup_seconds:.3f}s)")
    integration_started = time.perf_counter()
    integration_config = (
        adequacy.production_config("timing")
        if config.mode != "smoke"
        else adequacy.CampaignConfig(
            mode="smoke",
            effects=config.effects,
            evaluation_truths=config.truths,
            original_calibration_replicates=1,
            original_evaluation_replicates=1,
            fresh_calibration_replicates=1,
            fresh_evaluation_replicates=1,
            low_bank_size=min(8, config.bank_size),
            high_bank_size=config.bank_size,
            bank_root=legacy.SMOKE_BANK_ROOT,
        )
    )
    integration = adequacy._build_primary_integration(bank, integration_config, site_ids)
    integration_seconds = time.perf_counter() - integration_started
    if progress is not None:
        progress(f"Goal 051 integration complete ({integration_seconds:.3f}s)")
    contract = {
        "schema_version": 1,
        "workflow": "goal051-misspecification-screen",
        "config": asdict(cast(Any, config)),
        "cell_ids": list(cell_ids),
        "cell_truths": list(truths),
        "source_hashes": source_hashes,
        "reference_manifest": references,
        "bank_provenance": bank_provenance,
        "seed_controls": seed_controls,
        "workers": workers,
        "pairing": {"complete_replicate_unit": True, "cells_per_replicate": CELL_COUNT},
    }
    fingerprint = _json_sha256(contract)
    contract["run_fingerprint"] = fingerprint
    contract_path = output_dir / "run_contract.json"
    if (
        contract_path.exists()
        and json.loads(contract_path.read_text()).get("run_fingerprint") != fingerprint
    ):
        raise ValueError("output directory contains a different frozen run contract")
    if not contract_path.exists():
        _write_json(contract_path, contract)
    shape = (CELL_COUNT, config.replicates, len(config.effects))
    profiles = np.empty(shape, dtype=np.float64)
    holdout = np.empty(shape, dtype=np.float64)
    prey = np.empty((CELL_COUNT, config.replicates), dtype=np.float64)
    predator = np.empty_like(prey)
    mle = np.empty((CELL_COUNT, config.replicates), dtype=np.int64)
    opaque = np.empty((CELL_COUNT, config.replicates), dtype="<U64")
    diagnostics: dict[str, FloatArray] = {}
    phase_started = time.perf_counter()
    pending: list[tuple[int, Any]] = []
    shard_dir = output_dir / "shards"
    shard_dir.mkdir(exist_ok=True)
    for index, seed in enumerate(seeds):
        shard = shard_dir / f"{index:04d}.npz"
        if shard.exists():
            with np.load(shard, allow_pickle=False) as values:
                if str(values.get("source_fingerprint", "")) != fingerprint or str(
                    values.get("seed_fingerprint", "")
                ) != _seed_fingerprint(seed):
                    raise ValueError(
                        f"existing shard is bound to a different source or seed: {shard}"
                    )
                names = (
                    "profiles",
                    "holdout_joint",
                    "prey_score",
                    "predator_score",
                    "mle_index",
                    "opaque_ids",
                )
                payload = {name: np.asarray(values[name]) for name in names}
                diagnostics_json = str(values.get("diagnostics_json", "{}"))
                resumed_diagnostics = {
                    key: np.asarray(value, dtype=np.float64)
                    for key, value in json.loads(diagnostics_json).items()
                }
                if str(values.get("diagnostics_digest", "")) != _diagnostics_digest(
                    resumed_diagnostics
                ):
                    raise ValueError(f"existing shard has an invalid diagnostics hash: {shard}")
                if str(values.get("payload_digest", "")) != _payload_digest(payload):
                    raise ValueError(f"existing shard has an invalid payload hash: {shard}")
                for key, value in resumed_diagnostics.items():
                    diagnostics.setdefault(
                        key, np.full((CELL_COUNT, config.replicates), np.nan, dtype=np.float64)
                    )[:, index] = value
            result = payload
        else:
            pending.append((index, seed))
            continue
        profiles[:, index], holdout[:, index] = result["profiles"], result["holdout_joint"]
        prey[:, index], predator[:, index], mle[:, index], opaque[:, index] = (
            result["prey_score"],
            result["predator_score"],
            result["mle_index"],
            result["opaque_ids"],
        )

    def run(item: tuple[int, Any]) -> tuple[int, dict[str, Any]]:
        index, seed = item
        return index, _score_replicate(fixed, setup, seed, integration, specs, config.effects)

    def store(item: tuple[int, dict[str, Any]]) -> None:
        index, result = item
        payload = {
            name: result[name]
            for name in (
                "profiles",
                "holdout_joint",
                "prey_score",
                "predator_score",
                "mle_index",
                "opaque_ids",
            )
        }
        path = shard_dir / f"{index:04d}.npz"
        if path.exists():
            raise ValueError(f"refusing to overwrite completed shard: {path}")
        np.savez_compressed(
            path,
            **payload,
            diagnostics_json=np.asarray(
                json.dumps(
                    {key: value.tolist() for key, value in result["diagnostics"].items()},
                    sort_keys=True,
                )
            ),
            diagnostics_digest=np.asarray(_diagnostics_digest(result["diagnostics"])),
            source_fingerprint=np.asarray(fingerprint),
            seed_fingerprint=np.asarray(_seed_fingerprint(seeds[index])),
            payload_digest=np.asarray(_payload_digest(payload)),
        )
        profiles[:, index], holdout[:, index] = payload["profiles"], payload["holdout_joint"]
        prey[:, index], predator[:, index], mle[:, index], opaque[:, index] = (
            payload["prey_score"],
            payload["predator_score"],
            payload["mle_index"],
            payload["opaque_ids"],
        )
        for key, value in result["diagnostics"].items():
            diagnostics.setdefault(
                key, np.full((CELL_COUNT, config.replicates), np.nan, dtype=np.float64)
            )[:, index] = value
        if progress is not None and (index + 1) % 100 == 0:
            progress(f"Goal 051 completed {index + 1}/{config.replicates} paired blocks")

    if workers == 1:
        for item in map(run, pending):
            store(item)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for item in executor.map(run, pending):
                store(item)
    generation_seconds = time.perf_counter() - phase_started
    if (
        not np.isfinite(profiles).all()
        or not np.isfinite(holdout).all()
        or not np.isfinite(prey).all()
        or len(set(opaque.ravel().tolist())) != CELL_COUNT * config.replicates
    ):
        raise RuntimeError("campaign output failed finite or identity checks")
    serialization_started = time.perf_counter()
    arrays = {
        "profiles": profiles,
        "holdout_joint": holdout,
        "prey_score": prey,
        "predator_score": predator,
        "mle_index": mle,
        "opaque_ids": opaque,
        "cell_ids": np.asarray(cell_ids),
        "truths": np.asarray(truths, dtype=np.float64),
    }
    arrays.update({f"diagnostic_{name}": value for name, value in diagnostics.items()})
    output_hashes: dict[str, str] = {}
    packed_path = output_dir / "campaign_arrays.npz"
    np.savez_compressed(packed_path, **cast(Any, arrays))
    output_hashes[packed_path.name] = _file_sha256(packed_path)
    frozen = {
        "schema_version": 1,
        "metadata_joined": True,
        "endpoints_evaluated": False,
        "run_fingerprint": fingerprint,
        "cell_ids": list(cell_ids),
        "truths": list(truths),
        "grid": list(config.effects),
        "files": output_hashes,
        "reference_manifest": references,
    }
    _write_json(output_dir / "frozen_scores.json", frozen)
    serialization_seconds = time.perf_counter() - serialization_started
    validation_started = time.perf_counter()
    validation = {
        "profiles_shape": profiles.shape == shape,
        "holdout_shape": holdout.shape == shape,
        "score_shapes": prey.shape == (CELL_COUNT, config.replicates)
        and predator.shape == prey.shape
        and mle.shape == prey.shape
        and opaque.shape == prey.shape,
        "all_main_arrays_finite": all(
            np.isfinite(array).all() for array in (profiles, holdout, prey, predator, mle)
        ),
        "profile_minimum_zero": bool(np.all(np.min(profiles, axis=-1) == 0.0)),
        "mle_matches_lowest_index": bool(np.array_equal(mle, np.argmin(profiles, axis=-1))),
        "grid_is_registered": tuple(config.effects)
        == tuple(EFFECT_GRID if config.mode != "smoke" else config.effects),
        "cell_ids_in_registered_order": cell_ids == tuple(_cell_id(spec) for spec in specs),
        "truths_in_registered_order": truths == tuple(_cell_truth(spec) for spec in specs),
        "opaque_ids_nonempty_unique": all(bool(value) for value in opaque.ravel())
        and len(set(opaque.ravel().tolist())) == CELL_COUNT * config.replicates,
        "seed_controls": seed_controls,
    }
    if not all(
        value is True for value in validation.values() if isinstance(value, (bool, np.bool_))
    ):
        raise RuntimeError("campaign validation failed")
    validation_seconds = time.perf_counter() - validation_started
    actual_seconds = time.perf_counter() - run_started
    timing = {
        "field_setup": setup_seconds,
        "integration": integration_seconds,
        "generation_scoring": generation_seconds,
        "serialization": serialization_seconds,
        "validation": validation_seconds,
        "total": actual_seconds,
    }
    measured_components = (
        setup_seconds
        + integration_seconds
        + generation_seconds
        + serialization_seconds
        + validation_seconds
    )
    startup_overhead = max(0.0, actual_seconds - measured_components)
    fixed_cost = setup_seconds + integration_seconds + startup_overhead
    scalable_cost = (
        (generation_seconds + serialization_seconds + validation_seconds)
        * 1_000
        / config.replicates
    )
    production_workload = 1.5 * (fixed_cost + scalable_cost)
    projection = {
        "scoring_projection_factor": 1.5,
        "timing_replicates": config.replicates,
        "production_replicates": 1_000,
        "startup_overhead_seconds": startup_overhead,
        "fixed_cost_seconds": fixed_cost,
        "scalable_cost_seconds": scalable_cost,
        "production_workload_seconds_conservative": production_workload,
        "preparation_seconds": PREPARATION_SECONDS,
        "timing_seconds_actual": actual_seconds,
        "synthesis_seconds_reserved": SYNTHESIS_SECONDS,
        "total_projected_seconds": production_workload
        + PREPARATION_SECONDS
        + actual_seconds
        + SYNTHESIS_SECONDS,
    }
    outcome = (
        "non_scientific_smoke"
        if config.mode == "smoke"
        else "timing_complete"
        if config.mode == "timing"
        else "production_complete"
    )
    summary = {
        **contract,
        "timings": timing,
        "timings_sha256": _json_sha256(timing),
        "timing_projection": projection,
        "validation": validation,
        "output_hashes": output_hashes,
        "frozen_scores_sha256": _file_sha256(output_dir / "frozen_scores.json"),
        "input_hash": input_hash,
        "outcome": outcome,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "completed_utc": datetime.now(UTC).isoformat(),
    }
    _write_json(output_dir / "run_summary.json", summary)
    return summary


__all__ = [
    "CampaignConfig",
    "production_config",
    "run_campaign",
    "smoke_config",
    "timing_config",
    "validate_production_budget",
]
