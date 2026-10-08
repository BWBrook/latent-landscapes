"""Bounded, synthetic checks for the Goal 047 Stage A runner."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes import arc2c_campaign as arc2c
from latent_landscapes import arc2c_likelihood as likelihood
from latent_landscapes import arc3_campaign as arc3
from latent_landscapes import arc3_design, arc3_landscapes
from latent_landscapes.goal007 import benchmark as goal007

SCRIPT = Path(__file__).parents[1] / "scripts" / "run_integration_validation.py"
SPEC = importlib.util.spec_from_file_location("integration_validation", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_combined_tiny_banks_match_direct_integration() -> None:
    rng = np.random.default_rng(7047)
    left_bank = rng.uniform(0.0, 80.0, size=(8, 3))
    right_bank = rng.uniform(0.0, 80.0, size=(8, 3))
    site_ids = ("a", "b", "c")
    effects = (1.0, 2.0, 5.0)
    left = likelihood.build_joint_integration(left_bank, site_ids, (1.0,), effects)
    right = likelihood.build_joint_integration(right_bank, site_ids, (1.0,), effects)
    combined = RUNNER.combine_integrations(
        left,
        right,
        hashlib.sha256(np.concatenate((left_bank, right_bank)).tobytes()).hexdigest(),
        half_size=8,
    )
    direct = likelihood.build_joint_integration(
        np.concatenate((left_bank, right_bank)), site_ids, (1.0,), effects
    )
    np.testing.assert_allclose(combined.category_mass, direct.category_mass, rtol=0, atol=1e-14)
    for observed, expected in zip(combined.survival_moments, direct.survival_moments, strict=True):
        np.testing.assert_allclose(observed, expected, rtol=0, atol=1e-14)
    assert combined.bank_checksum == direct.bank_checksum


def _tiny_context(archetype: str = "connected") -> tuple[dict[str, object], object]:
    landscape = arc3_landscapes.build_landscape(archetype, 2026090812)
    access, balanced = arc3_design.build_sampling_pair(landscape, 2026090812)
    access_coords, access_ordered = arc3._validate_design(access, landscape)
    balanced_coords, balanced_ordered = arc3._validate_design(balanced, landscape)
    access = arc3._canonical_design(access, access_ordered)
    balanced = arc3._canonical_design(balanced, balanced_ordered)
    union = arc3._union_design(access, access_coords, balanced_coords)
    union_fixed = goal007.FixedInputs(landscape, union, {"design_valid": True})
    designs = (
        ("access", goal007.FixedInputs(landscape, access, {"design_valid": True})),
        ("balanced", goal007.FixedInputs(landscape, balanced, {"design_valid": True})),
    )
    config = arc2c.BridgeConfig(
        bank_size=16,
        calibration_replicates=2,
        validation_replicates=2,
        calibration_rank=2,
        rhos=(0.5, 1.0),
        effects=(1.0, 3.0, 5.0),
    )
    manifest = arc2c.spawn_seed_manifest(config)
    return {
        "union_fixed": union_fixed,
        "designs": designs,
        "manifest": manifest,
        "config": config,
    }, landscape


@pytest.mark.parametrize("archetype", ("connected", "corridor"))
def test_reduced_surfaces_match_frozen_arc3_dataset_task(archetype: str) -> None:
    context, _ = _tiny_context(archetype)
    site_ids = tuple(site.site_id for site in context["union_fixed"].design.sites)
    rng = np.random.default_rng(7048)
    bank = rng.uniform(0.0, 80.0, size=(16, len(site_ids)))
    integration = likelihood.build_joint_integration(
        bank, site_ids, (0.5, 1.0), (1.0, 3.0, 5.0)
    )
    seed = context["manifest"].validation[0]
    mapped = RUNNER.paired_mapped_histories(context, seed, arc3, likelihood)
    for alpha in (0.25, 0.5, 1.0):
        view = RUNNER.alpha_views(integration, bank.shape[0])[RUNNER.ALPHA_LABELS[alpha]]
        block = arc3._dataset_task(
            context["union_fixed"], context["designs"], seed, view, arc3._truths()
        )
        assert block.training_joint is not None
        for design_index in range(2):
            for effect_index in range(3):
                observed = RUNNER._surface(
                    mapped[design_index][effect_index], view, likelihood
                )
                np.testing.assert_allclose(
                    observed,
                    block.training_joint[design_index * 3 + effect_index],
                    rtol=0,
                    atol=1e-12,
                )


def test_output_is_refuse_overwrite_and_binds_array_hash(tmp_path: Path) -> None:
    output = tmp_path / "diagnostic"
    arrays = {"effects": np.asarray([1.0, 2.0]), "corridor_rhos": np.asarray([1.0])}
    report: dict[str, object] = {"schema_version": 1}
    RUNNER.write_output(output, arrays, report)
    assert report["completion_status"] == "complete"
    assert report["arrays_sha256"] == hashlib.sha256(
        (output / "diagnostic-arrays.npz").read_bytes()
    ).hexdigest()
    try:
        RUNNER.write_output(output, arrays, {})
    except FileExistsError:
        pass
    else:
        raise AssertionError("runner must refuse to overwrite an existing output")
