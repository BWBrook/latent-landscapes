from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from latent_landscapes import final_procedure_evaluation as producer

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "qualify_final_procedure_evaluation.py"
)
SPEC = importlib.util.spec_from_file_location("qualify_final_procedure_evaluation", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
qualification = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = qualification
SPEC.loader.exec_module(qualification)


def _runtime(
    platform_value: str = "Linux-6.8.0-142-generic-x86_64-with-glibc2.39",
) -> dict[str, Any]:
    return {
        "bit_generator": "PCG64",
        "numpy_version": "2.5.1",
        "platform": platform_value,
        "python_version": "3.14.5",
        "scipy_version": "1.18.0",
        "sys_version": "3.14.5 frozen",
        "thread_environment": {name: "1" for name in qualification.THREAD_VARIABLES},
        "baseline_binary_hashes_available": False,
    }


def test_runtime_record_hashes_current_executable_extensions_and_numeric_configs() -> None:
    row = qualification.runtime_record()
    assert set(qualification.CORE_RUNTIME_KEYS).issubset(row)
    assert row["bit_generator"] == "PCG64"
    assert len(row["python_executable"]["sha256"]) == 64
    assert set(row["numeric_extensions"]) == {
        "numpy._core._multiarray_umath",
        "numpy.linalg._umath_linalg",
        "numpy.random._pcg64",
        "scipy.optimize._lbfgsb",
        "scipy.special._ufuncs",
    }
    assert all(len(value["sha256"]) == 64 for value in row["numeric_extensions"].values())
    assert set(row["numerical_configuration"]) == {"numpy", "scipy"}
    assert row["baseline_binary_hashes_available"] is False
    assert "not established" in row["binary_identity_claim"]


def test_kernel_only_drift_is_compatible_but_requires_review() -> None:
    baseline = _runtime()
    observed = _runtime("Linux-6.8.0-146-generic-x86_64-with-glibc2.39")
    result = qualification.compare_runtime(observed, baseline)
    assert result["passed"]
    assert result["kernel_only_difference"]
    assert result["runtime_changed"]
    assert result["production_runtime_review_required"]
    assert not result["prior_binary_identity_verified"]


def test_version_or_thread_drift_fails_runtime_qualification() -> None:
    baseline = _runtime()
    observed = _runtime()
    observed["numpy_version"] = "2.5.2"
    assert not qualification.compare_runtime(observed, baseline)["passed"]
    observed = _runtime()
    observed["thread_environment"]["OMP_NUM_THREADS"] = "2"
    assert not qualification.compare_runtime(observed, baseline)["passed"]


def test_mechanical_test_gate_binds_frozen_sources_command_and_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    hashes = {}
    for relative in qualification.MECHANICAL_TEST_FILES:
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {relative}\n", encoding="utf-8")
        hashes[relative] = qualification.sha256_file(path)
    (tmp_path / "benchmark").mkdir()
    observed: dict[str, Any] = {}

    def fake_run(command: list[str], **kwargs: Any) -> SimpleNamespace:
        observed.update(command=command, **kwargs)
        kwargs["stdout"].write("42 passed in 1.00s\n")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(qualification.subprocess, "run", fake_run)
    result = qualification.qualify_mechanical_tests(
        tmp_path, {"source_hashes": hashes}, "a" * 64
    )
    assert result["passed"]
    assert result["exit_code"] == 0
    assert result["source_manifest_sha256"] == "a" * 64
    assert result["test_source_hashes"] == hashes
    assert result["test_source_set_sha256"] == qualification.canonical_sha256(hashes)
    assert result["log_sha256"] == qualification.sha256_file(
        tmp_path / "benchmark/mechanical-tests.log"
    )
    assert observed["command"] == [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        *qualification.MECHANICAL_TEST_FILES,
        "-p",
        "no:cacheprovider",
    ]
    assert observed["cwd"] == source
    assert observed["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    assert observed["check"] is False


def test_reused_reference_audits_use_bounded_parallelism_and_stable_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    observed: dict[str, Any] = {"tasks": []}

    class Future:
        def __init__(self, row: dict[str, Any]) -> None:
            self.row = row

        def result(self) -> dict[str, Any]:
            return self.row

    class Executor:
        def __init__(self, *, max_workers: int, mp_context: Any) -> None:
            observed.update(max_workers=max_workers, mp_context=mp_context)

        def __enter__(self) -> Executor:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def submit(self, function: Any, task: tuple[Any, ...]) -> Future:
            observed["tasks"].append((function, task))
            kind, node = str(task[3]), int(task[4])
            return Future(
                {
                    "kind": kind,
                    "node": node,
                    "passed": True,
                    "release_blocked": False,
                    "accepted_comparison_passed": True,
                    "completed": 999 if kind == "effect" else 99,
                    "generator_replays": 3 if kind == "effect" else 99,
                }
            )

    monkeypatch.setattr(qualification, "ProcessPoolExecutor", Executor)
    monkeypatch.setattr(qualification, "as_completed", lambda futures: reversed(futures))
    result = qualification.qualify_reused_references(
        tmp_path,
        {
            "qualified_package": "/qualified",
            "prior_reference_root": "/prior",
            "original_binding": "c" * 64,
        },
        "b" * 64,
        workers=51,
    )
    assert result["passed"]
    assert observed["max_workers"] == 12
    assert len(observed["tasks"]) == 12
    assert [(row["kind"], row["node"]) for row in result["audits"]] == [
        *[("effect", node) for node in qualification.EFFECT_REUSE_NODES],
        *[("screen", node) for node in qualification.SCREEN_REUSE_NODES],
    ]
    progress = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [row["completed"] for row in progress] == list(range(1, 13))
    assert all(row["stage"] == "reused_reference_audits" for row in progress)


def test_synthetic_cache_is_full_shaped_tie_fixture_and_explicitly_nonproduction(
    tmp_path: Path,
) -> None:
    path = tmp_path / "synthetic.npz"
    metadata = qualification.synthetic_reference_cache(path, binding_sha256="a" * 64)
    assert metadata["scope"] == "mechanical-synthetic-only"
    assert metadata["npz_sha256"] == qualification.sha256_file(path)
    assert json.loads(path.with_suffix(".json").read_text()) == metadata
    with np.load(path, allow_pickle=False) as values:
        assert values["screen"].shape == (99, 765)
        assert values["effect"].shape == (765, 999)
        assert values["valid"].shape == (765,)
        assert values["screen_usable"].shape == (765,)
        assert len(np.unique(values["screen"][:, 0])) < 99
        result = producer.decide_cached(
            ["mechanical"],
            np.zeros((1, 765)),
            [0.0],
            values["screen"],
            values["effect"],
            values["valid"],
            computation_complete=True,
        )
    assert result["case_ids"] == ["mechanical"]
    assert result["computation_complete"]
    assert result["valid_effect_tables"] == 765


def test_budget_projection_counts_full_registered_workload() -> None:
    stages = {
        stage: [
            {"cell": cell, "replicate": 0, "elapsed_seconds": 1.0}
            for cell in range(10)
        ]
        for stage in ("main", "decision", "holdout")
    }
    stages["diagnostics"] = [
        {"cell": 1, "replicate": 0, "elapsed_seconds": 2.0},
        {"cell": 7, "replicate": 0, "elapsed_seconds": 3.0},
    ]
    references = [{"producer_elapsed_seconds": 1.0} for _ in range(3)]
    result = qualification.project_budget(stages, references, workers=10)
    assert result["production_histories"] == 5_000
    assert result["diagnostic_histories"] == 50
    assert result["new_effect_reference_fits"] == 465_534
    assert result["historical_reference_allowance_hours"] == [36.0, 40.0]
    assert result["passed"]


def test_concurrency_worker_scores_then_waits_at_task_barrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Gate:
        waits = 0

        def wait(self, timeout: int) -> None:
            assert timeout == 600
            self.waits += 1

    task_barrier = Gate()
    task_release = Gate()
    raw = {
        "prey_counts": np.zeros((160, 13), dtype=np.int8),
        "predator_counts": np.zeros((160, 6), dtype=np.int8),
    }
    training = SimpleNamespace(
        observations=object(),
        bank=object(),
        map_a=np.zeros((2, 2)),
        site_a=np.zeros(120),
    )
    producer_resources = SimpleNamespace(
        public=object(), bank=SimpleNamespace(bank_size=131_072)
    )
    independent_resources = SimpleNamespace(
        bank=object(), context=SimpleNamespace(site_ids=tuple(range(160)))
    )
    fake_evaluation = SimpleNamespace(
        generate_history=lambda *args, **kwargs: (raw, {}),
        make_observation_data=lambda *args, **kwargs: SimpleNamespace(training=training),
    )
    fake_likelihood = SimpleNamespace(
        point_score=lambda *args, **kwargs: SimpleNamespace(training_logjoint=-12.5)
    )
    fake_audit = SimpleNamespace(
        direct_point_score=lambda *args, **kwargs: {"training_logjoint": -12.5}
    )
    monkeypatch.setitem(
        sys.modules, "latent_landscapes.final_procedure_evaluation", fake_evaluation
    )
    monkeypatch.setitem(
        sys.modules, "latent_landscapes.preinvasion_likelihood", fake_likelihood
    )
    monkeypatch.setitem(sys.modules, "audit_final_procedure_evaluation", fake_audit)
    monkeypatch.setattr(
        qualification, "_PROBE_LOADED", (producer_resources, independent_resources)
    )
    monkeypatch.setattr(qualification, "_PROBE_PACKAGE", "/qualified")
    monkeypatch.setattr(qualification, "_PROBE_TASK_BARRIER", task_barrier)
    monkeypatch.setattr(qualification, "_PROBE_TASK_RELEASE", task_release)
    row = qualification._probe_worker(3)
    assert row["task"] == 3
    assert row["producer_bank_size"] == 131_072
    assert row["audit_sites"] == 160
    assert row["point_score_abs_difference"] == 0.0
    assert task_barrier.waits == 1
    assert task_release.waits == 1
    assert qualification._PROBE_WORKING is not None


def _fake_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    concurrency_passed: bool = True,
    mechanical_tests_passed: bool = True,
) -> None:
    binding = "b" * 64
    manifest = {
        "qualified_package": "/qualified",
        "prior_reference_root": "/prior",
        "original_binding": "c" * 64,
        "maximum_workers": 51,
        "rss_cap_bytes": qualification.RSS_CAP_BYTES,
        "qualification_wall_seconds": qualification.QUALIFICATION_CAP_SECONDS,
    }

    def run_history_stage(
        root: Path,
        *,
        phase: str,
        cases: list[tuple[int, int]],
        stage: str,
        workers: int,
        reference_cache_path: Path | None = None,
    ) -> list[dict[str, Any]]:
        assert phase == "benchmark"
        assert workers == 4
        if stage == "decision":
            assert reference_cache_path is not None
        rows = []
        for cell, replicate in cases:
            directory = root / "benchmark/evaluation" / f"cell-{cell:02d}" / f"rep-{replicate:03d}"
            directory.mkdir(parents=True, exist_ok=True)
            receipt = directory / f"{stage}-complete.json"
            receipt.write_text("{}\n", encoding="utf-8")
            rows.append(
                {
                    "cell": cell,
                    "replicate": replicate,
                    "stage": stage,
                    "elapsed_seconds": 0.001,
                    "path": str(receipt),
                    "passed": True,
                }
            )
        return rows

    fake_runner = SimpleNamespace(
        verify_custody=lambda root: (manifest, binding), run_history_stage=run_history_stage
    )
    monkeypatch.setitem(sys.modules, "run_final_procedure_evaluation", fake_runner)
    observed = _runtime()
    monkeypatch.setattr(qualification, "runtime_record", lambda: observed)
    monkeypatch.setattr(
        qualification,
        "qualify_mechanical_tests",
        lambda *args: {
            "passed": mechanical_tests_passed,
            "exit_code": 0 if mechanical_tests_passed else 1,
            "log": "benchmark/test.log",
        },
    )
    monkeypatch.setattr(
        qualification,
        "qualify_reused_references",
        lambda *args, **kwargs: {"passed": True, "audits": []},
    )
    monkeypatch.setattr(
        qualification,
        "qualify_mechanical_effect_references",
        lambda *args: {
            "passed": True,
            "audits": [
                {"producer_elapsed_seconds": 0.001, "passed": True} for _ in range(3)
            ],
        },
    )
    monkeypatch.setattr(
        qualification,
        "qualify_public_refits",
        lambda *args: {"passed": True, "histories_refit": 8},
    )
    monkeypatch.setattr(
        qualification,
        "qualify_concurrency",
        lambda manifest, workers: {
            "passed": concurrency_passed,
            "requested_workers": workers,
            "initialized_workers": workers if concurrency_passed else workers - 1,
        },
    )


def test_qualify_persists_bound_success_and_never_uses_production_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_dependencies(monkeypatch)
    (tmp_path / "original-runtime.json").write_text(json.dumps(_runtime()) + "\n")
    result = qualification.qualify(tmp_path, 4)
    saved = json.loads((tmp_path / "benchmark/qualification.json").read_text())
    assert result == saved
    assert result["passed"]
    assert result["qualified_workers"] == 4
    assert result["new_production_histories_generated"] == 0
    assert result["new_production_reference_rows_generated"] == 0
    assert result["production_execution"] is False
    assert result["production_authorized"] is True
    assert set(result["history_stage_checks"]) == {
        "main",
        "decision",
        "holdout",
        "diagnostics",
    }
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    starts = {row["stage"] for row in events if row["event"] == "stage_start"}
    completes = {row["stage"] for row in events if row["event"] == "stage_complete"}
    expected = {
        "custody",
        "mechanical_tests",
        "runtime",
        "reused_reference_audits",
        "mechanical_effect_references",
        "public_fixture_refits",
        "history_main",
        "history_decision",
        "history_holdout",
        "history_diagnostics",
        "budget_projection",
        "concurrency_memory",
    }
    assert starts == expected
    assert completes == expected
    assert events[-1]["event"] == "qualification_complete"
    assert events[-1]["passed"] is True


def test_qualify_fails_closed_when_requested_worker_count_is_not_observed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_dependencies(monkeypatch, concurrency_passed=False)
    (tmp_path / "original-runtime.json").write_text(json.dumps(_runtime()) + "\n")
    result = qualification.qualify(tmp_path, 4)
    assert not result["passed"]
    assert result["qualified_workers"] == 0
    assert result["state"] == "qualification_failed"
    assert result["production_authorized"] is False
    assert result["failure"]["type"] == "RuntimeError"
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    concurrency = [
        row
        for row in events
        if row["event"] == "stage_complete" and row["stage"] == "concurrency_memory"
    ]
    assert len(concurrency) == 1
    assert concurrency[0]["passed"] is False
    assert concurrency[0]["error_type"] == "RuntimeError"
    assert events[-1]["event"] == "qualification_failed"


def test_qualify_fails_closed_when_frozen_mechanical_tests_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_dependencies(monkeypatch, mechanical_tests_passed=False)
    result = qualification.qualify(tmp_path, 4)
    assert not result["passed"]
    assert result["qualified_workers"] == 0
    assert result["mechanical_tests"]["exit_code"] == 1
    assert result["state"] == "qualification_failed"
    assert result["failure"]["type"] == "RuntimeError"
    assert "pytest is unavailable" in result["failure"]["message"]
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    mechanical = [
        row
        for row in events
        if row["event"] == "stage_complete" and row["stage"] == "mechanical_tests"
    ]
    assert len(mechanical) == 1
    assert mechanical[0]["passed"] is False
    assert events[-1]["event"] == "qualification_failed"


def test_qualify_marks_kernel_change_pending_review_after_numerical_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_dependencies(monkeypatch)
    baseline = _runtime()
    observed = _runtime("Linux-6.8.0-146-generic-x86_64-with-glibc2.39")
    monkeypatch.setattr(qualification, "runtime_record", lambda: observed)
    (tmp_path / "original-runtime.json").write_text(json.dumps(baseline) + "\n")
    result = qualification.qualify(tmp_path, 4)
    assert result["passed"]
    assert result["state"] == "qualified_pending_runtime_review"
    assert result["production_runtime_review_required"]
    assert result["production_authorized"] is False


def test_existing_qualification_is_reused_only_with_unchanged_binding_and_files(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source-manifest.json"
    source.write_text("frozen\n", encoding="utf-8")
    evidence = tmp_path / "benchmark/evidence.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("{}\n", encoding="utf-8")
    receipt = {
        "schema": qualification.SCHEMA,
        "binding_sha256": qualification.sha256_file(source),
        "files": {"benchmark/evidence.json": qualification.sha256_file(evidence)},
    }
    (tmp_path / "benchmark/qualification.json").write_text(json.dumps(receipt) + "\n")
    assert qualification.qualify(tmp_path, 51) == receipt
    evidence.write_text('{"changed":true}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="evidence changed"):
        qualification.qualify(tmp_path, 51)
