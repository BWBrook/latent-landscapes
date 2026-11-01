"""Frozen case identities and training-only data for the development challenge."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, cast

import numpy as np

from latent_landscapes import (
    adjusted_background_likelihood,
    arc2b_campaign,
    capstone_public,
    final_procedure_evaluation,
    preinvasion_campaign,
)
from latent_landscapes.arc3_landscapes import ARCHETYPES, build_landscape
from latent_landscapes.final_procedure_evaluation import CELLS
from latent_landscapes.goal001 import design as goal001_design
from latent_landscapes.goal001 import landscape as goal001_landscape
from latent_landscapes.goal001 import spread as goal001_spread
from latent_landscapes.goal001.design import Cluster, DesignSite, EligibleCentre, SamplingDesign
from latent_landscapes.goal001.landscape import Landscape
from latent_landscapes.goal006 import spread as goal006_spread
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.misspecification_generator import (
    GeneratorSetup,
    _exposure_score,
    build_field_sampler,
)
from latent_landscapes.monitoring_design import build_master_monitoring_design

CELL_INDICES = (0, 1, 3, 4, 6, 7, 8, 9)
REPLICATES = (5, 6)
C_ROOT = 2026110107
C_NAMESPACE = 711
PREY_TIMES = preinvasion_campaign.PREY_TIMES
PREDATOR_TIMES = preinvasion_campaign.PREDATOR_TIMES
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SELECTOR_SOURCE_PATHS = (
    "artifacts/paper1_profile_development_20261018/check-master-selector.py",
    "src/latent_landscapes/monitoring_design.py",
    "src/latent_landscapes/arc3_landscapes.py",
    "src/latent_landscapes/goal001/design.py",
)
SELECTOR_SOLVER_FIELDS = (
    "status",
    "seed",
    "candidate_count",
    "selected_count",
    "eligible_input_sha256",
    "network_sha256",
    "selected_cluster_ids",
    "selected_centre_ids",
    "method_checks",
)


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return cast(dict[str, Any], value)


def _npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as source:
        return {name: source[name] for name in source.files}


def _save_npz(path: Path, values: Mapping[str, Any]) -> None:
    np.savez_compressed(path, **dict(values))


def _bindings(paths: Sequence[Path]) -> dict[str, str]:
    return {str(path.resolve()): sha256(path) for path in paths}


def _verify_bindings(bindings: Mapping[str, str]) -> None:
    for name, digest in bindings.items():
        if sha256(Path(name)) != digest:
            raise ValueError(f"input changed since freeze: {name}")


def _relative_bindings(paths: Sequence[Path], source_root: Path) -> dict[str, str]:
    root = source_root.resolve()
    result: dict[str, str] = {}
    for path in paths:
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError as error:
            raise ValueError(f"geometry source lies outside its source root: {path}") from error
        result[relative.as_posix()] = sha256(resolved)
    return result


def _safe_source_path(source_root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe repository-relative source path: {relative}")
    return source_root / path


def _required_geometry_source_names() -> set[str]:
    return {
        path.resolve().relative_to(REPOSITORY_ROOT).as_posix()
        for path in _generation_source_paths()
    } | set(SELECTOR_SOURCE_PATHS)


def _verify_runtime_sources(source_root: Path) -> None:
    for runtime_path in _generation_source_paths():
        relative = runtime_path.resolve().relative_to(REPOSITORY_ROOT).as_posix()
        if sha256(runtime_path) != sha256(_safe_source_path(source_root, relative)):
            raise ValueError(f"source root differs from executing source: {relative}")


def _verify_relative_bindings(bindings: Mapping[str, str], source_root: Path) -> None:
    if not _required_geometry_source_names() <= set(bindings):
        raise ValueError("portable geometry source binding is incomplete")
    for relative, digest in bindings.items():
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise ValueError("portable geometry source binding is malformed")
        path = _safe_source_path(source_root, relative)
        if sha256(path) != digest:
            raise ValueError(f"portable geometry source changed: {relative}")


def _geometry_binding_record(manifest: Path, plan: Mapping[str, Any]) -> dict[str, Any]:
    sources = plan.get("geometry_source_sha256")
    selector_relative = plan.get("selector_receipt_relative")
    selector_digest = plan.get("selector_receipt_sha256")
    if (
        not isinstance(sources, Mapping)
        or not isinstance(selector_relative, str)
        or not isinstance(selector_digest, str)
    ):
        raise ValueError("frozen manifest lacks portable geometry bindings")
    return {
        "schema": "development-challenge-geometry-binding-v1",
        "manifest_sha256": sha256(manifest),
        "selector_receipt_relative": selector_relative,
        "selector_receipt_sha256": selector_digest,
        "geometry_source_sha256": dict(sources),
    }


def _verify_geometry_manifest(
    manifest: Path, source_root: Path
) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    _verify_runtime_sources(source_root)
    plan = _read_json(manifest)
    binding = _geometry_binding_record(manifest, plan)
    sources = cast(dict[str, str], binding["geometry_source_sha256"])
    _verify_relative_bindings(sources, source_root)
    selector_path = _safe_source_path(source_root, binding["selector_receipt_relative"])
    if sha256(selector_path) != binding["selector_receipt_sha256"]:
        raise ValueError("portable selector receipt changed")
    selector = _read_json(selector_path)
    _verify_selector_sources(selector, source_root=source_root)
    return plan, selector_path, binding


def _generation_source_paths() -> tuple[Path, ...]:
    modules = (
        adjusted_background_likelihood,
        arc2b_campaign,
        capstone_public,
        final_procedure_evaluation,
        preinvasion_campaign,
        goal001_design,
        goal001_landscape,
        goal001_spread,
        goal006_spread,
    )
    module_paths = tuple(Path(cast(str, module.__file__)) for module in modules)
    local_paths = tuple(
        Path(__file__).with_name(name)
        for name in (
            "arc3_landscapes.py",
            "misspecification_generator.py",
            "monitoring_design.py",
        )
    )
    return (Path(__file__), *module_paths, *local_paths)


def _verify_selector_sources(
    selector: Mapping[str, Any], *, source_root: Path = REPOSITORY_ROOT
) -> None:
    recorded = selector.get("source_sha256")
    if not isinstance(recorded, Mapping):
        raise ValueError("pilot selector lacks its source hash binding")
    if not set(SELECTOR_SOURCE_PATHS) <= set(recorded):
        raise ValueError("pilot selector source hash binding is incomplete")
    for name, digest in recorded.items():
        relative = Path(str(name))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("pilot selector contains an unsafe source path")
        if not isinstance(digest, str) or sha256(source_root / relative) != digest:
            raise ValueError(f"pilot selector source changed: {relative}")


def _verify_selector_solver(
    replayed: Mapping[str, Any], frozen: Mapping[str, Any]
) -> None:
    for field in SELECTOR_SOLVER_FIELDS:
        if replayed.get(field) != frozen.get(field):
            raise ValueError(f"frozen selector replay differs: solver.{field}")


def _archived_truth(index: int) -> dict[str, Any]:
    cell = CELLS[index]
    return {
        "cell_index": cell.index,
        "label": cell.label,
        "background": cell.background,
        "effect": cell.h,
        "mean_hazard": cell.mu,
        "generating_beta": cell.beta,
        "detection_sd": cell.detection_sd,
    }


def _verify_archived_identity(
    directory: Path, index: int, replicate: int, observation_digest: str
) -> tuple[Path, Path]:
    inputs_path = directory / "inputs-complete.json"
    evaluator_path = directory / "evaluator.json"
    inputs = _read_json(inputs_path)
    files = inputs.get("files")
    if not isinstance(files, Mapping):
        raise ValueError("archived input receipt lacks file hashes")
    expected_files = {
        "observations.npz": observation_digest,
        "evaluator.json": sha256(evaluator_path),
    }
    for name, digest in expected_files.items():
        if files.get(name) != digest:
            raise ValueError(f"archived input receipt hash differs: {name}")
    evaluator = _read_json(evaluator_path)
    if (
        evaluator.get("history_index")
        != index * final_procedure_evaluation.REPLICATES + replicate
        or evaluator.get("cell_index") != index
        or evaluator.get("replicate") != replicate
        or evaluator.get("truth") != _archived_truth(index)
    ):
        raise ValueError("archived cell/replicate identity differs")
    return inputs_path, evaluator_path


def c_seed_record(map_index: int, effect_index: int) -> dict[str, Any]:
    if map_index not in range(len(ARCHETYPES)) or effect_index not in (0, 1):
        raise ValueError("invalid C case index")
    address = [C_ROOT, C_NAMESPACE, 1, map_index, effect_index]
    return {
        "root": C_ROOT,
        "namespace": C_NAMESPACE,
        "stage": 1,
        "address": address,
        "streams": {
            name: int(
                np.random.SeedSequence([*address, index]).generate_state(1, dtype=np.uint64)[0]
            )
            for index, name in enumerate(preinvasion_campaign.STREAM_NAMES)
        },
    }


def freeze_panel_manifest(
    archive_root: Path,
    public_dir: Path,
    banks: Mapping[str, Mapping[str, Path]],
    selector_receipt: Path,
    output: Path,
    *,
    source_root: Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    """Freeze identities without loading biological observations."""
    if output.exists():
        raise FileExistsError(output)
    if set(banks) != {"B0", "A"}:
        raise ValueError("the archived panel requires primary B0 and independent A")
    _verify_runtime_sources(source_root)
    portable_source_paths = [
        _safe_source_path(source_root, relative)
        for relative in sorted(_required_geometry_source_names())
    ]
    try:
        selector_relative = selector_receipt.resolve().relative_to(source_root.resolve()).as_posix()
    except ValueError as error:
        raise ValueError("selector receipt must be inside the explicit source root") from error
    sources = [
        public_dir / "public_inputs.npz",
        public_dir / "exposure.npz",
        selector_receipt,
        *portable_source_paths,
    ]
    selector = _read_json(selector_receipt)
    _verify_selector_sources(selector, source_root=source_root)
    bank_records: dict[str, dict[str, str]] = {}
    for role, spec in banks.items():
        if not {"raw", "compressed"} <= set(spec) or set(spec) - {"raw", "compressed", "manifest"}:
            raise ValueError("bank specs require raw/compressed and optional manifest")
        bank_records[role] = {key: str(path.resolve()) for key, path in spec.items()}
        sources.extend(spec.values())
    records = []
    reporting = {}
    for index in CELL_INDICES:
        cell = CELLS[index]
        for replicate in REPLICATES:
            history_id = f"cell-{index:02d}-rep-{replicate:03d}"
            observation = (
                archive_root / f"cell-{index:02d}" / f"rep-{replicate:03d}" / "observations.npz"
            )
            digest = sha256(observation)
            inputs_path, evaluator_path = _verify_archived_identity(
                observation.parent, index, replicate, digest
            )
            sources.extend((observation, inputs_path, evaluator_path))
            reporting[history_id] = asdict(cell)
            for arm in ("A", "B"):
                records.append(
                    {
                        "dataset_id": f"{history_id}-arm-{arm}",
                        "biological_history_id": history_id,
                        "arm": arm,
                        "stratum": "archived_reference_map",
                        "input_dir": str(public_dir.resolve()),
                        "source_observations": str(observation.resolve()),
                        "source_observations_sha256": digest,
                        "bank_roles": ["B0", "A"] if cell.mu == 0.004 else ["B0"],
                        "site_count": 120,
                    }
                )
    c_cases = []
    for index, archetype in enumerate(ARCHETYPES):
        selected = selector["cases"][index]
        solver = selected.get("solver")
        if (
            selected["archetype"] != archetype
            or selected["status"] != "selected_verified"
            or not isinstance(solver, Mapping)
            or not set(SELECTOR_SOLVER_FIELDS) <= set(solver)
        ):
            raise ValueError("pilot selector identity/status mismatch")
        for effect_index, effect in enumerate((1.0, 3.0)):
            c_cases.append(
                {
                    "dataset_id": f"C-map-{index:02d}-case-{effect_index:02d}",
                    "arm": "C",
                    "stratum": "new_master_panel",
                    "archetype": archetype,
                    "map_index": index,
                    "map_seed": selected["map_seed"],
                    "sampling_seeds": selected["seeds"],
                    "site_count": 260,
                    "seeds": c_seed_record(index, effect_index),
                    "reporting": {
                        "h": effect,
                        "mu": 0.004,
                        "beta": 0.5,
                        "detection_sd": 0.2,
                        "background": "exact",
                    },
                    "bank_seed_policy": {
                        "root": C_ROOT,
                        "namespace": C_NAMESPACE,
                        "stage": 2,
                        "address": [C_ROOT, C_NAMESPACE, 2, index, "row"],
                    },
                }
            )
    result = {
        "schema": "development-challenge-manifest-v1",
        "state": "identities_frozen_no_outcomes_loaded",
        "datasets": records,
        "reporting": reporting,
        "banks": bank_records,
        "optional_c_cases": c_cases,
        "selector_receipt": str(selector_receipt.resolve()),
        "selector_receipt_relative": selector_relative,
        "selector_receipt_sha256": sha256(selector_receipt),
        "geometry_source_sha256": _relative_bindings(portable_source_paths, source_root),
        "original_source_root": str(source_root.resolve()),
        "source_input_sha256": _bindings(sources),
        "independence": "16 biological histories; 32 paired-arm datasets, not 32 replicates",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_json(output, result)
    return result


def training_observation_arrays(
    source: Mapping[str, np.ndarray],
    public: Mapping[str, np.ndarray],
    *,
    arm: str,
    baseline_site_ids: Sequence[str] | None = None,
) -> dict[str, np.ndarray]:
    """Remove held-out counts and encode unavailable visits explicitly."""
    if arm not in {"A", "B", "C"}:
        raise ValueError("unknown monitoring arm")
    public_ids = tuple(map(str, public["site_ids"]))
    ids = tuple(map(str, source["site_ids"]))
    if (
        len(set(ids)) != len(ids)
        or len(set(public_ids)) != len(public_ids)
        or set(ids) != set(public_ids)
    ):
        raise ValueError("source sites must exactly match unique public sites")
    source_index = {value: index for index, value in enumerate(ids)}
    public_splits = np.asarray(public["site_splits"]).astype(str)
    if (
        public_splits.shape != (len(public_ids),)
        or not np.isin(public_splits, ("training", "holdout")).all()
    ):
        raise ValueError("invalid public site splits")
    training_ids = tuple(
        site_id
        for site_id, split in zip(public_ids, public_splits, strict=True)
        if split == "training"
    )
    selected = np.asarray([source_index[site_id] for site_id in training_ids], dtype=np.int64)
    if "training_mask" in source:
        mask = np.asarray(source["training_mask"])
        if mask.dtype != bool or mask.shape != (len(ids),):
            raise ValueError("training_mask must be a boolean site vector")
        expected = np.asarray([value in training_ids for value in ids])
        if not np.array_equal(mask, expected):
            raise ValueError("observation/public training split differs")
    prey_times = np.asarray(source.get("prey_times", PREY_TIMES), dtype=np.float64)
    predator_times = np.asarray(source.get("predator_times", PREDATOR_TIMES), dtype=np.float64)
    if not np.array_equal(prey_times, PREY_TIMES) or not np.array_equal(
        predator_times, PREDATOR_TIMES
    ):
        raise ValueError("the panel requires the frozen full calendars")
    if float(np.asarray(source.get("cohort_start", -60.0))) != -60.0:
        raise ValueError("the panel cohort must start at day -60")

    def counts(name: str, visits: int) -> np.ndarray:
        value = np.asarray(source[name])
        if value.ndim == 3 and value.shape[0] == 1:
            value = value[0]
        if value.shape != (len(ids), visits):
            raise ValueError(f"invalid {name} shape")
        return value[selected].copy()

    def availability(name: str, visits: int) -> np.ndarray:
        value = np.asarray(source.get(name, np.ones((len(ids), visits), dtype=bool)))
        if value.ndim == 3 and value.shape[0] == 1:
            value = value[0]
        if value.dtype != bool:
            raise ValueError(f"invalid {name}")
        if value.ndim == 0:
            value = np.full((len(ids), visits), bool(value), dtype=bool)
        elif value.shape == (len(ids),):
            value = np.broadcast_to(value[:, None], (len(ids), visits))
        if value.shape != (len(ids), visits):
            raise ValueError(f"invalid {name}")
        return value[selected].copy()

    prey = counts("prey_counts", len(PREY_TIMES))
    predator = counts("predator_counts", len(PREDATOR_TIMES))
    prey_observed = availability("prey_observed", len(PREY_TIMES))
    predator_observed = availability("predator_observed", len(PREDATOR_TIMES))
    if arm != "A":
        prey_observed[:, prey_times <= 0] = False
    if arm == "C":
        if baseline_site_ids is None or not set(baseline_site_ids) <= set(training_ids):
            raise ValueError("C requires its nested predator-network site IDs")
        network = np.asarray([site_id in baseline_site_ids for site_id in training_ids])
        predator_observed &= network[:, None]
    for value, observed in ((prey, prey_observed), (predator, predator_observed)):
        value[~observed] = 0
        if not np.isin(value, (0, 1, 2)).all():
            raise ValueError("observed replicate counts must be 0, 1 or 2")
    initial = np.asarray(source.get("initial_alive", True))
    if initial.dtype != bool:
        raise ValueError("initial_alive must be boolean")
    if initial.ndim == 0:
        initial = np.full(len(training_ids), bool(initial), dtype=bool)
    elif initial.shape == (len(ids),):
        initial = initial[selected]
    else:
        raise ValueError("invalid initial_alive shape")
    return {
        "site_ids": np.asarray(training_ids),
        "training_mask": np.ones(len(training_ids), dtype=bool),
        "prey_counts": prey.astype(np.int8),
        "predator_counts": predator.astype(np.int8),
        "prey_observed": prey_observed,
        "predator_observed": predator_observed,
        "prey_times": prey_times,
        "predator_times": predator_times,
        "cohort_start": np.asarray(-60.0),
        "initial_alive": initial,
    }


def materialize_archived_panel(manifest: Path, output: Path) -> dict[str, Any]:
    plan = _read_json(manifest)
    _verify_bindings(plan["source_input_sha256"])
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    public_source = Path(plan["datasets"][0]["input_dir"])
    public_output = output / "public" / "legacy"
    public_output.mkdir(parents=True)
    for name in ("public_inputs.npz", "exposure.npz"):
        shutil.copyfile(public_source / name, public_output / name)
    public = _npz(public_output / "public_inputs.npz")
    records = []
    for case in plan["datasets"]:
        source = _npz(Path(case["source_observations"]))
        arrays = training_observation_arrays(source, public, arm=case["arm"])
        if len(arrays["site_ids"]) != case["site_count"]:
            raise ValueError("unexpected archived training count")
        destination = output / "datasets" / case["dataset_id"] / "observations.npz"
        destination.parent.mkdir(parents=True)
        _save_npz(destination, arrays)
        records.append(
            {
                **case,
                "input_dir": str(public_output.resolve()),
                "observations": str(destination.resolve()),
                "observations_sha256": sha256(destination),
            }
        )
    result = {
        **plan,
        "state": "archived_training_inputs_prepared",
        "datasets": records,
        "frozen_manifest": str(manifest.resolve()),
        "frozen_manifest_sha256": sha256(manifest),
    }
    _write_json(output / "manifest.json", result)
    return result


def build_general_site_setup(fixed: FixedInputs) -> GeneratorSetup:
    sites = tuple(sorted(fixed.design.sites, key=lambda site: site.site_id))
    if not sites or len({site.site_id for site in sites}) != len(sites):
        raise ValueError("sites must be nonempty and unique")
    if len({(site.row, site.col) for site in sites}) != len(sites):
        raise ValueError("physical sites must be unique")
    accepted, exposure, count, score = _exposure_score(fixed)
    rows = np.asarray([site.row for site in sites], dtype=np.int64)
    cols = np.asarray([site.col for site in sites], dtype=np.int64)
    if (
        (rows < 0).any()
        or (cols < 0).any()
        or (rows >= fixed.landscape.shape[0]).any()
        or (cols >= fixed.landscape.shape[1]).any()
    ):
        raise ValueError("sampled sites are outside the map")
    if not fixed.landscape.source_reachable[rows, cols].all():
        raise ValueError("all sampled sites must be source-reachable")
    return GeneratorSetup(
        tuple(site.site_id for site in sites),
        rows,
        cols,
        tuple(site.split for site in sites),
        tuple(site.cluster_id for site in sites),
        accepted,
        exposure,
        count,
        score,
        build_field_sampler(fixed.landscape.shape),
    )


@dataclass(frozen=True)
class MasterInputs:
    fixed: FixedInputs
    setup: GeneratorSetup
    metadata: dict[str, Any]


def prepare_master_public(
    manifest: Path, map_index: int, output: Path, *, source_root: Path
) -> dict[str, Any]:
    """Regenerate the already-selected geometry; generate no biological history."""
    plan, selector_path, geometry_binding = _verify_geometry_manifest(manifest, source_root)
    case = next(row for row in plan["optional_c_cases"] if row["map_index"] == map_index)
    selector = _read_json(selector_path)["cases"][map_index]
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    try:
        landscape = build_landscape(case["archetype"], case["map_seed"])
        sampling, holdout, arm = case["sampling_seeds"]
        master = build_master_monitoring_design(
            landscape,
            sampling_seed=sampling,
            holdout_seed=holdout,
            arm_seed=arm,
            map_seed=case["map_seed"],
            solver_time_limit=30,
        )
        frozen_solver = selector.get("solver")
        if not isinstance(frozen_solver, Mapping):
            raise ValueError("pilot selector lacks its solver binding")
        _verify_selector_solver(master.solver_receipt.as_dict(), frozen_solver)
        for key in ("master_site_ids", "baseline_site_ids", "holdout_site_ids", "c_site_ids"):
            if list(getattr(master, key)) != selector[key]:
                raise ValueError(f"frozen selector replay differs: {key}")
        fixed = FixedInputs(landscape, master.sampling, {"master_design_verified": True})
        setup = build_general_site_setup(fixed)
        _save_npz(output / "public_inputs.npz", capstone_public._fixed_arrays(fixed))
        np.savez_compressed(
            output / "exposure.npz",
            map_a=setup.exposure_score,
            site_a=setup.exposure_score[setup.site_rows, setup.site_cols],
            accepted_mask=setup.accepted_mask,
        )
        design = {
            "clusters": [asdict(value) for value in master.sampling.clusters],
            "sites": [asdict(value) for value in master.sampling.sites],
            "eligible_centres": [asdict(value) for value in master.sampling.eligible_centres],
        }
        _write_json(output / "design.json", design)
        metadata = {
            "schema": "development-challenge-master-inputs-v1",
            "state": "geometry_prepared",
            "map_index": map_index,
            "archetype": case["archetype"],
            "map_seed": case["map_seed"],
            "sampling_seeds": case["sampling_seeds"],
            "baseline_site_ids": master.baseline_site_ids,
            "holdout_site_ids": master.holdout_site_ids,
            "c_site_ids": master.c_site_ids,
            "solver": master.solver_receipt.as_dict(),
            "unreachable_tie_count": setup.unreachable_tie_count,
            "unreachable_tie_exposure_score": setup.unreachable_tie_exposure_score,
            "files": {
                name: sha256(output / name)
                for name in ("public_inputs.npz", "exposure.npz", "design.json")
            },
            "geometry_binding": geometry_binding,
        }
        _write_json(output / "public_inputs.json", metadata)
        return metadata
    except Exception as error:
        _write_json(output / "failure.json", {"type": type(error).__name__, "message": str(error)})
        raise


def load_master_public(
    directory: Path, *, expected_manifest: Path, source_root: Path
) -> MasterInputs:
    plan, _selector_path, expected_binding = _verify_geometry_manifest(
        expected_manifest, source_root
    )
    metadata = _read_json(directory / "public_inputs.json")
    if metadata.get("state") != "geometry_prepared":
        raise ValueError("master public inputs are not prepared")
    if metadata.get("geometry_binding") != expected_binding:
        raise ValueError("master public inputs belong to a different frozen manifest")
    if metadata.get("map_index") not in {
        case["map_index"] for case in plan["optional_c_cases"]
    }:
        raise ValueError("master public inputs have an unknown frozen map index")
    for name, digest in metadata["files"].items():
        if sha256(directory / name) != digest:
            raise ValueError(f"master public input changed: {name}")
    public, exposure = _npz(directory / "public_inputs.npz"), _npz(directory / "exposure.npz")
    design = _read_json(directory / "design.json")
    landscape = Landscape(**{field.name: public[field.name] for field in fields(Landscape)})
    sampling = SamplingDesign(
        public["access_network"],
        tuple(EligibleCentre(**row) for row in design["eligible_centres"]),
        tuple(Cluster(**row) for row in design["clusters"]),
        tuple(DesignSite(**row) for row in design["sites"]),
    )
    fixed = FixedInputs(landscape, sampling, {"frozen_master_geometry_loaded": True})
    setup = GeneratorSetup(
        tuple(map(str, public["site_ids"])),
        public["site_rows"],
        public["site_cols"],
        tuple(map(str, public["site_splits"])),
        tuple(map(str, public["site_clusters"])),
        exposure["accepted_mask"],
        exposure["map_a"],
        metadata["unreachable_tie_count"],
        metadata["unreachable_tie_exposure_score"],
        build_field_sampler(landscape.shape),
    )
    return MasterInputs(fixed, setup, metadata)


def generate_arm_c_case(
    manifest: Path,
    dataset_id: str,
    public_dir: Path,
    output: Path,
    *,
    source_root: Path,
) -> dict[str, Any]:
    """Explicit post-review biological generation, separate from identity freezing."""
    plan, _selector_path, _binding = _verify_geometry_manifest(manifest, source_root)
    case = next(row for row in plan["optional_c_cases"] if row["dataset_id"] == dataset_id)
    public = load_master_public(
        public_dir, expected_manifest=manifest, source_root=source_root
    )
    if any(
        public.metadata[key] != case[key]
        for key in ("map_index", "archetype", "map_seed", "sampling_seeds")
    ):
        raise ValueError("C case/public map identity mismatch")
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    truth = case["reporting"]
    generator_truth = preinvasion_campaign.OpenTruth(
        index=case["map_index"] * 2 + int(truth["h"] == 3),
        effect=truth["h"],
        mean_hazard=truth["mu"],
        beta=truth["beta"],
        detection_sd=truth["detection_sd"],
    )
    observations, evaluator = preinvasion_campaign.generate_open_history(
        public.fixed, public.setup, generator_truth, case["seeds"]
    )
    full = {key: observations[key] for key in ("prey_counts", "predator_counts")}
    full.update(
        site_ids=np.asarray(public.setup.site_ids),
        training_mask=np.asarray([split == "training" for split in public.setup.site_splits]),
    )
    public_arrays = _npz(public_dir / "public_inputs.npz")
    analyst = training_observation_arrays(
        full, public_arrays, arm="C", baseline_site_ids=public.metadata["baseline_site_ids"]
    )
    if len(analyst["site_ids"]) != 260 or analyst["predator_observed"].any(axis=1).sum() != 120:
        raise ValueError("C training/predator-network counts do not match the design")
    _save_npz(output / "observations.npz", analyst)
    _save_npz(
        output / "evaluator.npz",
        {key: value for key, value in evaluator.items() if isinstance(value, np.ndarray)},
    )
    result = {
        **case,
        "state": "generated_development_only",
        "input_dir": str(public_dir.resolve()),
        "observations": str((output / "observations.npz").resolve()),
        "observations_sha256": sha256(output / "observations.npz"),
        "files": {
            name: sha256(output / name)
            for name in ("observations.npz", "evaluator.npz")
        },
        "file_roles": {
            "analyst": ["observations.npz"],
            "reporting_only": ["evaluator.npz", "receipt.json"],
        },
        "source_input_sha256": {
            "frozen_manifest": sha256(manifest),
            "master_public_metadata": sha256(public_dir / "public_inputs.json"),
        },
    }
    _write_json(output / "receipt.json", result)
    return result
