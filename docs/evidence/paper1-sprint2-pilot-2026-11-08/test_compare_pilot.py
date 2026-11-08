from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location(
    "compare_pilot", Path(__file__).with_name("compare_pilot.py")
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def receipt():
    mesh = sorted(set(np.linspace(0, m.LOG_MAX, 5)) | set(np.linspace(0, m.LOG_MAX, 35)))

    def view(spatial):
        def row(x):
            r = {"h": float(np.exp(x)), "log_h": x, "criterion": -x / 10, "w": x / 5}
            if spatial:
                r.update(
                    tied=False,
                    nuisance_contacts={"positive_sigma": []},
                    h_domain_contacts={
                        "positive_sigma": ["lower"]
                        if x == 0
                        else ["upper"]
                        if x == m.LOG_MAX
                        else []
                    },
                )
            else:
                r.update(
                    eligible=True,
                    nuisance_bound_contacts=[],
                    h_domain_contacts=["lower"] if x == 0 else ["upper"] if x == m.LOG_MAX else [],
                )
            return r

        return {
            "free": row(0),
            "null": row(0),
            "profile": [row(float(x)) for x in mesh],
            "level_sets": [
                {
                    "cutoff": c,
                    "status": "available",
                    "set_class": "proper_subset",
                    "touches_h1": True,
                    "touches_h30": False,
                    "empty": False,
                    "roots_log_h": [2.5],
                    "components": [
                        {
                            "lower_log_h": 0.0,
                            "upper_log_h": 2.5,
                            "lower_domain_contact": True,
                            "upper_domain_contact": False,
                            "singleton": False,
                        }
                    ],
                }
                for c in m.CUTOFFS
            ],
        }

    return {
        "schema": "fit-dataset-v1",
        "source": {"commit": m.COMMIT, "working_tree_changes": []},
        "cutoffs": list(m.CUTOFFS),
        "search_mode": "lean",
        "tight_replay": "always_on_inside_PanelSearch.run",
        "failure_class": "resolved",
        "all_triggered": [],
        "errors": [],
        "threads": {
            name: "1"
            for name in ("OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OMP_NUM_THREADS")
        },
        "search": {"status": "profile_numerically_resolved", "failure": None},
        "envelope_guard": {"unresolved_fit_events": 0, "anchor_guard_events": 0, "events": []},
        "latent_audit": {
            "multimodal_latent": False,
            "flagged": [],
            "lr_limit": 25.0,
            "exhaustive": False,
        },
        "families": {
            "spatial": {"status": "available", "standard": view(True), "tight": view(True)},
            "exposure": {"status": "available", **view(False)},
            "constant": {"status": "available", **view(False)},
        },
    }


@pytest.fixture
def evidence(tmp_path):
    left, right = receipt(), receipt()
    root = tmp_path / "mirror"
    attempt = root / "case" / "attempt-001"
    result = attempt / "result"
    result.mkdir(parents=True)
    local = tmp_path / "local"
    local.mkdir()
    lpath, rpath = local / "receipt.json", result / "receipt.json"
    for side, folder, doc in [("local", local, left), ("target", result, right)]:
        base = f"/{side}/data"
        doc["inputs"] = {
            "input_dir": base,
            "observations": base + "/obs.npz",
            "arrival_bank": base + "/arrivals.npy",
            "compressed_bank": base + "/compressed.npz",
        }
        doc["input_sha256"] = {
            base + "/" + name: str(i) * 64
            for i, name in enumerate(
                ["public_inputs.npz", "exposure.npz", "obs.npz", "arrivals.npy", "compressed.npz"],
                1,
            )
        }
        child = folder / "search_receipt.json"
        child.write_text(
            json.dumps(
                {
                    "mode": "lean",
                    "status": "profile_numerically_resolved",
                    "cutoffs": list(m.CUTOFFS),
                }
            )
        )
        doc["search"].update(
            receipt=str(child)
            if side == "local"
            else "/remote/results/case/attempt-001/result/search_receipt.json",
            receipt_sha256=m.digest(child),
        )

    def run(mutation=None, task=False):
        a, b = copy.deepcopy(left), copy.deepcopy(right)
        if mutation:
            mutation(a, b)
        lpath.write_text(json.dumps(a))
        rpath.write_text(json.dumps(b))
        taskpath = attempt / "_task.json"
        if task:
            taskpath.write_text(
                json.dumps(
                    {
                        "attempt": "attempt-001",
                        "output_sha256": {
                            "result/receipt.json": m.digest(rpath),
                            "result/search_receipt.json": m.digest(result / "search_receipt.json"),
                        },
                        "status": "resolved",
                        "failure_class": "resolved",
                        "exit_code": 0,
                        "task_sha256": "a" * 64,
                    }
                )
            )
        return m.compare(lpath, rpath, root, "/remote/results", taskpath if task else None)

    return run, left, right, lpath, rpath, root


def test_valid_evidence_and_task(evidence):
    out = evidence[0](task=True)
    assert out["status"] == "pass", out
    assert out["task"]["outputs_verified"] == 2
    assert out["qualification_evidence"] is False
    assert len(out["views"]) == 4


def test_offset_scores_preserve_w(evidence):
    def change(a, b):
        for name in m.VIEWS:
            v = m.view_of(b, name)
            for row in [v["free"], v["null"], *v["profile"]]:
                row["criterion"] += 100

    assert evidence[0](change)["status"] == "pass"


@pytest.mark.parametrize("delta,expected", [(0.00999, "pass"), (0.01001, "fail")])
def test_w_boundary(evidence, delta, expected):
    def change(a, b):
        row = m.view_of(b, "spatial.tight")["profile"][1]
        row["criterion"] -= delta / 2
        row["w"] += delta

    assert evidence[0](change)["status"] == expected


@pytest.mark.parametrize("delta,expected", [(0.00499, "pass"), (0.00501, "fail")])
def test_endpoint_boundary(evidence, delta, expected):
    def change(a, b):
        level = m.view_of(b, "constant")["level_sets"][7]
        level["roots_log_h"][0] += delta
        level["components"][0]["upper_log_h"] += delta

    assert evidence[0](change)["status"] == expected


def test_topology_no_tangency_waiver(evidence):
    def change(a, b):
        m.view_of(b, "exposure")["level_sets"][0]["roots_log_h"].append(2.50000001)

    assert evidence[0](change)["status"] == "fail"


def test_missing_mesh_indeterminate(evidence):
    def change(a, b):
        m.view_of(b, "constant")["profile"].pop(1)

    out = evidence[0](change)
    assert out["status"] == "indeterminate" and "mandatory" in str(out["unavailable"])


def test_exact_shared_only(evidence):
    def change(a, b):
        v = m.view_of(b, "spatial.standard")
        row = copy.deepcopy(v["profile"][1])
        row.update(
            log_h=0.123456789, h=float(np.exp(0.123456789)), criterion=-0.0123456789, w=0.0246913578
        )
        v["profile"].append(row)

    out = evidence[0](change)
    assert out["status"] == "pass"
    assert out["views"]["spatial.standard"]["target_only"]["count"] == 1


@pytest.mark.parametrize("kind", ["contacts", "failure", "latent", "guard"])
def test_diagnostics_fail(evidence, kind):
    def change(a, b):
        if kind == "contacts":
            m.view_of(b, "constant")["free"]["nuisance_bound_contacts"] = ["alpha:upper"]
        elif kind == "failure":
            b["failure_class"] = "execution_error"
        elif kind == "latent":
            b["latent_audit"]["multimodal_latent"] = True
        else:
            b["envelope_guard"]["unresolved_fit_events"] = 1

    assert evidence[0](change)["status"] == "fail"


@pytest.mark.parametrize("kind", ["data", "source", "child_hash", "unknown_field"])
def test_identity_or_missing_evidence_indeterminate(evidence, kind):
    def change(a, b):
        if kind == "data":
            b["input_sha256"]["/target/data/obs.npz"] = "a" * 64
        elif kind == "source":
            b["source"]["working_tree_changes"] = [" M something"]
        elif kind == "child_hash":
            b["search"]["receipt_sha256"] = "a" * 64
        else:
            del b["latent_audit"]["multimodal_latent"]

    assert evidence[0](change)["status"] == "indeterminate"


def test_prefix_component_mapping(evidence):
    def change(a, b):
        b["search"]["receipt"] = "/remote/results-evil/case/attempt-001/result/search_receipt.json"

    assert evidence[0](change)["status"] == "indeterminate"


def test_task_tampering_and_omission(evidence):
    run, _, _, lp, rp, root = evidence
    assert run(task=True)["status"] == "pass"
    task = rp.parent.parent / "_task.json"
    record = m.read(task)
    record["output_sha256"]["result/receipt.json"] = "f" * 64
    task.write_text(json.dumps(record))
    assert m.compare(lp, rp, root, "/remote/results", task)["status"] == "indeterminate"
    del record["output_sha256"]["result/receipt.json"]
    task.write_text(json.dumps(record))
    assert m.compare(lp, rp, root, "/remote/results", task)["status"] == "indeterminate"


def test_historical_exception_not_general_dirty_permission(evidence):
    def change(a, b):
        a["source"].update(commit=m.OLD_COMMIT, working_tree_changes=[" M scripts/fit_dataset.py"])

    assert evidence[0](change)["status"] == "indeterminate"


@pytest.mark.parametrize("kind", ["threads", "cutoff", "nonfinite", "shifted_mesh"])
def test_settings_or_missing_required_evidence(evidence, kind):
    def change(a, b):
        v = m.view_of(b, "spatial.standard")
        if kind == "threads":
            b["threads"]["OMP_NUM_THREADS"] = "2"
        elif kind == "cutoff":
            v["level_sets"].pop()
        elif kind == "nonfinite":
            v["profile"][1]["criterion"] = float("nan")
        else:
            row = next(r for r in v["profile"] if r["log_h"] == m.LOG_MAX / 4)
            row["log_h"] += 1e-12

    out = evidence[0](change)
    assert out["status"] == "indeterminate"


def test_endpoint_type_failure(evidence):
    def change(a, b):
        m.view_of(b, "spatial.tight")["level_sets"][0]["components"][0]["upper_domain_contact"] = (
            True
        )

    assert evidence[0](change)["status"] == "fail"


def test_noncommon_contacts_require_diagnosis(evidence):
    def change(a, b):
        v = m.view_of(b, "constant")
        row = copy.deepcopy(v["profile"][1])
        row.update(
            log_h=0.123456789,
            h=float(np.exp(0.123456789)),
            criterion=-0.0123456789,
            w=0.0246913578,
            nuisance_bound_contacts=["alpha:lower"],
        )
        v["profile"].append(row)

    assert evidence[0](change)["status"] == "fail"


def test_task_path_traversal(evidence):
    run, _, _, lp, rp, root = evidence
    run(task=True)
    task = rp.parent.parent / "_task.json"
    record = m.read(task)
    record["attempt"] = "../attempt-001"
    task.write_text(json.dumps(record))
    assert m.compare(lp, rp, root, "/remote/results", task)["status"] == "indeterminate"


def test_cli_preserves_receipts(evidence, tmp_path):
    import subprocess
    import sys

    run, _, _, lp, rp, root = evidence
    run(task=True)
    before = (lp.read_bytes(), rp.read_bytes())
    output = tmp_path / "comparison.json"
    done = subprocess.run(
        [
            sys.executable,
            str(Path(m.__file__)),
            str(lp),
            str(rp),
            "--target-results-root",
            str(root),
            "--remote-results-prefix",
            "/remote/results",
            "--target-task",
            str(rp.parent.parent / "_task.json"),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr
    assert m.read(output)["status"] == "pass"
    assert (lp.read_bytes(), rp.read_bytes()) == before
