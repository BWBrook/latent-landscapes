"""Run the fixed archive-replay pilot with shared, exact beta-row integrations."""

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
from latent_landscapes import adjusted_background_replay as replay
from latent_landscapes import arc2b_campaign as prey
from latent_landscapes import arc2c_likelihood as joint
from latent_landscapes import misspecification_generator as generator
from latent_landscapes import model_adequacy_campaign as adequacy
from latent_landscapes.goal011 import benchmark as goal011

EFFECTS = tuple(float(x) for x in np.linspace(1.0, 10.0, 181))
BETAS = tuple(float(x) for x in np.linspace(-2.0, 2.0, 81))
TIMING_BETAS = (-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0)
REGISTRATION = Path("docs/goals/052-adjusted-background-pilot/registration-2026-09-24.md")
SCORE_TOLERANCE = 1e-10
ARCHIVE_CONTRACT_SHA256 = "750c0735701bfdc91f4d80aa5c67dc14db50b0c1c6615261364771674caa44c4"
ROW_SHAPES = {
    "latent_training": (24, 181),
    "latent_holdout_joint": (24, 181),
    "oracle_training": (24, 181),
    "oracle_holdout": (24, 181),
    "latent_holdout_predator": (24,),
    "h1_max_abs_difference": (),
}


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def source_hashes(repository: Path) -> dict[str, str]:
    paths = [
        *sorted((repository / "src").rglob("*.py")),
        *sorted((repository / "tests").glob("test_adjusted_background_*.py")),
        repository / "scripts/run_adjusted_background_pilot.py",
        repository / REGISTRATION,
        repository / "pyproject.toml",
        repository / "uv.lock",
    ]
    return {str(path.relative_to(repository)): sha256(path) for path in paths}


def verify_legacy_sources(repository: Path, contract_path: Path) -> dict[str, Any]:
    if sha256(contract_path) != ARCHIVE_CONTRACT_SHA256:
        raise ValueError("frozen Goal 051 run-contract digest does not match")
    contract = json.loads(contract_path.read_text())
    expected = contract["source_hashes"]
    relative = {name: digest for name, digest in expected.items() if not Path(name).is_absolute()}
    for name, digest in relative.items():
        if sha256(repository / name) != digest:
            raise ValueError(f"frozen Goal 051 source/input changed: {name}")
    return {"relative_files_verified": len(relative), "contract_sha256": sha256(contract_path)}


def load_row(
    data_path: Path, receipt_path: Path, *, fingerprint: str, index: int, beta: float
) -> tuple[dict[str, np.ndarray], dict[str, Any]] | None:
    """Validate committed rows; preserve uncommitted fragments for diagnosis."""
    if not data_path.exists() or not receipt_path.exists():
        suffix = f".uncommitted-{time.time_ns()}"
        for path in (
            data_path,
            receipt_path,
            data_path.with_suffix(".npz.tmp"),
            receipt_path.with_suffix(".json.tmp"),
        ):
            if path.exists():
                path.rename(path.with_name(path.name + suffix))
        return None
    receipt = json.loads(receipt_path.read_text())
    if (
        receipt["fingerprint"] != fingerprint
        or receipt["index"] != index
        or receipt["beta"] != beta
        or sha256(data_path) != receipt["sha256"]
    ):
        raise ValueError(f"beta row identity mismatch: {index}")
    with np.load(data_path, allow_pickle=False) as data:
        if set(data.files) != set(ROW_SHAPES):
            raise ValueError(f"beta row schema mismatch: {index}")
        values = {name: data[name] for name in data.files}
    if any(
        value.shape != ROW_SHAPES[name] or value.dtype != np.float64 or not np.isfinite(value).all()
        for name, value in values.items()
    ):
        raise ValueError(f"beta row values/shapes mismatch: {index}")
    if values["h1_max_abs_difference"].item() > SCORE_TOLERANCE:
        raise ValueError("cached h=1 factorization control failed")
    return values, receipt


def save_row(
    data_path: Path,
    receipt_path: Path,
    values: dict[str, np.ndarray],
    receipt: dict[str, Any],
    *,
    started: float | None = None,
) -> None:
    """Commit data atomically and its authenticated receipt last."""
    data_temp = data_path.with_suffix(".npz.tmp")
    receipt_temp = receipt_path.with_suffix(".json.tmp")
    with data_temp.open("wb") as handle:
        np.savez_compressed(handle, **cast(Any, values))
        handle.flush()
        os.fsync(handle.fileno())
    receipt["sha256"] = sha256(data_temp)
    if started is not None:
        receipt["seconds"] = time.perf_counter() - started
    write_json(receipt_temp, receipt)
    data_temp.replace(data_path)
    receipt_temp.replace(receipt_path)


def _score_row(
    beta: float,
    prepared: likelihood.PreparedBank,
    all_a: np.ndarray,
    site_a: np.ndarray,
    cells: tuple[generator.GeneratedCell, ...],
) -> dict[str, np.ndarray]:
    hazards = likelihood.normalized_hazards(beta, all_a, site_a)
    integration = likelihood.build_integration(prepared, EFFECTS, hazards)
    shape = (len(cells), len(EFFECTS))
    values: dict[str, np.ndarray] = {
        name: np.empty(shape)
        for name in ("latent_training", "latent_holdout_joint", "oracle_training", "oracle_holdout")
    }
    predator = np.empty(len(cells))
    max_h1_difference = 0.0
    for index, cell in enumerate(cells):
        histories = cast(Any, cell.dataset.histories)
        train, heldout, marginal = joint.evaluate_dataset(histories, integration)
        values["latent_training"][index] = train[0]
        values["latent_holdout_joint"][index] = heldout[0]
        predator[index] = marginal[0]
        oracle_train, oracle_heldout = likelihood.oracle_evaluate_dataset(
            histories,
            cell.latent_truth.arrival,
            EFFECTS,
            hazards,
            site_ids=prepared.site_ids,
        )
        values["oracle_training"][index] = oracle_train
        values["oracle_holdout"][index] = oracle_heldout
        ordered, positions = joint._prepare_histories(histories, integration)
        emissions = prey._predator_category_probabilities(ordered, 0.65)
        margins = np.einsum("sc,sc->s", integration.category_mass[0, positions], emissions)
        training_mask = np.asarray([row.split == "training" for row in ordered])
        train_predator = np.log(margins[training_mask]).sum()
        h1_difference = max(
            abs(train[0, 0] - train_predator - oracle_train[0]),
            abs(heldout[0, 0] - marginal[0] - oracle_heldout[0]),
        )
        max_h1_difference = max(max_h1_difference, float(h1_difference))
        if h1_difference > SCORE_TOLERANCE:
            raise RuntimeError("h=1 prey likelihood depends on arrival information")
    values["latent_holdout_predator"] = predator
    values["h1_max_abs_difference"] = np.asarray(max_h1_difference, dtype=np.float64)
    if not all(np.isfinite(value).all() for value in values.values()):
        raise RuntimeError(f"non-finite beta row {beta}")
    return values


def run_pilot(
    *,
    output_dir: Path,
    bank_cache: Path,
    archive_path: Path,
    archive_contract: Path,
    execution_wrapper: Path,
    workers: int = 8,
    max_seconds: int = 14_400,
) -> dict[str, Any]:
    """Qualify the frozen replay and complete each numerical row at most once.

    An external exclusive lock owns process-level dispatch. Completed row files
    can be reused after an operational interruption only under identical source,
    input and grid bindings. A completed pilot is never rerun.
    """
    started = time.perf_counter()
    if not 1 <= workers <= 32 or max_seconds < 1800:
        raise ValueError("invalid resource envelope")
    repository = Path(__file__).resolve().parents[2]
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "run_summary.json"
    if summary_path.exists():
        raise ValueError("completed pilot already has a run summary; refusing rerun")
    sources = source_hashes(repository)
    wrapper_hash = sha256(execution_wrapper)
    frozen_sources = verify_legacy_sources(repository, archive_contract)
    archive = replay.load_production_archive(archive_path)
    fixed = goal011.build_fixed_inputs()
    setup = generator.build_generator_setup(fixed)
    site_ids = setup.site_ids
    bank, bank_provenance = adequacy._load_bank(
        adequacy.production_config("timing"), bank_cache, site_ids
    )
    contract = {
        "workflow": "goal052_fixed_archive_adjusted_background_pilot_v1",
        "source_hashes": sources,
        "execution_wrapper_sha256": wrapper_hash,
        "legacy_source_control": frozen_sources,
        "archive_sha256": archive.sha256,
        "bank": bank_provenance,
        "effects": EFFECTS,
        "betas": BETAS,
        "replicate_indices": replay.REPLAY_REPLICATE_INDICES,
        "cell_ids": replay.REPLAY_CELL_IDS,
        "alpha": 1.0,
        "mean_background_hazard": 0.002,
        "python": platform.python_version(),
        "numpy": np.__version__,
    }
    fingerprint = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
    contract["fingerprint"] = fingerprint
    contract_path = output_dir / "run_contract.json"
    if contract_path.exists():
        if json.loads(contract_path.read_text()) != json.loads(json.dumps(contract)):
            raise ValueError("existing row cache belongs to different source or inputs")
    else:
        write_json(contract_path, contract)
    attempt = {
        "started_utc": datetime.now(UTC).isoformat(),
        "workers": workers,
        "max_seconds": max_seconds,
        "fingerprint": fingerprint,
    }
    with (output_dir / "attempts.jsonl").open("a") as handle:
        handle.write(json.dumps(attempt) + "\n")
    print("Verified frozen source, archive and K131072 bank; building legacy control", flush=True)
    legacy_started = time.perf_counter()
    legacy_integration = adequacy._build_primary_integration(
        bank, adequacy.production_config("timing"), site_ids
    )
    legacy_seconds = time.perf_counter() - legacy_started
    cells: list[generator.GeneratedCell] = []
    replay_receipts = []
    for replicate in replay.REPLAY_REPLICATE_INDICES:
        selected = replay.replay_selected_cells(fixed, setup, replicate)
        check = replay.verify_original_replay(
            selected, legacy_integration, replicate, archive=archive
        )
        replay_receipts.append(asdict(check))
        cells.extend(selected)
    panel = tuple(cells)
    write_json(output_dir / "replay_checks.json", replay_receipts)
    print("All 24 legacy histories replay exactly", flush=True)
    prepared = likelihood.prepare_bank(bank, site_ids)
    all_a = setup.exposure_score
    site_a = all_a[setup.site_rows, setup.site_cols]
    row_dir = output_dir / "rows"
    row_dir.mkdir(exist_ok=True)

    def row_paths(index: int) -> tuple[Path, Path]:
        return row_dir / f"{index:03d}.npz", row_dir / f"{index:03d}.json"

    def read_row(index: int) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
        data_path, receipt_path = row_paths(index)
        cached = load_row(
            data_path, receipt_path, fingerprint=fingerprint, index=index, beta=BETAS[index]
        )
        if cached is None:
            raise ValueError(f"beta row not committed: {index}")
        return cached

    def compute_row(index: int) -> dict[str, Any]:
        data_path, receipt_path = row_paths(index)
        cached = load_row(
            data_path, receipt_path, fingerprint=fingerprint, index=index, beta=BETAS[index]
        )
        if cached is not None:
            return cached[1]
        row_started = time.perf_counter()
        values = _score_row(BETAS[index], prepared, all_a, site_a, panel)
        receipt = {
            "index": index,
            "beta": BETAS[index],
            "fingerprint": fingerprint,
            "seconds": time.perf_counter() - row_started,
        }
        save_row(data_path, receipt_path, values, receipt, started=row_started)
        print(f"beta={BETAS[index]:+.2f} complete ({receipt['seconds']:.2f}s)", flush=True)
        return receipt

    timing_indices = [int(np.argmin(np.abs(np.asarray(BETAS) - beta))) for beta in TIMING_BETAS]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        timing_receipts = list(executor.map(compute_row, timing_indices))

    zero_index = BETAS.index(0.0)
    zero, _ = read_row(zero_index)
    legacy_train = []
    legacy_holdout = []
    legacy_predator = []
    for cell in panel:
        train, heldout, predator = joint.evaluate_dataset(
            cast(Any, cell.dataset.histories), legacy_integration
        )
        legacy_train.append(train[0])
        legacy_holdout.append(heldout[0])
        legacy_predator.append(predator[0])
    control_differences = {
        "training_log_score_max_abs": float(np.max(np.abs(zero["latent_training"] - legacy_train))),
        "holdout_joint_max_abs": float(
            np.max(np.abs(zero["latent_holdout_joint"] - legacy_holdout))
        ),
        "holdout_predator_max_abs": float(
            np.max(np.abs(zero["latent_holdout_predator"] - legacy_predator))
        ),
    }
    for name in ("training", "holdout"):
        original = np.asarray(legacy_train if name == "training" else legacy_holdout)
        updated = zero["latent_training" if name == "training" else "latent_holdout_joint"]
        original_lr = 2 * (original.max(axis=1, keepdims=True) - original)
        updated_lr = 2 * (updated.max(axis=1, keepdims=True) - updated)
        control_differences[f"{name}_LR_max_abs"] = float(np.max(np.abs(original_lr - updated_lr)))
    write_json(output_dir / "beta_zero_checks.json", control_differences)
    if max(control_differences.values()) > SCORE_TOLERANCE:
        raise RuntimeError(f"factored beta=0 kernel failed: {control_differences}")

    pending = [
        i
        for i in range(len(BETAS))
        if load_row(*row_paths(i), fingerprint=fingerprint, index=i, beta=BETAS[i]) is None
    ]
    elapsed = time.perf_counter() - started
    slowest = max(row["seconds"] for row in timing_receipts)
    projection = {
        "fingerprint": fingerprint,
        "workers": workers,
        "elapsed_seconds": elapsed,
        "legacy_construction_seconds": legacy_seconds,
        "timing_indices": timing_indices,
        "slowest_measured_row_seconds": slowest,
        "remaining_rows": len(pending),
        "factor": 1.5,
        "remaining_grid_projected_seconds": 1.5 * slowest * math.ceil(len(pending) / workers),
        "synthesis_verification_reserve_seconds": 1800,
        "max_seconds": max_seconds,
    }
    projection["complete_projected_seconds"] = (
        elapsed + projection["remaining_grid_projected_seconds"] + 1800
    )
    write_json(output_dir / "timing_projection.json", projection)
    if source_hashes(repository) != sources or sha256(execution_wrapper) != wrapper_hash:
        raise RuntimeError("source changed during numerical/timing qualification")
    if projection["complete_projected_seconds"] > max_seconds:
        raise RuntimeError("measured workload needs an operational resource/time revision")
    print(
        f"Controls pass; complete projection {projection['complete_projected_seconds']:.0f}s "
        f"within {max_seconds}s; continuing {len(pending)} rows",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(compute_row, index) for index in pending]
        for future in as_completed(futures):
            future.result()

    rows = [read_row(index) for index in range(len(BETAS))]
    score_names = ("latent_training", "latent_holdout_joint", "oracle_training", "oracle_holdout")
    evidence = {name: np.stack([row[0][name] for row in rows], axis=1) for name in score_names}
    predator_rows = np.stack([row[0]["latent_holdout_predator"] for row in rows])
    if not np.array_equal(predator_rows, np.broadcast_to(predator_rows[0], predator_rows.shape)):
        raise RuntimeError("predator marginal changed with beta")
    evidence.update(
        {
            "effects": np.asarray(EFFECTS),
            "betas": np.asarray(BETAS),
            "cell_ids": np.asarray([cell.cell.cell_id for cell in panel]),
            "replicate_indices": np.repeat(replay.REPLAY_REPLICATE_INDICES, 4),
            "truth_h": np.asarray([cell.cell.truth_h for cell in panel]),
            "opaque_ids": np.asarray([cell.dataset.opaque_id for cell in panel]),
            "site_ids": np.asarray(site_ids),
            "site_A": site_a,
            "map_A": all_a,
            "training_mask": np.asarray([split == "training" for split in setup.site_splits]),
            "true_arrival": np.stack([cell.latent_truth.arrival for cell in panel]),
            "true_extirpation": np.stack([cell.latent_truth.prey_extirpation for cell in panel]),
            "true_hazards": np.stack([cell.latent_truth.background_hazard for cell in panel]),
            "predator_counts": np.asarray(
                [
                    [row.predator_detection_counts for row in cell.dataset.histories]
                    for cell in panel
                ]
            ),
            "prey_counts": np.asarray(
                [[row.prey_detection_counts for row in cell.dataset.histories] for cell in panel]
            ),
            "latent_holdout_predator": predator_rows[0],
            "legacy_training": np.asarray(legacy_train),
            "legacy_holdout_joint": np.asarray(legacy_holdout),
        }
    )
    evidence_path = output_dir / "evidence.npz"
    np.savez_compressed(evidence_path, **cast(Any, evidence))
    if source_hashes(repository) != sources or sha256(execution_wrapper) != wrapper_hash:
        raise RuntimeError("source changed during production")
    summary = {
        "outcome": "completed_fixed_24_history_grid_pilot",
        "finished_utc": datetime.now(UTC).isoformat(),
        "fingerprint": fingerprint,
        "source_identity_unchanged": True,
        "archive_sha256": archive.sha256,
        "bank_checksum": prepared.bank_checksum,
        "evidence_sha256": sha256(evidence_path),
        "rows_verified": len(rows),
        "histories": len(panel),
        "elapsed_seconds": time.perf_counter() - started,
        "legacy_construction_seconds": legacy_seconds,
        "workers": workers,
        "row_seconds": [row[1]["seconds"] for row in rows],
        "beta_zero_checks": control_differences,
        "h1_factorization_max_abs_difference": max(
            float(row[0]["h1_max_abs_difference"]) for row in rows
        ),
        "exact_legacy_replay_passed": all(
            check["controls"] and all(check["controls"].values()) for check in replay_receipts
        ),
        "timing_projection": projection,
        "limitations": [
            "Retrospective six-block pilot, not confirmation or recovery.",
            "Finite grid, fixed empirical bank, known nuisances and one landscape.",
            "A-only adjustment omits G; no nonzero-beta exact-model positive-control history.",
            "Likelihood geometry is uncalibrated; no previous cutoffs applied.",
        ],
    }
    write_json(summary_path, summary)
    print(f"Pilot complete in {summary['elapsed_seconds']:.1f}s", flush=True)
    return summary
