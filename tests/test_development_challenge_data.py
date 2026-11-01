from __future__ import annotations

import json
import shutil
from dataclasses import fields, replace
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from latent_landscapes import development_challenge_data as data
from latent_landscapes import preinvasion_campaign
from latent_landscapes.arc3_landscapes import ARCHETYPES
from latent_landscapes.final_procedure_evaluation import CELLS
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.goal011.benchmark import build_fixed_inputs
from latent_landscapes.misspecification_generator import build_generator_setup


def example_arrays() -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    ids = np.asarray([f"site-{i:03d}" for i in range(160)])
    public = {"site_ids": ids, "site_splits": np.asarray(["training"] * 120 + ["holdout"] * 40)}
    source = {
        "site_ids": ids,
        "training_mask": np.arange(160) < 120,
        "prey_counts": np.broadcast_to(np.arange(13) % 3, (160, 13)).copy(),
        "predator_counts": np.broadcast_to(np.arange(6) % 3, (160, 6)).copy(),
        "initial_alive": np.arange(160) % 2 == 0,
    }
    source["prey_counts"][120:] = 99
    source["predator_counts"][120:] = 99
    return source, public


def test_training_only_masking_preserves_post_data_cohort_and_predators() -> None:
    source, public = example_arrays()
    a = data.training_observation_arrays(source, public, arm="A")
    b = data.training_observation_arrays(source, public, arm="B")
    assert len(a["site_ids"]) == 120
    assert not np.isin(a["site_ids"], source["site_ids"][120:]).any()
    assert np.array_equal(a["prey_counts"], source["prey_counts"][:120])
    assert a["prey_observed"].all()
    assert not b["prey_observed"][:, :7].any()
    assert b["prey_observed"][:, 7:].all()
    assert not b["prey_counts"][:, :7].any()
    assert np.array_equal(a["prey_counts"][:, 7:], b["prey_counts"][:, 7:])
    assert np.array_equal(a["predator_counts"], b["predator_counts"])
    assert np.array_equal(a["initial_alive"], b["initial_alive"])
    assert float(b["cohort_start"]) == -60
    assert np.array_equal(b["prey_times"], data.PREY_TIMES)
    assert not any("truth" in key or key in {"h", "mu", "beta", "index"} for key in b)


def test_site_order_is_public_order_and_split_mismatch_is_rejected() -> None:
    source, public = example_arrays()
    source = {key: value[::-1].copy() for key, value in source.items()}
    result = data.training_observation_arrays(source, public, arm="A")
    assert np.array_equal(result["site_ids"], public["site_ids"][:120])
    source["training_mask"][0] = True
    with pytest.raises(ValueError, match="split differs"):
        data.training_observation_arrays(source, public, arm="A")


def test_masked_prey_and_predator_counts_are_uninformative() -> None:
    source, public = example_arrays()
    source["predator_observed"] = np.ones((160, 6), dtype=bool)
    source["predator_observed"][2, 3] = False
    first = data.training_observation_arrays(source, public, arm="B")
    source["prey_counts"][:, :7] = 99
    source["predator_counts"][2, 3] = 99
    second = data.training_observation_arrays(source, public, arm="B")
    for key in first:
        assert np.array_equal(first[key], second[key])
    source["prey_counts"][1, 7] = 3
    with pytest.raises(ValueError, match="counts"):
        data.training_observation_arrays(source, public, arm="B")


def test_arm_c_has_260_training_sites_and_only_120_predator_sites() -> None:
    ids = np.asarray([f"s{i:03d}" for i in range(300)])
    source = {
        "site_ids": ids,
        "prey_counts": np.ones((300, 13), dtype=np.int8),
        "predator_counts": np.ones((300, 6), dtype=np.int8),
    }
    public = {"site_ids": ids, "site_splits": np.asarray(["training"] * 260 + ["holdout"] * 40)}
    result = data.training_observation_arrays(
        source, public, arm="C", baseline_site_ids=tuple(map(str, ids[:120]))
    )
    assert result["prey_counts"].shape == (260, 13)
    assert result["prey_observed"].sum() == 260 * 6
    assert result["predator_observed"].sum() == 120 * 6
    assert not result["predator_counts"][120:].any()
    assert not result["predator_observed"][120:].any()
    with pytest.raises(ValueError, match="nested"):
        data.training_observation_arrays(
            source, public, arm="C", baseline_site_ids=tuple(map(str, ids[-40:]))
        )


@pytest.fixture
def frozen_panel(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    observation_source, public = example_arrays()
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    np.savez_compressed(public_dir / "public_inputs.npz", **cast(dict[str, Any], public))
    np.savez_compressed(public_dir / "exposure.npz", site_a=np.arange(160), map_a=np.arange(600))
    archive = tmp_path / "archive"
    for cell in data.CELL_INDICES:
        for rep in data.REPLICATES:
            path = archive / f"cell-{cell:02d}" / f"rep-{rep:03d}" / "observations.npz"
            path.parent.mkdir(parents=True)
            np.savez_compressed(path, **cast(dict[str, Any], observation_source))
            evaluator = {
                "history_index": cell * 500 + rep,
                "cell_index": cell,
                "cell_label": CELLS[cell].label,
                "replicate": rep,
                "truth": data._archived_truth(cell),
                "seeds": {"root": 1},
            }
            evaluator_path = path.parent / "evaluator.json"
            evaluator_path.write_text(json.dumps(evaluator))
            (path.parent / "inputs-complete.json").write_text(
                json.dumps(
                    {
                        "binding_sha256": "fixture",
                        "files": {
                            "observations.npz": data.sha256(path),
                            "evaluator.json": data.sha256(evaluator_path),
                        },
                    }
                )
            )
    source_root = tmp_path / "source-root"
    for relative in data._required_geometry_source_names():
        source_path = data.REPOSITORY_ROOT / relative
        destination = source_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, destination)
    selector = source_root / "selector.json"
    selector.write_text(
        json.dumps(
            {
                "source_sha256": {
                    relative: data.sha256(source_root / relative)
                    for relative in data.SELECTOR_SOURCE_PATHS
                },
                "cases": [
                    {
                        "archetype": name,
                        "status": "selected_verified",
                        "map_seed": 2026101801 + index,
                        "seeds": [2026101811 + index, 2026101911 + index, 2026102011 + index],
                        "solver": {
                            "status": "selected_verified",
                            "seed": 2026101811 + index,
                            "candidate_count": 2000,
                            "selected_count": 60,
                            "eligible_input_sha256": "a" * 64,
                            "network_sha256": "b" * 64,
                            "selected_cluster_ids": ["cluster"],
                            "selected_centre_ids": ["centre"],
                            "method_checks": {"joint_milp": True},
                        },
                    }
                    for index, name in enumerate(ARCHETYPES)
                ]
            }
        )
    )
    banks = {}
    for role in ("B0", "A"):
        paths = {key: tmp_path / f"{role}-{key}" for key in ("raw", "compressed")}
        for path in paths.values():
            path.write_bytes(role.encode())
        banks[role] = paths
    manifest = tmp_path / "frozen.json"
    plan = data.freeze_panel_manifest(
        archive, public_dir, banks, selector, manifest, source_root=source_root
    )
    return manifest, plan


def test_manifest_selection_seeds_and_materialization(
    frozen_panel: tuple[Path, dict[str, object]],
) -> None:
    path, _ = frozen_panel
    plan = json.loads(path.read_text())
    assert len(plan["datasets"]) == 32
    assert len({case["biological_history_id"] for case in plan["datasets"]}) == 16
    assert {case["arm"] for case in plan["datasets"]} == {"A", "B"}
    assert sum(case["bank_roles"] == ["B0", "A"] for case in plan["datasets"]) == 16
    assert len(plan["optional_c_cases"]) == 6
    assert all("reporting" not in case and "h" not in case for case in plan["datasets"])
    seeds = [
        seed for case in plan["optional_c_cases"] for seed in case["seeds"]["streams"].values()
    ]
    assert len(seeds) == len(set(seeds)) == 30
    bound_paths = set(plan["source_input_sha256"])
    source_root = Path(plan["original_source_root"])
    assert {
        str((source_root / relative).resolve())
        for relative in data._required_geometry_source_names()
    } <= bound_paths
    assert set(plan["geometry_source_sha256"]) == data._required_geometry_source_names()
    bound_names = {Path(name).name for name in bound_paths}
    assert {"inputs-complete.json", "evaluator.json"} <= bound_names
    result = data.materialize_archived_panel(path, path.parent / "prepared")
    assert len(result["datasets"]) == 32
    for case in result["datasets"]:
        with np.load(case["observations"], allow_pickle=False) as observations:
            assert observations["prey_counts"].shape == (120, 13)
            assert observations["predator_counts"].shape == (120, 6)
            assert observations["training_mask"].all()
            assert "truth" not in observations.files
        assert data.sha256(Path(case["observations"])) == case["observations_sha256"]
    source_exposure = Path(plan["datasets"][0]["input_dir"]) / "exposure.npz"
    copied_exposure = Path(result["datasets"][0]["input_dir"]) / "exposure.npz"
    assert source_exposure.read_bytes() == copied_exposure.read_bytes()


def test_frozen_input_change_stops_before_materialization(
    frozen_panel: tuple[Path, dict[str, object]],
) -> None:
    path, _ = frozen_panel
    plan = json.loads(path.read_text())
    Path(plan["datasets"][0]["source_observations"]).write_bytes(b"changed")
    output = path.parent / "must-not-exist"
    with pytest.raises(ValueError, match="input changed"):
        data.materialize_archived_panel(path, output)
    assert not output.exists()


def _refreeze(path: Path, output: Path) -> dict[str, Any]:
    plan = json.loads(path.read_text())
    return data.freeze_panel_manifest(
        Path(plan["datasets"][0]["source_observations"]).parents[2],
        Path(plan["datasets"][0]["input_dir"]),
        {
            role: {key: Path(value) for key, value in spec.items()}
            for role, spec in plan["banks"].items()
        },
        Path(plan["selector_receipt"]),
        output,
        source_root=Path(plan["original_source_root"]),
    )


def _copy_portable_geometry_sources(plan: dict[str, Any], destination: Path) -> None:
    original = Path(plan["original_source_root"])
    relative_paths = set(plan["geometry_source_sha256"]) | {
        plan["selector_receipt_relative"]
    }
    for relative in relative_paths:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original / relative, target)


def test_identity_freeze_rejects_archived_metadata_tampering(
    frozen_panel: tuple[Path, dict[str, object]],
) -> None:
    path, _ = frozen_panel
    plan = json.loads(path.read_text())
    evaluator = Path(plan["datasets"][0]["source_observations"]).with_name("evaluator.json")
    metadata = json.loads(evaluator.read_text())
    metadata["replicate"] = 7
    evaluator.write_text(json.dumps(metadata))
    receipt = evaluator.with_name("inputs-complete.json")
    inputs = json.loads(receipt.read_text())
    inputs["files"]["evaluator.json"] = data.sha256(evaluator)
    receipt.write_text(json.dumps(inputs))
    with pytest.raises(ValueError, match="archived cell/replicate identity differs"):
        _refreeze(path, path.parent / "bad-metadata.json")


def test_identity_freeze_rejects_recorded_observation_hash_tampering(
    frozen_panel: tuple[Path, dict[str, object]],
) -> None:
    path, _ = frozen_panel
    plan = json.loads(path.read_text())
    receipt = Path(plan["datasets"][0]["source_observations"]).with_name(
        "inputs-complete.json"
    )
    inputs = json.loads(receipt.read_text())
    inputs["files"]["observations.npz"] = "0" * 64
    receipt.write_text(json.dumps(inputs))
    with pytest.raises(ValueError, match=r"receipt hash differs: observations\.npz"):
        _refreeze(path, path.parent / "bad-receipt.json")


def test_identity_freeze_rejects_selector_source_tampering(
    frozen_panel: tuple[Path, dict[str, object]],
) -> None:
    path, _ = frozen_panel
    plan = json.loads(path.read_text())
    selector_path = Path(plan["selector_receipt"])
    selector = json.loads(selector_path.read_text())
    relative = data.SELECTOR_SOURCE_PATHS[0]
    selector["source_sha256"][relative] = "0" * 64
    selector_path.write_text(json.dumps(selector))
    with pytest.raises(ValueError, match="selector source changed"):
        _refreeze(path, path.parent / "bad-selector.json")


def test_selector_replay_rejects_solver_input_hash_tampering() -> None:
    frozen = {
        "status": "selected_verified",
        "seed": 1,
        "candidate_count": 20,
        "selected_count": 60,
        "eligible_input_sha256": "a" * 64,
        "network_sha256": "b" * 64,
        "selected_cluster_ids": ["cluster"],
        "selected_centre_ids": ["centre"],
        "method_checks": {"joint_milp": True},
    }
    data._verify_selector_solver(frozen, frozen)
    changed = {**frozen, "eligible_input_sha256": "c" * 64}
    with pytest.raises(ValueError, match=r"solver\.eligible_input_sha256"):
        data._verify_selector_solver(changed, frozen)


def test_general_setup_matches_frozen_160_law_and_arbitrary_subset() -> None:
    fixed = build_fixed_inputs()
    legacy = build_generator_setup(fixed)
    general = data.build_general_site_setup(fixed)
    for field in fields(legacy):
        first, second = getattr(legacy, field.name), getattr(general, field.name)
        if isinstance(first, np.ndarray):
            assert np.array_equal(first, second)
        elif field.name != "field_sampler":
            assert first == second
    truth = preinvasion_campaign.OpenTruth(99, 2.2, 0.002, 0.3, 0.1)
    seeds = {
        "streams": {
            name: 90901 + index for index, name in enumerate(preinvasion_campaign.STREAM_NAMES)
        }
    }
    old_obs, old_truth = preinvasion_campaign.generate_open_history(fixed, legacy, truth, seeds)
    new_obs, new_truth = preinvasion_campaign.generate_open_history(fixed, general, truth, seeds)
    for key in ("prey_counts", "predator_counts"):
        assert np.array_equal(old_obs[key], new_obs[key])
    assert np.array_equal(old_truth["site_hazard"], new_truth["site_hazard"])
    smaller = FixedInputs(fixed.landscape, replace(fixed.design, sites=fixed.design.sites[:17]), {})
    setup = data.build_general_site_setup(smaller)
    assert len(setup.site_ids) == 17
    assert np.array_equal(setup.exposure_score, legacy.exposure_score)
    assert setup.accepted_mask.all()
    with pytest.raises(ValueError, match="unique"):
        duplicate = replace(smaller, design=replace(smaller.design, sites=smaller.design.sites * 2))
        data.build_general_site_setup(duplicate)


def test_identity_freeze_does_not_load_observation_arrays(
    frozen_panel: tuple[Path, dict[str, object]], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = frozen_panel
    plan = json.loads(path.read_text())

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("identity freezing must not load NPZ values")

    monkeypatch.setattr(np, "load", forbidden)
    data.freeze_panel_manifest(
        Path(plan["datasets"][0]["source_observations"]).parents[2],
        Path(plan["datasets"][0]["input_dir"]),
        {
            role: {key: Path(value) for key, value in spec.items()}
            for role, spec in plan["banks"].items()
        },
        Path(plan["selector_receipt"]),
        path.parent / "another-freeze.json",
        source_root=Path(plan["original_source_root"]),
    )


def test_master_public_roundtrip_preserves_frozen_exposure_and_geometry(
    tmp_path: Path, frozen_panel: tuple[Path, dict[str, object]]
) -> None:
    from dataclasses import asdict

    from latent_landscapes import capstone_public

    fixed = build_fixed_inputs()
    setup = data.build_general_site_setup(fixed)
    arrays = capstone_public._fixed_arrays(fixed)
    np.savez_compressed(tmp_path / "public_inputs.npz", **cast(dict[str, Any], arrays))
    np.savez_compressed(
        tmp_path / "exposure.npz",
        map_a=setup.exposure_score,
        site_a=setup.exposure_score[setup.site_rows, setup.site_cols],
        accepted_mask=setup.accepted_mask,
    )
    design = {
        key: [asdict(row) for row in getattr(fixed.design, key)]
        for key in ("sites", "clusters", "eligible_centres")
    }
    (tmp_path / "design.json").write_text(json.dumps(design))
    manifest, _ = frozen_panel
    plan = json.loads(manifest.read_text())
    source_root = Path(plan["original_source_root"])
    metadata = {
        "state": "geometry_prepared",
        "unreachable_tie_count": setup.unreachable_tie_count,
        "unreachable_tie_exposure_score": setup.unreachable_tie_exposure_score,
        "files": {
            name: data.sha256(tmp_path / name)
            for name in ("public_inputs.npz", "exposure.npz", "design.json")
        },
        "geometry_binding": data._geometry_binding_record(manifest, plan),
        "map_index": 0,
    }
    (tmp_path / "public_inputs.json").write_text(json.dumps(metadata))
    loaded = data.load_master_public(
        tmp_path, expected_manifest=manifest, source_root=source_root
    )
    assert loaded.fixed.design.sites == fixed.design.sites
    assert loaded.fixed.design.clusters == fixed.design.clusters
    assert loaded.setup.site_ids == setup.site_ids
    assert np.array_equal(loaded.setup.exposure_score, setup.exposure_score)
    assert np.array_equal(loaded.fixed.landscape.passable, fixed.landscape.passable)
    rebased_root = tmp_path / "rebased-source"
    _copy_portable_geometry_sources(plan, rebased_root)
    rebased = data.load_master_public(
        tmp_path, expected_manifest=manifest, source_root=rebased_root
    )
    assert rebased.setup.site_ids == setup.site_ids

    tampered_manifest = tmp_path / "tampered-manifest.json"
    changed_plan = {**plan, "state": "tampered"}
    tampered_manifest.write_text(json.dumps(changed_plan))
    with pytest.raises(ValueError, match="different frozen manifest"):
        data.load_master_public(
            tmp_path, expected_manifest=tampered_manifest, source_root=rebased_root
        )

    missing_binding_manifest = tmp_path / "missing-binding-manifest.json"
    missing_plan = dict(plan)
    missing_sources = dict(plan["geometry_source_sha256"])
    missing_sources.pop(sorted(missing_sources)[0])
    missing_plan["geometry_source_sha256"] = missing_sources
    missing_binding_manifest.write_text(json.dumps(missing_plan))
    with pytest.raises(ValueError, match="portable geometry source binding is incomplete"):
        data.load_master_public(
            tmp_path, expected_manifest=missing_binding_manifest, source_root=rebased_root
        )

    metadata_path = tmp_path / "public_inputs.json"
    missing_metadata = dict(metadata)
    missing_metadata.pop("geometry_binding")
    metadata_path.write_text(json.dumps(missing_metadata))
    with pytest.raises(ValueError, match="different frozen manifest"):
        data.load_master_public(
            tmp_path, expected_manifest=manifest, source_root=rebased_root
        )
    metadata_path.write_text(json.dumps(metadata))

    selector_source = rebased_root / data.SELECTOR_SOURCE_PATHS[0]
    selector_source.write_bytes(selector_source.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="portable geometry source changed"):
        data.load_master_public(
            tmp_path, expected_manifest=manifest, source_root=rebased_root
        )
    (tmp_path / "exposure.npz").write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        data.load_master_public(
            tmp_path, expected_manifest=manifest, source_root=source_root
        )


def test_arm_c_generation_packages_only_training_observations(
    frozen_panel: tuple[Path, dict[str, object]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    path, _ = frozen_panel
    public_dir = path.parent / "master-public"
    public_dir.mkdir()
    ids = tuple(f"site-{i:03d}" for i in range(300))
    splits = tuple(["training"] * 260 + ["holdout"] * 40)
    np.savez_compressed(
        public_dir / "public_inputs.npz", site_ids=np.asarray(ids), site_splits=np.asarray(splits)
    )
    (public_dir / "public_inputs.json").write_text("{}")
    public = SimpleNamespace(
        fixed=object(),
        setup=SimpleNamespace(site_ids=ids, site_splits=splits),
        metadata={
            "map_index": 0,
            "archetype": "connected",
            "map_seed": 2026101801,
            "sampling_seeds": [2026101811, 2026101911, 2026102011],
            "baseline_site_ids": ids[:120],
        },
    )
    source_root = Path(json.loads(path.read_text())["original_source_root"])

    def fake_load(
        directory: Path, *, expected_manifest: Path, source_root: Path
    ) -> Any:
        assert directory == public_dir
        assert expected_manifest == path
        assert source_root == Path(json.loads(path.read_text())["original_source_root"])
        return public

    monkeypatch.setattr(data, "load_master_public", fake_load)

    def fake_generate(*args: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        assert len(args[1].site_ids) == 300
        assert args[2].mean_hazard == 0.004
        assert args[3] == data.c_seed_record(0, 0)
        return (
            {
                "prey_counts": np.ones((300, 13), dtype=np.int8),
                "predator_counts": np.ones((300, 6), dtype=np.int8),
            },
            {"arrival": np.arange(300), "truth": {"h": 1}},
        )

    monkeypatch.setattr(preinvasion_campaign, "generate_open_history", fake_generate)
    result = data.generate_arm_c_case(
        path,
        "C-map-00-case-00",
        public_dir,
        path.parent / "C-case",
        source_root=source_root,
    )
    with np.load(result["observations"], allow_pickle=False) as observed:
        assert len(observed["site_ids"]) == 260
        assert observed["predator_observed"].any(axis=1).sum() == 120
        assert observed["prey_observed"].sum() == 1560
        assert "truth" not in observed.files and "arrival" not in observed.files
    assert not (path.parent / "C-case" / "generated_observations.npz").exists()
    assert (path.parent / "C-case" / "evaluator.npz").exists()
    assert set(result["files"]) == {"observations.npz", "evaluator.npz"}
    assert result["file_roles"] == {
        "analyst": ["observations.npz"],
        "reporting_only": ["evaluator.npz", "receipt.json"],
    }
