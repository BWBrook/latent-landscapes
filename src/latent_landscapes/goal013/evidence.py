"""Strict authentication and reconciliation of accepted weak-contrast evidence."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from math import isfinite
from pathlib import Path
from statistics import fmean, median
from typing import Any

from latent_landscapes.goal002.calibration import normal_mean_interval
from latent_landscapes.goal010 import benchmark as goal010
from latent_landscapes.goal012 import artifacts as goal012_artifacts

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOAL009_EVIDENCE_DIR = (
    REPOSITORY_ROOT
    / "artifacts/goal009_remote_runs/goal009-20260727T093142Z-9cb53de/scientific-pack"
)
DEFAULT_GOAL012_EVIDENCE_DIR = (
    REPOSITORY_ROOT / "artifacts/goal012_remote_runs/goal012-20260730T142431Z-b2bdfbb/output"
)
GOAL009_TRUTH_SUMMARY_SHA256 = "bc4fce39bd3e2e0ca034089d0a800623e278783c4e88d7d6b75dacdd44599096"
GOAL012_TRUTH_SUMMARY_SHA256 = "40b1481af552b94573de4379d727fc1223ed08c6b6d8f1214117cfd9e01f34c9"
GOAL012_VERIFICATION_SHA256 = "0d25f0d0d8600bc3ef06daf094ac93a44426c682895edd691a956336c07b385f"
GOAL012_RUN_ID = "goal012-20260730T142431Z-b2bdfbb"
GOAL012_SOURCE_COMMIT = "b2bdfbb95051bfec09676c4cdbfa4e2e0303fd97"
GOAL012_OUTCOME = "cross_truth_design_limited"
WEAK_CELL_IDS = ("cell-00", "cell-01", "cell-02")
BANK_VARIANT_NAMES = ("full", "first_half", "second_half")


@dataclass(frozen=True, slots=True)
class EvidenceIdentity:
    source_goal: str
    path_identifier: str
    run_id: str
    source_commit: str
    outcome: str
    truth_cell_summary_sha256: str
    validation_results_sha256: str
    verification_sha256: str


@dataclass(frozen=True, slots=True)
class EvidenceReconciliationRow:
    source_goal: str
    truth_cell: str
    truth_rho: float
    truth_eta: float
    observation_representation: str
    candidate_eta_minimum: float
    candidate_eta_maximum: float
    descriptive_eta_maximum: float | None
    bank_variants: tuple[str, ...]
    bank_coverage_success_counts: tuple[int, ...]
    bank_connected_interior_counts: tuple[int, ...]
    bank_physical_connected_interior_counts: tuple[int, ...]
    bank_eta_zero_contact_counts: tuple[int, ...]
    bank_artificial_face_contact_counts: tuple[int, ...]
    bank_classes: tuple[str, ...]
    full_bank_eta_zero_contact_count: int
    full_bank_median_absolute_log_rho_error: float
    full_bank_median_absolute_eta_error: float
    full_bank_median_projected_log_rho_width: float
    full_bank_median_projected_eta_width: float
    full_bank_paired_brier_estimate: float
    full_bank_paired_brier_lower: float
    full_bank_paired_brier_upper: float
    full_bank_mean_stochastic_brier_worst_mle: float
    full_bank_mean_neutral_brier: float
    full_bank_finite_log_score_count: int


@dataclass(frozen=True, slots=True)
class BaselineValidationContact:
    truth_cell: str
    bank_variant: str
    block_index: int
    eta_zero_contact: bool


@dataclass(frozen=True, slots=True)
class ExistingEvidence:
    goal009: EvidenceIdentity
    goal012: EvidenceIdentity
    rows: tuple[EvidenceReconciliationRow, ...]
    goal012_contacts: tuple[BaselineValidationContact, ...]
    invariants: dict[str, bool]


@dataclass(frozen=True, slots=True)
class _Goal012Pack:
    identity: EvidenceIdentity
    config: dict[str, object]
    summary_rows: tuple[dict[str, str], ...]
    validation_rows: tuple[dict[str, str], ...]


@lru_cache(maxsize=8)
def authenticate_existing_evidence(
    goal009_evidence_dir: Path = DEFAULT_GOAL009_EVIDENCE_DIR,
    goal012_evidence_dir: Path = DEFAULT_GOAL012_EVIDENCE_DIR,
) -> ExistingEvidence:
    """Authenticate both published packs and recompute all six weak rows."""
    goal009_path = Path(goal009_evidence_dir)
    goal012_path = Path(goal012_evidence_dir)
    goal009_pack = goal010.read_goal009_pack(goal009_path, require_published=True)
    goal009_summary_hash = _sha256(goal009_path / "truth_cell_summary.csv")
    if goal009_summary_hash != GOAL009_TRUTH_SUMMARY_SHA256:
        raise ValueError("Goal009 truth-cell summary hash mismatch")
    goal009_identity = EvidenceIdentity(
        source_goal="009",
        path_identifier=(
            "artifacts/goal009_remote_runs/goal009-20260727T093142Z-9cb53de/scientific-pack"
        ),
        run_id=_required_string(goal009_pack.compute_provenance, "run_id"),
        source_commit=_required_string(
            goal009_pack.compute_provenance,
            "source_commit",
        ),
        outcome=goal009_pack.outcome,
        truth_cell_summary_sha256=goal009_summary_hash,
        validation_results_sha256=_sha256(goal009_path / "validation_results.csv"),
        verification_sha256=goal009_pack.verification_sha256,
    )
    goal012_pack = _read_goal012_pack(goal012_path)

    goal009_rows = _reconcile_source(
        source_goal="009",
        config=goal009_pack.config,
        validation_rows=goal009_pack.validation_rows,
        summary_rows=goal009_pack.summary_rows,
    )
    goal012_rows = _reconcile_source(
        source_goal="012",
        config=goal012_pack.config,
        validation_rows=goal012_pack.validation_rows,
        summary_rows=goal012_pack.summary_rows,
    )
    contacts = tuple(
        BaselineValidationContact(
            truth_cell=row["truth_cell"],
            bank_variant=row["bank_variant"],
            block_index=_integer(row["block_index"], "block_index"),
            eta_zero_contact=(
                "eta_min"
                in _faces(
                    row["expanded_support_boundary_faces"],
                    "expanded_support_boundary_faces",
                )
            ),
        )
        for row in goal012_pack.validation_rows
        if row["truth_cell"] in WEAK_CELL_IDS
    )
    invariants = {
        "published_goal009_identity": goal009_pack.is_published_goal009,
        "published_goal012_identity": (
            goal012_pack.identity.verification_sha256 == GOAL012_VERIFICATION_SHA256
        ),
        "truth_cell_summary_hashes": (
            goal009_identity.truth_cell_summary_sha256 == GOAL009_TRUTH_SUMMARY_SHA256
            and goal012_pack.identity.truth_cell_summary_sha256 == GOAL012_TRUTH_SUMMARY_SHA256
        ),
        "six_weak_reconciliation_rows": len(goal009_rows) == len(goal012_rows) == 3,
        "goal012_contact_row_identity": len(contacts) == 3 * 3 * 500
        and len({(row.truth_cell, row.bank_variant, row.block_index) for row in contacts})
        == len(contacts),
    }
    if not all(invariants.values()):
        raise ValueError("accepted evidence failed reconciliation invariants")
    return ExistingEvidence(
        goal009=goal009_identity,
        goal012=goal012_pack.identity,
        rows=(*goal009_rows, *goal012_rows),
        goal012_contacts=contacts,
        invariants=invariants,
    )


def _read_goal012_pack(path: Path) -> _Goal012Pack:
    if not path.is_dir():
        raise ValueError("Goal012 pack directory does not exist")
    items = tuple(path.rglob("*"))
    if any(item.is_symlink() for item in items):
        raise ValueError("Goal012 pack must not contain symbolic links")
    observed = {item.relative_to(path).as_posix() for item in items if item.is_file()}
    if observed != set(goal012_artifacts.EXPECTED_FILES):
        raise ValueError("Goal012 pack does not match the exact 15-file contract")
    verification = _read_json_object(path / "verification.json")
    config = _read_json_object(path / "config.json")
    compute = _read_json_object(path / "compute_provenance.json")
    summary = _read_json_object(path / "summary.json")
    expected_hashes = verification.get("sha256")
    expected_paths = set(goal012_artifacts.EXPECTED_FILES) - {"verification.json"}
    if not isinstance(expected_hashes, dict) or set(expected_hashes) != expected_paths:
        raise ValueError("Goal012 verification hash surface is incomplete")
    for relative in sorted(expected_paths):
        expected = expected_hashes.get(relative)
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("Goal012 verification contains an invalid hash")
        if _sha256(path / relative) != expected:
            raise ValueError(f"Goal012 pack hash mismatch for {relative}")
    verification_hash = _sha256(path / "verification.json")
    summary_hash = _sha256(path / "truth_cell_summary.csv")
    published = (
        verification_hash == GOAL012_VERIFICATION_SHA256
        and summary_hash == GOAL012_TRUTH_SUMMARY_SHA256
        and compute.get("run_id") == GOAL012_RUN_ID
        and compute.get("source_commit") == GOAL012_SOURCE_COMMIT
        and summary.get("outcome") == GOAL012_OUTCOME
        and verification.get("outcome") == GOAL012_OUTCOME
        and verification.get("all_invariants_pass") is True
        and verification.get("compute_provenance_validated") is True
        and config.get("goal") == "012"
        and config.get("truth_cell_order") == [f"cell-{index:02d}" for index in range(9)]
        and config.get("bank_size") == 4096
        and config.get("calibration_blocks") == 500
        and config.get("validation_blocks") == 500
        and config.get("calibration_rank_one_based") == 476
        and config.get("known_detection_probability") == 0.65
        and config.get("records_per_dataset") == 1920
        and config.get("training_records_per_dataset") == 1440
        and config.get("holdout_records_per_dataset") == 480
        and config.get("candidate_etas")
        == [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5]
    )
    if not published:
        raise ValueError("pack does not match the published Goal012 identity")
    validation_rows = _read_csv(path / "validation_results.csv")
    summary_rows = _read_csv(path / "truth_cell_summary.csv")
    if len(validation_rows) != 9 * 3 * 500 or len(summary_rows) != 9 * 3:
        raise ValueError("Goal012 table row counts do not match production")
    validation_ids = tuple(
        (
            row.get("phase"),
            row.get("truth_cell"),
            row.get("bank_variant"),
            row.get("block_index"),
        )
        for row in validation_rows
    )
    summary_ids = tuple((row.get("truth_cell"), row.get("bank_variant")) for row in summary_rows)
    if len(set(validation_ids)) != len(validation_ids) or len(set(summary_ids)) != len(summary_ids):
        raise ValueError("Goal012 tables contain duplicate row identities")
    expected_validation_ids = {
        ("validation", f"cell-{cell:02d}", bank, str(block))
        for cell in range(9)
        for bank in BANK_VARIANT_NAMES
        for block in range(500)
    }
    expected_summary_ids = {
        (f"cell-{cell:02d}", bank) for cell in range(9) for bank in BANK_VARIANT_NAMES
    }
    if set(validation_ids) != expected_validation_ids or set(summary_ids) != expected_summary_ids:
        raise ValueError("Goal012 table row identities are incomplete")
    return _Goal012Pack(
        identity=EvidenceIdentity(
            source_goal="012",
            path_identifier=(
                "artifacts/goal012_remote_runs/goal012-20260730T142431Z-b2bdfbb/output"
            ),
            run_id=GOAL012_RUN_ID,
            source_commit=GOAL012_SOURCE_COMMIT,
            outcome=GOAL012_OUTCOME,
            truth_cell_summary_sha256=summary_hash,
            validation_results_sha256=_sha256(path / "validation_results.csv"),
            verification_sha256=verification_hash,
        ),
        config=config,
        summary_rows=summary_rows,
        validation_rows=validation_rows,
    )


def _reconcile_source(
    *,
    source_goal: str,
    config: dict[str, object],
    validation_rows: tuple[dict[str, str], ...],
    summary_rows: tuple[dict[str, str], ...],
) -> tuple[EvidenceReconciliationRow, ...]:
    by_summary = {(row["truth_cell"], row["bank_variant"]): row for row in summary_rows}
    reconciled: list[EvidenceReconciliationRow] = []
    for cell_id in WEAK_CELL_IDS:
        bank_aggregates = tuple(
            _aggregate_bank(
                source_goal=source_goal,
                rows=tuple(
                    row
                    for row in validation_rows
                    if row["truth_cell"] == cell_id and row["bank_variant"] == bank
                ),
                summary=by_summary[(cell_id, bank)],
            )
            for bank in BANK_VARIANT_NAMES
        )
        full = bank_aggregates[0]
        reconciled.append(
            EvidenceReconciliationRow(
                source_goal=source_goal,
                truth_cell=cell_id,
                truth_rho=full["truth_rho"],
                truth_eta=full["truth_eta"],
                observation_representation=(
                    "perfect_detection_collapsed_site_time_outcomes"
                    if source_goal == "009"
                    else "complete_two_visit_histories_known_p_0.65"
                ),
                candidate_eta_minimum=0.0,
                candidate_eta_maximum=(
                    float(max(_finite_sequence(config.get("candidate_etas"), "candidate_etas")))
                ),
                descriptive_eta_maximum=2.0 if source_goal == "012" else None,
                bank_variants=BANK_VARIANT_NAMES,
                bank_coverage_success_counts=tuple(
                    row["coverage_count"] for row in bank_aggregates
                ),
                bank_connected_interior_counts=tuple(
                    row["connected_interior_count"] for row in bank_aggregates
                ),
                bank_physical_connected_interior_counts=tuple(
                    row["physical_connected_interior_count"] for row in bank_aggregates
                ),
                bank_eta_zero_contact_counts=tuple(
                    row["eta_zero_contact_count"] for row in bank_aggregates
                ),
                bank_artificial_face_contact_counts=tuple(
                    row["artificial_face_contact_count"] for row in bank_aggregates
                ),
                bank_classes=tuple(row["cell_class"] for row in bank_aggregates),
                full_bank_eta_zero_contact_count=full["eta_zero_contact_count"],
                full_bank_median_absolute_log_rho_error=full["rho_error"],
                full_bank_median_absolute_eta_error=full["eta_error"],
                full_bank_median_projected_log_rho_width=full["rho_width"],
                full_bank_median_projected_eta_width=full["eta_width"],
                full_bank_paired_brier_estimate=full["brier_estimate"],
                full_bank_paired_brier_lower=full["brier_lower"],
                full_bank_paired_brier_upper=full["brier_upper"],
                full_bank_mean_stochastic_brier_worst_mle=full["mean_stochastic_brier"],
                full_bank_mean_neutral_brier=full["mean_neutral_brier"],
                full_bank_finite_log_score_count=full["finite_log_score_count"],
            )
        )
    return tuple(reconciled)


def _aggregate_bank(
    *,
    source_goal: str,
    rows: tuple[dict[str, str], ...],
    summary: dict[str, str],
) -> dict[str, Any]:
    if len(rows) != 500:
        raise ValueError("evidence cell-bank must contain exactly 500 validation rows")
    if {int(row["block_index"]) for row in rows} != set(range(500)):
        raise ValueError("evidence validation block identities are incomplete")
    prefix = "" if source_goal == "009" else "expanded_"
    included_field = f"{prefix}truth_included"
    component_field = f"{prefix}support_component_count"
    boundary_field = f"{prefix}support_boundary_contact"
    faces_field = f"{prefix}support_boundary_faces"
    rho_error_field = f"{prefix}minimum_absolute_log_rho_error"
    eta_error_field = f"{prefix}minimum_absolute_eta_error"
    rho_width_field = f"{prefix}projected_log_rho_width"
    eta_width_field = f"{prefix}projected_eta_width"
    brier_field = f"{prefix}paired_brier_difference"
    stochastic_brier_field = f"{prefix}stochastic_brier_maximum"
    stochastic_log_min_field = f"{prefix}stochastic_log_score_minimum"
    stochastic_log_max_field = f"{prefix}stochastic_log_score_maximum"
    faces = tuple(_faces(row[faces_field], faces_field) for row in rows)
    components = tuple(_integer(row[component_field], component_field) for row in rows)
    boundaries = tuple(_boolean(row[boundary_field], boundary_field) for row in rows)
    coverage_count = sum(_boolean(row[included_field], included_field) for row in rows)
    connected_count = sum(
        component == 1 and not boundary
        for component, boundary in zip(components, boundaries, strict=True)
    )
    physical_count = sum(
        component == 1 and "eta_min" not in row_faces
        for component, row_faces in zip(components, faces, strict=True)
    )
    eta_zero_count = sum("eta_min" in row_faces for row_faces in faces)
    artificial_count = sum(
        any(face in {"rho_min", "rho_max", "eta_max"} for face in row_faces) for row_faces in faces
    )
    rho_error = float(median(_finite_float(row[rho_error_field], rho_error_field) for row in rows))
    eta_error = float(median(_finite_float(row[eta_error_field], eta_error_field) for row in rows))
    rho_width = float(median(_finite_float(row[rho_width_field], rho_width_field) for row in rows))
    eta_width = float(median(_finite_float(row[eta_width_field], eta_width_field) for row in rows))
    brier = normal_mean_interval(
        tuple(_finite_float(row[brier_field], brier_field) for row in rows)
    )
    mean_stochastic_brier = fmean(
        _finite_float(row[stochastic_brier_field], stochastic_brier_field) for row in rows
    )
    mean_neutral_brier = fmean(
        _finite_float(row["neutral_brier_score"], "neutral_brier_score") for row in rows
    )
    finite_log_score_count = sum(
        isfinite(_float_allow_infinity(row[stochastic_log_min_field], stochastic_log_min_field))
        and isfinite(
            _float_allow_infinity(
                row[stochastic_log_max_field],
                stochastic_log_max_field,
            )
        )
        and isfinite(_float_allow_infinity(row["neutral_log_score"], "neutral_log_score"))
        for row in rows
    )
    if source_goal == "009":
        expected = {
            "coverage_count": _integer(
                summary["coverage_success_count"],
                "coverage_success_count",
            ),
            "connected_count": _integer(
                summary["topology_success_count"],
                "topology_success_count",
            ),
            "eta_zero_count": _integer(
                summary["eta_min_contact_count"],
                "eta_min_contact_count",
            ),
            "rho_error": _finite_float(
                summary["median_minimum_absolute_log_rho_error"],
                "median_minimum_absolute_log_rho_error",
            ),
            "eta_error": _finite_float(
                summary["median_minimum_absolute_eta_error"],
                "median_minimum_absolute_eta_error",
            ),
            "rho_width": _finite_float(
                summary["median_projected_log_rho_width"],
                "median_projected_log_rho_width",
            ),
            "eta_width": _finite_float(
                summary["median_projected_eta_width"],
                "median_projected_eta_width",
            ),
            "brier_estimate": _finite_float(
                summary["paired_brier_estimate"],
                "paired_brier_estimate",
            ),
            "brier_lower": _finite_float(
                summary["paired_brier_lower"],
                "paired_brier_lower",
            ),
            "brier_upper": _finite_float(
                summary["paired_brier_upper"],
                "paired_brier_upper",
            ),
        }
        cell_class = summary["downstream_class"]
    else:
        expected = {
            "coverage_count": _integer(
                summary["expanded_coverage_success_count"],
                "expanded_coverage_success_count",
            ),
            "connected_count": _integer(
                summary["expanded_topology_success_count"],
                "expanded_topology_success_count",
            ),
            "eta_zero_count": _integer(
                summary["eta_min_contact_count"],
                "eta_min_contact_count",
            ),
            "rho_error": _finite_float(
                summary["expanded_median_minimum_absolute_log_rho_error"],
                "expanded_median_minimum_absolute_log_rho_error",
            ),
            "eta_error": _finite_float(
                summary["expanded_median_minimum_absolute_eta_error"],
                "expanded_median_minimum_absolute_eta_error",
            ),
            "rho_width": _finite_float(
                summary["expanded_median_projected_log_rho_width"],
                "expanded_median_projected_log_rho_width",
            ),
            "eta_width": _finite_float(
                summary["expanded_median_projected_eta_width"],
                "expanded_median_projected_eta_width",
            ),
            "brier_estimate": _finite_float(
                summary["expanded_paired_brier_estimate"],
                "expanded_paired_brier_estimate",
            ),
            "brier_lower": _finite_float(
                summary["expanded_paired_brier_lower"],
                "expanded_paired_brier_lower",
            ),
            "brier_upper": _finite_float(
                summary["expanded_paired_brier_upper"],
                "expanded_paired_brier_upper",
            ),
        }
        cell_class = summary["expanded_class"]
    observed: dict[str, int | float] = {
        "coverage_count": coverage_count,
        "connected_count": connected_count,
        "eta_zero_count": eta_zero_count,
        "rho_error": rho_error,
        "eta_error": eta_error,
        "rho_width": rho_width,
        "eta_width": eta_width,
        "brier_estimate": brier.estimate,
        "brier_lower": brier.lower,
        "brier_upper": brier.upper,
    }
    if any(abs(float(observed[key]) - float(expected[key])) > 1e-12 for key in expected):
        raise ValueError("raw validation rows do not reconcile with accepted summary")
    return {
        "truth_rho": _finite_float(summary["truth_rho"], "truth_rho"),
        "truth_eta": _finite_float(summary["truth_eta"], "truth_eta"),
        "coverage_count": coverage_count,
        "connected_interior_count": connected_count,
        "physical_connected_interior_count": physical_count,
        "eta_zero_contact_count": eta_zero_count,
        "artificial_face_contact_count": artificial_count,
        "rho_error": rho_error,
        "eta_error": eta_error,
        "rho_width": rho_width,
        "eta_width": eta_width,
        "brier_estimate": brier.estimate,
        "brier_lower": brier.lower,
        "brier_upper": brier.upper,
        "mean_stochastic_brier": mean_stochastic_brier,
        "mean_neutral_brier": mean_neutral_brier,
        "finite_log_score_count": finite_log_score_count,
        "cell_class": cell_class,
    }


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"malformed JSON evidence file: {path.name}") from error
    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        raise ValueError(f"evidence JSON must contain an object: {path.name}")
    return payload


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError(f"malformed CSV schema: {path.name}")
            rows = tuple(dict(row) for row in reader)
    except (OSError, csv.Error) as error:
        raise ValueError(f"malformed CSV evidence file: {path.name}") from error
    if not rows or any(set(row) != set(reader.fieldnames) for row in rows):
        raise ValueError(f"malformed or empty CSV evidence file: {path.name}")
    return rows


def _required_string(mapping: dict[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"evidence field {key} must be a nonempty string")
    return value


def _finite_sequence(value: object, field: str) -> tuple[float, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a nonempty numeric array")
    values = tuple(float(item) for item in value)
    if not all(isfinite(item) for item in values):
        raise ValueError(f"{field} must contain finite values")
    return values


def _finite_float(value: str, field: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError(f"{field} must be numeric") from error
    if not isfinite(parsed):
        raise ValueError(f"{field} must be finite")
    return parsed


def _float_allow_infinity(value: str, field: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError(f"{field} must be numeric") from error
    if parsed != parsed:
        raise ValueError(f"{field} must not be NaN")
    return parsed


def _integer(value: str, field: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{field} must be an integer") from error
    if str(parsed) != value and value not in {f"{parsed}.0", f"+{parsed}"}:
        raise ValueError(f"{field} must use an integral representation")
    return parsed


def _boolean(value: str, field: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"{field} must be true or false")


def _faces(value: str, field: str) -> tuple[str, ...]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"{field} must be a JSON array") from error
    if (
        not isinstance(payload, list)
        or not all(isinstance(item, str) for item in payload)
        or len(set(payload)) != len(payload)
        or any(item not in {"rho_min", "rho_max", "eta_min", "eta_max"} for item in payload)
    ):
        raise ValueError(f"{field} contains invalid boundary faces")
    return tuple(payload)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


__all__ = [
    "BANK_VARIANT_NAMES",
    "DEFAULT_GOAL009_EVIDENCE_DIR",
    "DEFAULT_GOAL012_EVIDENCE_DIR",
    "WEAK_CELL_IDS",
    "BaselineValidationContact",
    "EvidenceIdentity",
    "EvidenceReconciliationRow",
    "ExistingEvidence",
    "authenticate_existing_evidence",
]
