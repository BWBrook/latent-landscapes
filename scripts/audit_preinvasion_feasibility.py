"""Independently replay Goal 056 fits against the direct empirical arrival bank.

This audit deliberately does not import the production likelihood, emissions,
compression, fitting, or execution modules.  It reconstructs the seven arrival
categories, their pseudo-arrivals, calendar-edge survival transforms, predator
mixture, and shared-site Beta detection probabilities from the frozen files.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

PREDATOR_TIMES = np.asarray((10.0, 20.0, 30.0, 40.0, 50.0, 60.0))
PREY_TIMES = np.arange(-60.0, 61.0, 10.0)
PSEUDO_ARRIVALS = np.asarray((5.0, 15.0, 25.0, 35.0, 45.0, 55.0, 70.0))
DETECTION_MEAN = 0.65
MODEL_ORDER = (
    "constant_free_h",
    "adjusted_free_h",
    "constant_h1",
    "adjusted_h1",
)
SCORE_TOLERANCE = 1e-8
STATISTIC_TOLERANCE = 1e-6
EXPECTED_SOURCE_BINDINGS = 98
RECOVERY_SOURCE_CHANGE_ALLOWLIST = {
    "src/latent_landscapes/preinvasion_fitting.py",
    "tests/test_preinvasion_fitting.py",
}
RECOVERY_EXTRA_BINDINGS = {
    "scripts/recover_preinvasion_profiles.py",
    "docs/goals/056-observed-nuisance-feasibility/profile-recovery-amendment.md",
}
RECOVERY_AUXILIARY_BINDINGS = {
    "README.md",
    "tests/test_adjusted_background_likelihood.py",
}


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value, np.generic):
        return jsonable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [jsonable(item) for item in value]
    return value


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(jsonable(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def verify_qualification(
    qualified_source_root: Path,
    qualification_directory: Path,
    verification_path: Path,
    source_manifest_path: Path,
) -> dict[str, Any]:
    qualification_path = qualification_directory / "qualification.json"
    qualification = read_json(qualification_path)
    verification = read_json(verification_path)
    source_manifest = read_json(source_manifest_path)
    qualified_sources = qualification.get("source_hashes", {})
    manifest_sources = source_manifest.get("source_hashes", {})
    if not isinstance(qualified_sources, dict) or not isinstance(manifest_sources, dict):
        raise ValueError("qualification and source manifest must contain source hashes")
    local_mismatches = []
    for relative, expected in qualified_sources.items():
        path = qualified_source_root / relative
        actual = sha256_file(path) if path.is_file() else None
        if actual != expected:
            local_mismatches.append(relative)
    qualification_sha = sha256_file(qualification_path)
    manifest_sha = sha256_file(source_manifest_path)
    compressed_path = qualification_directory / "compressed-bank.npz"
    checks = {
        "qualification_passed": qualification.get("passed") is True,
        "verification_passed": verification.get("passed") is True,
        "qualification_sha_matches": verification.get("qualification_sha256") == qualification_sha,
        "source_manifest_sha_matches": verification.get("source_manifest_sha256") == manifest_sha,
        "source_binding_count_matches": len(qualified_sources)
        == verification.get("source_bindings")
        == EXPECTED_SOURCE_BINDINGS,
        "source_manifest_matches_qualification": manifest_sources == qualified_sources,
        "qualified_source_snapshot_matches": not local_mismatches,
        "compressed_bank_matches": compressed_path.is_file()
        and sha256_file(compressed_path) == qualification.get("compressed_bank_sha256"),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "local_source_mismatches": local_mismatches,
        "source_bindings": len(qualified_sources),
        "qualification_sha256": qualification_sha,
        "qualification_verification_sha256": sha256_file(verification_path),
        "source_manifest_sha256": manifest_sha,
        "compressed_bank_sha256": sha256_file(compressed_path)
        if compressed_path.is_file()
        else None,
    }


def verify_recovery_source_change(
    repository: Path,
    qualified_source_root: Path,
    qualified_sources: dict[str, Any],
    completed: dict[str, Any],
) -> dict[str, Any]:
    current_sources = {
        relative: sha256_file(repository / relative) if (repository / relative).is_file() else None
        for relative in qualified_sources
    }

    changed = {
        relative
        for relative, qualified_hash in qualified_sources.items()
        if current_sources.get(relative) != qualified_hash
    }

    def fitter_ast_without_profile_starts(root: Path) -> str:
        path = root / "src/latent_landscapes/preinvasion_fitting.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        tree.body = [
            node
            for node in tree.body
            if not (isinstance(node, ast.FunctionDef) and node.name == "_profile_starts")
        ]
        return ast.dump(tree, include_attributes=False)

    checks = {
        "qualified_hashes_retained_in_receipt": completed.get("qualified_source_hashes")
        == qualified_sources,
        "current_hashes_match_receipt": completed.get("source_hashes") == current_sources,
        "receipt_allowlist_is_exact": set(completed.get("source_hash_differences_allowed", []))
        == RECOVERY_SOURCE_CHANGE_ALLOWLIST,
        "observed_changes_are_exact": changed == RECOVERY_SOURCE_CHANGE_ALLOWLIST,
        "fitter_ast_diff_is_confined_to_profile_starts": fitter_ast_without_profile_starts(
            repository
        )
        == fitter_ast_without_profile_starts(qualified_source_root),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "observed_source_changes": sorted(changed),
        "current_source_hashes": current_sources,
    }


def verify_recovery_manifest(
    repository: Path,
    qualified_source_root: Path,
    recovery_manifest_path: Path,
    original_source_manifest_path: Path,
) -> dict[str, Any]:
    manifest = read_json(recovery_manifest_path)
    sidecar_root = recovery_manifest_path.parent
    source_hashes = manifest.get("source_hashes", {})
    extra_bindings = manifest.get("extra_bindings", {})
    auxiliary_bindings = manifest.get("auxiliary_bindings", {})
    if not all(
        isinstance(value, dict) for value in (source_hashes, extra_bindings, auxiliary_bindings)
    ):
        raise ValueError("recovery manifest binding fields must be mappings")
    local_source_hashes = {
        relative: sha256_file(repository / relative) if (repository / relative).is_file() else None
        for relative in source_hashes
    }
    local_extra_hashes = {
        relative: sha256_file(repository / relative) if (repository / relative).is_file() else None
        for relative in extra_bindings
    }
    local_auxiliary_hashes = {
        relative: sha256_file(qualified_source_root / relative)
        if (qualified_source_root / relative).is_file()
        else None
        for relative in auxiliary_bindings
    }
    repair_ast_path = sidecar_root / "repair-ast-check.json"
    repair_patch_path = sidecar_root / "profile-repair.patch"
    wrapper_path = sidecar_root / "run_bounded.py"
    context_path = sidecar_root / "original-resource-context.json"
    repair = read_json(repair_ast_path)
    checks = {
        "current_core_sources_match": source_hashes == local_source_hashes,
        "extra_binding_paths_are_exact": set(extra_bindings) == RECOVERY_EXTRA_BINDINGS,
        "extra_bindings_match": extra_bindings == local_extra_hashes,
        "auxiliary_binding_paths_are_exact": set(auxiliary_bindings) == RECOVERY_AUXILIARY_BINDINGS,
        "auxiliary_bindings_match": auxiliary_bindings == local_auxiliary_hashes,
        "manifest_change_allowlist_is_exact": set(manifest.get("changed_source_bindings", []))
        == RECOVERY_SOURCE_CHANGE_ALLOWLIST,
        "repair_ast_receipt_matches": repair_ast_path.is_file()
        and sha256_file(repair_ast_path) == manifest.get("repair_ast_check_sha256"),
        "repair_ast_claim_is_exact": repair
        == {
            "changed_source_bindings": sorted(RECOVERY_SOURCE_CHANGE_ALLOWLIST),
            "only_profile_starts_ast_changed": True,
            "no_main_fit_algorithm_change": True,
        },
        "profile_repair_patch_matches": repair_patch_path.is_file()
        and repair_patch_path.stat().st_size > 0
        and sha256_file(repair_patch_path) == manifest.get("profile_repair_patch_sha256"),
        "wrapper_matches": wrapper_path.is_file()
        and sha256_file(wrapper_path) == manifest.get("wrapper_sha256"),
        "original_source_manifest_matches": sha256_file(original_source_manifest_path)
        == manifest.get("original_source_manifest_sha256"),
        "original_resource_context_matches": context_path.is_file()
        and sha256_file(context_path) == manifest.get("original_resource_context_sha256"),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "recovery_manifest_sha256": sha256_file(recovery_manifest_path),
        "repair_ast_check_sha256": sha256_file(repair_ast_path),
        "profile_repair_patch_sha256": sha256_file(repair_patch_path),
        "wrapper_sha256": sha256_file(wrapper_path),
        "original_resource_context_sha256": sha256_file(context_path),
    }


@dataclass(frozen=True)
class DirectBank:
    site_ids: tuple[str, ...]
    bank_size: int
    denominator: int
    values: tuple[tuple[FloatArray, ...], ...]
    category_mass: FloatArray


def load_direct_bank(
    bank_path: Path, site_ids: tuple[str, ...], expected_file_sha256: str
) -> DirectBank:
    if sha256_file(bank_path) != expected_file_sha256:
        raise ValueError("raw bank file does not match its qualification receipt")
    bank = np.load(bank_path, mmap_mode="r", allow_pickle=False)
    if bank.shape != (131_072, len(site_ids)) or not np.isfinite(bank).all() or (bank < 0).any():
        raise ValueError("raw bank has the wrong shape or invalid arrivals")
    categories = np.searchsorted(PREDATOR_TIMES, bank, side="left")
    denominator = bank.shape[0] + len(PSEUDO_ARRIVALS)
    values: list[tuple[FloatArray, ...]] = []
    masses = np.empty((len(site_ids), len(PSEUDO_ARRIVALS)), dtype=np.float64)
    for site in range(len(site_ids)):
        site_values = tuple(
            np.asarray(bank[categories[:, site] == category, site], dtype=np.float64)
            for category in range(len(PSEUDO_ARRIVALS))
        )
        values.append(site_values)
        masses[site] = np.asarray(
            [(len(category_values) + 1.0) / denominator for category_values in site_values]
        )
    return DirectBank(site_ids, bank.shape[0], denominator, tuple(values), masses)


def normalized_hazards(
    beta: float, mean_hazard: float, map_a: FloatArray, site_a: FloatArray
) -> FloatArray:
    scaled = beta * map_a
    shift = float(np.max(scaled))
    denominator = float(np.mean(np.exp(scaled - shift)))
    result = mean_hazard * np.exp(beta * site_a - shift) / denominator
    if not np.isfinite(result).all() or (result <= 0).any():
        raise ValueError("independent normalized hazards are invalid")
    return np.asarray(result, dtype=np.float64)


def direct_survival_moments(bank: DirectBank, hazards: FloatArray, effect: float) -> FloatArray:
    """Integrate survival at calendar edges using direct category Laplace sums."""
    knots = np.concatenate((np.asarray([-60.0]), PREY_TIMES))
    base = np.exp(-hazards[:, None] * (knots[None, :] + 60.0))
    moments = base[:, :, None] * bank.category_mass[:, None, :]
    delta = hazards * (effect - 1.0)
    transforms = np.empty((len(hazards), 6), dtype=np.float64)
    for site in range(len(hazards)):
        for category in range(6):
            upper = 10.0 * (category + 1)
            actual = bank.values[site][category]
            total = float(np.sum(np.exp(-delta[site] * (upper - actual)), dtype=np.float64))
            total += math.exp(-delta[site] * (upper - PSEUDO_ARRIVALS[category]))
            transforms[site, category] = total / bank.denominator
    for category in range(6):
        lower = 10.0 * category
        upper = lower + 10.0
        after = knots > lower
        moments[:, after, category] = (
            np.exp(
                -hazards[:, None] * (knots[None, after] + 60.0)
                - delta[:, None] * (knots[None, after] - upper)
            )
            * transforms[:, category, None]
        )
    if not np.isfinite(moments).all() or (moments < 0).any():
        raise ValueError("independent survival moments are invalid")
    return moments


def binomial_two_probability(count: int, probability: float = DETECTION_MEAN) -> float:
    return math.comb(2, count) * probability**count * (1.0 - probability) ** (2 - count)


def predator_emissions(counts: IntArray) -> FloatArray:
    sites, occasions = counts.shape
    if occasions != 6:
        raise ValueError("predator counts must have six occasions")
    result = np.empty((sites, 7), dtype=np.float64)
    for site in range(sites):
        for category in range(7):
            if np.any(counts[site, :category] != 0):
                result[site, category] = 0.0
                continue
            result[site, category] = math.prod(
                binomial_two_probability(int(value)) for value in counts[site, category:]
            )
    return result


def shared_detection_probability(
    counts: IntArray, detection_sd: float, probability: float = DETECTION_MEAN
) -> float:
    successes = int(np.sum(counts))
    trials = 2 * len(counts)
    log_value = math.fsum(math.log(math.comb(2, int(value))) for value in counts)
    log_value += successes * math.log(probability)
    log_value += (trials - successes) * math.log1p(-probability)
    variance = detection_sd * detection_sd
    if variance == 0.0 or trials == 0:
        return math.exp(log_value)
    maximum_variance = probability * (1.0 - probability)
    if not 0.0 < variance < maximum_variance:
        raise ValueError("detection SD is outside the shared-Beta domain")
    inverse_concentration = variance / (maximum_variance - variance)
    log_value += math.fsum(
        math.log1p(index * inverse_concentration / probability) for index in range(successes)
    )
    log_value += math.fsum(
        math.log1p(index * inverse_concentration / (1.0 - probability))
        for index in range(trials - successes)
    )
    log_value -= math.fsum(math.log1p(index * inverse_concentration) for index in range(trials))
    return math.exp(log_value)


def prey_factors(counts: IntArray, detection_sd: float) -> tuple[FloatArray, FloatArray]:
    sites, occasions = counts.shape
    events = np.zeros((sites, occasions), dtype=np.float64)
    alive = np.empty(sites, dtype=np.float64)
    for site in range(sites):
        alive[site] = shared_detection_probability(counts[site], detection_sd)
        for prefix in range(occasions):
            if np.all(counts[site, prefix:] == 0):
                events[site, prefix] = shared_detection_probability(
                    counts[site, :prefix], detection_sd
                )
    return events, alive


@dataclass(frozen=True)
class DirectScore:
    joint_site: FloatArray
    predator_site: FloatArray
    conditional_prey_site: FloatArray


def direct_score(
    bank: DirectBank,
    prey_counts: IntArray,
    predator_probability: FloatArray,
    map_a: FloatArray,
    site_a: FloatArray,
    *,
    h: float,
    beta: float,
    mu: float,
    detection_sd: float,
) -> DirectScore:
    hazards = normalized_hazards(beta, mu, map_a, site_a)
    moments = direct_survival_moments(bank, hazards, h)
    events, alive = prey_factors(prey_counts, detection_sd)
    weighted = np.einsum("stc,sc->st", moments, predator_probability, optimize=True)
    probability = np.sum((weighted[:, :-1] - weighted[:, 1:]) * events, axis=1)
    probability += weighted[:, -1] * alive
    predator_marginal = np.sum(bank.category_mass * predator_probability, axis=1)
    if (
        not np.isfinite(probability).all()
        or not np.isfinite(predator_marginal).all()
        or (probability <= 0).any()
        or (predator_marginal <= 0).any()
    ):
        raise ValueError("independent observation probabilities are invalid")
    joint = np.log(probability)
    predator = np.log(predator_marginal)
    return DirectScore(joint, predator, joint - predator)


def validate_completed_receipts(
    panel_output: Path, original_panel: Path | None = None
) -> dict[str, Any]:
    completed = read_json(panel_output / "completed.json")
    mismatches = []
    files = completed.get("files", {})
    if not isinstance(files, dict):
        raise ValueError("completed receipt has no file hash mapping")
    for relative, expected in files.items():
        path = panel_output / relative
        if not path.is_file() or sha256_file(path) != expected:
            mismatches.append(relative)
    manifest = read_json(panel_output / "panel" / "manifest.json")
    observation_path = panel_output / "panel" / "observations.npz"
    evaluator_path = panel_output / "panel" / "evaluator.npz"
    status = completed.get("status")
    recovered = status == "panel_recovered_pending_scientific_audit"
    checks = {
        "completed_status": status
        in {
            "panel_completed_pending_scientific_audit",
            "panel_recovered_pending_scientific_audit",
        },
        "completed_file_hashes": not mismatches,
        "observation_manifest_hash": sha256_file(observation_path)
        == manifest.get("observation_sha256"),
        "evaluator_manifest_hash": sha256_file(evaluator_path) == manifest.get("evaluator_sha256"),
    }
    preservation_mismatches: list[str] = []
    recovered_payload_mismatches: list[int] = []
    if recovered:
        checks["original_panel_supplied"] = original_panel is not None
        if original_panel is not None:
            immutable = [
                "panel/observations.npz",
                "panel/evaluator.npz",
                "panel/manifest.json",
            ]
            immutable += [f"results/cell-{index:02d}-main.json" for index in range(16)]
            copied = completed.get("copied_complete_cells", [])
            recovered_cells = completed.get("recovered_cells", [])
            if not isinstance(copied, list) or not isinstance(recovered_cells, list):
                raise ValueError("recovery receipt has invalid cell identity fields")
            if sorted(copied + recovered_cells) != list(range(16)) or set(copied) & set(
                recovered_cells
            ):
                raise ValueError("recovery receipt does not partition the sixteen cells")
            originally_missing = [
                index
                for index in range(16)
                if not (original_panel / "results" / f"cell-{index:02d}.json").is_file()
            ]
            checks["recovered_cells_match_original_missingness"] = bool(
                recovered_cells == completed.get("expected_missing")
                and recovered_cells == originally_missing
            )
            immutable += [f"results/cell-{int(index):02d}.json" for index in copied]
            for relative in immutable:
                original = original_panel / relative
                recovered_path = panel_output / relative
                if (
                    not original.is_file()
                    or not recovered_path.is_file()
                    or sha256_file(original) != sha256_file(recovered_path)
                ):
                    preservation_mismatches.append(relative)
            original_failed = original_panel / "failed.json"
            recovered_failed = panel_output / "original-failed.json"
            if (
                not original_failed.is_file()
                or not recovered_failed.is_file()
                or sha256_file(original_failed) != sha256_file(recovered_failed)
            ):
                preservation_mismatches.append("original-failed.json")
            for raw_index in recovered_cells:
                index = int(raw_index)
                main = read_json(original_panel / "results" / f"cell-{index:02d}-main.json")
                cell = read_json(panel_output / "results" / f"cell-{index:02d}.json")
                if cell.get("paired") != main.get("paired") or cell.get("pre_only") != main.get(
                    "pre_only"
                ):
                    recovered_payload_mismatches.append(index)
                if cell.get("profile_source_id") != "recovered-v1":
                    recovered_payload_mismatches.append(index)
        checks["immutable_original_files_preserved"] = not preservation_mismatches
        checks["recovered_main_payloads_preserved"] = not recovered_payload_mismatches
    else:
        checks["original_panel_not_applicable"] = original_panel is None
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "file_hash_mismatches": mismatches,
        "immutable_original_file_mismatches": preservation_mismatches,
        "recovered_main_payload_mismatches": recovered_payload_mismatches,
        "status": status,
        "completed_sha256": sha256_file(panel_output / "completed.json"),
        "panel_manifest_sha256": sha256_file(panel_output / "panel" / "manifest.json"),
        "observations_sha256": sha256_file(observation_path),
        "evaluator_sha256": sha256_file(evaluator_path),
    }


def recompute_numerical_audit(panel_output: Path) -> dict[str, Any]:
    grid = read_json(panel_output / "coarse-grid-audit.json")
    recorded = read_json(panel_output / "numerical-audit.json")
    profile_models = {
        "constant_h": "constant_free_h",
        "adjusted_h": "adjusted_free_h",
        "adjusted_beta": "adjusted_free_h",
    }
    rows = []
    for index in range(16):
        cell = read_json(panel_output / "results" / f"cell-{index:02d}.json")
        for model in MODEL_ORDER:
            fit = cell["paired"]["fits"][model]
            main = fit["raw_logjoint"]
            grid_gap = None if main is None else grid["max_logjoint"][model][index] - main
            profile_gaps: dict[str, float | None] = {}
            failed_nodes: dict[str, int] = {}
            for profile_name, profile_model in profile_models.items():
                if profile_model != model:
                    continue
                profile = cell["profiles"][profile_name]
                qualified = [
                    value
                    for value, status in zip(profile["values"], profile["statuses"], strict=True)
                    if value is not None and status == "converged"
                ]
                profile_gaps[profile_name] = (
                    max(qualified) - main if qualified and main is not None else None
                )
                failed_nodes[profile_name] = sum(
                    status != "converged" for status in profile["statuses"]
                )
            passed = bool(
                fit["numerical_status"] == "converged"
                and grid_gap is not None
                and grid_gap <= STATISTIC_TOLERANCE
                and all(
                    gap is not None and gap <= STATISTIC_TOLERANCE for gap in profile_gaps.values()
                )
            )
            rows.append(
                {
                    "index": index,
                    "model": model,
                    "passed": passed,
                    "grid_minus_main_logjoint": grid_gap,
                    "profile_minus_main_logjoint": profile_gaps,
                    "profile_failed_nodes": failed_nodes,
                    "main_replay_difference": cell["main_replay_logjoint_differences"][model],
                    "profile_source_id": cell.get("profile_source_id", "original"),
                }
            )
    recorded_rows = {(row["index"], row["model"]): row for row in recorded.get("rows", [])}
    row_mismatches = []
    for row in rows:
        if recorded_rows.get((row["index"], row["model"])) != row:
            row_mismatches.append([row["index"], row["model"]])
    passed = (
        len(rows) == 64
        and all(row["passed"] for row in rows)
        and recorded.get("passed") is True
        and not row_mismatches
    )
    return {
        "passed": passed,
        "rows": rows,
        "recorded_row_mismatches": row_mismatches,
        "recorded_numerical_audit_sha256": sha256_file(panel_output / "numerical-audit.json"),
        "coarse_grid_sha256": sha256_file(panel_output / "coarse-grid-audit.json"),
    }


def run_replay(
    repository: Path,
    qualified_source_root: Path,
    qualification_directory: Path,
    verification_path: Path,
    source_manifest_path: Path,
    recovery_manifest_path: Path | None,
    panel_output: Path,
    original_panel: Path | None,
    bank_path: Path,
    output: Path,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("preserve an earlier independent audit")
    output.mkdir(parents=True)
    completed = read_json(panel_output / "completed.json")
    recovered = completed.get("status") == "panel_recovered_pending_scientific_audit"
    qualification_check = verify_qualification(
        qualified_source_root,
        qualification_directory,
        verification_path,
        source_manifest_path,
    )
    receipt_check = validate_completed_receipts(panel_output, original_panel)
    numerical_check = recompute_numerical_audit(panel_output)
    qualification = read_json(qualification_directory / "qualification.json")
    qualified_sources = qualification.get("source_hashes", {})
    completed_sources = completed.get("source_hashes", {})
    if not isinstance(qualified_sources, dict) or not isinstance(completed_sources, dict):
        raise ValueError("qualification and completed receipts require source hash mappings")
    if recovered:
        if recovery_manifest_path is None:
            raise ValueError("a recovered panel requires --recovery-manifest")
        recovery_source_check = verify_recovery_source_change(
            repository, qualified_source_root, qualified_sources, completed
        )
        recovery_manifest_check = verify_recovery_manifest(
            repository,
            qualified_source_root,
            recovery_manifest_path,
            source_manifest_path,
        )
        source_binding_match = recovery_source_check["passed"]
    else:
        local_sources = {
            relative: sha256_file(repository / relative)
            if (repository / relative).is_file()
            else None
            for relative in qualified_sources
        }
        source_binding_match = completed_sources == qualified_sources == local_sources
        recovery_source_check = None
        recovery_manifest_check = None

    observation_path = panel_output / "panel" / "observations.npz"
    with np.load(observation_path, allow_pickle=False) as values:
        raw_ids = np.asarray(values["site_ids"]).astype(str)
        order = np.argsort(raw_ids, kind="stable")
        site_ids = tuple(raw_ids[order])
        prey = np.asarray(values["prey_counts"][:, order], dtype=np.int64)
        predator = np.asarray(values["predator_counts"][:, order], dtype=np.int64)
        splits = np.asarray(values["site_splits"])[order].astype(str)
        site_a = np.asarray(values["site_a"][order], dtype=np.float64)
        map_a = np.asarray(values["map_a"], dtype=np.float64)
        prey_times = np.asarray(values["prey_times"], dtype=np.float64)
        predator_times = np.asarray(values["predator_times"], dtype=np.float64)
    if not np.array_equal(prey_times, PREY_TIMES) or not np.array_equal(
        predator_times, PREDATOR_TIMES
    ):
        raise ValueError("panel observation calendar differs from the registered calendar")
    training = splits == "training"
    if int(training.sum()) != 120 or int((~training).sum()) != 40:
        raise ValueError("panel split differs from 120 training and 40 holdout sites")
    with np.load(qualification_directory / "compressed-bank.npz", allow_pickle=False) as cached:
        cached_ids = tuple(np.asarray(cached["site_ids"]).astype(str))
        cached_mass = np.asarray(cached["category_mass"], dtype=np.float64)
    if cached_ids != site_ids:
        raise ValueError("qualified bank site order does not match sorted panel observations")
    bank_receipt = qualification["bank_receipt"]
    bank = load_direct_bank(bank_path, site_ids, bank_receipt["bank_file_sha256"])
    mass_difference = float(np.max(np.abs(bank.category_mass - cached_mass)))

    manifest = read_json(panel_output / "panel" / "manifest.json")
    truths = manifest.get("truths", [])
    direct_training = np.empty((16, 4), dtype=np.float64)
    stored_training = np.empty((16, 4), dtype=np.float64)
    direct_holdout = np.empty((16, 4), dtype=np.float64)
    stored_holdout = np.empty((16, 4), dtype=np.float64)
    direct_cp = np.empty((16, 4, 40), dtype=np.float64)
    stored_cp = np.empty((16, 4, 40), dtype=np.float64)
    direct_predator = np.empty((16, len(site_ids)), dtype=np.float64)
    cached_predator = np.empty_like(direct_predator)
    direct_statistics = np.empty((16, 2), dtype=np.float64)
    stored_statistics = np.empty((16, 2), dtype=np.float64)
    fit_records = []

    for index in range(16):
        cell = read_json(panel_output / "results" / f"cell-{index:02d}.json")
        pred_emission = predator_emissions(predator[index])
        direct_predator[index] = np.log(np.sum(bank.category_mass * pred_emission, axis=1))
        cached_predator[index] = np.log(np.sum(cached_mass * pred_emission, axis=1))
        for model_index, model in enumerate(MODEL_ORDER):
            fit = cell["paired"]["fits"][model]
            if fit["numerical_status"] != "converged" or fit["raw_logjoint"] is None:
                raise ValueError(f"cell {index} model {model} has no converged finite fit")
            parameters = {
                "h": float(fit["h"]),
                "beta": float(fit["beta"]),
                "mu": float(fit["mu"]),
                "detection_sd": float(fit["detection_sd"]),
            }
            score = direct_score(
                bank,
                prey[index],
                pred_emission,
                map_a,
                site_a,
                **parameters,
            )
            direct_training[index, model_index] = float(np.sum(score.joint_site[training]))
            stored_training[index, model_index] = float(fit["raw_logjoint"])
            direct_cp[index, model_index] = score.conditional_prey_site[~training]
            stored_values = np.asarray(
                cell["holdout_scores"][model]["conditional_prey_site_nats"],
                dtype=np.float64,
            )
            if stored_values.shape != (40,):
                raise ValueError("stored holdout conditional score has the wrong shape")
            stored_cp[index, model_index] = stored_values
            direct_holdout[index, model_index] = float(
                np.sum(score.conditional_prey_site[~training])
            )
            stored_holdout[index, model_index] = float(
                cell["holdout_scores"][model]["conditional_prey_total_nats"]
            )
            truth = truths[index] if index < len(truths) else {}
            fit_records.append(
                {
                    "index": index,
                    "model": model,
                    "parameters": parameters,
                    "truth": truth,
                    "training_direct": direct_training[index, model_index],
                    "training_stored": stored_training[index, model_index],
                    "training_absdiff": abs(
                        direct_training[index, model_index] - stored_training[index, model_index]
                    ),
                    "holdout_conditional_direct": direct_holdout[index, model_index],
                    "holdout_conditional_stored": stored_holdout[index, model_index],
                    "holdout_conditional_absdiff": abs(
                        direct_holdout[index, model_index] - stored_holdout[index, model_index]
                    ),
                    "holdout_site_max_absdiff": float(
                        np.max(
                            np.abs(direct_cp[index, model_index] - stored_cp[index, model_index])
                        )
                    ),
                }
            )
            print(json.dumps({"independent_replay": [index, model]}), flush=True)

        direct_statistics[index, 0] = 2.0 * max(
            0.0, direct_training[index, 0] - direct_training[index, 2]
        )
        direct_statistics[index, 1] = 2.0 * max(
            0.0, direct_training[index, 1] - direct_training[index, 3]
        )
        stored_statistics[index, 0] = float(cell["paired"]["statistics"]["constant"])
        stored_statistics[index, 1] = float(cell["paired"]["statistics"]["adjusted"])
        if abs(float(cell["paired"]["T"]) - stored_statistics[index, 1]) > 1e-12:
            raise ValueError("paired T differs from the stored adjusted statistic")

    maxima = {
        "training_total_absdiff": float(np.max(np.abs(direct_training - stored_training))),
        "holdout_conditional_total_absdiff": float(np.max(np.abs(direct_holdout - stored_holdout))),
        "holdout_conditional_site_absdiff": float(np.max(np.abs(direct_cp - stored_cp))),
        "predator_log_marginal_absdiff": float(np.max(np.abs(direct_predator - cached_predator))),
        "effect_statistic_absdiff": float(np.max(np.abs(direct_statistics - stored_statistics))),
        "category_mass_absdiff": mass_difference,
    }
    score_passed = (
        maxima["training_total_absdiff"] <= SCORE_TOLERANCE
        and maxima["holdout_conditional_total_absdiff"] <= SCORE_TOLERANCE
        and maxima["holdout_conditional_site_absdiff"] <= SCORE_TOLERANCE
        and maxima["predator_log_marginal_absdiff"] <= SCORE_TOLERANCE
        and maxima["effect_statistic_absdiff"] <= STATISTIC_TOLERANCE
        and maxima["category_mass_absdiff"] <= np.finfo(np.float64).eps
    )
    arrays_path = output / "independent-replay-arrays.npz"
    np.savez_compressed(
        arrays_path,
        model_order=np.asarray(MODEL_ORDER),
        direct_training=direct_training,
        stored_training=stored_training,
        direct_holdout_conditional=direct_holdout,
        stored_holdout_conditional=stored_holdout,
        direct_holdout_conditional_site=direct_cp,
        stored_holdout_conditional_site=stored_cp,
        direct_predator_log_marginal=direct_predator,
        cached_predator_log_marginal=cached_predator,
        direct_statistics=direct_statistics,
        stored_statistics=stored_statistics,
    )
    details_path = output / "independent-replay-details.json"
    write_json(
        details_path,
        {
            "fit_records": fit_records,
            "maxima": maxima,
            "score_tolerance": SCORE_TOLERANCE,
            "statistic_tolerance": STATISTIC_TOLERANCE,
        },
    )
    passed = bool(
        qualification_check["passed"]
        and receipt_check["passed"]
        and numerical_check["passed"]
        and source_binding_match
        and (recovery_manifest_check is None or recovery_manifest_check["passed"])
        and score_passed
    )
    receipt = {
        "passed": passed,
        "qualification": qualification_check,
        "panel_receipts": receipt_check,
        "numerical_audit_replay": numerical_check,
        "completed_source_bindings_match_qualification": source_binding_match,
        "recovery_mode": recovered,
        "recovery_source_change": recovery_source_check,
        "recovery_manifest": recovery_manifest_check,
        "direct_score_passed": score_passed,
        "maxima": maxima,
        "fit_count": len(fit_records),
        "source_bindings": len(qualification.get("source_hashes", {})),
        "inputs": {
            "raw_bank_sha256": sha256_file(bank_path),
            "qualification_sha256": sha256_file(qualification_directory / "qualification.json"),
            "qualification_verification_sha256": sha256_file(verification_path),
            "source_manifest_sha256": sha256_file(source_manifest_path),
            "recovery_manifest_sha256": sha256_file(recovery_manifest_path)
            if recovery_manifest_path is not None
            else None,
            "completed_sha256": sha256_file(panel_output / "completed.json"),
            "panel_manifest_sha256": sha256_file(panel_output / "panel" / "manifest.json"),
        },
        "outputs": {
            "independent_replay_arrays_sha256": sha256_file(arrays_path),
            "independent_replay_details_sha256": sha256_file(details_path),
        },
    }
    write_json(output / "independent-audit.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--qualified-source-root",
        type=Path,
        help="root of the exact source snapshot bound to the original qualification",
    )
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--qualification-verification", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--recovery-manifest", type=Path)
    parser.add_argument("--qualification-only", action="store_true")
    parser.add_argument("--panel-output", type=Path)
    parser.add_argument(
        "--original-panel",
        type=Path,
        help="interrupted panel root required when auditing a recovered panel",
    )
    parser.add_argument("--bank-path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.qualification_only:
        result = verify_qualification(
            args.qualified_source_root or args.repository,
            args.qualification,
            args.qualification_verification,
            args.source_manifest,
        )
    else:
        if args.panel_output is None or args.bank_path is None or args.output is None:
            parser.error("full replay requires --panel-output, --bank-path and --output")
        result = run_replay(
            args.repository,
            args.qualified_source_root or args.repository,
            args.qualification,
            args.qualification_verification,
            args.source_manifest,
            args.recovery_manifest,
            args.panel_output,
            args.original_panel,
            args.bank_path,
            args.output,
        )
    print(json.dumps(jsonable(result), sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
