"""Reconcile weak-contrast estimation, detection, and support decisions."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import cast

WEAK_CONTRAST = 0.5
FULL_BANK = "full"
BANK_ORDER = {"full": 0, "first_half": 1, "second_half": 2}


@dataclass(frozen=True)
class DecisionTargetSummary:
    """Campaign-level rates for one weak-contrast truth and bank."""

    truth_cell: str
    truth_rho: float
    truth_eta: float
    bank_variant: str
    validation_count: int
    mle_exact_count: int
    mle_exact_rate: float
    mle_nonzero_count: int
    mle_nonzero_rate: float
    support_excludes_zero_count: int
    support_excludes_zero_rate: float
    truth_coverage_count: int
    truth_coverage_rate: float
    calibrated_cutoff: float
    binary_auc: float
    binary_false_positive_rate: float
    binary_power: float
    binary_power_lower: float
    binary_practically_useful: bool
    campaign_relationship: str = "independent_campaign_level_comparison"


@dataclass(frozen=True)
class PairedDisagreement:
    """Wave-paired Goal 012 point-estimate by support decision counts."""

    truth_cell: str
    truth_rho: float
    bank_variant: str
    validation_count: int
    mle_exact_support_excludes_zero_count: int
    mle_exact_support_includes_zero_count: int
    mle_inexact_support_excludes_zero_count: int
    mle_inexact_support_includes_zero_count: int


@dataclass(frozen=True)
class ProfileMechanics:
    """Reduced mechanics for one representative joint profile."""

    truth_cell: str
    truth_rho: float
    truth_eta: float
    bank_variant: str
    block_index: int
    fitted_eta: float
    profiled_zero_lr: float
    calibrated_cutoff: float
    zero_exclusion_margin: float
    zero_in_support: bool
    profile_log_score_eta_0_5_minus_eta_0: float
    rho_fixed_zero_lr: float
    rho_fixed_minus_profiled_zero_lr: float


@dataclass(frozen=True)
class ProfileCurve:
    """Profile-likelihood curve retained for the compact review figure."""

    truth_cell: str
    truth_rho: float
    fitted_eta: float
    calibrated_cutoff: float
    eta_values: tuple[float, ...]
    likelihood_ratio_values: tuple[float, ...]


@dataclass(frozen=True)
class Goal017Result:
    """Complete existing-evidence reconciliation."""

    decision_summaries: tuple[DecisionTargetSummary, ...]
    paired_disagreements: tuple[PairedDisagreement, ...]
    profile_mechanics: tuple[ProfileMechanics, ...]
    profile_curves: tuple[ProfileCurve, ...]
    outcome: str
    goal016_outcome: str
    half_bank_maximum_rate_difference: float


def analyze_evidence(goal012_dir: Path, goal016_dir: Path) -> Goal017Result:
    """Read accepted Goal 012/016 packs and reconcile their decision targets."""
    goal012 = Path(goal012_dir)
    goal016 = Path(goal016_dir)
    validation = _read_csv(
        goal012 / "validation_results.csv",
        {
            "truth_cell",
            "truth_rho",
            "truth_eta",
            "bank_variant",
            "block_index",
            "expanded_minimum_absolute_eta_error",
            "expanded_mle_cells",
            "expanded_support_boundary_faces",
            "expanded_truth_included",
        },
    )
    cell_summaries = _read_csv(
        goal012 / "truth_cell_summary.csv",
        {
            "truth_cell",
            "truth_rho",
            "truth_eta",
            "bank_variant",
            "expanded_cutoff",
        },
    )
    profiles = _read_csv(
        goal012 / "representative_profiles.csv",
        {
            "truth_cell",
            "truth_rho",
            "truth_eta",
            "block_index",
            "bank_variant",
            "eta",
            "rho",
            "expanded_log_likelihood",
            "expanded_cutoff",
        },
    )
    funnel = _read_csv(
        goal016 / "funnel_performance.csv",
        {
            "representation",
            "rho",
            "final_auc",
            "false_positive_rate",
            "power",
            "power_lower",
            "practically_useful",
            "null_count",
            "alternative_count",
        },
    )
    goal016_outcome = _read_goal016_outcome(goal016 / "summary.json")

    weak_validation = [row for row in validation if _close(_float(row, "truth_eta"), 0.5)]
    if not weak_validation:
        raise ValueError("validation_results.csv has no eta = 0.5 rows")
    binary_by_rho = _binary_rows_by_rho(funnel)
    cutoff_by_group = _cutoffs_by_group(cell_summaries)
    grouped: dict[tuple[str, float, str], list[dict[str, str]]] = defaultdict(list)
    for row in weak_validation:
        key = (row["truth_cell"], _float(row, "truth_rho"), row["bank_variant"])
        grouped[key].append(row)

    decision_rows: list[DecisionTargetSummary] = []
    disagreement_rows: list[PairedDisagreement] = []
    for key in sorted(grouped, key=lambda value: (value[1], BANK_ORDER.get(value[2], 99))):
        truth_cell, truth_rho, bank = key
        rows = grouped[key]
        if truth_rho not in binary_by_rho:
            raise ValueError(f"funnel_performance.csv has no composite row for rho {truth_rho:g}")
        if key not in cutoff_by_group:
            raise ValueError(f"truth_cell_summary.csv has no row for {truth_cell}/{bank}")
        binary = binary_by_rho[truth_rho]
        exact = [_close(_float(row, "expanded_minimum_absolute_eta_error"), 0.0) for row in rows]
        nonzero = [_mle_excludes_zero(row["expanded_mle_cells"]) for row in rows]
        support_excludes = [
            "eta_min" not in _json_strings(row["expanded_support_boundary_faces"]) for row in rows
        ]
        covered = [_bool(row, "expanded_truth_included") for row in rows]
        n = len(rows)
        decision_rows.append(
            DecisionTargetSummary(
                truth_cell=truth_cell,
                truth_rho=truth_rho,
                truth_eta=WEAK_CONTRAST,
                bank_variant=bank,
                validation_count=n,
                mle_exact_count=sum(exact),
                mle_exact_rate=sum(exact) / n,
                mle_nonzero_count=sum(nonzero),
                mle_nonzero_rate=sum(nonzero) / n,
                support_excludes_zero_count=sum(support_excludes),
                support_excludes_zero_rate=sum(support_excludes) / n,
                truth_coverage_count=sum(covered),
                truth_coverage_rate=sum(covered) / n,
                calibrated_cutoff=cutoff_by_group[key],
                binary_auc=_float(binary, "final_auc"),
                binary_false_positive_rate=_float(binary, "false_positive_rate"),
                binary_power=_float(binary, "power"),
                binary_power_lower=_float(binary, "power_lower"),
                binary_practically_useful=_bool(binary, "practically_useful"),
            )
        )
        disagreement_rows.append(
            PairedDisagreement(
                truth_cell=truth_cell,
                truth_rho=truth_rho,
                bank_variant=bank,
                validation_count=n,
                mle_exact_support_excludes_zero_count=sum(
                    is_exact and excludes
                    for is_exact, excludes in zip(exact, support_excludes, strict=True)
                ),
                mle_exact_support_includes_zero_count=sum(
                    is_exact and not excludes
                    for is_exact, excludes in zip(exact, support_excludes, strict=True)
                ),
                mle_inexact_support_excludes_zero_count=sum(
                    not is_exact and excludes
                    for is_exact, excludes in zip(exact, support_excludes, strict=True)
                ),
                mle_inexact_support_includes_zero_count=sum(
                    not is_exact and not excludes
                    for is_exact, excludes in zip(exact, support_excludes, strict=True)
                ),
            )
        )

    mechanics, curves = _reduce_representative_profiles(profiles)
    full = [row for row in decision_rows if row.bank_variant == FULL_BANK]
    if len(full) != 3:
        raise ValueError(f"expected three full-bank weak-contrast truths, found {len(full)}")
    outcome = _classify_outcome(full)
    return Goal017Result(
        decision_summaries=tuple(decision_rows),
        paired_disagreements=tuple(disagreement_rows),
        profile_mechanics=mechanics,
        profile_curves=curves,
        outcome=outcome,
        goal016_outcome=goal016_outcome,
        half_bank_maximum_rate_difference=_half_bank_stability(decision_rows),
    )


def _read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"missing evidence file: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        missing = sorted(required - fields)
        if missing:
            raise ValueError(f"{path.name} missing columns: {', '.join(missing)}")
        rows: list[dict[str, str]] = []
        for raw in reader:
            if any(value is None for value in raw.values()):
                raise ValueError(f"{path.name} contains a malformed row")
            rows.append({key: cast(str, value) for key, value in raw.items()})
    if not rows:
        raise ValueError(f"{path.name} contains no data rows")
    return rows


def _read_goal016_outcome(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"missing evidence file: {path}")
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("outcome"), str):
        raise ValueError("summary.json has no string outcome")
    outcome = cast(str, payload["outcome"])
    if outcome != "information_retained_support_target_limited":
        raise ValueError(f"Goal 016 outcome is not the accepted repaired result: {outcome}")
    return outcome


def _binary_rows_by_rho(rows: list[dict[str, str]]) -> dict[float, dict[str, str]]:
    selected = [row for row in rows if row["representation"] == "current_composite_statistic"]
    result: dict[float, dict[str, str]] = {}
    for row in selected:
        rho = _float(row, "rho")
        if rho in result:
            raise ValueError(f"funnel_performance.csv repeats composite rho {rho:g}")
        result[rho] = row
    return result


def _cutoffs_by_group(rows: list[dict[str, str]]) -> dict[tuple[str, float, str], float]:
    result: dict[tuple[str, float, str], float] = {}
    for row in rows:
        if not _close(_float(row, "truth_eta"), WEAK_CONTRAST):
            continue
        key = (row["truth_cell"], _float(row, "truth_rho"), row["bank_variant"])
        result[key] = _float(row, "expanded_cutoff")
    return result


def _reduce_representative_profiles(
    rows: list[dict[str, str]],
) -> tuple[tuple[ProfileMechanics, ...], tuple[ProfileCurve, ...]]:
    grouped: dict[tuple[str, float, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["bank_variant"] != FULL_BANK or not _close(_float(row, "truth_eta"), WEAK_CONTRAST):
            continue
        key = (row["truth_cell"], _float(row, "truth_rho"), _int(row, "block_index"))
        grouped[key].append(row)
    mechanics: list[ProfileMechanics] = []
    curves: list[ProfileCurve] = []
    for key in sorted(grouped, key=lambda value: value[1]):
        truth_cell, truth_rho, block_index = key
        group = grouped[key]
        profile: dict[float, float] = {}
        fixed_rho: dict[float, float] = {}
        for row in group:
            eta = _float(row, "eta")
            score = _float(row, "expanded_log_likelihood")
            profile[eta] = max(profile.get(eta, -math.inf), score)
            if _close(_float(row, "rho"), truth_rho):
                fixed_rho[eta] = max(fixed_rho.get(eta, -math.inf), score)
        if 0.0 not in profile or WEAK_CONTRAST not in profile:
            raise ValueError(f"representative profile {truth_cell} lacks eta 0 or 0.5")
        if 0.0 not in fixed_rho:
            raise ValueError(f"representative profile {truth_cell} lacks its true rho")
        global_max = max(profile.values())
        fitted_eta = min(eta for eta, score in profile.items() if _close(score, global_max))
        profiled_zero_lr = 2.0 * (global_max - profile[0.0])
        fixed_zero_lr = 2.0 * (max(fixed_rho.values()) - fixed_rho[0.0])
        cutoff_values = {_float(row, "expanded_cutoff") for row in group}
        if len(cutoff_values) != 1:
            raise ValueError(f"representative profile {truth_cell} has inconsistent cutoffs")
        cutoff = cutoff_values.pop()
        eta_values = tuple(sorted(profile))
        lr_values = tuple(2.0 * (global_max - profile[eta]) for eta in eta_values)
        mechanics.append(
            ProfileMechanics(
                truth_cell=truth_cell,
                truth_rho=truth_rho,
                truth_eta=WEAK_CONTRAST,
                bank_variant=FULL_BANK,
                block_index=block_index,
                fitted_eta=fitted_eta,
                profiled_zero_lr=profiled_zero_lr,
                calibrated_cutoff=cutoff,
                zero_exclusion_margin=profiled_zero_lr - cutoff,
                zero_in_support=profiled_zero_lr <= cutoff,
                profile_log_score_eta_0_5_minus_eta_0=(profile[WEAK_CONTRAST] - profile[0.0]),
                rho_fixed_zero_lr=fixed_zero_lr,
                rho_fixed_minus_profiled_zero_lr=fixed_zero_lr - profiled_zero_lr,
            )
        )
        curves.append(
            ProfileCurve(
                truth_cell=truth_cell,
                truth_rho=truth_rho,
                fitted_eta=fitted_eta,
                calibrated_cutoff=cutoff,
                eta_values=eta_values,
                likelihood_ratio_values=lr_values,
            )
        )
    if len(mechanics) != 3:
        raise ValueError(
            f"expected three full-bank weak representative profiles, found {len(mechanics)}"
        )
    return tuple(mechanics), tuple(curves)


def _classify_outcome(full_rows: list[DecisionTargetSummary]) -> str:
    if not all(row.binary_practically_useful for row in full_rows):
        return "contrast_information_absent"
    if sum(row.mle_nonzero_rate for row in full_rows) / len(full_rows) < 0.8:
        return "point_estimation_limited"
    binary_gaps = [row.binary_power - row.support_excludes_zero_rate for row in full_rows]
    mle_gaps = [row.mle_nonzero_rate - row.support_excludes_zero_rate for row in full_rows]
    if min(binary_gaps) >= 0.15 and min(mle_gaps) >= 0.15:
        return "continuous_support_conservative_relative_to_detection"
    return "decision_targets_broadly_concordant"


def _half_bank_stability(rows: list[DecisionTargetSummary]) -> float:
    by_rho_bank = {(row.truth_rho, row.bank_variant): row for row in rows}
    differences: list[float] = []
    for rho in sorted({row.truth_rho for row in rows}):
        full = by_rho_bank[(rho, FULL_BANK)]
        for bank in ("first_half", "second_half"):
            half = by_rho_bank[(rho, bank)]
            differences.extend(
                [
                    abs(full.mle_exact_rate - half.mle_exact_rate),
                    abs(full.mle_nonzero_rate - half.mle_nonzero_rate),
                    abs(full.support_excludes_zero_rate - half.support_excludes_zero_rate),
                ]
            )
    return max(differences, default=0.0)


def _mle_excludes_zero(raw: str) -> bool:
    payload: object = json.loads(raw)
    if not isinstance(payload, list) or not payload:
        raise ValueError("expanded_mle_cells must be a nonempty JSON list")
    eta_values: list[float] = []
    for cell in payload:
        if not isinstance(cell, list) or len(cell) != 2 or not isinstance(cell[1], (int, float)):
            raise ValueError("expanded_mle_cells contains an invalid cell")
        eta_values.append(float(cell[1]))
    return min(eta_values) > 0.0


def _json_strings(raw: str) -> tuple[str, ...]:
    payload: object = json.loads(raw)
    if not isinstance(payload, list) or not all(isinstance(value, str) for value in payload):
        raise ValueError("boundary faces must be a JSON string list")
    return tuple(cast(list[str], payload))


def _float(row: dict[str, str], key: str) -> float:
    try:
        return float(row[key])
    except ValueError as error:
        raise ValueError(f"invalid numeric value for {key}: {row[key]}") from error


def _int(row: dict[str, str], key: str) -> int:
    try:
        return int(row[key])
    except ValueError as error:
        raise ValueError(f"invalid integer value for {key}: {row[key]}") from error


def _bool(row: dict[str, str], key: str) -> bool:
    value = row[key].strip().lower()
    if value not in {"true", "false"}:
        raise ValueError(f"invalid boolean value for {key}: {row[key]}")
    return value == "true"


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12)
