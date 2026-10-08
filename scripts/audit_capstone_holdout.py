#!/usr/bin/env python3
"""Independent audit of the released Goal 061 holdout scores.

This auditor reconstructs the public map/design, binds the frozen arrival bank,
training observations, fits, and training diagnostics, and then evaluates the
same 16 fixed parameter vectors with the independent direct empirical scorer.
It never fits, optimises, generates a reference history, or accesses truth.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import itertools
import json
import math
import platform
import resource
import sys
import tarfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

SCHEMA = "goal061-independent-holdout-audit-v1"
EXPECTED_HOLDOUT_SHA256 = "53903e56b0b86d8d713bf643d9c3062e8ce918fa8b84afa48f9b8ace6859fe6a"
EXPECTED_TRAINING_LOCK_SHA256 = "2265d62e3e953792b2892a4d7b34c784d5800b2f7ba078db99ed753e13bd1861"
EXPECTED_MAIN_ADAPTER_SHA256 = "9e43c6664b6f47fc1b6111c243365982e6aaa39064d03e9e2067d972aa660bc7"
EXPECTED_HOLDOUT_MEMBERS = ("holdout.npz", "padding.bin", "salt.bin")
EXPECTED_CASE_IDS = tuple(f"case-{index:02d}" for index in range(4))
MODEL_ORDER = (
    "constant_free_h",
    "adjusted_free_h",
    "constant_h1",
    "adjusted_h1",
)
LEADING_PAIRS = {
    "case-00": ("adjusted_free_h", "adjusted_h1"),
    "case-01": ("adjusted_free_h", "adjusted_h1"),
    "case-02": ("constant_free_h", "adjusted_free_h"),
    "case-03": ("adjusted_free_h", "adjusted_h1"),
}
SCORE_TOLERANCE = 1e-8
STATISTIC_TOLERANCE = 1e-6
BANK_SIZE = 131_072
SITE_COUNT = 160
TRAINING_SITE_COUNT = 120
HOLDOUT_SITE_COUNT = 40


class AuditStopError(ValueError):
    """A frozen identity, schema, score, or aggregation failed audit."""


@dataclass(frozen=True)
class ObservationBundle:
    case_ids: tuple[str, ...]
    site_ids: tuple[str, ...]
    prey_counts: IntArray
    predator_counts: IntArray


@dataclass(frozen=True)
class AuditModules:
    public: ModuleType
    direct: ModuleType


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def array_binding(value: Any) -> dict[str, Any]:
    array = np.ascontiguousarray(np.asarray(value))
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "sha256": hashlib.sha256(array.tobytes(order="C")).hexdigest(),
    }


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AuditStopError(f"missing or invalid JSON: {path}") from error
    if not isinstance(value, dict):
        raise AuditStopError(f"JSON root must be an object: {path}")
    return value


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to replace earlier audit output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_jsonable(value), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_audit_modules(audit_source: Path) -> AuditModules:
    source = audit_source.resolve()
    required = ("audit_capstone_public.py", "audit_preinvasion_feasibility.py")
    missing = [name for name in required if not (source / name).is_file()]
    if missing:
        raise AuditStopError(f"independent audit source is incomplete: {missing}")
    sys.path.insert(0, str(source))
    try:
        direct = importlib.import_module("audit_preinvasion_feasibility")
        public = importlib.import_module("audit_capstone_public")
    finally:
        if sys.path and sys.path[0] == str(source):
            sys.path.pop(0)
    expected_modules = {
        public: source / "audit_capstone_public.py",
        direct: source / "audit_preinvasion_feasibility.py",
    }
    for module, expected in expected_modules.items():
        if Path(str(module.__file__)).resolve() != expected.resolve():
            raise AuditStopError(
                f"independent audit imported {module.__name__} from an unfrozen location"
            )
    return AuditModules(public=public, direct=direct)


def validate_holdout_archive(
    path: Path, extracted_npz: Path, expected_sha256: str
) -> dict[str, Any]:
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise AuditStopError("released holdout archive differs from its commitment")
    try:
        with tarfile.open(path, mode="r:*") as archive:
            members = archive.getmembers()
            names = tuple(member.name.removeprefix("./") for member in members)
            if tuple(sorted(names)) != tuple(sorted(EXPECTED_HOLDOUT_MEMBERS)):
                raise AuditStopError("released holdout archive member schema changed")
            if any(
                not member.isfile() or "/" in name or name in {"", ".", ".."}
                for name, member in zip(names, members, strict=True)
            ):
                raise AuditStopError(
                    "released holdout archive contains a non-regular or nested member"
                )
            holdout_member = members[names.index("holdout.npz")]
            member_handle = archive.extractfile(holdout_member)
            if member_handle is None:
                raise AuditStopError("released archive holdout member cannot be read")
            member_digest = hashlib.sha256()
            while block := member_handle.read(8 * 1024 * 1024):
                member_digest.update(block)
            member_sha256 = member_digest.hexdigest()
    except (OSError, tarfile.TarError) as error:
        raise AuditStopError("released holdout archive is not a valid tar archive") from error
    extracted_sha256 = sha256_file(extracted_npz)
    if member_sha256 != extracted_sha256:
        raise AuditStopError("extracted holdout.npz differs from the committed archive member")
    return {
        "sha256": actual,
        "holdout_npz_member_sha256": member_sha256,
        "extracted_holdout_npz_sha256": extracted_sha256,
        "members": [
            {"name": name, "size": int(member.size)}
            for name, member in zip(names, members, strict=True)
        ],
    }


def load_observations(
    path: Path,
    *,
    expected_sites: int,
    label: str,
) -> ObservationBundle:
    required = {"case_ids", "site_ids", "prey_counts", "predator_counts"}
    try:
        with np.load(path, allow_pickle=False) as saved:
            if set(saved.files) != required:
                raise AuditStopError(f"{label} observation archive schema changed")
            case_ids = tuple(str(value) for value in np.asarray(saved["case_ids"]).reshape(-1))
            site_ids = tuple(str(value) for value in np.asarray(saved["site_ids"]).reshape(-1))
            prey_raw = np.asarray(saved["prey_counts"])
            predator_raw = np.asarray(saved["predator_counts"])
    except (OSError, ValueError) as error:
        if isinstance(error, AuditStopError):
            raise
        raise AuditStopError(f"{label} observation archive is invalid") from error
    if case_ids != EXPECTED_CASE_IDS:
        raise AuditStopError(f"{label} case identities changed")
    if (
        len(site_ids) != expected_sites
        or len(set(site_ids)) != expected_sites
        or any(not value for value in site_ids)
    ):
        raise AuditStopError(f"{label} site identities are invalid")
    if (
        prey_raw.shape != (4, expected_sites, 13)
        or predator_raw.shape != (4, expected_sites, 6)
        or not np.issubdtype(prey_raw.dtype, np.integer)
        or not np.issubdtype(predator_raw.dtype, np.integer)
        or not np.isin(prey_raw, (0, 1, 2)).all()
        or not np.isin(predator_raw, (0, 1, 2)).all()
    ):
        raise AuditStopError(f"{label} count arrays violate the frozen schema")
    return ObservationBundle(
        case_ids,
        site_ids,
        np.asarray(prey_raw, dtype=np.int64),
        np.asarray(predator_raw, dtype=np.int64),
    )


def merge_canonical_observations(
    training: ObservationBundle,
    holdout: ObservationBundle,
    canonical_site_ids: Sequence[str],
    canonical_training_mask: NDArray[Any],
) -> tuple[IntArray, IntArray, dict[str, Any]]:
    """Merge by identifier, never by concatenated row position."""
    canonical = tuple(str(value) for value in canonical_site_ids)
    mask = np.asarray(canonical_training_mask, dtype=bool)
    if (
        len(canonical) != SITE_COUNT
        or len(set(canonical)) != SITE_COUNT
        or mask.shape != (SITE_COUNT,)
        or int(mask.sum()) != TRAINING_SITE_COUNT
    ):
        raise AuditStopError("public canonical site partition is invalid")
    training_set = set(training.site_ids)
    holdout_set = set(holdout.site_ids)
    expected_training = {canonical[index] for index in np.flatnonzero(mask)}
    expected_holdout = {canonical[index] for index in np.flatnonzero(~mask)}
    if training_set & holdout_set:
        raise AuditStopError("training and holdout site identities overlap")
    if training_set != expected_training or holdout_set != expected_holdout:
        raise AuditStopError("released observations do not complement the public split")
    if training.case_ids != holdout.case_ids:
        raise AuditStopError("training and holdout case identities differ")

    lookup = {site_id: index for index, site_id in enumerate(canonical)}
    prey = np.empty((4, SITE_COUNT, 13), dtype=np.int64)
    predator = np.empty((4, SITE_COUNT, 6), dtype=np.int64)
    assigned = np.zeros(SITE_COUNT, dtype=bool)
    for bundle in (training, holdout):
        positions = np.asarray([lookup[site_id] for site_id in bundle.site_ids], dtype=np.int64)
        if assigned[positions].any():
            raise AuditStopError("observation merge assigns a canonical site twice")
        prey[:, positions] = bundle.prey_counts
        predator[:, positions] = bundle.predator_counts
        assigned[positions] = True
    if not assigned.all():
        raise AuditStopError("observation merge leaves canonical sites unassigned")

    training_positions = np.asarray(
        [lookup[site_id] for site_id in training.site_ids], dtype=np.int64
    )
    holdout_positions = np.asarray(
        [lookup[site_id] for site_id in holdout.site_ids], dtype=np.int64
    )
    if not mask[training_positions].all() or mask[holdout_positions].any():
        raise AuditStopError("observation merge changed the public split labels")
    return (
        prey,
        predator,
        {
            "method": "identifier-indexed assignment into canonical 160-site order",
            "canonical_site_ids": list(canonical),
            "canonical_training_mask": mask.tolist(),
            "training_input_order": list(training.site_ids),
            "holdout_input_order": list(holdout.site_ids),
            "training_positions": training_positions.tolist(),
            "holdout_positions": holdout_positions.tolist(),
            "prey_counts": array_binding(prey),
            "predator_counts": array_binding(predator),
        },
    )


def verify_training_manifest(training_root: Path, training_npz: Path) -> dict[str, Any]:
    path = training_npz.with_name("training_manifest.json")
    manifest = read_json(path)
    expected = {
        "schema_version": "goal060-training-v1",
        "case_count": 4,
        "site_count": TRAINING_SITE_COUNT,
        "prey_visits": 13,
        "predator_visits": 6,
        "arrays_sha256": sha256_file(training_npz),
    }
    if manifest != expected:
        raise AuditStopError("training observation manifest differs from its frozen contract")
    return {"path": str(path.relative_to(training_root)), "sha256": sha256_file(path), **manifest}


def verify_public_ready(public_package: Path) -> dict[str, Any]:
    ready_path = public_package / "public-ready.json"
    ready = read_json(ready_path)
    files = ready.get("files")
    critical = (
        "arrival_bank/arrivals.npy",
        "arrival_bank/manifest.json",
        "public_inputs/accepted_candidate.json",
        "public_inputs/exposure.npz",
        "public_inputs/failed_attempts.json",
        "public_inputs/public_inputs.json",
        "public_inputs/public_inputs.npz",
        "public_inputs/seed_ledger.json",
    )
    if ready.get("public_ready") is not True or not isinstance(files, Mapping):
        raise AuditStopError("frozen public package is not marked ready")
    mismatches = []
    bindings: dict[str, str] = {}
    for relative in critical:
        path = public_package / relative
        expected = files.get(relative)
        actual = sha256_file(path) if path.is_file() else None
        if not isinstance(expected, str) or actual != expected:
            mismatches.append(relative)
        elif actual is not None:
            bindings[relative] = actual
    if mismatches:
        raise AuditStopError(f"critical frozen public files changed: {mismatches}")
    return {
        "sha256": sha256_file(ready_path),
        "schema_version": ready.get("schema_version"),
        "critical_files": bindings,
    }


def verify_training_lock(
    training_lock: Path,
    training_root: Path,
    public_package: Path,
    audit_source: Path,
    *,
    expected_sha256: str,
) -> dict[str, Any]:
    """Bind every file used for scoring to the immutable training lock."""
    lock_sha256 = sha256_file(training_lock)
    if lock_sha256 != expected_sha256:
        raise AuditStopError("training lock differs from the accepted root digest")
    lock = read_json(training_lock)
    if lock.get("schema") != "goal061-blinded-training-lock-v1":
        raise AuditStopError("training lock schema changed")
    children = lock.get("child_manifests")
    if not isinstance(children, list):
        raise AuditStopError("training lock has no child manifests")
    by_role: dict[str, list[Mapping[str, Any]]] = {}
    for child in children:
        if isinstance(child, Mapping) and isinstance(child.get("role"), str):
            by_role.setdefault(str(child["role"]), []).append(child)

    def unique_child(role: str) -> Mapping[str, Any]:
        rows = by_role.get(role, [])
        if len(rows) != 1:
            raise AuditStopError(f"training lock does not uniquely bind {role}")
        return rows[0]

    source_manifest_path = training_root / "source-manifest.json"
    computation_path = training_root / "analysis" / "computation-complete.json"
    source_sha256 = sha256_file(source_manifest_path)
    computation_sha256 = sha256_file(computation_path)
    public_ready_sha256 = sha256_file(public_package / "public-ready.json")
    if (
        lock.get("source_manifest_sha256") != source_sha256
        or unique_child("frozen_production_source").get("manifest_sha256") != source_sha256
        or unique_child("frozen_production_inputs").get("manifest_sha256") != source_sha256
        or unique_child("completed_training_analysis").get("manifest_sha256") != computation_sha256
        or unique_child("qualified_public_package").get("manifest_sha256") != public_ready_sha256
    ):
        raise AuditStopError("training lock child-manifest binding changed")

    source_manifest = read_json(source_manifest_path)
    if (
        source_manifest.get("schema_version") != "goal061-blinded-training-freeze-v1"
        or source_manifest.get("scientific_source_changes") != []
    ):
        raise AuditStopError("frozen source manifest contract changed")
    source_hashes = source_manifest.get("source_hashes")
    frozen_inputs = source_manifest.get("frozen_input_hashes")
    if not isinstance(source_hashes, Mapping) or not isinstance(frozen_inputs, Mapping):
        raise AuditStopError("frozen source manifest lacks hash mappings")
    selected_sources = (
        "scripts/audit_capstone_public.py",
        "scripts/audit_preinvasion_feasibility.py",
        "src/latent_landscapes/arc3_design.py",
        "src/latent_landscapes/arc3_landscapes.py",
        "src/latent_landscapes/goal006/spread.py",
        "src/latent_landscapes/goal007/benchmark.py",
        "src/latent_landscapes/misspecification_generator.py",
        "src/latent_landscapes/capstone_references.py",
        "src/latent_landscapes/capstone_qualification.py",
        "src/latent_landscapes/capstone_training.py",
        "src/latent_landscapes/preinvasion_fitting.py",
        "src/latent_landscapes/preinvasion_likelihood.py",
    )
    source_mismatches = []
    for relative in selected_sources:
        if relative.startswith("scripts/"):
            path = audit_source / Path(relative).name
        else:
            path = training_root / "source" / relative
        if not path.is_file() or sha256_file(path) != source_hashes.get(relative):
            source_mismatches.append(relative)
    if source_mismatches:
        raise AuditStopError(f"frozen independent scoring sources changed: {source_mismatches}")
    expected_package = (training_root / "source" / "src" / "latent_landscapes").resolve()
    latent = importlib.import_module("latent_landscapes")
    package_paths = tuple(Path(value).resolve() for value in latent.__path__)
    if expected_package not in package_paths:
        raise AuditStopError("independent audit did not import the frozen scientific source")

    training_relative = "training-inputs/training_observations.npz"
    manifest_relative = "training-inputs/training_manifest.json"
    input_mismatches = []
    for relative in (training_relative, manifest_relative):
        path = training_root / relative
        if not path.is_file() or sha256_file(path) != frozen_inputs.get(relative):
            input_mismatches.append(relative)
    if input_mismatches:
        raise AuditStopError(f"frozen training inputs changed: {input_mismatches}")

    computation = read_json(computation_path)
    if (
        computation.get("schema") != "goal061-blinded-training-computation-v1"
        or computation.get("all_numerical_audits_consistent") is not True
        or computation.get("diagnostic_cases_requiring_review") != []
    ):
        raise AuditStopError("frozen computation manifest is not numerically qualified")
    computation_files = computation.get("files")
    if not isinstance(computation_files, Mapping):
        raise AuditStopError("frozen computation manifest lacks file hashes")
    selected_computation = []
    for history in range(4):
        selected_computation.extend(
            (
                f"analysis/fit/fits/history-{history:02d}-full-main.json",
                f"analysis/fit/fits/history-{history:02d}-full.json",
                f"analysis/audits/training/history-{history:02d}.json",
            )
        )
    computation_mismatches = []
    for relative in selected_computation:
        path = training_root / relative
        if not path.is_file() or sha256_file(path) != computation_files.get(relative):
            computation_mismatches.append(relative)
    if computation_mismatches:
        raise AuditStopError(f"frozen fit or diagnostic files changed: {computation_mismatches}")
    return {
        "training_lock_sha256": lock_sha256,
        "source_manifest_sha256": source_sha256,
        "computation_manifest_sha256": computation_sha256,
        "public_ready_sha256": public_ready_sha256,
        "training_observations_sha256": str(frozen_inputs[training_relative]),
        "training_manifest_sha256": str(frozen_inputs[manifest_relative]),
        "selected_source_hashes": {
            relative: str(source_hashes[relative]) for relative in selected_sources
        },
        "selected_computation_file_count": len(selected_computation),
    }


def load_direct_bank(
    modules: AuditModules,
    public_package: Path,
    canonical_site_ids: Sequence[str],
) -> tuple[Any, dict[str, Any]]:
    directory = public_package / "arrival_bank"
    manifest_path = directory / "manifest.json"
    array_path = directory / "arrivals.npy"
    manifest = read_json(manifest_path)
    expected_ids = tuple(str(value) for value in canonical_site_ids)
    expected_file_hash = manifest.get("arrivals_file_sha256")
    if (
        manifest.get("schema_version") != "goal059-arrival-bank-v1"
        or manifest.get("bank_size") != BANK_SIZE
        or manifest.get("array_shape") != [BANK_SIZE, SITE_COUNT]
        or tuple(str(value) for value in manifest.get("site_ids", ())) != expected_ids
        or not isinstance(expected_file_hash, str)
    ):
        raise AuditStopError("arrival-bank manifest identity or shape changed")
    actual_file_hash = sha256_file(array_path)
    if actual_file_hash != expected_file_hash:
        raise AuditStopError("raw arrival bank differs from its manifest")
    arrivals = np.load(array_path, mmap_mode="r", allow_pickle=False)
    if (
        arrivals.shape != (BANK_SIZE, SITE_COUNT)
        or arrivals.dtype != np.dtype(np.float64)
        or not np.isfinite(arrivals).all()
        or (arrivals < 0).any()
    ):
        raise AuditStopError("raw arrival bank array is invalid")
    array_hash = hashlib.sha256(np.ascontiguousarray(arrivals).tobytes(order="C")).hexdigest()
    if array_hash != manifest.get("array_sha256"):
        raise AuditStopError("raw arrival bank content hash differs from its manifest")
    bank = modules.public.make_direct_bank(arrivals, expected_ids)
    if (
        tuple(bank.site_ids) != expected_ids
        or int(bank.bank_size) != BANK_SIZE
        or np.asarray(bank.category_mass).shape != (SITE_COUNT, 7)
    ):
        raise AuditStopError("independent direct-bank construction changed identity")
    return bank, {
        "manifest_sha256": sha256_file(manifest_path),
        "arrivals_file_sha256": actual_file_hash,
        "array_sha256": array_hash,
        "array_shape": list(arrivals.shape),
        "bank_size": int(bank.bank_size),
        "site_ids": list(expected_ids),
    }


def _finite_float(value: Any, *, label: str) -> float:
    if value is None or isinstance(value, bool):
        raise AuditStopError(f"{label} is not a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise AuditStopError(f"{label} is not a finite number") from error
    if not math.isfinite(result):
        raise AuditStopError(f"{label} is not a finite number")
    return result


def load_fixed_fits(
    training_root: Path,
) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, Any]]:
    all_points: dict[str, dict[str, dict[str, float]]] = {}
    receipts: dict[str, Any] = {}
    for history, case_id in enumerate(EXPECTED_CASE_IDS):
        fit_dir = training_root / "analysis" / "fit" / "fits"
        main_path = fit_dir / f"history-{history:02d}-full-main.json"
        full_path = fit_dir / f"history-{history:02d}-full.json"
        audit_path = (
            training_root / "analysis" / "audits" / "training" / f"history-{history:02d}.json"
        )
        main = read_json(main_path)
        full = read_json(full_path)
        audit = read_json(audit_path)
        if (
            main.get("history") != history
            or full.get("history") != history
            or main.get("representation") != "full"
            or full.get("representation") != "full"
            or main.get("bank_size") != BANK_SIZE
            or full.get("bank_size") != BANK_SIZE
        ):
            raise AuditStopError(f"{case_id} fit identity changed")
        main_fits = main.get("fits")
        full_fits = full.get("fits")
        if (
            not isinstance(main_fits, Mapping)
            or set(main_fits) != set(MODEL_ORDER)
            or main_fits != full_fits
        ):
            raise AuditStopError(f"{case_id} fixed fit records are incomplete or inconsistent")
        if (
            audit.get("passed") is not True
            or audit.get("audit_consistent") is not True
            or audit.get("diagnostic_passed") is not True
            or audit.get("release_blocked") is not False
            or audit.get("case_id") != case_id
            or audit.get("history") != history
        ):
            raise AuditStopError(f"{case_id} frozen training audit is not valid")
        main_errors = audit.get("main_score_abs_error")
        if not isinstance(main_errors, Mapping) or set(main_errors) != set(MODEL_ORDER):
            raise AuditStopError(f"{case_id} training score audit is incomplete")
        if any(
            abs(_finite_float(main_errors[model], label=f"{case_id} {model} training replay error"))
            > SCORE_TOLERANCE
            for model in MODEL_ORDER
        ):
            raise AuditStopError(f"{case_id} training score replay exceeded tolerance")
        input_files = audit.get("input_files")
        if not isinstance(input_files, Mapping):
            raise AuditStopError(f"{case_id} training audit lacks input bindings")
        input_mismatches = []
        for relative, expected in input_files.items():
            path = training_root / str(relative)
            if not path.is_file() or sha256_file(path) != expected:
                input_mismatches.append(str(relative))
        if input_mismatches:
            raise AuditStopError(f"{case_id} frozen training inputs changed: {input_mismatches}")

        points: dict[str, dict[str, float]] = {}
        for model in MODEL_ORDER:
            row = main_fits[model]
            if (
                not isinstance(row, Mapping)
                or row.get("model") != model
                or row.get("numerical_status") != "converged"
            ):
                raise AuditStopError(f"{case_id} {model} is not a converged fixed fit")
            point = {
                "h": _finite_float(row.get("h"), label=f"{case_id} {model} h"),
                "beta": _finite_float(row.get("beta"), label=f"{case_id} {model} beta"),
                "mu": _finite_float(row.get("mu"), label=f"{case_id} {model} mu"),
                "detection_sd": _finite_float(
                    row.get("detection_sd"), label=f"{case_id} {model} detection_sd"
                ),
            }
            if (
                point["h"] < 1.0
                or point["mu"] <= 0.0
                or not 0.0 <= point["detection_sd"] < math.sqrt(0.65 * 0.35)
                or (model.startswith("constant") and point["beta"] != 0.0)
                or (model.endswith("h1") and point["h"] != 1.0)
            ):
                raise AuditStopError(f"{case_id} {model} fixed point violates its model domain")
            points[model] = point
        all_points[case_id] = points
        receipts[case_id] = {
            "main_fit_sha256": sha256_file(main_path),
            "full_fit_sha256": sha256_file(full_path),
            "training_audit_sha256": sha256_file(audit_path),
            "maximum_training_replay_abs_error": max(
                abs(float(main_errors[model])) for model in MODEL_ORDER
            ),
            "parameters": points,
            "fit_record_sha256": {
                model: canonical_json_sha256(main_fits[model]) for model in MODEL_ORDER
            },
            "diagnostic_flags": {
                model: {
                    "main_statuses_converged": full.get("main_statuses_converged", {}).get(model),
                    "audit_passed": audit.get("passed"),
                    "diagnostic_passed": audit.get("diagnostic_passed"),
                    "diagnostics_change_declaration": audit.get("diagnostics_change_declaration"),
                }
                for model in MODEL_ORDER
            },
        }
    return all_points, receipts


def _case_clusters(context: Any) -> tuple[str, ...]:
    mask = np.asarray(context.training, dtype=bool)
    clusters = tuple(str(value) for value in np.asarray(context.cluster_ids)[~mask])
    if len(clusters) != HOLDOUT_SITE_COUNT or len(set(clusters)) != 8:
        raise AuditStopError("public holdout cluster structure changed")
    counts = {cluster: clusters.count(cluster) for cluster in set(clusters)}
    if set(counts.values()) != {5}:
        raise AuditStopError("public holdout clusters are not eight five-site groups")
    return clusters


def score_fixed_points(
    modules: AuditModules,
    bank: Any,
    context: Any,
    prey: IntArray,
    predator: IntArray,
    fixed_points: Mapping[str, Mapping[str, Mapping[str, float]]],
) -> dict[str, Any]:
    holdout_mask = ~np.asarray(context.training, dtype=bool)
    holdout_site_ids = tuple(str(value) for value in np.asarray(context.site_ids)[holdout_mask])
    holdout_clusters = _case_clusters(context)
    cases: dict[str, Any] = {}
    for history, case_id in enumerate(EXPECTED_CASE_IDS):
        models: dict[str, Any] = {}
        totals: dict[str, float] = {}
        for model in MODEL_ORDER:
            point = fixed_points[case_id][model]
            result = modules.public.direct_point_score(
                bank,
                context,
                prey[history],
                predator[history],
                point,
            )
            site = np.asarray(result["holdout_conditional_prey_site"], dtype=np.float64)
            if site.shape != (HOLDOUT_SITE_COUNT,) or not np.isfinite(site).all():
                raise AuditStopError(f"{case_id} {model} produced invalid direct site scores")
            total = float(np.sum(site, dtype=np.float64))
            mean = float(np.mean(site, dtype=np.float64))
            clusters = {
                cluster: float(
                    np.sum(site[np.asarray(holdout_clusters) == cluster], dtype=np.float64)
                )
                for cluster in sorted(set(holdout_clusters))
            }
            if total != float(result["holdout_conditional_prey_total"]):
                raise AuditStopError(f"{case_id} {model} direct total aggregation changed")
            returned_clusters = {
                str(key): float(value) for key, value in result["holdout_cluster_totals"].items()
            }
            if returned_clusters != clusters:
                raise AuditStopError(f"{case_id} {model} direct cluster aggregation changed")
            models[model] = {
                "parameters": dict(point),
                "conditional_prey_total_nats": total,
                "conditional_prey_nats_per_site": mean,
                "conditional_prey_site_nats": site.tolist(),
                "cluster_contributions_nats": clusters,
            }
            totals[model] = total

        differences = [
            {
                "left": left,
                "right": right,
                "left_minus_right_nats": totals[left] - totals[right],
            }
            for left, right in itertools.combinations(MODEL_ORDER, 2)
        ]
        maximum = max(totals.values())
        winner_set = [model for model in MODEL_ORDER if totals[model] == maximum]
        ordered = sorted(totals.values(), reverse=True)
        winning_margin = ordered[0] - ordered[1]
        predicted = LEADING_PAIRS[case_id]
        cases[case_id] = {
            "history": history,
            "holdout_site_ids": list(holdout_site_ids),
            "holdout_cluster_ids": list(holdout_clusters),
            "models": models,
            "pairwise_differences": differences,
            "winner_set": winner_set,
            "winning_margin_nats": winning_margin,
            "leading_pair_forecast": {
                "named_pair": list(predicted),
                "hit": bool(set(winner_set) & set(predicted)),
                "co_winners_outside_named_pair": [
                    model for model in winner_set if model not in predicted
                ],
                "named_two_of_four": True,
            },
        }
    return cases


def _maximum_abs_difference(left: Sequence[Any], right: Sequence[Any], *, label: str) -> float:
    try:
        first = np.asarray(left, dtype=np.float64)
        second = np.asarray(right, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise AuditStopError(f"main result {label} is not numeric") from error
    if first.shape != second.shape or not np.isfinite(first).all() or not np.isfinite(second).all():
        raise AuditStopError(f"main result {label} has the wrong shape or nonfinite values")
    return float(np.max(np.abs(first - second))) if first.size else 0.0


def _main_cases(main: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = main.get("cases")
    if isinstance(raw, Mapping):
        cases = {str(key): value for key, value in raw.items()}
    elif isinstance(raw, list):
        cases = {
            str(row.get("case_id")): row
            for row in raw
            if isinstance(row, Mapping) and isinstance(row.get("case_id"), str)
        }
    else:
        raise AuditStopError("main score output has no case results")
    if set(cases) != set(EXPECTED_CASE_IDS) or not all(
        isinstance(row, Mapping) for row in cases.values()
    ):
        raise AuditStopError("main score output case identities changed")
    return cases  # type: ignore[return-value]


def compare_main_results(
    main: Mapping[str, Any],
    independent_cases: Mapping[str, Any],
    fit_receipts: Mapping[str, Any],
    *,
    tolerance: float,
) -> dict[str, Any]:
    """Compare every score and aggregation while preserving raw discrepancies."""
    cases = _main_cases(main)
    rows: list[dict[str, Any]] = []
    all_within = True
    for case_id in EXPECTED_CASE_IDS:
        main_case = cases[case_id]
        direct_case = independent_cases[case_id]
        main_models = main_case.get("fits", main_case.get("models"))
        if not isinstance(main_models, Mapping) or set(main_models) != set(MODEL_ORDER):
            raise AuditStopError(f"main score output lacks four models for {case_id}")
        main_totals: dict[str, float] = {}
        for model in MODEL_ORDER:
            main_row = main_models[model]
            direct_row = direct_case["models"][model]
            if not isinstance(main_row, Mapping):
                raise AuditStopError(f"main score output has invalid {case_id} {model} row")
            if main_row.get("status") != "available":
                raise AuditStopError(f"main score output made {case_id} {model} unavailable")
            fit_payload = main_row.get("fit")
            if not isinstance(fit_payload, Mapping):
                raise AuditStopError(
                    f"main score output omits the frozen fit for {case_id} {model}"
                )
            if (
                canonical_json_sha256(fit_payload)
                != fit_receipts[case_id]["fit_record_sha256"][model]
            ):
                raise AuditStopError(
                    f"main score output changed the frozen fit record for {case_id} {model}"
                )
            main_parameters = {
                name: fit_payload.get(name) for name in ("h", "beta", "mu", "detection_sd")
            }
            if main_parameters != direct_row["parameters"]:
                raise AuditStopError(
                    f"main score output changed the fixed parameters for {case_id} {model}"
                )
            if main_row.get("fit_status") != "converged":
                raise AuditStopError(f"main score output changed fit status for {case_id} {model}")
            if main_row.get("diagnostic_flags") != fit_receipts[case_id]["diagnostic_flags"][model]:
                raise AuditStopError(
                    f"main score output changed diagnostic flags for {case_id} {model}"
                )
            main_total = _finite_float(
                main_row.get("total_nats", main_row.get("conditional_prey_total_nats")),
                label=f"{case_id} {model} total",
            )
            main_totals[model] = main_total
            total_difference = main_total - direct_row["conditional_prey_total_nats"]
            mean_difference = (
                _finite_float(
                    main_row.get(
                        "mean_nats_per_site", main_row.get("conditional_prey_nats_per_site")
                    ),
                    label=f"{case_id} {model} mean",
                )
                - direct_row["conditional_prey_nats_per_site"]
            )
            site_max = _maximum_abs_difference(
                main_row.get("site_nats", main_row.get("conditional_prey_site_nats", ())),
                direct_row["conditional_prey_site_nats"],
                label=f"{case_id} {model} site scores",
            )
            main_clusters = main_row.get("cluster_nats", main_row.get("cluster_contributions_nats"))
            direct_clusters = direct_row["cluster_contributions_nats"]
            if not isinstance(main_clusters, Mapping) or set(main_clusters) != set(direct_clusters):
                raise AuditStopError(f"main score output changed clusters for {case_id} {model}")
            cluster_differences = {
                cluster: _finite_float(
                    main_clusters[cluster], label=f"{case_id} {model} {cluster} total"
                )
                - direct_clusters[cluster]
                for cluster in sorted(direct_clusters)
            }
            maximum = max(
                abs(total_difference),
                abs(mean_difference),
                site_max,
                *(abs(value) for value in cluster_differences.values()),
            )
            within = maximum <= tolerance
            all_within &= within
            rows.append(
                {
                    "case_id": case_id,
                    "model": model,
                    "main_minus_independent_total_nats": total_difference,
                    "main_minus_independent_mean_nats": mean_difference,
                    "maximum_site_abs_difference_nats": site_max,
                    "main_minus_independent_cluster_nats": cluster_differences,
                    "maximum_abs_difference_nats": maximum,
                    "within_tolerance": within,
                }
            )

        main_pairwise = main_case.get("pair_differences", main_case.get("pairwise_differences"))
        if not isinstance(main_pairwise, list) or len(main_pairwise) != 6:
            raise AuditStopError(f"main score output lacks six pairwise differences for {case_id}")
        direct_pairs = {
            (row["left"], row["right"]): row["left_minus_right_nats"]
            for row in direct_case["pairwise_differences"]
        }
        observed_pairs: dict[tuple[str, str], float] = {}
        for row in main_pairwise:
            if not isinstance(row, Mapping):
                raise AuditStopError(f"main score output has malformed pairwise rows for {case_id}")
            key = (str(row.get("left")), str(row.get("right")))
            observed_pairs[key] = _finite_float(
                row.get("left_minus_right_nats"), label=f"{case_id} pairwise difference {key}"
            )
        if set(observed_pairs) != set(direct_pairs):
            raise AuditStopError(f"main score output pair identities changed for {case_id}")
        main_pair_arithmetic = {
            (left, right): observed_pairs[(left, right)] - (main_totals[left] - main_totals[right])
            for left, right in observed_pairs
        }
        pair_discrepancies = {
            f"{left}_minus_{right}": observed_pairs[(left, right)] - direct_pairs[(left, right)]
            for left, right in direct_pairs
        }
        pair_within = all(abs(value) <= tolerance for value in pair_discrepancies.values())
        pair_arithmetic_exact = all(value == 0.0 for value in main_pair_arithmetic.values())
        all_within &= pair_within
        all_within &= pair_arithmetic_exact
        maximum_main = max(main_totals.values())
        exact_main_winners = [model for model in MODEL_ORDER if main_totals[model] == maximum_main]
        stored_winners = list(main_case.get("winner_set", ()))
        stored_winner_arithmetic_exact = stored_winners == exact_main_winners
        all_within &= stored_winner_arithmetic_exact
        independent_winners = direct_case["winner_set"]
        exact_winner_sets_agree = exact_main_winners == independent_winners
        main_margin = main_case.get("winning_margin_nats")
        direct_margin = direct_case["winning_margin_nats"]
        if main_margin is None or direct_margin is None:
            margin_difference = None
        else:
            margin_difference = (
                _finite_float(main_margin, label=f"{case_id} winning margin") - direct_margin
            )
        ordered_main = sorted(main_totals.values(), reverse=True)
        recomputed_main_margin = ordered_main[0] - ordered_main[1]
        main_margin_arithmetic_exact = (
            main_margin is None
            if recomputed_main_margin is None
            else _finite_float(main_margin, label=f"{case_id} winning margin")
            == recomputed_main_margin
        )
        all_within &= main_margin_arithmetic_exact
        numerically_resolved = bool(
            exact_winner_sets_agree and recomputed_main_margin > 2.0 * tolerance
        )
        predicted_pair = list(LEADING_PAIRS[case_id])
        expected_hit = bool(set(exact_main_winners) & set(predicted_pair))
        expected_outside = [model for model in exact_main_winners if model not in predicted_pair]
        forecast_exact = bool(
            list(main_case.get("predicted_pair", ())) == predicted_pair
            and main_case.get("pair_hit") is expected_hit
            and main_case.get("co_winners_outside_predicted_pair") == expected_outside
            and main_case.get("named_two_of_four") is True
        )
        all_within &= forecast_exact
        rows.append(
            {
                "case_id": case_id,
                "aggregation": "pairwise_and_winner",
                "main_minus_independent_pairwise_nats": pair_discrepancies,
                "main_pairwise_arithmetic_residual_nats": {
                    f"{left}_minus_{right}": value
                    for (left, right), value in main_pair_arithmetic.items()
                },
                "stored_winner_set_matches_main_exact_maxima": stored_winner_arithmetic_exact,
                "main_winner_set": exact_main_winners,
                "independent_winner_set": independent_winners,
                "winner_sets_match_exactly": exact_winner_sets_agree,
                "main_minus_independent_winning_margin_nats": margin_difference,
                "stored_winning_margin_matches_main_totals": main_margin_arithmetic_exact,
                "ranking_numerically_resolved_at_audit_tolerance": numerically_resolved,
                "leading_pair_forecast_arithmetic_exact": forecast_exact,
                "within_tolerance": pair_within
                and pair_arithmetic_exact
                and stored_winner_arithmetic_exact
                and main_margin_arithmetic_exact,
            }
        )
    return {
        "passed": all_within,
        "absolute_tolerance_nats": tolerance,
        "rows": rows,
        "maximum_abs_difference_nats": max(
            (
                float(row.get("maximum_abs_difference_nats", 0.0))
                for row in rows
                if row.get("maximum_abs_difference_nats") is not None
            ),
            default=0.0,
        ),
    }


def verify_main_provenance(
    main: Mapping[str, Any],
    lock_receipt: Mapping[str, Any],
    holdout_archive_sha256: str,
) -> dict[str, Any]:
    if main.get("schema") != "goal061-capstone-holdout-score-v1":
        raise AuditStopError("main holdout score schema changed")
    if list(main.get("models", ())) != list(MODEL_ORDER):
        raise AuditStopError("main holdout score model order changed")
    expected = {
        "holdout_archive_sha256": holdout_archive_sha256,
        "training_observations_sha256": lock_receipt["training_observations_sha256"],
        "computation_manifest_sha256": lock_receipt["computation_manifest_sha256"],
        "training_lock_sha256": lock_receipt["training_lock_sha256"],
    }
    mismatches = {
        name: {"expected": value, "actual": main.get(name)}
        for name, value in expected.items()
        if main.get(name) != value
    }
    if mismatches:
        raise AuditStopError(f"main holdout score provenance changed: {sorted(mismatches)}")
    source_hashes = main.get("source_hashes")
    if not isinstance(source_hashes, Mapping):
        raise AuditStopError("main holdout score lacks frozen source hashes")
    expected_sources = lock_receipt["selected_source_hashes"]
    production_relatives = (
        "src/latent_landscapes/capstone_references.py",
        "src/latent_landscapes/capstone_qualification.py",
        "src/latent_landscapes/capstone_training.py",
        "src/latent_landscapes/preinvasion_fitting.py",
        "src/latent_landscapes/preinvasion_likelihood.py",
    )
    source_mismatches = []
    for relative in production_relatives:
        if source_hashes.get(relative) != expected_sources.get(relative):
            source_mismatches.append(relative)
    if source_hashes.get("source-manifest.json") != lock_receipt["source_manifest_sha256"]:
        source_mismatches.append("source-manifest.json")
    if source_mismatches:
        raise AuditStopError(
            f"main scorer did not use the frozen production source: {source_mismatches}"
        )
    runtime = main.get("runtime")
    if not isinstance(runtime, Mapping):
        raise AuditStopError("main holdout score lacks runtime evidence")
    if (
        not str(runtime.get("python", "")).startswith("3.14.5")
        or runtime.get("numpy") != "2.5.1"
        or runtime.get("scipy") != "1.18.0"
        or runtime.get("adapter_script_sha256") != EXPECTED_MAIN_ADAPTER_SHA256
    ):
        raise AuditStopError(
            "main scorer did not use the frozen adapter and qualified numerical runtime"
        )
    elapsed = _finite_float(runtime.get("elapsed_seconds"), label="main elapsed_seconds")
    maximum_rss = runtime.get("max_rss_bytes")
    if elapsed <= 0.0 or type(maximum_rss) is not int or maximum_rss <= 0:
        raise AuditStopError("main scorer runtime measurements are invalid")
    return {
        **expected,
        "source_hashes": {
            relative: str(expected_sources[relative]) for relative in production_relatives
        },
        "runtime": dict(runtime),
    }


def verify_audit_runtime() -> dict[str, str]:
    scipy = importlib.import_module("scipy")
    versions = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }
    expected = {"python": "3.14.5", "numpy": "2.5.1", "scipy": "1.18.0"}
    if versions != expected:
        raise AuditStopError(
            f"independent audit runtime differs from the qualified runtime: {versions}"
        )
    return versions


def runtime_receipt(started: float) -> dict[str, Any]:
    scipy = importlib.import_module("scipy")
    maximum_rss = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    rss_units = "bytes" if sys.platform == "darwin" else "KiB"
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "platform": platform.platform(),
        "elapsed_seconds": time.monotonic() - started,
        "maximum_resident_set_size": maximum_rss,
        "maximum_resident_set_size_units": rss_units,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.monotonic()
    qualified_runtime = verify_audit_runtime()
    modules = load_audit_modules(args.audit_source)
    lock_receipt = verify_training_lock(
        args.training_lock,
        args.training_root,
        args.public_package,
        args.audit_source,
        expected_sha256=args.expected_training_lock_sha256,
    )
    archive_receipt = validate_holdout_archive(
        args.holdout_archive, args.holdout_npz, args.expected_holdout_sha256
    )
    public_ready = verify_public_ready(args.public_package)
    _fixed, _setup, context, public_receipt = modules.public.reconstruct_public_inputs(
        args.public_package / "public_inputs"
    )
    canonical = tuple(str(value) for value in context.site_ids)
    training_mask = np.asarray(context.training, dtype=bool)
    training_npz = args.training_root / "training-inputs" / "training_observations.npz"
    training_manifest = verify_training_manifest(args.training_root, training_npz)
    training = load_observations(training_npz, expected_sites=TRAINING_SITE_COUNT, label="training")
    holdout = load_observations(
        args.holdout_npz, expected_sites=HOLDOUT_SITE_COUNT, label="holdout"
    )
    prey, predator, merge_receipt = merge_canonical_observations(
        training, holdout, canonical, training_mask
    )
    bank, bank_receipt = load_direct_bank(modules, args.public_package, canonical)
    fixed_points, fit_receipts = load_fixed_fits(args.training_root)
    main = read_json(args.main_results)
    main_provenance = verify_main_provenance(main, lock_receipt, archive_receipt["sha256"])
    independent_cases = score_fixed_points(modules, bank, context, prey, predator, fixed_points)
    comparison = compare_main_results(
        main,
        independent_cases,
        fit_receipts,
        tolerance=args.score_tolerance,
    )
    passed = comparison["passed"] is True
    result = {
        "schema": SCHEMA,
        "passed": passed,
        "scientific_scope": {
            "target": "conditional prey predictive log score at the 40 prospectively held sites",
            "comparison": (
                "four frozen training-fit parameter vectors within each of four neutral cases"
            ),
            "unit_reporting": (
                "site contributions, eight descriptive five-site cluster sums, case totals "
                "and means"
            ),
            "scope_limits": [
                "shared-map conditional predictive comparison",
                "sites and clusters are not treated as independent replicates",
                (
                    "no truth, recovery, power, coverage, calibration, causal or new-map "
                    "transfer inference"
                ),
            ],
        },
        "checks": {
            "holdout_archive_commitment": True,
            "public_inputs_reconstructed": bool(public_receipt.get("passed")),
            "canonical_observation_complement": True,
            "raw_bank_hash_and_shape": True,
            "sixteen_frozen_fit_bindings": True,
            "all_training_diagnostics_valid": True,
            "main_score_comparison": comparison["passed"],
            "qualified_runtime_exact": True,
        },
        "inputs": {
            "training_lock": lock_receipt,
            "audit_source": {
                "audit_capstone_public_sha256": sha256_file(
                    args.audit_source / "audit_capstone_public.py"
                ),
                "audit_preinvasion_feasibility_sha256": sha256_file(
                    args.audit_source / "audit_preinvasion_feasibility.py"
                ),
            },
            "holdout_archive": archive_receipt,
            "holdout_npz": {
                "sha256": sha256_file(args.holdout_npz),
                "prey_counts": array_binding(holdout.prey_counts),
                "predator_counts": array_binding(holdout.predator_counts),
            },
            "training": {
                "observations_sha256": sha256_file(training_npz),
                "manifest": training_manifest,
                "prey_counts": array_binding(training.prey_counts),
                "predator_counts": array_binding(training.predator_counts),
            },
            "public_ready": public_ready,
            "public_inputs": public_receipt,
            "arrival_bank": bank_receipt,
            "fit_receipts": fit_receipts,
            "main_results": {
                "sha256": sha256_file(args.main_results),
                "provenance": main_provenance,
            },
        },
        "canonical_merge": merge_receipt,
        "independent_cases": independent_cases,
        "main_comparison": comparison,
        "runtime": {**runtime_receipt(started), "qualified_versions": qualified_runtime},
    }
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-source", type=Path, required=True)
    parser.add_argument("--public-package", type=Path, required=True)
    parser.add_argument("--training-root", type=Path, required=True)
    parser.add_argument("--training-lock", type=Path, required=True)
    parser.add_argument("--holdout-archive", type=Path, required=True)
    parser.add_argument("--holdout-npz", type=Path, required=True)
    parser.add_argument("--main-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-holdout-sha256", default=EXPECTED_HOLDOUT_SHA256)
    parser.add_argument("--expected-training-lock-sha256", default=EXPECTED_TRAINING_LOCK_SHA256)
    parser.add_argument("--score-tolerance", type=float, default=SCORE_TOLERANCE)
    args = parser.parse_args(argv)
    if len(args.expected_holdout_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in args.expected_holdout_sha256
    ):
        parser.error("--expected-holdout-sha256 must be a lowercase SHA-256 digest")
    if len(args.expected_training_lock_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in args.expected_training_lock_sha256
    ):
        parser.error("--expected-training-lock-sha256 must be a lowercase SHA-256 digest")
    if not math.isfinite(args.score_tolerance) or args.score_tolerance < 0.0:
        parser.error("--score-tolerance must be finite and nonnegative")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = run(args)
        write_json(args.output, result)
    except Exception as error:
        print(f"audit_capstone_holdout: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"passed": result["passed"], "output": str(args.output)}, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
