"""Workflow guards, using mechanical fixtures without scientific fitting."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_final_procedure_evaluation as runner


@pytest.fixture
def staged(tmp_path, monkeypatch):
    counts = {"fit": 0, "generate": 0, "diagnose": 0}
    observations = {name: np.array([1, 2]) for name in runner.OBSERVATION_KEYS}
    evaluator = {name: np.array([1.0, 2.0]) for name in runner.EVALUATOR_KEYS}
    evaluator.update(truth={"background": "exact"}, seeds={"root": 987654321})
    main = {
        "fits": {"adjusted_free_h": {"raw_logjoint": -2.0}},
        "observed_effect_statistic": 0.0,
    }

    def generate(*args, **kwargs):
        counts["generate"] += 1
        assert kwargs["root"] == 987654321
        return observations, evaluator

    def fit(*args, output, **kwargs):
        counts["fit"] += 1
        runner.immutable_json(output, main)
        return main

    def diagnose(*args):
        counts["diagnose"] += 1
        return {"test_fixture": True}

    monkeypatch.setattr(runner, "_CONTEXT", SimpleNamespace(public=None, bank=None))
    monkeypatch.setattr(runner, "_RESOURCES", None)
    monkeypatch.setattr(runner.evaluation, "generate_history", generate)
    monkeypatch.setattr(runner.evaluation, "fit_main", fit)
    monkeypatch.setattr(runner.evaluation, "diagnose_main", diagnose)
    monkeypatch.setattr(
        runner.evaluation,
        "make_observation_data",
        lambda *args: SimpleNamespace(training=None, holdout=None),
    )
    monkeypatch.setattr(runner.evaluation, "pre_surface", lambda *args: np.zeros(765))
    for name in ("audit_history_inputs", "audit_history_main", "audit_history_diagnostics"):
        monkeypatch.setattr(
            runner.audit, name, lambda *args: {"passed": True, "release_blocked": False}
        )
    task = (str(tmp_path), "benchmark", 0, 0, "main", "a" * 64)
    directory = tmp_path / "benchmark/evaluation/cell-00/rep-000"
    return task, directory, counts


def test_resume_never_replaces_completed_main(staged):
    task, directory, counts = staged
    receipt = runner._history_worker(task)
    assert receipt["passed"] and counts == {"fit": 1, "generate": 1, "diagnose": 0}
    assert runner._history_worker(task) == receipt
    assert counts == {"fit": 1, "generate": 1, "diagnose": 0}
    (directory / "main-complete.json").unlink()
    runner._history_worker(task)
    assert counts == {"fit": 1, "generate": 1, "diagnose": 0}
    (directory / "main.json").write_text("{}\n")
    with pytest.raises(ValueError, match="checksum"):
        runner._history_worker(task)


def test_history_identity_and_phase_guards(staged):
    task, directory, _ = staged
    runner._history_worker(task)
    with pytest.raises(ValueError, match="declarations"):
        runner._history_worker((*task[:4], "diagnostics", task[5]))
    (directory / "main-complete.json").unlink()
    metadata = runner.read(directory / "evaluator.json")
    metadata["seeds"]["root"] = 2026101101
    runner.write(directory / "evaluator.json", metadata)
    inputs = runner.read(directory / "inputs-complete.json")
    inputs["files"] = runner.hashes(directory, list(inputs["files"]))
    runner.write(directory / "inputs-complete.json", inputs)
    with pytest.raises(ValueError, match="evaluation address"):
        runner._history_worker(task)


def test_failed_independent_audit_stops_before_fitting(staged, monkeypatch):
    task, directory, counts = staged
    monkeypatch.setattr(
        runner.audit,
        "audit_history_inputs",
        lambda *args: {"passed": False, "release_blocked": True},
    )
    with pytest.raises(ValueError, match="blocked release"):
        runner._history_worker(task)
    assert counts["fit"] == 0
    assert not (directory / "main-complete.json").exists()
    assert runner.read(directory / "inputs-audit.json")["release_blocked"]


def test_production_requires_supervisor_and_runtime_approval(tmp_path, monkeypatch):
    monkeypatch.delenv("GOAL062_SUPERVISOR_PID", raising=False)
    with pytest.raises(ValueError, match="supervisor"):
        runner.production(tmp_path, 51)
    import qualify_final_procedure_evaluation as qualify

    runtime = {"test_runtime": "changed"}
    monkeypatch.setattr(qualify, "runtime_record", lambda: runtime)
    runner.write(tmp_path / "source-manifest.json", {"test": True})
    binding = runner.references.sha256(tmp_path / "source-manifest.json")
    receipt = {
        "passed": True,
        "binding_sha256": binding,
        "runtime_sha256": runner.audit.canonical_sha256(runtime),
        "runtime_changed": True,
        "files": {},
    }
    runner.write(tmp_path / "benchmark/qualification.json", receipt)
    with pytest.raises(FileNotFoundError):
        runner.require_production_approval(tmp_path)
    approval = {
        "approved": True,
        "binding_sha256": binding,
        "runtime_sha256": receipt["runtime_sha256"],
        "qualification_sha256": runner.references.sha256(tmp_path / "benchmark/qualification.json"),
    }
    runner.write(tmp_path / "production-runtime-approval.json", approval)
    assert runner.require_production_approval(tmp_path) == receipt
    monkeypatch.setattr(qualify, "runtime_record", lambda: {"test_runtime": "drifted"})
    with pytest.raises(ValueError, match="runtime differs"):
        runner.require_production_approval(tmp_path)


def test_immutable_arrays_reject_changed_payload(tmp_path):
    path = tmp_path / "arrays.npz"
    arrays = {"ids": np.array(["one", "two"]), "float": np.array([np.nan, 2.0])}
    runner.save_arrays(path, arrays)
    runner.save_arrays(path, arrays)
    with pytest.raises(ValueError, match="immutable arrays"):
        runner.save_arrays(path, {**arrays, "float": np.array([np.nan, 3.0])})


def test_diagnostic_selection_preserves_fixed_set_and_first_failures(tmp_path):
    receipts = []
    for rep, status in [(9, False), (6, False), (1, True)]:
        directory = tmp_path / str(rep)
        runner.write(
            directory / "main.json",
            {
                "fits": {"x": {"raw_logjoint": -2.0}},
                "main_statuses_converged": {"x": status},
                "nesting_status": {"x": "passed"},
                "all_main_replays_passed": True,
            },
        )
        receipts.append({"cell": 3, "replicate": rep, "path": str(directory)})
    selected, provenance = runner.select_diagnostics(receipts)
    assert len(selected) == 51
    assert (3, 6) in selected and (3, 9) not in selected
    assert provenance["selected_examples"] == {"cell-03/nonconvergence": (3, 6)}


def test_checkpoint_refuses_relabelled_phase(staged):
    task, directory, _ = staged
    runner._history_worker(task)
    path = directory / "main-complete.json"
    receipt = json.loads(path.read_text())
    receipt["phase"] = "production"
    runner.write(path, receipt)
    with pytest.raises(ValueError, match="stale main"):
        runner._history_worker(task)


def test_summary_publishes_into_history_directory_and_resumes_immutably(tmp_path):
    from summarize_final_procedure_evaluation import write_summary

    directory = tmp_path / "summary"
    runner.immutable_json(directory / "histories.json", [{"test_fixture": True}])
    result = {"cells": [], "between_cell_contrasts": []}
    runner.publish_summary(result, directory, write_summary)
    assert runner.read(directory / "summary.json") == result
    assert (directory / "cell_summary.csv").is_file()
    runner.publish_summary(result, directory, write_summary)
    with pytest.raises(ValueError, match="differs from persisted"):
        runner.publish_summary({**result, "changed": True}, directory, write_summary)
    assert runner.read(directory / "histories.json") == [{"test_fixture": True}]


def test_complete_seed_ledgers_are_frozen_before_generation(tmp_path):
    receipt = runner.freeze_seed_ledgers(tmp_path, "a" * 64)
    evaluation = runner.read(tmp_path / "production/seed-ledger.json")
    bootstrap = runner.read(tmp_path / "production/bootstrap-seed-ledger.json")
    assert len(evaluation) == 27000 and len(bootstrap) == 20000
    assert len({row["seed"] for row in evaluation + bootstrap}) == 47000
    assert {row["address"][2] for row in evaluation} == {1}
    assert {row["address"][2] for row in bootstrap} == {2}
    assert runner.freeze_seed_ledgers(tmp_path, "a" * 64) == receipt
    assert not (tmp_path / "production/evaluation").exists()
