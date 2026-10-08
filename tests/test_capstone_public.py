from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import latent_landscapes.capstone_public as cap
from latent_landscapes import preinvasion_campaign as pre_campaign
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.misspecification_generator import build_generator_setup

MECHANICAL_ROOT = 987654321


def _mechanical_public() -> cap.PublicInputs:
    map_seed = cap._u64_seed(MECHANICAL_ROOT, cap.MAP_STAGE, 0)
    sampling_seed = cap._u64_seed(MECHANICAL_ROOT, cap.SAMPLING_STAGE, 0)
    fixed = cap._make_fixed(map_seed, sampling_seed)
    return cap.PublicInputs(fixed, build_generator_setup(fixed), {"root": MECHANICAL_ROOT})


def test_seeded_map_and_canonical_site_order() -> None:
    public = _mechanical_public()
    assert public.fixed.landscape.shape == (72, 84)
    assert len(public.setup.site_ids) == 160
    assert public.setup.site_ids == tuple(sorted(public.setup.site_ids))
    assert abs(float(public.setup.exposure_score.mean())) < 1e-12
    assert abs(float(public.setup.exposure_score.std()) - 1.0) < 1e-12


def test_mechanical_freeze_round_trips(tmp_path: Path) -> None:
    cap.freeze_public_inputs(tmp_path / "public", root=MECHANICAL_ROOT)
    loaded = cap.load_public_inputs(tmp_path / "public")
    assert loaded.metadata["root"] == MECHANICAL_ROOT
    assert loaded.metadata["array_sha256"] == cap._array_hashes(loaded.fixed)


def test_exact_generator_matches_preinvasion_campaign() -> None:
    public = _mechanical_public()
    streams = {
        name: cap._u64_seed(MECHANICAL_ROOT, 10 + i, 0) for i, name in enumerate(cap.STREAM_NAMES)
    }
    seeds = {"streams": streams}
    truth = cap.GeneralTruth(0, 1.0, 0.002, 0.3, 0.0, "exact")
    observed, evaluator = cap.generate_exact_history(public.fixed, public.setup, truth, seeds)
    expected = pre_campaign.generate_open_history(
        public.fixed, public.setup, pre_campaign.OpenTruth(0, 1.0, 0.002, 0.3, 0.0), seeds
    )
    assert np.array_equal(observed["prey_counts"], expected[0]["prey_counts"])
    assert np.array_equal(observed["predator_counts"], expected[0]["predator_counts"])
    assert observed["prey_counts"].shape == (160, 13)
    assert observed["predator_counts"].shape == (160, 6)
    assert evaluator["truth"]["mean_hazard"] == truth.mean_hazard


def test_b100_formula_has_expected_scaling() -> None:
    public = _mechanical_public()
    field = cap._b100_hazard(public.setup, np.random.default_rng(MECHANICAL_ROOT), 0.004)
    values = field[public.setup.accepted_mask]
    assert np.isfinite(values).all()
    assert (values > 0).all()
    assert abs(float(values.mean()) - 0.004) < 1e-12
    gaussian = public.setup.field_sampler.sample(np.random.default_rng(MECHANICAL_ROOT))
    raw = np.exp(
        np.sqrt(np.log(2)) * (0.7 * public.setup.exposure_score + np.sqrt(0.51) * gaussian)
    )
    assert public.setup.accepted_mask.all()
    np.testing.assert_allclose(field, 0.004 * raw / raw.mean(), rtol=1e-14, atol=0)


def test_numerical_failure_keeps_first_structural_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixed = _mechanical_public().fixed
    calls = []

    def structural(map_seed: int, sampling_seed: int) -> FixedInputs:
        calls.append((map_seed, sampling_seed))
        return fixed

    def failed_setup(*args: object) -> None:
        assert (tmp_path / "public" / "public_inputs.npz").is_file()
        assert (tmp_path / "public" / "accepted_candidate.json").is_file()
        raise RuntimeError("mechanical certificate failure")

    monkeypatch.setattr(cap, "_make_fixed", structural)
    monkeypatch.setattr(cap, "build_generator_setup", failed_setup)
    with pytest.raises(RuntimeError, match="mechanical certificate failure"):
        cap.freeze_public_inputs(tmp_path / "public", root=MECHANICAL_ROOT)
    assert len(calls) == 1
    metadata = json.loads((tmp_path / "public" / "public_inputs.json").read_text())
    assert metadata["state"] == "qualification_failed"
    assert metadata["attempt"] == 0
    with pytest.raises(ValueError, match="qualification did not pass"):
        cap.load_public_inputs(tmp_path / "public")
    with pytest.raises(FileExistsError):
        cap.freeze_public_inputs(tmp_path / "public", root=MECHANICAL_ROOT)


def test_serial_and_two_worker_tiny_banks_match(tmp_path: Path) -> None:
    public = _mechanical_public()
    serial = cap.build_arrival_bank(
        public, tmp_path / "serial", root=MECHANICAL_ROOT, workers=1, bank_size=8, chunk_size=4
    )
    parallel = cap.build_arrival_bank(
        public, tmp_path / "parallel", root=MECHANICAL_ROOT, workers=2, bank_size=8, chunk_size=4
    )
    first = np.load(tmp_path / "serial" / "arrivals.npy")
    second = np.load(tmp_path / "parallel" / "arrivals.npy")
    assert np.array_equal(first, second)
    assert serial["array_sha256"] == parallel["array_sha256"]
    assert json.loads((tmp_path / "parallel" / "manifest.json").read_text())["bank_size"] == 8
