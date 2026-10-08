from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "score_capstone_holdout", Path(__file__).parents[1] / "scripts" / "score_capstone_holdout.py"
)
assert _SPEC is not None and _SPEC.loader is not None
score = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = score
_SPEC.loader.exec_module(score)


def _archive_bytes(*, bad_counts: bool = False, reverse_sites: bool = False) -> bytes:
    stream = io.BytesIO()
    np.savez_compressed(
        stream,
        case_ids=np.asarray(score.CASE_IDS),
        site_ids=np.asarray(
            [f"site-{index:03d}" for index in range(120, 160)][::-1]
            if reverse_sites
            else [f"site-{index:03d}" for index in range(120, 160)]
        ),
        prey_counts=np.zeros((4, 40, 13), dtype=np.int8) + (3 if bad_counts else 0),
        predator_counts=np.zeros((4, 40, 6), dtype=np.int8),
    )
    entries = {"holdout.npz": stream.getvalue(), "padding.bin": b"", "salt.bin": b"s" * 32}
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        for name, payload in sorted(entries.items()):
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return output.getvalue()


def test_load_holdout_archive_validates_schema_and_counts(tmp_path: Path) -> None:
    payload = _archive_bytes()
    archive = tmp_path / "holdout.tar"
    archive.write_bytes(payload)
    loaded = score.load_holdout_archive(
        archive, expected_sha256=hashlib.sha256(payload).hexdigest()
    )
    assert loaded.case_ids == score.CASE_IDS
    assert loaded.site_ids == tuple(f"site-{index:03d}" for index in range(120, 160))
    assert loaded.prey_counts.shape == (4, 40, 13)

    malformed = tmp_path / "bad.tar"
    bad = _archive_bytes(bad_counts=True)
    malformed.write_bytes(bad)
    with pytest.raises(ValueError, match="counts"):
        score.load_holdout_archive(malformed, expected_sha256=hashlib.sha256(bad).hexdigest())


def test_merge_observations_places_arrays_by_canonical_site_mask() -> None:
    public_ids = tuple(f"site-{index:03d}" for index in range(160))
    splits = tuple("holdout" if index % 4 == 0 else "training" for index in range(160))
    training_ids = tuple(
        site for site, split in zip(public_ids, splits, strict=True) if split == "training"
    )
    holdout_ids = tuple(
        site for site, split in zip(public_ids, splits, strict=True) if split == "holdout"
    )
    public = SimpleNamespace(setup=SimpleNamespace(site_ids=public_ids, site_splits=splits))
    train = SimpleNamespace(
        case_ids=score.CASE_IDS,
        observations=SimpleNamespace(
            site_ids=training_ids,
            prey_counts=np.ones((4, 120, 13), dtype=np.int64),
            predator_counts=np.ones((4, 120, 6), dtype=np.int64),
        ),
    )
    holdout = score.HoldoutArrays(
        score.CASE_IDS,
        holdout_ids,
        np.full((4, 40, 13), 2, dtype=np.int64),
        np.full((4, 40, 6), 2, dtype=np.int64),
    )
    observations = score.merge_observations(public, train, holdout)
    assert observations.site_ids == public_ids
    np.testing.assert_array_equal(observations.prey_counts[:, np.asarray(splits) == "training"], 1)
    np.testing.assert_array_equal(observations.prey_counts[:, np.asarray(splits) == "holdout"], 2)
    np.testing.assert_array_equal(
        observations.predator_emissions,
        score.likelihood._predator_emissions(observations.predator_counts),
    )
    assert observations.training_mask.sum() == 120
    assert (~observations.training_mask).sum() == 40
    reversed_holdout = score.HoldoutArrays(
        score.CASE_IDS,
        holdout_ids[::-1],
        holdout.prey_counts,
        holdout.predator_counts,
    )
    with pytest.raises(ValueError, match="holdout site IDs"):
        score.merge_observations(public, train, reversed_holdout)


def test_load_frozen_panel_preserves_invalid_fit_and_audit(tmp_path: Path) -> None:
    fits = {
        model: {
            "model": model,
            "h": 1.0,
            "beta": 0.0,
            "mu": 0.002,
            "detection_sd": 0.1,
            "raw_logjoint": -1.0,
            "numerical_status": "converged" if model != "constant_h1" else "invalid",
        }
        for model in score.MODEL_NAMES
    }
    fit_dir = tmp_path / "analysis" / "fit" / "fits"
    audit_dir = tmp_path / "analysis" / "audits" / "training"
    fit_dir.mkdir(parents=True)
    audit_dir.mkdir(parents=True)
    main = {"history": 0, "representation": "full", "fits": fits}
    full = {**main, "main_statuses_converged": {model: model != "constant_h1" for model in fits}}
    (fit_dir / "history-00-full-main.json").write_text(json.dumps(main), encoding="utf-8")
    full_path = fit_dir / "history-00-full.json"
    full_path.write_text(json.dumps(full), encoding="utf-8")
    audit = {
        "history": 0,
        "case_id": "case-00",
        "kind": "training_case",
        "input_files": {
            "analysis/fit/fits/history-00-full.json": hashlib.sha256(
                full_path.read_bytes()
            ).hexdigest()
        },
        "passed": True,
        "diagnostic_passed": True,
    }
    (audit_dir / "history-00.json").write_text(json.dumps(audit), encoding="utf-8")
    panel = score.load_frozen_panel(tmp_path, 0)
    assert panel["fits"]["constant_h1"].numerical_status == "invalid"
    assert panel["audit"]["diagnostic_passed"] is True


def test_score_aggregation_records_ties_and_unavailable_forecast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    public_ids = tuple(f"site-{index:03d}" for index in range(160))
    holdout_ids = public_ids[-40:]
    public = SimpleNamespace(
        setup=SimpleNamespace(
            site_ids=public_ids,
            site_cluster_ids=tuple(f"cluster-{index // 5:02d}" for index in range(160)),
        )
    )
    context = SimpleNamespace(public=public, bank=object())
    holdout = score.HoldoutArrays(
        score.CASE_IDS,
        holdout_ids,
        np.zeros((4, 40, 13), dtype=np.int64),
        np.zeros((4, 40, 6), dtype=np.int64),
    )
    monkeypatch.setattr(score.references, "load_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(score, "load_holdout_archive", lambda *_args, **_kwargs: holdout)
    monkeypatch.setattr(
        score,
        "_training_inputs",
        lambda _root: (tmp_path / "train.npz", tmp_path / "train.json", "digest"),
    )
    monkeypatch.setattr(score.training, "load_training", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(score, "merge_observations", lambda *_args: object())
    monkeypatch.setattr(score, "_source_hashes", lambda _root: {"source-manifest.json": "digest"})
    monkeypatch.setattr(score, "_verify_computation_manifest", lambda *_args: "digest")
    monkeypatch.setattr(score, "sha256", lambda _path: "digest")
    training_root = tmp_path / "training"
    (training_root / "analysis" / "fit").mkdir(parents=True)
    (training_root / "analysis" / "fit" / "fit.json").write_text(
        json.dumps({"training_npz_sha256": "digest"}), encoding="utf-8"
    )
    (training_root / "source-manifest.json").write_text(
        json.dumps(
            {
                "source_hashes": {},
                "frozen_input_hashes": {
                    "training-inputs/training_observations.npz": "digest",
                    "training-inputs/training_manifest.json": "digest",
                },
            }
        ),
        encoding="utf-8",
    )
    lock = tmp_path / "training-lock.json"
    lock.write_text(
        json.dumps(
            {
                "source_manifest_sha256": "digest",
                "child_manifests": [
                    {"role": "completed_training_analysis", "manifest_sha256": "digest"}
                ],
            }
        ),
        encoding="utf-8",
    )

    def panel(history: int) -> dict[str, object]:
        fits = {}
        for model in score.MODEL_NAMES:
            valid = not (history == 1 and model == "constant_h1")
            fits[model] = SimpleNamespace(
                model=model,
                h=1.0,
                beta=0.0,
                mu=0.002,
                detection_sd=0.1,
                raw_logjoint=-1.0,
                numerical_status="converged" if valid else "invalid",
                converged=valid,
            )
        records = {
            model: {
                "model": model,
                "h": 1.0,
                "beta": 0.0,
                "mu": 0.002,
                "detection_sd": 0.1,
                "raw_logjoint": -1.0,
                "numerical_status": "converged",
            }
            for model in score.MODEL_NAMES
        }
        return {
            "fits": fits,
            "main": {"fits": records},
            "full": {"main_statuses_converged": {model: True for model in score.MODEL_NAMES}},
            "audit": {"passed": True, "diagnostic_passed": True},
            "paths": {},
        }

    monkeypatch.setattr(score, "load_frozen_panel", lambda _root, history: panel(history))

    def fake_score(_public, _bank, _observed, fit, *, history):
        total = 5.0 if history == 0 else float(score.MODEL_NAMES.index(fit.model) + 1)
        return {
            "conditional_prey_total_nats": total,
            "conditional_prey_nats_per_site": total / 40,
            "conditional_prey_site_nats": np.full(40, total / 40),
            "cluster_contributions_nats": {"cluster": total},
        }

    monkeypatch.setattr(score.qualification, "_heldout_row", fake_score)
    result = score.score_holdout(
        tmp_path / "public",
        training_root,
        tmp_path / "holdout.tar",
        tmp_path / "output",
        training_lock=lock,
    )
    first = result["cases"][0]
    assert first["winner_set"] == list(score.MODEL_NAMES)
    assert first["pair_hit"] is True
    assert first["winning_margin_nats"] == 0.0
    assert len(first["pair_differences"]) == 6
    unavailable = result["cases"][1]
    assert unavailable["winner_set"] is None
    assert unavailable["pair_hit"] is None
    assert unavailable["winning_margin_nats"] is None
