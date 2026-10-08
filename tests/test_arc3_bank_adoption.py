from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from latent_landscapes.arc2c_design import BridgeConfig
from latent_landscapes.arc3_campaign import run_campaign, write_campaign_bundle
from latent_landscapes.arc3_design import MASTER_SEED, PILOT_MAP_SEED, build_sampling_pair
from latent_landscapes.arc3_landscapes import ARCHETYPES, build_landscape, describe_landscape


def _adoption_module():
    path = Path(__file__).parents[1] / "scripts" / "arc3_bank_adoption.py"
    spec = importlib.util.spec_from_file_location("arc3_bank_adoption_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def adoption_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Any, Path, Path, Path]:
    module = _adoption_module()
    old_dir, new_dir = tmp_path / "old", tmp_path / "new"
    old_root, new_root = tmp_path / "old-source", tmp_path / "new-source"
    old_dir.mkdir()
    new_dir.mkdir()
    for root in (old_root, new_root):
        (root / "src").mkdir(parents=True)
        (root / "src" / "model.py").write_text("same\n", encoding="utf-8")
    snapshot = b'{"sha256":{"src/model.py":"same"}}\n'
    for root in (old_root, new_root):
        (root / "SOURCE_SNAPSHOT.json").write_bytes(snapshot)
    snapshot_sha = _sha(old_root / "SOURCE_SNAPSHOT.json")
    old_freeze = {
        "selected_bank_size": 2,
        "reference_bank_size": 4,
        "source_snapshot_sha256": snapshot_sha,
        "setting": "same",
    }
    new_freeze = {
        "selected_bank_size": 4,
        "reference_bank_size": 8,
        "source_snapshot_sha256": snapshot_sha,
        "setting": "same",
    }
    old_sha, new_sha = "a" * 64, "b" * 64
    scene_common = {
        "archetype": "connected",
        "map_seed": 11,
        "sampling_seed": 12,
        "purpose": "test",
    }
    config_common = dict(
        master_seed=1,
        calibration_replicates=2,
        validation_replicates=2,
        calibration_rank=2,
        rhos=(0.5, 1.0),
        effects=(1.0, 3.0),
    )
    truths = ("truth",)
    axes = {
        "rhos": np.array([0.5, 1.0]),
        "effects": np.array([1.0, 3.0]),
        "condition_ids": np.array(["condition"]),
        "design_ids": np.array(["design"]),
        "truth_effects": np.array([1.0]),
        "truth_rhos": np.array([1.0]),
    }
    for directory, root, freeze, freeze_sha, size in (
        (old_dir, old_root, old_freeze, old_sha, 4),
        (new_dir, new_root, new_freeze, new_sha, 8),
    ):
        scene = {
            **scene_common,
            "production_freeze": freeze,
            "production_freeze_sha256": freeze_sha,
        }
        source = {
            "head": "same",
            "requested_source_commit": "same",
            "dirty": False,
            "active_source_sha256": {
                str(root / "src" / "model.py"): _sha(root / "src" / "model.py")
            },
            "production_freeze": freeze,
            "production_freeze_sha256": freeze_sha,
        }
        summary = {
            "mode": "production",
            "is_production": True,
            "scene_metadata": scene,
            "source_provenance": source,
            "workflow": "workflow",
            "schema_version": 1,
            "designs": ["access"],
            "lanes": ["lane"],
            "truths": [],
            "invariants": {"ok": True},
            "source_commit": "same",
            "outcome": "outcome",
            "counts": {"bank_draws": size, "sites": 1},
        }
        (directory / "run_summary.json").write_text(json.dumps(summary), encoding="utf-8")
        seeds = {
            "master_seed": 1,
            "calibration_seeds": [1],
            "validation_seeds": [2],
            "site_ids": ["site"],
            "scene_metadata": scene,
            "source_commit": "same",
            "source_provenance": source,
            "bank_seeds": list(range(size)),
        }
        (directory / "seed_provenance.json").write_text(json.dumps(seeds), encoding="utf-8")
        np.save(directory / "base_arrivals.npy", np.arange(size, dtype=float).reshape(size, 1))
        np.savez(directory / "profiles.npz", **axes)
    old_bank = np.load(old_dir / "base_arrivals.npy")
    np.save(new_dir / "base_arrivals.npy", np.concatenate((old_bank, old_bank), axis=0))
    old_bundle = SimpleNamespace(
        config=SimpleNamespace(bank_size=4, **config_common),
        truths=truths,
        run_summary=json.loads((old_dir / "run_summary.json").read_text()),
        profiles=axes,
    )
    new_bundle = SimpleNamespace(
        config=SimpleNamespace(bank_size=8, **config_common),
        truths=truths,
        run_summary=json.loads((new_dir / "run_summary.json").read_text()),
        profiles=axes,
    )
    monkeypatch.setattr(
        module,
        "load_map_bundle",
        lambda path: old_bundle if path == old_dir.resolve() else new_bundle,
    )
    monkeypatch.setattr(
        module.arc3,
        "validate_production_freeze",
        lambda config, scene, freeze: (dict(freeze), old_sha if config.bank_size == 4 else new_sha),
    )
    receipt = {
        "schema_version": 1,
        "map_id": {"archetype": "connected", "map_seed": 11},
        "old_freeze_sha256": old_sha,
        "new_freeze_sha256": new_sha,
        "source_snapshot_sha256": snapshot_sha,
        "old_source_root": str(old_root),
        "new_source_root": str(new_root),
        "old_reference_dir": str(old_dir),
        "new_reference_dir": str(new_dir),
        "files": {"selected": {}, "reference": {}},
    }
    for role, directory in (("selected", old_dir), ("reference", new_dir)):
        receipt["files"][role] = {name: _sha(directory / name) for name in module.BUNDLE_FILES}
    receipt_path = tmp_path / "adoption-receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    return module, old_dir, new_dir, receipt_path


def test_valid_adoption_receipt(adoption_fixture: tuple[Any, Path, Path, Path]) -> None:
    module, old_dir, new_dir, receipt = adoption_fixture
    evidence = module.validate_adoption(old_dir, new_dir, receipt)
    assert evidence["old_freeze_sha256"] == "a" * 64
    assert evidence["new_freeze_sha256"] == "b" * 64


@pytest.mark.parametrize("change", ["role", "hash", "source", "scene"])
def test_adoption_rejects_tampering(
    adoption_fixture: tuple[Any, Path, Path, Path], change: str
) -> None:
    module, old_dir, new_dir, receipt_path = adoption_fixture
    payload = json.loads(receipt_path.read_text())
    if change == "role":
        module.load_map_bundle(old_dir).run_summary["scene_metadata"]["production_freeze"][
            "reference_bank_size"
        ] = 2
    elif change == "hash":
        payload["files"]["selected"]["base_arrivals.npy"] = "c" * 64
        receipt_path.write_text(json.dumps(payload))
    elif change == "source":
        payload["old_source_root"] = str(old_dir)
        receipt_path.write_text(json.dumps(payload))
    else:
        module.load_map_bundle(old_dir).run_summary["scene_metadata"]["purpose"] = "changed"
    with pytest.raises(ValueError):
        module.validate_adoption(old_dir, new_dir, receipt_path)


def _load_checker(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_both_reviewers_use_a_real_adopted_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _adoption_module()
    archetype = "connected"
    landscape = build_landscape(archetype, PILOT_MAP_SEED)
    sampling_seed = int(
        np.random.SeedSequence([MASTER_SEED, PILOT_MAP_SEED, 1]).generate_state(1)[0]
    )
    campaign_seed = int(
        np.random.SeedSequence(
            [MASTER_SEED, PILOT_MAP_SEED, ARCHETYPES.index(archetype), 2]
        ).generate_state(1)[0]
    )
    access, balanced = build_sampling_pair(landscape, sampling_seed)

    def config(bank: int) -> BridgeConfig:
        return BridgeConfig(
            master_seed=campaign_seed,
            bank_size=bank,
            calibration_replicates=2,
            validation_replicates=2,
            calibration_rank=2,
            rhos=(0.5, 1.0, 2.0),
            effects=(1.0, 3.0, 5.0),
        )

    common_scene = {
        "archetype": archetype,
        "map_seed": PILOT_MAP_SEED,
        "sampling_seed": sampling_seed,
        "purpose": "test adoption",
        "landscape_descriptors": describe_landscape(landscape),
    }
    old_dir, new_dir = tmp_path / "old", tmp_path / "new"
    for directory, bank in ((old_dir, 4), (new_dir, 8)):
        result = run_campaign(
            landscape,
            access,
            balanced,
            config(bank),
            source_commit="test",
            scene_metadata=common_scene,
        )
        write_campaign_bundle(result, directory)
    new_summary = json.loads((new_dir / "run_summary.json").read_text())

    source_roots = (tmp_path / "old-source", tmp_path / "new-source")
    old_summary = json.loads((old_dir / "run_summary.json").read_text())
    active = old_summary["source_provenance"]["active_source_sha256"]
    campaign_root = Path(run_campaign.__code__.co_filename).resolve().parents[2]
    for root in source_roots:
        for raw_path in active:
            relative = Path(raw_path).resolve().relative_to(campaign_root)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(Path(raw_path).read_bytes())
        root.mkdir(parents=True, exist_ok=True)
    snapshot = source_roots[0] / "SOURCE_SNAPSHOT.json"
    snapshot.write_text("{}\n", encoding="utf-8")
    (source_roots[1] / "SOURCE_SNAPSHOT.json").write_bytes(snapshot.read_bytes())
    snapshot_sha = _sha(snapshot)
    freezes = (
        {
            "selected_bank_size": 2,
            "reference_bank_size": 4,
            "source_snapshot_sha256": snapshot_sha,
            "setting": "same",
        },
        {
            "selected_bank_size": 4,
            "reference_bank_size": 8,
            "source_snapshot_sha256": snapshot_sha,
            "setting": "same",
        },
    )
    freeze_shas = ("a" * 64, "b" * 64)
    for directory, root, freeze, freeze_sha in zip(
        (old_dir, new_dir), source_roots, freezes, freeze_shas, strict=True
    ):
        summary = old_summary if directory == old_dir else new_summary
        scene = {
            **common_scene,
            "production_freeze": freeze,
            "production_freeze_sha256": freeze_sha,
        }
        source = dict(summary["source_provenance"])
        source["active_source_sha256"] = {
            str(root / Path(raw_path).resolve().relative_to(campaign_root)): digest
            for raw_path, digest in active.items()
        }
        source.update({"production_freeze": freeze, "production_freeze_sha256": freeze_sha})
        summary.update(
            mode="production",
            is_production=True,
            outcome="production_pending_numerical_review",
            scene_metadata=scene,
            source_provenance=source,
        )
        (directory / "run_summary.json").write_text(json.dumps(summary), encoding="utf-8")
        seeds = json.loads((directory / "seed_provenance.json").read_text())
        seeds.update(scene_metadata=scene, source_provenance=source)
        (directory / "seed_provenance.json").write_text(json.dumps(seeds), encoding="utf-8")

    ensemble = _load_checker(
        Path(__file__).parents[1] / "scripts" / "check_arc3_ensemble_numerics.py",
        "ensemble_adoption_integration_actual",
    )
    monkeypatch.setattr(
        ensemble.arc3,
        "validate_production_freeze",
        lambda config, scene, freeze: (
            dict(freeze),
            freeze_shas[0] if config.bank_size == 4 else freeze_shas[1],
        ),
    )
    receipt = tmp_path / "adoption-receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "map_id": {"archetype": archetype, "map_seed": PILOT_MAP_SEED},
                "old_freeze_sha256": freeze_shas[0],
                "new_freeze_sha256": freeze_shas[1],
                "source_snapshot_sha256": snapshot_sha,
                "old_source_root": str(source_roots[0]),
                "new_source_root": str(source_roots[1]),
                "old_reference_dir": str(old_dir),
                "new_reference_dir": str(new_dir),
                "files": {
                    "selected": {name: _sha(old_dir / name) for name in module.BUNDLE_FILES},
                    "reference": {name: _sha(new_dir / name) for name in module.BUNDLE_FILES},
                },
            }
        )
    )
    bundle_bytes = {
        directory: {name: (directory / name).read_bytes() for name in module.BUNDLE_FILES}
        for directory in (old_dir, new_dir)
    }
    report = ensemble.run_check(
        old_dir, new_dir, tmp_path / "ensemble.json", adoption_receipt=receipt
    )
    assert report["adoption"]["receipt_sha256"] == _sha(receipt)
    assert report["production_eligible"] is True
    numerics = _load_checker(
        Path(__file__).parents[1] / "scripts" / "check_arc3_numerics.py",
        "numerics_adoption_integration_actual",
    )
    monkeypatch.setattr(
        numerics.arc3,
        "validate_production_freeze",
        lambda config, scene, freeze: (
            dict(freeze),
            freeze_shas[0] if config.bank_size == 4 else freeze_shas[1],
        ),
    )
    halfgrid = numerics.run_check(
        old_dir,
        tmp_path / "halfgrid.json",
        workers=1,
        reference_dir=new_dir,
        adoption_receipt=receipt,
    )
    assert halfgrid["adoption"]["new_freeze_sha256"] == freeze_shas[1]
    assert halfgrid["reference_bundle"]["directory"] == str(new_dir)
    for directory, expected in bundle_bytes.items():
        assert {name: (directory / name).read_bytes() for name in module.BUNDLE_FILES} == expected
