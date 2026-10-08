from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import sys
from concurrent.futures import Future
from pathlib import Path
from typing import Any

import numpy as np
from pytest import MonkeyPatch

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_preinvasion_effect_reference.py"
sys.path.insert(0, str(_SCRIPT.parent))
_SPEC = importlib.util.spec_from_file_location("audit_preinvasion_effect_reference", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
audit = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = audit
_SPEC.loader.exec_module(audit)
DirectBank = audit.DirectBank
MECHANICAL_ROOT = 987654321


def _context() -> audit.AuditContext:
    return audit.AuditContext(
        tuple(f"site-{index:03d}" for index in range(160)),
        np.asarray([True] * 120 + [False] * 40),
        np.zeros((72, 84), dtype=np.float64),
        np.zeros(160, dtype=np.float64),
    )


def _bank(context: audit.AuditContext) -> DirectBank:
    arrivals = tuple(np.asarray([5.0 + 10.0 * category]) for category in range(7))
    values = tuple(arrivals for _ in context.site_ids)
    masses = np.full((160, 7), 1.0 / 7.0, dtype=np.float64)
    return DirectBank(context.site_ids, 7, 14, values, masses)


def _arrays(node_id: int = 382, reference: int = 0) -> dict[str, np.ndarray[Any, Any]]:
    truth = audit.NODE_TRUTHS[node_id]
    prey = np.zeros((160, 13), dtype=np.int8)
    predator = np.zeros((160, 6), dtype=np.int8)
    streams = audit.expected_streams(node_id, reference, root=MECHANICAL_ROOT)
    return {
        "prey_counts": prey,
        "predator_counts": predator,
        "arrival": np.zeros(160, dtype=np.float64),
        "loss": np.full(160, 100.0, dtype=np.float64),
        "site_hazard": np.full(160, truth["mu"], dtype=np.float64),
        "site_detection": np.full(160, 0.65, dtype=np.float64),
        "prey_alive": np.ones((160, 13), dtype=bool),
        "seed_ids": np.asarray([streams[name] for name in audit.STREAM_NAMES], dtype=np.uint64),
    }


def _row(
    context: audit.AuditContext,
    bank: DirectBank,
    arrays: dict[str, np.ndarray[Any, Any]],
    *,
    node_id: int = 382,
    reference: int = 0,
) -> dict[str, Any]:
    truth = audit.NODE_TRUTHS[node_id]
    score, _ = audit.independent_training_score(
        bank,
        context,
        arrays["prey_counts"].astype(np.int64),
        arrays["predator_counts"].astype(np.int64),
        truth,
    )
    parameters = dict(truth)
    fit = {
        "model": "adjusted_h1",
        **parameters,
        "raw_logjoint": score,
        "numerical_status": "converged",
        "starts": [],
        "nfev": 1,
        "boundary_flags": [],
    }
    prey = arrays["prey_counts"]
    predator = arrays["predator_counts"]
    opaque = hashlib.sha256(predator.tobytes() + prey.tobytes()).hexdigest()
    return {
        "schema_version": audit.SCHEMA_VERSION,
        "node_id": node_id,
        "reference": reference,
        "truth": {
            "index": reference,
            "effect": truth["h"],
            "beta": truth["beta"],
            "mean_hazard": truth["mu"],
            "detection_sd": truth["detection_sd"],
        },
        "seed_ids": {
            "root": MECHANICAL_ROOT,
            "namespace": audit.SEED_NAMESPACE,
            "coarse_node": node_id,
            "reference": reference,
            "streams": audit.expected_streams(node_id, reference, root=MECHANICAL_ROOT),
        },
        "observations": {"opaque_id": opaque},
        "null_fit": fit,
        "free_fit": {**fit, "model": "adjusted_free_h"},
        "statistics": {"truth_logjoint": score, "T": 0.0, "valid": True},
        "error": None,
    }


def test_seed_ledger_reconstructs_every_stage_address(tmp_path: Path) -> None:
    expected = audit.expected_ledger(root=987654321, references=2)
    assert expected.shape == (4 * 2, 5)
    assert len({tuple(row) for row in expected}) == len(expected)
    path = tmp_path / "seed_ledger.npz"
    np.savez_compressed(path, ledger=expected)
    assert audit.validate_ledger(path, root=987654321, references=2)["passed"]

    corrupted = expected.copy()
    corrupted[-1, 3] += 1
    np.savez_compressed(path, ledger=corrupted)
    assert not audit.validate_ledger(path, root=987654321, references=2)["passed"]


def test_cli_accepts_bounded_mechanical_root_and_reference_count() -> None:
    args = audit.parse_args(
        [
            "--run",
            "run",
            "--bank-path",
            "bank.npy",
            "--qualification",
            "qualification.json",
            "--registration",
            "registration.md",
            "--source-freeze",
            "source-manifest.json",
            "--freeze",
            "freeze",
            "--output",
            "audit",
            "--root",
            "987654321",
            "--references",
            "2",
        ]
    )
    assert args.root == 987654321
    assert args.references == 2
    assert not args.replay_generators


def test_mechanical_table_loader_uses_root_T_schema(tmp_path: Path) -> None:
    rows = [
        {"audit_valid": True, "statistic": {"direct": 0.0}},
        {"audit_valid": False, "statistic": {"direct": 1.5}},
    ]
    np.savez_compressed(
        tmp_path / "node-0382.npz",
        node_id=np.asarray(382),
        reference=np.arange(2),
        T=np.asarray([0.0, 1.5]),
        valid=np.asarray([True, False]),
        usable=np.asarray(False),
        null_raw_logjoint=np.asarray([2.0, 3.0]),
        free_raw_logjoint=np.asarray([2.0, 3.75]),
    )
    rows[0]["points"] = {"null": {"direct": 2.0}, "free": {"direct": 2.0}}
    rows[1]["points"] = {"null": {"direct": 3.0}, "free": {"direct": 3.75}}
    result = audit.validate_node_table(tmp_path, 382, rows, references=2)
    assert result["passed"]
    assert not result["usable"]
    assert result["invalid"] == 1


def test_independent_row_audit_passes_true_null_and_free_points() -> None:
    context = _context()
    bank = _bank(context)
    arrays = _arrays()
    row = _row(context, bank, arrays)
    result = audit.audit_row(
        row,
        arrays,
        bank,
        context,
        node_id=382,
        reference=0,
        root=MECHANICAL_ROOT,
    )
    assert result["audit_consistent"]
    assert result["audit_valid"]
    assert result["statistic"]["null_ge_truth"]
    assert result["statistic"]["free_ge_null"]
    assert all(point["absolute_difference"] == 0.0 for point in result["points"].values())


def test_score_mismatch_is_campaign_safety_failure() -> None:
    context = _context()
    bank = _bank(context)
    arrays = _arrays()
    row = _row(context, bank, arrays)
    row["free_fit"]["raw_logjoint"] += 2e-8
    result = audit.audit_row(
        row,
        arrays,
        bank,
        context,
        node_id=382,
        reference=0,
        root=MECHANICAL_ROOT,
    )
    assert result["score_mismatch"]
    assert not result["audit_consistent"]
    assert not result["audit_valid"]


def test_retained_optimizer_failure_can_be_audit_consistent() -> None:
    context = _context()
    bank = _bank(context)
    arrays = _arrays()
    row = _row(context, bank, arrays)
    row["free_fit"]["numerical_status"] = "optimizer_failed"
    row["statistics"]["valid"] = False
    result = audit.audit_row(
        row,
        arrays,
        bank,
        context,
        node_id=382,
        reference=0,
        root=MECHANICAL_ROOT,
    )
    assert result["audit_consistent"]
    assert not result["audit_valid"]
    assert not result["score_mismatch"]


def test_explicit_nonfinite_optimizer_failure_is_retained_without_scoring_point() -> None:
    context = _context()
    bank = _bank(context)
    arrays = _arrays()
    row = _row(context, bank, arrays)
    row["free_fit"].update(
        {
            "h": None,
            "beta": None,
            "mu": None,
            "detection_sd": None,
            "raw_logjoint": None,
            "numerical_status": "optimizer_failed",
        }
    )
    row["statistics"].update({"T": None, "valid": False})
    result = audit.audit_row(
        row,
        arrays,
        bank,
        context,
        node_id=382,
        reference=0,
        root=MECHANICAL_ROOT,
    )
    assert result["audit_consistent"]
    assert not result["audit_valid"]
    assert not result["points"]["free"]["parameters_available"]


def test_latent_and_seed_corruption_invalidate_reference() -> None:
    context = _context()
    bank = _bank(context)
    arrays = _arrays()
    row = _row(context, bank, arrays)
    corrupted = copy.deepcopy(arrays)
    corrupted["site_hazard"][3] *= 1.01
    corrupted["seed_ids"][0] += 1
    result = audit.audit_row(
        row,
        corrupted,
        bank,
        context,
        node_id=382,
        reference=0,
        root=MECHANICAL_ROOT,
    )
    assert not result["latent_check"]["passed"]
    assert not result["seed_array_matches"]
    assert not result["audit_consistent"]
    assert not result["audit_valid"]


def test_auditor_does_not_import_production_likelihood_or_effect_module() -> None:
    source = Path(audit.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    assert "latent_landscapes.preinvasion_likelihood" not in imported
    assert "latent_landscapes.preinvasion_execution" not in imported
    assert "latent_landscapes.preinvasion_effect_reference" not in imported


def test_row_safety_stop_preserves_partial_summary(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text(
        '{"ledger_sha256":"ledger"}\n', encoding="utf-8"
    )
    qualification = tmp_path / "qualification.json"
    qualification.write_text(
        '{"bank_receipt":{"bank_file_sha256":"abc"}}\n', encoding="utf-8"
    )

    class FailingExecutor:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def submit(self, *args: Any, **kwargs: Any) -> Future[dict[str, Any]]:
            future: Future[dict[str, Any]] = Future()
            future.set_exception(RuntimeError("synthetic worker failure"))
            return future

        def shutdown(self, *args: Any, **kwargs: Any) -> None:
            pass

    monkeypatch.setattr(audit, "verify_provenance", lambda *args, **kwargs: {"passed": True})
    monkeypatch.setattr(audit, "load_context", lambda path: _context())
    monkeypatch.setattr(
        audit,
        "validate_ledger",
        lambda *args, **kwargs: {"passed": True, "sha256": "ledger"},
    )
    monkeypatch.setattr(audit, "ProcessPoolExecutor", FailingExecutor)

    output = tmp_path / "audit"
    result = audit.run_audit(
        run=run,
        bank_path=tmp_path / "bank.npy",
        qualification=qualification,
        registration=tmp_path / "registration.md",
        source_freeze=tmp_path / "source-manifest.json",
        freeze=tmp_path / "freeze",
        output=output,
        workers=1,
        generator_replays=False,
        root=MECHANICAL_ROOT,
        references=1,
    )

    assert result["campaign_safety_failure"]
    assert result["rows_audited"] == 1
    assert result["nodes"] == []
    assert "worker_error" in (output / "independent-audit-rows.jsonl").read_text()
    assert (output / "independent-audit.json").is_file()
