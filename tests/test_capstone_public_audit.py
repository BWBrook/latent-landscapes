from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import platform
import sys
from pathlib import Path

import numpy as np

from latent_landscapes import capstone_public as public_api
from latent_landscapes import capstone_qualification as qualification
from latent_landscapes.misspecification_generator import build_generator_setup

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_capstone_public.py"
sys.path.insert(0, str(_SCRIPT.parent))
_SPEC = importlib.util.spec_from_file_location("audit_capstone_public", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
audit = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = audit
_SPEC.loader.exec_module(audit)

MECHANICAL_ROOT = 987654321


def _mechanical_public() -> public_api.PublicInputs:
    map_seed = public_api._u64_seed(MECHANICAL_ROOT, public_api.MAP_STAGE, 0)
    sampling_seed = public_api._u64_seed(MECHANICAL_ROOT, public_api.SAMPLING_STAGE, 0)
    fixed = public_api._make_fixed(map_seed, sampling_seed)
    return public_api.PublicInputs(
        fixed, build_generator_setup(fixed), {"root": MECHANICAL_ROOT}
    )


def test_address_contracts_are_exact_and_separated() -> None:
    bank = [audit.public_seed(audit.BANK_DOMAIN, index, root=MECHANICAL_ROOT) for index in range(8)]
    streams = audit.public_fixture_streams(0, root=MECHANICAL_ROOT)
    assert tuple(streams) == tuple(audit.PUBLIC_STREAM_STAGES)
    assert len(set(bank)) == len(bank)
    assert not set(bank).intersection(streams.values())
    screen_seed = audit.confirmatory_seed(
        audit.SCREEN_DOMAIN, 0, 0, 2, root=MECHANICAL_ROOT
    )
    effect_seed = audit.confirmatory_seed(
        audit.EFFECT_DOMAIN, 0, 0, 2, root=MECHANICAL_ROOT
    )
    assert screen_seed != effect_seed


def test_direct_bank_preserves_alpha_one_pseudo_arrivals() -> None:
    arrivals = np.asarray([[5.0, 15.0], [70.0, 25.0]], dtype=np.float64)
    bank = audit.make_direct_bank(arrivals, ("a", "b"))
    assert bank.bank_size == 2
    assert bank.denominator == 9
    np.testing.assert_allclose(bank.category_mass.sum(axis=1), 1.0)
    np.testing.assert_allclose(bank.category_mass[0], np.asarray([2, 1, 1, 1, 1, 1, 2]) / 9)


def test_independent_b100_map_and_replay_use_registered_mean() -> None:
    public = _mechanical_public()
    streams = audit.public_fixture_streams(6, root=MECHANICAL_ROOT)
    truth = {
        "background": "B100-A",
        "h": 1.0,
        "beta": 0.0,
        "mu": 0.0025,
        "detection_sd": 0.2,
    }
    replay = audit.replay_public_history(public.fixed, public.setup, truth, streams)
    assert abs(float(replay["hazard_map"].mean()) - 0.0025) <= 1e-15
    assert replay["prey_counts"].shape == (160, 13)
    assert replay["predator_counts"].shape == (160, 6)
    assert np.all(replay["prey_counts"][~replay["prey_alive"]] == 0)


def test_multi_history_direct_score_matches_one_history_path() -> None:
    public = _mechanical_public()
    arrivals = np.tile(np.linspace(5.0, 70.0, 160), (8, 1))
    bank = audit.make_direct_bank(arrivals, public.setup.site_ids)
    context = audit.AuditContext(
        tuple(public.setup.site_ids),
        np.asarray(public.setup.site_splits) == "training",
        np.asarray(public.setup.exposure_score),
        np.asarray(
            public.setup.exposure_score[public.setup.site_rows, public.setup.site_cols]
        ),
        tuple(public.setup.site_cluster_ids),
    )
    prey = np.zeros((2, 160, 13), dtype=np.int64)
    predator = np.zeros((2, 160, 6), dtype=np.int64)
    prey[1, :, :7] = 1
    parameters = {"h": 3.0, "beta": 0.5, "mu": 0.0025, "detection_sd": 0.2}
    batch = audit.direct_multi_training_scores(bank, context, prey, predator, parameters)
    separate = np.asarray(
        [
            audit.direct_training_score(bank, context, prey[i], predator[i], parameters)
            for i in range(2)
        ]
    )
    np.testing.assert_allclose(batch, separate, rtol=0.0, atol=1e-12)


def test_profile_and_complete_stability_predicates() -> None:
    primary = {
        "T": 2.0,
        "profiles": {
            "constant_h": {"values": [0.0, -1.0, -3.0]},
            "adjusted_h": {"values": [0.0, -0.5, -2.0]},
            "adjusted_beta": {"values": [-1.0, 0.0, -1.0]},
        },
        "generating_lr": {"h": 1.0, "beta": 0.5},
        "holdout_scores": {name: float(index) for index, name in enumerate(audit.MODEL_NAMES)},
    }
    half = {
        "T": 2.25,
        "profiles": {
            "constant_h": {"values": [0.0, -1.1, -3.1]},
            "adjusted_h": {"values": [0.0, -0.6, -2.1]},
            "adjusted_beta": {"values": [-1.1, 0.0, -1.0]},
        },
        "generating_lr": {"h": 1.2, "beta": 0.7},
        "holdout_scores": {
            name: float(index) + 0.1 * index for index, name in enumerate(audit.MODEL_NAMES)
        },
    }
    result = audit.stability_predicates(primary, half, exact_family=True)
    assert result["passed"]
    failed = dict(half)
    failed["T"] = 2.5000001
    assert not audit.stability_predicates(primary, failed, exact_family=True)["passed"]


def test_full_grid_neighbors_ranks_union_and_effect_rule() -> None:
    grid = audit.nuisance_grid()
    assert len(grid) == 765
    assert grid[0] == (-2.0, 0.0005, 0.0)
    assert grid[-1] == (2.0, 0.006, 0.4)
    assert len(audit.nuisance_neighbors(0)) == 4
    assert len(audit.nuisance_neighbors(382)) == 7
    surface = np.zeros(765)
    surface[383] = 2.0
    assert audit.local_discrepancy(surface, 382) == 4.0

    # Node 0 is excluded because all 99 reference values lie below observed D;
    # every zero-discrepancy node is retained by the inclusive tie rule.
    observed = np.zeros((4, 765))
    observed[:, 1] = 2.0
    references = np.zeros((765, 99))
    retained = audit.screen_sets(observed, references)
    assert all(0 not in case for case in retained)
    assert all(1 in case for case in retained)
    union = set().union(*map(set, retained))
    assert len(union) <= 765

    effect = audit.effect_decision(5.0, (1, 2), {1: np.zeros(999), 2: np.zeros(999)})
    assert effect["p_BB"] == 0.011
    assert effect["declare"]


def test_public_and_bank_provenance_reconstruct_on_mechanical_root(tmp_path: Path) -> None:
    public_dir = tmp_path / "public"
    public_api.freeze_public_inputs(public_dir, root=MECHANICAL_ROOT)
    _, _, context, public_result = audit.reconstruct_public_inputs(
        public_dir, expected_root=MECHANICAL_ROOT
    )
    assert public_result["passed"]

    bank_dir = tmp_path / "bank"
    public = _mechanical_public()
    public_api.build_arrival_bank(
        public, bank_dir, root=MECHANICAL_ROOT, workers=1, bank_size=8, chunk_size=4
    )
    raw, bank_result = audit.audit_arrival_bank(
        bank_dir,
        context.site_ids,
        fixed=public.fixed,
        map_a=public.setup.exposure_score,
        expected_size=8,
        expected_root=MECHANICAL_ROOT,
    )
    assert raw.shape == (8, 160)
    assert bank_result["passed"]

    manifest = json.loads((bank_dir / "manifest.json").read_text())
    manifest["array_sha256"] = "0" * 64
    (bank_dir / "manifest.json").write_text(json.dumps(manifest))
    try:
        audit.audit_arrival_bank(
            bank_dir,
            context.site_ids,
            fixed=public.fixed,
            map_a=public.setup.exposure_score,
            expected_size=8,
            expected_root=MECHANICAL_ROOT,
        )
    except ValueError as error:
        assert "provenance" in str(error)
    else:
        raise AssertionError("corrupt manifest was accepted")


def test_terminal_first_structural_map_failure_is_independently_reproduced(
    tmp_path: Path,
) -> None:
    public_dir = tmp_path / "public"
    try:
        public_api.freeze_public_inputs(public_dir, root=1)
    except RuntimeError:
        pass
    else:
        raise AssertionError("test root 1 unexpectedly passed its numerical certificate")
    result = audit.audit_failed_public_inputs(public_dir, expected_root=1)
    assert result["passed"]
    assert result["terminal_negative_qualification"]
    assert result["attempt"] == 0


def test_public_fixture_ledger_and_all_eight_replays_are_bitwise(tmp_path: Path) -> None:
    public_dir = tmp_path / "public"
    public_api.freeze_public_inputs(public_dir, root=MECHANICAL_ROOT)
    qualification_dir = tmp_path / "qualification"
    qualification_dir.mkdir()
    (qualification_dir / "qualification.json").write_text('{"passed": true}\n')
    (qualification_dir / "mechanical-receipt.json").write_text('{"passed": true}\n')
    panel_dir = tmp_path / "panel"
    qualification.generate_public_panel(
        public_dir,
        qualification_dir,
        panel_dir,
        root=MECHANICAL_ROOT,
    )
    public = public_api.load_public_inputs(public_dir)
    context = audit.AuditContext(
        tuple(public.setup.site_ids),
        np.asarray(public.setup.site_splits) == "training",
        np.asarray(public.setup.exposure_score),
        np.asarray(
            public.setup.exposure_score[public.setup.site_rows, public.setup.site_cols]
        ),
        tuple(public.setup.site_cluster_ids),
    )
    prey, predator, truths, result = audit.audit_public_panel(
        panel_dir,
        public.fixed,
        public.setup,
        context,
        expected_root=MECHANICAL_ROOT,
    )
    assert result["passed"]
    assert prey.shape == (8, 160, 13)
    assert predator.shape == (8, 160, 6)
    assert len(truths) == 8


def test_independent_stability_uses_T_core_and_generating_coordinates() -> None:
    grids = {
        "constant_h": [1.0, 3.0, 10.0],
        "adjusted_h": [1.0, 3.0, 10.0],
        "adjusted_beta": [-1.0, 0.0, 1.0],
    }

    def row(T: float, shift: float) -> dict[str, object]:
        profiles = {
            name: {
                "grid": grid,
                "values": [shift, -0.1 + shift, -20.0 + shift],
                "statuses": ["converged"] * 3,
            }
            for name, grid in grids.items()
        }
        return {
            "paired": {"T": T},
            "fits": {
                name: {"numerical_status": "converged"} for name in audit.MODEL_NAMES
            },
            "profiles": profiles,
            "nesting_gaps": {"constant": 0.0, "adjusted": 0.0},
            "profile_main_gaps": {
                "constant_h": 0.0,
                "adjusted_h": 0.0,
                "adjusted_beta": 0.0,
            },
            "heldout_scores": {
                name: {"conditional_prey_total_nats": float(index) + shift}
                for index, name in enumerate(audit.MODEL_NAMES)
            },
        }

    rows = {
        "full": row(2.0, 0.0),
        "first_half": row(2.4, 0.1),
        "second_half": row(1.6, -0.1),
    }
    result = audit.independent_stability(
        rows,
        {"background": "exact", "effect": 3.0, "beta": 0.0},
    )
    assert result["passed"]
    rows["first_half"]["paired"] = {"T": 2.5000001}
    assert not audit.independent_stability(
        rows,
        {"background": "exact", "effect": 3.0, "beta": 0.0},
    )["passed"]


def test_registered_calibration_fixture_reconstructs_expected_decisions() -> None:
    directory = (
        Path(__file__).resolve().parents[1]
        / "artifacts/goal059_execution/calibration-fixture"
    )
    result = audit.audit_calibration_fixture(directory)
    assert result["candidate_counts"] == [765, 1, 1, 470]
    assert result["union_count"] == 765
    assert [row["p_BB"] for row in result["decisions"]] == [1.0, 0.976, 0.011, 1.0]


def test_source_and_runtime_freeze_bind_running_checkout(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    registration = (
        repository / "docs/goals/059-capstone-preparation/registration-2026-10-04.md"
    )
    runtime = tmp_path / "runtime.json"
    runtime.write_text(
        json.dumps(
            {
                "python_version": platform.python_version(),
                "numpy_version": np.__version__,
                "bit_generator": "PCG64",
            }
        )
    )
    relative = str(registration.relative_to(repository))
    manifest = tmp_path / "source-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "source_hashes": {
                    relative: hashlib.sha256(registration.read_bytes()).hexdigest()
                },
                "runtime_sha256": hashlib.sha256(runtime.read_bytes()).hexdigest(),
            }
        )
    )
    result = audit.audit_source_freeze(repository, manifest, runtime, registration)
    assert result["passed"]


def test_auditor_has_no_production_likelihood_normalizer_or_fitter_import() -> None:
    tree = ast.parse(_SCRIPT.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    forbidden = {
        "latent_landscapes.adjusted_background_likelihood",
        "latent_landscapes.preinvasion_likelihood",
        "latent_landscapes.preinvasion_fitting",
        "latent_landscapes.capstone_public",
        "latent_landscapes.capstone_qualification",
        "latent_landscapes.capstone_calibration",
    }
    assert not imported.intersection(forbidden)
