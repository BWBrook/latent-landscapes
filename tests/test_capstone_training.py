from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from latent_landscapes import capstone_public as cap
from latent_landscapes import capstone_qualification as qualification
from latent_landscapes import capstone_training as training
from latent_landscapes import preinvasion_fitting as fitting
from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.misspecification_generator import build_generator_setup

MECHANICAL_ROOT = 987654321


def _public() -> cap.PublicInputs:
    map_seed = cap._u64_seed(MECHANICAL_ROOT, cap.MAP_STAGE, 0)
    sampling_seed = cap._u64_seed(MECHANICAL_ROOT, cap.SAMPLING_STAGE, 0)
    fixed = cap._make_fixed(map_seed, sampling_seed)
    return cap.PublicInputs(fixed, build_generator_setup(fixed), {"root": MECHANICAL_ROOT})


def _package(tmp_path: Path, public: cap.PublicInputs) -> tuple[Path, Path]:
    observations = qualification.mechanical_observations(public)
    mask = np.asarray(public.setup.site_splits) == "training"
    npz_path = tmp_path / "training_observations.npz"
    np.savez_compressed(
        npz_path,
        case_ids=np.asarray(training.TRAINING_CASE_IDS, dtype="U16"),
        site_ids=np.asarray(public.setup.site_ids, dtype="U32")[mask],
        prey_counts=observations.prey_counts[:, mask],
        predator_counts=observations.predator_counts[:, mask],
    )
    manifest_path = tmp_path / "training_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": training.TRAINING_SCHEMA,
                "case_count": 4,
                "site_count": 120,
                "prey_visits": 13,
                "predator_visits": 6,
                "arrays_sha256": hashlib.sha256(npz_path.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    return npz_path, manifest_path


@pytest.fixture(scope="module")
def public() -> cap.PublicInputs:
    return _public()


@pytest.fixture(scope="module")
def bank(public: cap.PublicInputs) -> likelihood.CompressedBank:
    arrivals = np.asarray(
        (np.arange(16, dtype=float)[:, None] * 3.25 + np.arange(160, dtype=float)[None, :])
        % 60.0
    )
    return likelihood.compress_bank(arrivals, public.setup.site_ids)


def test_load_training_binds_exact_schema_and_real_120_site_split(
    public: cap.PublicInputs, tmp_path: Path
) -> None:
    npz_path, manifest_path = _package(tmp_path, public)
    cases = training.load_training(
        public, npz_path, manifest_path, hashlib.sha256(npz_path.read_bytes()).hexdigest()
    )
    assert cases.case_ids == training.TRAINING_CASE_IDS
    assert cases.observations.site_ids == tuple(
        str(value)
        for value, split in zip(public.setup.site_ids, public.setup.site_splits, strict=True)
        if split == "training"
    )
    assert cases.observations.prey_counts.shape == (4, 120, 13)
    assert cases.observations.predator_counts.shape == (4, 120, 6)
    assert np.all(cases.observations.training_mask)
    assert cases.observations.initial_alive.all()


@pytest.mark.parametrize("tamper", ["manifest", "npz"])
def test_load_training_rejects_undocumented_fields(
    public: cap.PublicInputs, tmp_path: Path, tamper: str
) -> None:
    npz_path, manifest_path = _package(tmp_path, public)
    if tamper == "manifest":
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload["truth"] = "secret-bearing"
        manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    else:
        values = {
            "case_ids": np.asarray(training.TRAINING_CASE_IDS),
            "site_ids": np.asarray(public.setup.site_ids)[
                np.asarray(public.setup.site_splits) == "training"
            ],
            "prey_counts": np.zeros((4, 120, 13), dtype=np.int8),
            "predator_counts": np.zeros((4, 120, 6), dtype=np.int8),
            "private_truth": np.zeros(4, dtype=np.int8),
        }
        np.savez_compressed(npz_path, **values)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["arrays_sha256"] = hashlib.sha256(npz_path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="undocumented"):
        training.load_training(public, npz_path, manifest_path)


def test_load_training_rejects_noncanonical_site_or_count_schema(
    public: cap.PublicInputs, tmp_path: Path
) -> None:
    npz_path, manifest_path = _package(tmp_path, public)
    with np.load(npz_path, allow_pickle=False) as values:
        arrays = {name: values[name] for name in values.files}
    arrays["prey_counts"] = arrays["prey_counts"].astype(np.float64)
    np.savez_compressed(npz_path, **arrays)
    with pytest.raises(ValueError, match=r"integer|schema"):
        training.load_training(public, npz_path, manifest_path)


def test_make_training_data_matches_public_qualification_subset(
    public: cap.PublicInputs, bank: likelihood.CompressedBank, tmp_path: Path
) -> None:
    npz_path, manifest_path = _package(tmp_path, public)
    cases = training.load_training(public, npz_path, manifest_path)
    observed = qualification.mechanical_observations(public)
    expected = qualification.make_fit_data(public, bank, observed, history=2, training=True)
    actual = training.make_training_data(public, bank, cases, 2)
    assert actual.observations.site_ids == expected.observations.site_ids
    assert actual.bank.site_ids == expected.bank.site_ids
    assert actual.map_a.shape == (72, 84)
    assert actual.site_a.shape == (120,)
    np.testing.assert_array_equal(
        actual.observations.prey_counts, expected.observations.prey_counts
    )
    np.testing.assert_array_equal(
        actual.observations.predator_counts, expected.observations.predator_counts
    )
    np.testing.assert_allclose(
        training.qualification.fit_loglikelihood(
            actual, h=3.0, beta=0.0, mu=0.0025, detection_sd=0.2
        ),
        qualification.fit_loglikelihood(
            expected, h=3.0, beta=0.0, mu=0.0025, detection_sd=0.2
        ),
        rtol=0,
        atol=0,
    )


def test_pre_scores_ignore_postday0_predator_counts(
    public: cap.PublicInputs, tmp_path: Path
) -> None:
    npz_path, manifest_path = _package(tmp_path, public)
    cases = training.load_training(public, npz_path, manifest_path)
    changed = cases.observations.predator_counts.copy()
    changed[:] = (changed + 1) % 3
    altered_observations = likelihood.prepare_observations(
        cases.observations.prey_counts,
        changed,
        cases.observations.site_ids,
        np.ones(120, dtype=bool),
    )
    altered = training.TrainingCases(cases.case_ids, altered_observations)
    np.testing.assert_array_equal(
        training.observed_pre_scores(public, cases),
        training.observed_pre_scores(public, altered),
    )


def test_fit_training_case_delegates_and_persists_main_before_profiles(
    public: cap.PublicInputs,
    bank: likelihood.CompressedBank,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    npz_path, manifest_path = _package(tmp_path, public)
    cases = training.load_training(public, npz_path, manifest_path)
    fits = {
        name: fitting.FitResult(name, 1.0, 0.0, 0.0025, 0.2, -float(index), "converged", 1, 0.0)
        for index, name in enumerate(
            ("constant_free_h", "adjusted_free_h", "constant_h1", "adjusted_h1")
        )
    }
    paired = fitting.PairedFitResult(
        0.0,
        fits,
        {"adjusted": 0.0, "constant": 0.0},
        fitting.CostSummary(4, 0, 4, 0.0, 0.0, 0.0),
    )
    profile = fitting.ProfileResult(
        "h",
        np.asarray([1.0, 10.0]),
        np.asarray([-1.0, -2.0]),
        (),
        ("converged", "converged"),
        1,
        0.0,
        False,
        None,
    )
    monkeypatch.setattr(training.fitting, "paired_fit", lambda data, callback: paired)

    def profile_checked(*args: Any, **kwargs: Any) -> fitting.ProfileResult:
        assert (tmp_path / "out" / "history-00-full-main.json").is_file()
        return profile

    monkeypatch.setattr(training.fitting, "profile_h", profile_checked)
    monkeypatch.setattr(training.fitting, "profile_beta", profile_checked)
    result = training.fit_training_case(public, bank, cases, history=0, output=tmp_path / "out")
    assert result["main_statuses_converged"] == dict.fromkeys(fits, True)
    assert result["nesting_gap_diagnostic_passed"]
    assert result["observed_adjusted_validity"]["valid"]
    assert "heldout_scores" not in result
    assert (tmp_path / "out" / "history-00-full-main.json").is_file()
    assert (tmp_path / "out" / "history-00-full.json").is_file()


def test_fit_training_case_retains_invalid_main_and_unavailable_diagnostics(
    public: cap.PublicInputs,
    bank: likelihood.CompressedBank,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    npz_path, manifest_path = _package(tmp_path, public)
    cases = training.load_training(public, npz_path, manifest_path)
    fits = {
        name: fitting.FitResult(name, np.nan, np.nan, np.nan, np.nan, np.nan, "invalid", 0, 0.0)
        for name in (
            "constant_free_h",
            "adjusted_free_h",
            "constant_h1",
            "adjusted_h1",
        )
    }
    paired = fitting.PairedFitResult(
        np.nan,
        fits,
        {"adjusted": np.nan, "constant": np.nan},
        fitting.CostSummary(0, 0, 0, 0.0, 0.0, 0.0),
    )
    monkeypatch.setattr(training.fitting, "paired_fit", lambda data, callback: paired)
    result = training.fit_training_case(public, bank, cases, history=0, output=tmp_path / "out")
    assert not result["observed_adjusted_validity"]["valid"]
    assert all(not profile["values"] for profile in result["profiles"].values())
    assert all(not profile["statuses_converged"] for profile in result["profiles"].values())
    assert all(np.isnan(value) for value in result["main_replay_logjoint_differences"].values())
    assert (tmp_path / "out" / "history-00-full-main.json").is_file()


def _paired_with_adjusted_scores(
    null_score: float,
    free_score: float,
    *,
    null_status: str = "converged",
    free_status: str = "converged",
    statistic: float = 13.0,
) -> fitting.PairedFitResult:
    fits = {
        "constant_free_h": fitting.FitResult(
            "constant_free_h", 1.0, 0.0, 0.0025, 0.2, -2.0, "converged", 1, 0.0
        ),
        "constant_h1": fitting.FitResult(
            "constant_h1", 1.0, 0.0, 0.0025, 0.2, -3.0, "converged", 1, 0.0
        ),
        "adjusted_free_h": fitting.FitResult(
            "adjusted_free_h", 1.0, 0.0, 0.0025, 0.2, free_score, free_status, 1, 0.0
        ),
        "adjusted_h1": fitting.FitResult(
            "adjusted_h1", 1.0, 0.0, 0.0025, 0.2, null_score, null_status, 1, 0.0
        ),
    }
    return fitting.PairedFitResult(
        statistic,
        fits,
        {"adjusted": statistic, "constant": 2.0},
        fitting.CostSummary(4, 0, 4, 0.0, 0.0, 0.0),
    )


def test_observed_adjusted_pair_rejects_negative_nesting_without_changing_main_t() -> None:
    paired = _paired_with_adjusted_scores(-10.0, -10.000002)
    validity = training.observed_adjusted_validity(paired)
    batch = training.observed_adjusted_effect_batch(paired)
    assert not validity["valid"]
    assert validity["free_minus_null"] == pytest.approx(-0.000002)
    assert paired.T == 13.0
    assert np.isnan(batch.statistics()[0])


def test_observed_adjusted_pair_marks_nonfinite_or_unconverged_invalid() -> None:
    for paired in (
        _paired_with_adjusted_scores(-10.0, float("nan")),
        _paired_with_adjusted_scores(-10.0, -9.0, free_status="failed_optimizer"),
    ):
        validity = training.observed_adjusted_validity(paired)
        batch = training.observed_adjusted_effect_batch(paired)
        assert not validity["valid"]
        assert np.isnan(batch.statistics()[0])
