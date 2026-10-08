from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes import capstone_public as cap
from latent_landscapes import capstone_qualification as qualification
from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.misspecification_generator import build_generator_setup

MECHANICAL_ROOT = 987654321


@pytest.fixture(scope="module")
def public() -> cap.PublicInputs:
    map_seed = cap._u64_seed(MECHANICAL_ROOT, cap.MAP_STAGE, 0)
    sampling_seed = cap._u64_seed(MECHANICAL_ROOT, cap.SAMPLING_STAGE, 0)
    fixed = cap._make_fixed(map_seed, sampling_seed)
    return cap.PublicInputs(fixed, build_generator_setup(fixed), {"root": MECHANICAL_ROOT})


@pytest.fixture(scope="module")
def tiny_bank(public: cap.PublicInputs) -> np.ndarray:
    seeds = tuple(cap._u64_seed(MECHANICAL_ROOT, cap.BANK_STAGE, i) for i in range(32))
    return np.asarray(arc2b._generate_bank(public.fixed, seeds), dtype=np.float64)


def test_domain_and_mechanical_patterns_are_fixed(public: cap.PublicInputs) -> None:
    points = qualification.domain_points()
    assert len(points) == 17
    assert {(p.h, p.beta, p.mu, p.detection_sd) for p in points[:-1]} == {
        (h, beta, mu, sd)
        for h in (1.0, 10.0)
        for beta in (-2.0, 2.0)
        for mu in (0.0005, 0.006)
        for sd in (0.0, 0.4)
    }
    assert points[-1] == qualification.DomainPoint(3.0, 0.0, 0.0025, 0.2)
    observations = qualification.mechanical_observations(public)
    assert observations.prey_counts.shape == (4, 160, 13)
    assert observations.predator_counts.shape == (4, 160, 6)
    assert np.all(observations.prey_counts[0] == 0)
    assert np.all(observations.prey_counts[1] == 2)
    assert np.array_equal(
        observations.prey_counts[2], (np.arange(160)[:, None] + np.arange(13)) % 3
    )
    assert np.all(observations.prey_counts[3, :, :7] == 2)
    assert np.all(observations.predator_counts[3, :, :3] == 0)
    assert np.all(observations.predator_counts[3, :, 3:] == 1)


def test_compressed_exact_and_pair_checks_use_tiny_bank(
    public: cap.PublicInputs, tiny_bank: np.ndarray
) -> None:
    bank = likelihood.compress_bank(tiny_bank, public.setup.site_ids)
    observed = qualification.mechanical_observations(public)
    comparison = qualification.compare_compressed_exact(public, bank, observed)
    assert comparison["points"] == 17
    assert comparison["passed"]
    train = qualification.make_fit_data(public, bank, observed, history=0, training=True)
    holdout = qualification.make_fit_data(public, bank, observed, history=0, training=False)
    primitive = qualification.adjusted_pair_primitive(
        train,
        holdout_data=holdout,
        full_public=public,
        full_bank=bank,
        full_observed=observed,
        history=0,
    )
    assert primitive["passed"]
    assert primitive["holdout_changed"]
    assert primitive["training_unchanged"]
    assert primitive["training_rebuild_unchanged"]
    assert primitive["effect_reference_pair_statuses_match"]


def test_coarse_grid_has_registered_size(public: cap.PublicInputs, tiny_bank: np.ndarray) -> None:
    bank = likelihood.compress_bank(tiny_bank, public.setup.site_ids)
    observed = qualification.mechanical_observations(public)
    audit = qualification.coarse_grid_audit(
        qualification.make_fit_data(public, bank, observed, history=0, training=True)
    )
    assert audit["points"] == audit["expected_points"] == 1350
    assert set(audit["max_logjoint"]) == set(qualification.MODEL_NAMES)
    assert audit["diagnostic_only"]


def test_manifest_shape_site_order_and_hash_are_checked(
    public: cap.PublicInputs, tiny_bank: np.ndarray, tmp_path: Path
) -> None:
    bank_dir = tmp_path / "bank"
    bank_dir.mkdir()
    np.save(bank_dir / "arrivals.npy", tiny_bank)
    seeds = np.asarray(
        [cap._u64_seed(MECHANICAL_ROOT, cap.BANK_STAGE, i) for i in range(tiny_bank.shape[0])],
        dtype=np.uint64,
    )
    np.savez_compressed(bank_dir / "seed_ledger.npz", seeds=seeds)
    np.savez_compressed(bank_dir / "chunk-00000000.npz", offset=0, seeds=seeds, arrivals=tiny_bank)
    started = {
        "root": MECHANICAL_ROOT,
        "namespace": cap.NAMESPACE,
        "stage": cap.BANK_STAGE,
        "bank_size": tiny_bank.shape[0],
        "site_ids": list(public.setup.site_ids),
    }
    started_path = bank_dir / "started.json"
    started_path.write_text(json.dumps(started), encoding="utf-8")
    manifest = {
        "root": MECHANICAL_ROOT,
        "namespace": cap.NAMESPACE,
        "stage": cap.BANK_STAGE,
        "array_shape": list(tiny_bank.shape),
        "bank_size": tiny_bank.shape[0],
        "site_ids": list(public.setup.site_ids),
        "array_sha256": qualification._array_sha(tiny_bank),
        "arrivals_file_sha256": qualification._sha(bank_dir / "arrivals.npy"),
        "started_receipt_sha256": qualification._sha(started_path),
        "ledger_sha256": qualification._array_sha(seeds),
        "ledger_file_sha256": qualification._sha(bank_dir / "seed_ledger.npz"),
        "public_input_array_sha256": cap._array_hashes(public.fixed),
        "map_a_sha256": qualification._array_sha(public.setup.exposure_score),
        "chunks": [{"offset": 0, "rows": tiny_bank.shape[0]}],
    }
    manifest["chunks"][0]["file_sha256"] = qualification._sha(bank_dir / "chunk-00000000.npz")
    (bank_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    result = qualification.validate_bank_manifest(
        public, bank_dir, expected_bank_size=tiny_bank.shape[0]
    )
    assert result["array_shape"] == [32, 160]
    manifest["site_ids"] = list(reversed(manifest["site_ids"]))
    (bank_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="site order"):
        qualification.validate_bank_manifest(
            public, bank_dir, expected_bank_size=tiny_bank.shape[0]
        )


def test_public_panel_ledger_is_frozen_before_generation(tmp_path: Path) -> None:
    public_dir = tmp_path / "public"
    cap.freeze_public_inputs(public_dir, root=MECHANICAL_ROOT)
    qualification_dir = tmp_path / "qualification"
    qualification_dir.mkdir()
    receipt = {"passed": True}
    (qualification_dir / "qualification.json").write_text(json.dumps(receipt), encoding="utf-8")
    (qualification_dir / "mechanical-receipt.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    output = tmp_path / "panel"
    manifest = qualification.generate_public_panel(
        public_dir, qualification_dir, output, root=MECHANICAL_ROOT
    )
    assert manifest["state"] == "generated"
    assert manifest["root"] == MECHANICAL_ROOT
    assert manifest["seed_ledger_sha256"]
    assert json.loads((output / "truths.json").read_text())["truths"][6]["beta"] is None
    with np.load(output / "observations.npz") as observations:
        assert observations["prey_counts"].shape == (8, 160, 13)
    with np.load(output / "evaluator.npz") as evaluator:
        assert evaluator["stream_seeds"].shape == (8, 6)
        assert evaluator["map_hazard"].shape == (8, 72, 84)
    release = qualification._validate_panel_release(cap.load_public_inputs(public_dir), output)
    assert release["state"] == "generated"
    release["evaluator_npz_sha256"] = "0" * 64
    (output / "manifest.json").write_text(json.dumps(release), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest hash"):
        qualification._validate_panel_release(cap.load_public_inputs(public_dir), output)
    with pytest.raises(FileExistsError):
        qualification.generate_public_panel(
            public_dir, qualification_dir, output, root=MECHANICAL_ROOT
        )


def test_stability_uses_union_core_and_checks_generating_node() -> None:
    def row(tail: float) -> dict[str, Any]:
        profiles = {
            "constant_h": {"grid": [1.0, 2.0, 3.0], "values": [0.0, -2.5, tail]},
            "adjusted_h": {"grid": [1.0, 2.0, 3.0], "values": [0.0, -2.5, tail]},
            "adjusted_beta": {"grid": [-1.0, 0.0, 1.0], "values": [0.0, -2.5, tail]},
        }
        fits = {name: {"h": 1.0, "raw_logjoint": 0.0} for name in qualification.MODEL_NAMES}
        heldout = {name: {"conditional_prey_total_nats": 0.0} for name in qualification.MODEL_NAMES}
        return {
            "paired": {"fits": fits},
            "adjusted_T": 0.0,
            "profiles": profiles,
            "profile_main_gaps": {name: 0.0 for name in profiles},
            "profile_statuses_converged": {name: True for name in profiles},
            "main_statuses_converged": {name: True for name in fits},
            "nesting_gap_gate": True,
            "heldout_scores": heldout,
        }

    rows = {name: row(-25.0) for name in ("full", "first_half", "second_half")}
    rows["first_half"] = row(-30.0)
    summary = qualification.bank_stability_summary(rows, generating_h=1.0)
    assert summary["gates"]["centered_profile_R_movement"]
    assert summary["gates"]["generating_profile_R_movement"]
    outside = qualification.bank_stability_summary(rows, generating_h=3.0)
    assert not outside["gates"]["generating_profile_R_movement"]
    core = {name: row(-25.0) for name in ("full", "first_half", "second_half")}
    core["first_half"] = row(-25.0)
    for profile in ("constant_h", "adjusted_h", "adjusted_beta"):
        core["first_half"]["profiles"][profile]["values"][1] = -2.8
    core_summary = qualification.bank_stability_summary(core, generating_h=1.0)
    assert not core_summary["gates"]["centered_profile_R_movement"]
