from __future__ import annotations

# ruff: noqa: E501
import json
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes import preinvasion_effect_reference as effect
from latent_landscapes import preinvasion_fitting as fitting

MECHANICAL_ROOT = 987654321


def test_coarse_nodes_have_registered_ids_and_order() -> None:
    nodes = effect.node_specs()
    assert tuple(n.coarse_id for n in nodes) == (382, 0, 764, 44)
    assert tuple((n.beta, n.mu, n.detection_sd) for n in nodes) == (
        (0.0, 0.0025, 0.2), (-2.0, 0.0005, 0.0), (2.0, 0.006, 0.4), (-2.0, 0.006, 0.4)
    )
    assert effect.BETA_GRID.size == 17
    assert effect.MU_GRID.tolist() == [0.0005, 0.001, 0.0016, 0.002, 0.0025, 0.0032, 0.004, 0.005, 0.006]
    assert len(effect.full_grid_metadata()) == 765


def test_seed_address_is_order_independent_and_exact() -> None:
    a = effect.reference_seeds(382, 23, root=MECHANICAL_ROOT)
    b = effect.reference_seeds(382, 23, root=MECHANICAL_ROOT)
    assert a == b
    expected = int(np.random.SeedSequence([MECHANICAL_ROOT, 58, 382, 23, 1]).generate_state(1, dtype=np.uint64)[0])
    assert a["streams"]["spread"] == expected
    assert effect.reference_seeds(0, 23, root=MECHANICAL_ROOT) != a


def test_ledger_validates_complete_addresses() -> None:
    ledger = effect.seed_ledger(root=MECHANICAL_ROOT, nodes=effect.node_specs()[:1], references=2)
    meta = effect.validate_seed_ledger(ledger, root=MECHANICAL_ROOT, nodes=effect.node_specs()[:1], references=2)
    assert tuple(meta["shape"]) == (2, 5)
    bad = ledger.copy()
    bad[0, 3] += 1
    with pytest.raises(ValueError, match="address law"):
        effect.validate_seed_ledger(bad, root=MECHANICAL_ROOT, nodes=effect.node_specs()[:1], references=2)


def test_worker_address_schedule_is_complete_and_ordered() -> None:
    tasks = effect._tasks(MECHANICAL_ROOT, 3)
    assert len(tasks) == 12
    assert [(task[0].coarse_id, task[1]) for task in tasks[:5]] == [(382, 0), (382, 1), (382, 2), (0, 0), (0, 1)]
    assert len({(node.coarse_id, ref) for node, ref, _root in tasks}) == len(tasks)


def test_mechanical_generation_prepares_full_history_without_registered_stream() -> None:
    fixed, setup = effect.campaign.public_inputs()
    # Generation is exercised with the qualification root only; no bank or fit
    # is loaded by this regression test.
    context = type("Context", (), {"fixed": fixed, "setup": setup})()
    raw, evaluator, _timing = effect.generate_reference(context, effect.node_specs()[0], 0, root=MECHANICAL_ROOT)
    assert np.asarray(raw["prey_counts"]).shape == (160, 13)
    assert np.asarray(raw["predator_counts"]).shape == (160, 6)
    assert evaluator["seed_ids"]["root"] == MECHANICAL_ROOT


def test_shared_loader_preserves_casewise_ranks_and_checks_union_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from latent_landscapes.preinvasion_calibration import (
        ScreenResult,
        combine_casewise_effect_tests,
    )
    from latent_landscapes.preinvasion_effect_gate import plan_effect_references

    screens = tuple(ScreenResult(name, "ready", (node,), None) for name, node in
                    (("A", 0), ("shared", 0), ("invalid", 44), ("missing", 764)))
    plan = plan_effect_references(screens, max_union_candidates=3)
    refs = np.zeros(999)
    refs[:39] = 1.0
    np.savez(tmp_path / "node-0000.npz", T=refs, valid=np.ones(999, dtype=bool), usable=np.asarray(True))
    invalid = np.ones(999, dtype=bool)
    invalid[998] = False
    np.savez(tmp_path / "node-0044.npz", T=refs, valid=invalid, usable=np.asarray(False))
    loaded = effect.load_effect_reference_tables(tmp_path, plan)
    assert loaded.status == "ready"
    assert set(loaded.tables) == {0, 44}
    result = combine_casewise_effect_tests(screens, [1.0] * 4, loaded.tables, max_candidates=765)
    assert [item.status for item in result.decisions] == ["declared", "declared", "abstain_no_fit", "abstain_missing_effect_table"]
    assert [item.p_value for item in result.decisions] == pytest.approx([.05, .05, 1., 1.])
    over = plan_effect_references(screens, max_union_candidates=2)
    def no_load(*args, **kwargs):
        raise AssertionError("over-cap union must not open a table")
    monkeypatch.setattr(effect.np, "load", no_load)
    assert effect.load_effect_reference_tables(tmp_path, over).status == "abstain_over_cap"


def test_jsonable_replaces_nonfinite_with_null() -> None:
    value = effect.jsonable({"nan": float("nan"), "inf": float("inf"), "x": np.float64(2.0)})
    assert value == {"nan": None, "inf": None, "x": 2.0}
    json.dumps(value, allow_nan=False)


def test_fit_pair_preserves_invalid_nesting_without_clamping() -> None:
    class Data:
        truth_beta = 0.0
        truth_mu = 0.001
        truth_sd = 0.0

    class Result:
        def __init__(self, model: str, ll: float, ok: bool = True) -> None:
            self.model = model
            self.h = 1.0
            self.beta = 0.0
            self.mu = 0.001
            self.detection_sd = 0.0
            self.raw_logjoint = ll
            self.numerical_status = "converged" if ok else "failed"
            self.nfev = 1
            self.elapsed_seconds = 0.0
            self.starts = ()
            self.objective_gap = 0.0
            self.boundary_flags = ()
            self.warnings = ()

        @property
        def parameters(self):
            return {"h": self.h, "beta": self.beta, "mu": self.mu, "detection_sd": self.detection_sd}

        @property
        def converged(self):
            return self.numerical_status == "converged"

    calls = iter((Result("adjusted_h1", 4.0), Result("adjusted_free_h", 3.0)))
    old = fitting._run_fit
    fitting._run_fit = lambda *args, **kwargs: next(calls)  # type: ignore[assignment]
    try:
        pair = effect.fit_effect_pair_with_truth(Data(), lambda *_a, **_k: 2.0, {"beta": 0.0, "mu": 0.001, "detection_sd": 0.0})
    finally:
        fitting._run_fit = old
    assert pair.statistics["T"] == 0.0
    assert pair.statistics["valid"] is False
    assert pair.statistics["free_ge_null"] is False


def test_fit_pair_uses_the_adjusted_pair_from_four_model_contract() -> None:
    class Data:
        pass

    def callback(_data, *, h, beta, mu, detection_sd):
        return -((h - 1.5) ** 2 + (beta - 0.2) ** 2 + (mu - 0.002) ** 2 + detection_sd**2)

    old = fitting._run_fit
    calls = []

    def wrapped(*args, **kwargs):
        result = old(*args, **kwargs)
        calls.append(result.model)
        return result

    fitting._run_fit = wrapped  # type: ignore[assignment]
    try:
        pair = effect.fit_effect_pair(Data(), callback)
    finally:
        fitting._run_fit = old
    assert calls == ["adjusted_h1", "adjusted_free_h"]
    assert pair.null_fit.model == "adjusted_h1"
    assert pair.free_fit.model == "adjusted_free_h"


def test_checkpoint_schema(tmp_path: Path) -> None:
    node = effect.node_specs()[0]
    class Fit:
        model = "adjusted_h1"
        h = beta = mu = detection_sd = 0.0
        raw_logjoint = 1.0
        numerical_status = "converged"
        nfev = 1
        elapsed_seconds = 0.0
        starts = ()
        objective_gap = 0.0
        boundary_flags = ()
        warnings = ()
        @property
        def parameters(self): return {"h": 1.0, "beta": 0.0, "mu": .001, "detection_sd": 0.0}
        @property
        def converged(self): return True
    pair = effect.EffectFitBatch(Fit(), Fit(), 1.0, {"T": 0.0, "valid": True})
    raw = {"opaque_id": "x", "prey_counts": np.zeros((160, 13), dtype=np.int8), "predator_counts": np.zeros((160, 6), dtype=np.int8)}
    ev = {"truth": {"beta": 0.0}, "seed_ids": effect.reference_seeds(node.coarse_id, 0, root=MECHANICAL_ROOT), "arrival": np.zeros(160), "loss": np.zeros(160), "site_hazard": np.zeros(160), "site_detection": np.zeros(160), "prey_alive": np.zeros((160, 13), dtype=bool)}
    payload = effect.row_payload(node, 0, raw, ev, pair, {})
    effect.checkpoint_history(tmp_path / "x.npz", raw, ev, payload)
    assert (tmp_path / "x.npz").exists()
    assert json.loads((tmp_path / "x.json").read_text())["node_id"] == node.coarse_id
