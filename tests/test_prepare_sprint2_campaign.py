from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def staged(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    module = importlib.import_module("prepare_sprint2_campaign")
    real_panel = json.loads(module.PANEL.read_text())
    panel = tmp_path / "panel.json"
    manifest = tmp_path / "maps.json"
    maps_root = tmp_path / "maps"
    records = []
    for name in sorted({r["map"] for r in real_panel["datasets"]}):
        archetype, index = name.rsplit("-", 1)
        directory = maps_root / name
        directory.mkdir(parents=True)
        record = {
            "role": "qualification",
            "archetype": archetype,
            "map_index": int(index),
            "spawn_key": [2, ["connected", "corridor", "barrier"].index(archetype), int(index)],
            "seeds": {"map_seed": int(index)},
            "status": "ok",
            "admissible": True,
            "baseline_site_ids": ["s1"],
            "c_site_ids": ["s1", "s2"],
            "holdout_site_ids": ["s3"],
        }
        record["files"] = {}
        for filename in module.MAP_FILES:
            if filename == "record.json":
                continue
            path = directory / filename
            path.write_bytes((name + filename).encode())
            record["files"][filename] = module.campaign.sha256(path)
        (directory / "record.json").write_text(json.dumps(record))
        compact = {k: v for k, v in record.items() if not k.endswith("_site_ids")}
        for key in ("baseline_site_ids", "c_site_ids", "holdout_site_ids"):
            compact[key + "_sha256"] = hashlib.sha256(json.dumps(record[key]).encode()).hexdigest()
        records.append(compact)
    manifest.write_text(json.dumps({"role": "qualification", "maps": records}))
    real_panel["map_manifest_sha256"] = module.campaign.sha256(manifest)
    panel.write_text(json.dumps(real_panel))
    monkeypatch.setattr(module, "PANEL", panel)
    monkeypatch.setattr(module, "MAP_MANIFEST", manifest)
    monkeypatch.setattr(module, "PANEL_SHA256", module.campaign.sha256(panel))
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module.campaign, "verify_source", lambda task: {"commit": "a" * 40})
    monkeypatch.setattr(module, "verify_independent_banks", lambda a, b: None)
    sif = tmp_path / "runtime.sif"
    sif.write_bytes(b"test runtime")
    (tmp_path / "uv.lock").write_text("test lock")
    runtime = tmp_path / "runtime.json"
    runtime.write_text(
        json.dumps(
            {
                "schema": "sprint2-runtime-v1",
                "source_commit": "a" * 40,
                "python_executable": sys.executable,
                "oci_uri": "docker://example@sha256:" + "b" * 64,
                "sif": str(sif),
                "sif_sha256": module.campaign.sha256(sif),
                "uv_lock_sha256": module.campaign.sha256(tmp_path / "uv.lock"),
            }
        )
    )
    args = SimpleNamespace(
        maps_root=maps_root,
        results_root=tmp_path / "results",
        runtime_receipt=runtime,
        source_commit="a" * 40,
        python=sys.executable,
        execution_context="apptainer",
        dependency_plan=[],
        phase="banks",
        output_dir=tmp_path / "banks-plan",
    )
    return module, args, real_panel


def prepare(staged, phase, deps=(), suffix=""):
    module, args, _ = staged
    current = SimpleNamespace(**vars(args))
    current.phase = phase
    current.output_dir = args.output_dir.parent / f"{phase}-plan{suffix}"
    current.dependency_plan = list(deps)
    result = module.prepare(current)
    return result, current.output_dir / "plan.json"


def complete(module, args, task, result, files=None):
    directory = args.results_root / task["task_id"]
    attempt = directory / "attempt-0001"
    target = attempt / task["result_path"]
    target.parent.mkdir(parents=True)
    for name, data in (files or {}).items():
        (target.parent / name).write_bytes(data)
    target.write_text(json.dumps(result))
    status = (
        "completed"
        if task["result_schema"] != "fit-dataset-v1"
        else ("resolved" if result["failure_class"] == "resolved" else "scientific_failure")
    )
    record = {
        "task_id": task["task_id"],
        "task": task,
        "task_sha256": module.campaign.task_digest(task),
        "attempt": attempt.name,
        "status": status,
        "failure_class": result.get("failure_class"),
        "exit_code": 0,
        "source": {"commit": args.source_commit, "tracked_changes": []},
        "output_sha256": {
            str(p.relative_to(attempt)): module.campaign.sha256(p)
            for p in attempt.rglob("*")
            if p.is_file()
        },
    }
    for path in (directory / "_task.json", attempt / "_task.json"):
        path.write_text(json.dumps(record))
    return target


def completed_inputs(staged):
    module, args, panel = staged
    banks, bp = prepare(staged, "banks")
    histories, hp = prepare(staged, "histories")
    for task in banks["tasks"]:
        argv = task["argv"]
        map_dir = Path(argv[argv.index("--map-dir") + 1])
        replicate = int(argv[argv.index("--bank-replicate") + 1])
        record = json.loads((map_dir / "record.json").read_text())
        output = args.results_root / task["task_id"] / "attempt-0001/bank"
        raw, compressed = f"bank{replicate}".encode(), f"compressed{replicate}".encode()
        result = {
            "schema": task["result_schema"],
            "map": record,
            "bank_replicate": replicate,
            "bank_size": 131072,
            "series_order": 192,
            "map_input_sha256": {
                name: module.campaign.sha256(map_dir / name) for name in module.MAP_FILES
            },
            "raw": str(output / "arrivals.npy"),
            "compressed": str(output / "compressed.npz"),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
        }
        complete(module, args, task, result, {"arrivals.npy": raw, "compressed.npz": compressed})
    by_id = {module.history_id(row): row for row in panel["datasets"]}
    for task in histories["tasks"]:
        row = by_id[task["task_id"]]
        map_dir = args.maps_root / row["map"]
        observation = row["dataset_id"].encode()
        result = {
            "schema": task["result_schema"],
            "map": json.loads((map_dir / "record.json").read_text()),
            "map_input_sha256": {
                name: module.campaign.sha256(map_dir / name) for name in module.MAP_FILES
            },
            **{key: row[key] for key in ("address", "background", "arm")},
            "truth": {"mu": row["mu"], "h": row["h"], "detection_sd": 0.2},
            "files": {"observations.npz": hashlib.sha256(observation).hexdigest()},
        }
        complete(module, args, task, result, {"observations.npz": observation})
    return bp, hp


def test_frozen_counts_pairing_and_explicit_runtime(staged):
    module, _, panel = staged
    banks, _ = prepare(staged, "banks")
    histories, _ = prepare(staged, "histories")
    assert len(banks["tasks"]) == 18
    assert len(histories["tasks"]) == 207
    for task in banks["tasks"] + histories["tasks"]:
        assert task["source_commit"] == "a" * 40
        assert task["input_sha256"][task["runtime"]["sif"]] == task["runtime"]["sif_sha256"]
        assert any(Path(p).name == "uv.lock" for p in task["input_sha256"])
    rows = {module.history_id(r): r for r in panel["datasets"]}
    for task in histories["tasks"]:
        row, argv = rows[task["task_id"]], task["argv"]
        assert argv[argv.index("--address") + 1] == ",".join(map(str, row["address"]))
        assert argv[argv.index("--arm") + 1] == row["arm"]


def test_missing_dependencies_cannot_create_fits_or_success(staged):
    _, args, _ = staged
    plan, path = prepare(staged, "fits")
    assert not plan["tasks"] and len(plan["pending"]) == 486
    index = json.loads((path.parent / "qualification-index.json").read_text())
    assert len(index["cases"]) == 207
    assert all(
        v["lean"] is None and v["observation_sha256"] is None for v in index["cases"].values()
    )
    assert not args.results_root.exists()


def test_map_payload_and_validation_role_are_rejected(staged):
    module, args, _ = staged
    with pytest.raises(ValueError, match="remain unopened"):
        module.load_qualification(args.maps_root / "validation")
    path = args.maps_root / "connected-0/public_inputs.npz"
    original = path.read_bytes()
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="payload differs"):
        module.load_qualification(args.maps_root)
    path.write_bytes(original)
    manifest = json.loads(module.MAP_MANIFEST.read_text())
    manifest["role"] = "validation"
    module.MAP_MANIFEST.write_text(json.dumps(manifest))
    panel = json.loads(module.PANEL.read_text())
    panel["map_manifest_sha256"] = module.campaign.sha256(module.MAP_MANIFEST)
    module.PANEL.write_text(json.dumps(panel))
    module.PANEL_SHA256 = module.campaign.sha256(module.PANEL)
    with pytest.raises(ValueError, match="only qualification"):
        module.load_qualification(args.maps_root)


def test_fits_audits_integration_and_scientific_failures_keep_exact_denominators(staged):
    module, args, panel = staged
    bp, hp = completed_inputs(staged)
    fits, fp = prepare(staged, "fits", [bp, hp])
    assert len(fits["tasks"]) == 486 and not fits["pending"]
    assert sum(t["task_id"].endswith("independent_bank") for t in fits["tasks"]) == 54
    assert sum("--exhaustive-audit" in t["argv"] for t in fits["tasks"]) == 18
    failed_row = next(
        r for r in panel["datasets"] if r["integration_screen"] and not r["independent_bank"]
    )
    failed = module.fit_id(failed_row, "lean")
    for task in fits["tasks"]:
        complete(
            module,
            args,
            task,
            {
                "schema": "fit-dataset-v1",
                "failure_class": "numerical_error" if task["task_id"] == failed else "resolved",
            },
        )
    audits, ap = prepare(staged, "audits", [bp, hp, fp])
    assert len(audits["tasks"]) == 466
    assert len(audits["pending"]) == 2
    index = json.loads((ap.parent / "qualification-index.json").read_text())
    ref = index["cases"][failed_row["dataset_id"]]["lean"]
    assert json.loads(Path(ref["path"]).read_text())["failure_class"] == "numerical_error"
    integration, _ = prepare(staged, "integration", [bp, hp, fp])
    assert len(integration["tasks"]) == 9 and not integration["pending"]
    assert all(t["result_schema"] == "sprint2-integration-screen-v1" for t in integration["tasks"])


def test_changed_dependency_receipt_is_not_used(staged):
    module, args, panel = staged
    bp, hp = completed_inputs(staged)
    row = panel["datasets"][0]
    receipt = args.results_root / module.history_id(row) / "_task.json"
    value = json.loads(receipt.read_text())
    value["task_sha256"] = "0" * 64
    receipt.write_text(json.dumps(value))
    fits, _ = prepare(staged, "fits", [bp, hp])
    assert len(fits["pending"]) == len(module.fit_roles(row))
    assert all(row["dataset_id"] in p["task_id"] for p in fits["pending"])


def test_runtime_hash_change_stops_preparation(staged):
    _, args, _ = staged
    runtime = json.loads(args.runtime_receipt.read_text())
    Path(runtime["sif"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="SIF changed"):
        prepare(staged, "banks")
