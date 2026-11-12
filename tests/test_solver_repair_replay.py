from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import compare_solver_repair_replay as compare
import prepare_solver_repair_replay as prepare
from pbs import campaign


def value(criterion=0.0, eligible=True):
    return {
        "criterion": criterion,
        "eligible": eligible,
        "h": 1.0,
        "parameters": {"alpha": -5.5, "beta": 0.0, "detection_sd": 0.2},
    }


def receipts():
    endpoint = math.log(30.0)
    levels = [
        {
            "cutoff": c,
            "status": "available",
            "roots_log_h": [],
            "components": [{"lower_log_h": 0.0, "upper_log_h": endpoint}],
        }
        for c in compare.audit.fit.CUTOFF_GRID
    ]
    points = []
    for x, criterion in ((0.0, -1.0), (endpoint, -3.0)):
        points.append(
            {
                "log_h": x,
                "h": math.exp(x),
                "criterion": criterion,
                "positive_sigma": value(criterion),
                "sigma_zero": value(criterion - 1),
            }
        )
    spatial = {
        "free": {"criterion": 0.0, "h": 1.0, "positive_sigma": value(), "sigma_zero": value(-1.0)},
        "null": {"criterion": -1.0, "positive_sigma": value(-1.0), "sigma_zero": value(-2.0)},
        "lr1": 2.0,
        "profile": [{"log_h": p["log_h"], "criterion": p["criterion"]} for p in points],
        "level_sets": copy.deepcopy(levels),
    }
    reduced = {
        "status": "available",
        "free": {**value(), "h": math.e},
        "null": value(-1),
        "lr1": 2.0,
        "profile": [
            {"log_h": x, **value(y), "h": math.exp(x)} for x, y in ((0.0, -1.0), (endpoint, -3.0))
        ],
        "level_sets": copy.deepcopy(levels),
    }
    root = {
        "schema": "fit-dataset-v1",
        "failure_class": "resolved",
        "source": {"commit": prepare.FROZEN},
        "data_identity": {"sites": 10},
        "search_mode": "dense",
        "cutoffs": list(compare.audit.fit.CUTOFF_GRID),
        "tight_replay": "always_on_inside_PanelSearch.run",
        "inputs": {
            "input_dir": "/data/map",
            "observations": "/data/o.npz",
            "arrival_bank": "/data/a.npy",
            "compressed_bank": "/data/c.npz",
        },
        "input_sha256": {
            p: "a" * 64
            for p in (
                "/data/map/public_inputs.npz",
                "/data/map/exposure.npz",
                "/data/o.npz",
                "/data/a.npy",
                "/data/c.npz",
            )
        },
        "families": {
            "spatial": {
                "status": "available",
                "standard": copy.deepcopy(spatial),
                "tight": copy.deepcopy(spatial),
            },
            "exposure": copy.deepcopy(reduced),
            "constant": copy.deepcopy(reduced),
        },
    }
    return root, {"points": {"False": copy.deepcopy(points), "True": copy.deepcopy(points)}}


def test_selection_is_frozen_hash_order_with_two_per_stratum():
    rows = []
    roles = ("dense", "lean", "independent_bank", "exhaustive")
    for arm in "ABC":
        for role in roles:
            rows.extend(
                {"task_id": f"fit-case-{i:03d}-{arm}-{role}", "status": "resolved"}
                for i in range(34)
            )
    rows.extend({"task_id": f"fit-extra-{i}-A-dense", "status": "resolved"} for i in range(9))
    snapshot = {"completed": rows}
    selected = prepare.select_ids(snapshot)
    assert len(selected) == 24
    assert prepare.select_ids({"completed": list(reversed(rows))}) == selected
    for arm in "ABC":
        for role in roles:
            eligible = [r["task_id"] for r in rows if r["task_id"].endswith(f"-{arm}-{role}")]
            expected = sorted(
                eligible, key=lambda x: hashlib.sha256((prepare.SALT + x).encode()).hexdigest()
            )[:2]
            assert [s for s in selected if s.endswith(f"-{arm}-{role}")] == expected
    with pytest.raises(ValueError, match="417"):
        prepare.select_ids({"completed": rows[:-1]})


def test_exact_reference_and_free_candidate_are_distinct():
    root, search = receipts()
    assert compare.reference_at(root, search, "constant", 0.0)["kind"] == "stored_profile_row"
    assert compare.reference_at(root, search, "constant", 1.0)["kind"] == "free_candidate_at_own_h"
    with pytest.raises(ValueError, match="no exact"):
        compare.reference_at(root, search, "constant", 0.5)
    inventory = prepare.anchor_inventory(root)
    assert inventory["constant"]["required_anchor_count"] == 3
    assert inventory["constant"]["reference_kinds"][-1]["kind"] == "free_candidate_at_own_h"


def test_regression_comparison_checks_both_branches_and_no_interpolation():
    baseline, search = receipts()
    candidate = copy.deepcopy(baseline)
    probe = {
        "criterion": -1.0,
        "eligible": True,
        "fit": {"positive_sigma": value(-1.0), "sigma_zero": value(-1.999998)},
    }
    report = compare.compare_anchor(baseline, search, candidate, "spatial.standard", 0.0, probe)
    assert report["checks"][0]["failures"] == []
    assert report["checks"][2]["failures"] == ["criterion_shift"]
    probe["fit"]["sigma_zero"]["criterion"] = -2.0
    probe["fit"]["sigma_zero"]["eligible"] = False
    report = compare.compare_anchor(baseline, search, candidate, "spatial.standard", 0.0, probe)
    assert "eligibility_changed" in report["checks"][2]["failures"]
    shifted = compare.check_values("lr", {**value(), "w": 0}, {**value(), "w": 0.00101})
    assert shifted["failures"] == ["profile_lr_shift"]
    with pytest.raises(ValueError, match="boolean"):
        compare.check_values("elig", value(), value(eligible=1))


def test_data_change_is_not_misreported_as_numerical_regression():
    baseline, _ = receipts()
    candidate = copy.deepcopy(baseline)
    candidate["input_sha256"]["/data/a.npy"] = "b" * 64
    with pytest.raises(ValueError, match="input payload"):
        compare.check_data_identity(baseline, candidate)


def test_unresolved_candidate_is_nonregression_failure_without_invented_probes(
    tmp_path, monkeypatch
):
    baseline, search = receipts()
    candidate = copy.deepcopy(baseline)
    candidate["source"]["commit"] = "b" * 40
    candidate["failure_class"] = "family_fit_failed"
    paths = {}
    for name, data in (("baseline", baseline), ("search", search), ("candidate", candidate)):
        paths[name] = tmp_path / (name + ".json")
        paths[name].write_text(json.dumps(data))
    monkeypatch.setattr(compare, "imported_source_check", lambda _commit: None)
    monkeypatch.setattr(
        compare.audit, "Probe", lambda *_args: pytest.fail("unresolved candidate probed")
    )
    result = compare.run_probe(
        SimpleNamespace(
            baseline_receipt=paths["baseline"],
            baseline_sha256=campaign.sha256(paths["baseline"]),
            baseline_search=paths["search"],
            baseline_search_sha256=campaign.sha256(paths["search"]),
            candidate_receipt=paths["candidate"],
            candidate_sha256=campaign.sha256(paths["candidate"]),
            candidate_commit="b" * 40,
            output_dir=tmp_path / "out",
            checkpoint_dir=tmp_path / "cache",
        )
    )
    assert result["status"] == "nonregression_failure"
    assert result["failure"] == "candidate_fit_unresolved" and result["anchors"] == []


def test_probe_resume_restores_warm_start_state_and_rejects_identity_drift(tmp_path, monkeypatch):
    baseline, search = receipts()
    candidate = copy.deepcopy(baseline)
    candidate["source"]["commit"] = "b" * 40
    paths = {}
    for name, data in (("baseline", baseline), ("search", search), ("candidate", candidate)):
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(data))
        paths[name] = path
    evidence = SimpleNamespace(
        sha256=campaign.sha256(paths["candidate"]), verify_unchanged=lambda: None
    )
    monkeypatch.setattr(compare.audit.Evidence, "load", lambda _path: evidence)
    monkeypatch.setattr(compare, "imported_source_check", lambda _commit: None)
    stop_after = [2]

    class Probe:
        def __init__(self, _evidence, _output):
            self.search = SimpleNamespace(
                points={False: {}, True: {}}, criterion=SimpleNamespace(stats={})
            )
            self.reduced = {name: SimpleNamespace(points={}) for name in ("constant", "exposure")}
            self.calls = 0

        def evaluate(self, name, x, _budget):
            if stop_after[0] is not None and self.calls == stop_after[0]:
                raise OSError("simulated interruption")
            self.calls += 1
            preceding = sum(len(v) for v in self.search.points.values()) + sum(
                len(v.points) for v in self.reduced.values()
            )
            ref = compare.reference_at(baseline, search, name, x)
            delta = preceding * 1e-9
            raw = {
                "criterion": ref["criterion"] + delta,
                "eligible": ref["eligible"],
                "fit": copy.deepcopy(ref["fit"]),
                "preceding_points": preceding,
            }
            state = {"preceding_points": preceding, "parameters": {"alpha": -5.5}}
            if name.startswith("spatial."):
                for family in compare.audit.FAMILIES:
                    raw["fit"][family]["criterion"] += delta
                self.search.points[name == "spatial.tight"][x] = state
            else:
                self.reduced[name].points[x] = state
            return raw

    monkeypatch.setattr(compare.audit, "Probe", Probe)

    def arguments(out, cache):
        return SimpleNamespace(
            baseline_receipt=paths["baseline"],
            baseline_sha256=campaign.sha256(paths["baseline"]),
            baseline_search=paths["search"],
            baseline_search_sha256=campaign.sha256(paths["search"]),
            candidate_receipt=paths["candidate"],
            candidate_sha256=campaign.sha256(paths["candidate"]),
            candidate_commit="b" * 40,
            output_dir=tmp_path / out,
            checkpoint_dir=tmp_path / cache,
        )

    first = compare.run_probe(arguments("attempt-1", "cache"))
    assert first["status"] == "execution_error"
    stop_after[0] = None
    resumed = compare.run_probe(arguments("attempt-2", "cache"))
    fresh = compare.run_probe(arguments("fresh", "fresh-cache"))
    assert resumed["status"] == fresh["status"] == "passed"
    assert resumed["checkpoint_hits"] == 2
    assert resumed["anchors"] == fresh["anchors"]
    saved_path = next(p for p in (tmp_path / "cache").glob("*.json") if p.name != "identity.json")
    saved_original = saved_path.read_text()
    corrupted = json.loads(saved_original)
    corrupted["state"]["preceding_points"] = 999
    saved_path.write_text(json.dumps(corrupted))
    with pytest.raises(ValueError, match="payload hash"):
        compare.run_probe(arguments("corrupt-attempt", "cache"))
    saved_path.write_text(saved_original)
    identity = tmp_path / "cache/identity.json"
    data = json.loads(identity.read_text())
    data["source"] = "c" * 40
    identity.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="another frozen"):
        compare.run_probe(arguments("attempt-3", "cache"))


def test_fit_plan_preserves_old_data_runtime_flags_and_original_attempts(tmp_path):
    original_results = tmp_path / "original"
    sif = tmp_path / "runtime.sif"
    sif.write_bytes(b"image")
    runtime = {
        "context": "apptainer",
        "python": "/original/.venv/bin/python",
        "sif": str(sif),
        "sif_sha256": campaign.sha256(sif),
    }
    selection = {
        "schema": "solver-repair-replay-selection-v1",
        "nonregression": [],
        "development_failed": [],
    }
    before = {}
    for i in range(51):
        task_id = f"fit-case-{i:03d}-A-dense"
        directory = original_results / task_id
        attempt = directory / "attempt-0001/fit"
        attempt.mkdir(parents=True)
        receipt = attempt / "receipt.json"
        receipt.write_text("{}")
        task = {
            "task_id": task_id,
            "source_commit": prepare.FROZEN,
            "runtime": runtime,
            "argv": [
                runtime["python"],
                "scripts/fit_dataset.py",
                "--search",
                "dense",
                "--exhaustive-audit",
                "--output-dir",
                "{attempt_dir}/fit",
            ],
            "input_sha256": {str(sif): campaign.sha256(sif)},
            "result_path": "fit/receipt.json",
            "result_schema": "fit-dataset-v1",
        }
        record = {
            "task": task,
            "task_sha256": campaign.task_digest(task),
            "source": {"commit": prepare.FROZEN},
            "status": "resolved" if i < 24 else "scientific_failure",
            "attempt": "attempt-0001",
            "output_sha256": {"fit/receipt.json": campaign.sha256(receipt)},
        }
        path = directory / "_task.json"
        path.write_text(json.dumps(record))
        before[path] = campaign.sha256(path)
        row = {
            "task_id": task_id,
            "original_task_record_sha256": campaign.sha256(path),
            "baseline_receipt_sha256": campaign.sha256(receipt),
            "original_attempt": "attempt-0001",
        }
        selection["nonregression" if i < 24 else "development_failed"].append(row)
    selected_path = tmp_path / "selection.json"
    selected_path.write_text(json.dumps(selection))
    plan = prepare.prepare_fits(selected_path, original_results, "b" * 40, tmp_path / "plan")
    assert plan["groups"] == {"nonregression": 24, "development_failed": 27}
    for task in plan["tasks"]:
        assert task["runtime"] == runtime and task["source_commit"] == "b" * 40
        assert task["argv"][-5:] == [
            "--search",
            "dense",
            "--exhaustive-audit",
            "--output-dir",
            "{attempt_dir}/fit",
        ]
        assert "run-fit" in task["argv"]
    assert all(campaign.sha256(path) == sha for path, sha in before.items())
    with pytest.raises(FileExistsError):
        prepare.prepare_fits(selected_path, original_results, "b" * 40, tmp_path / "plan")


def test_summary_requires_probe_plan_and_task_identity(tmp_path):
    selected = tmp_path / "selection.json"
    selected.write_text(json.dumps({"nonregression": [{"task_id": "original-A-dense"}]}))
    fits = tmp_path / "fits.json"
    fits.write_text(
        json.dumps(
            {"source_commit": "b" * 40, "selection_sha256": campaign.sha256(selected), "tasks": []}
        )
    )
    probes = tmp_path / "probes.json"
    probe_plan = {
        "source_commit": "b" * 40,
        "selection_sha256": campaign.sha256(selected),
        "fit_plan_sha256": campaign.sha256(fits),
        "tasks": [],
    }
    probes.write_text(json.dumps(probe_plan))
    result = prepare.summarize(selected, fits, probes, tmp_path / "fits", tmp_path / "probes")
    assert result["all_nonregression_passed"] is False
    assert result["nonregression_probes"][0]["status"] == "missing"
    wrong = tmp_path / "probes/repair-probe-original-A-dense/_task.json"
    wrong.parent.mkdir(parents=True)
    wrong.write_text(json.dumps({"task_sha256": "0" * 64}))
    with pytest.raises(ValueError, match="probe task identity"):
        prepare.summarize(selected, fits, probes, tmp_path / "fits", tmp_path / "probes")
    probe_plan["source_commit"] = "c" * 40
    probes.write_text(json.dumps(probe_plan))
    with pytest.raises(ValueError, match="another replay"):
        prepare.summarize(selected, fits, probes, tmp_path / "fits", tmp_path / "probes")
