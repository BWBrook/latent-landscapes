"""Freeze the repair sample and prepare immutable fit/probe campaign tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from audit_sprint2_pair import VIEWS, profile_rows, required_nodes, view_of
from pbs import campaign

ROOT = Path(__file__).resolve().parents[1]
FROZEN = "99af5206b6a4e53f5b8e9d71cbf348f95e9ae574"
SALT = "repair-3307-nonregression-v1:"
Json = dict[str, Any]


def read(path: Path) -> Json:
    return json.loads(path.read_text())


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def coordinate_digest(nodes: set[float] | dict[float, Any]) -> str:
    return hashlib.sha256(
        json.dumps([x.hex() for x in sorted(nodes)], separators=(",", ":")).encode()
    ).hexdigest()


def select_ids(snapshot: Json) -> list[str]:
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    resolved = [r["task_id"] for r in snapshot["completed"] if r["status"] == "resolved"]
    if len(resolved) != 417 or len(set(resolved)) != 417:
        raise ValueError("the frozen resolved pool must contain exactly 417 distinct tasks")
    for task_id in resolved:
        arm, role = task_id.rsplit("-", 2)[-2:]
        groups[(arm, role)].append(task_id)
    expected = {(a, r) for a in "ABC" for r in ("dense", "lean", "independent_bank", "exhaustive")}
    if set(groups) != expected or any(len(v) < 2 for v in groups.values()):
        raise ValueError("the twelve arm-by-role strata must each contain at least two tasks")
    return [
        task_id
        for key in sorted(groups)
        for task_id in sorted(
            groups[key], key=lambda x: hashlib.sha256((SALT + x).encode()).hexdigest()
        )[:2]
    ]


def anchor_inventory(receipt: Json) -> Json:
    import math

    views = {}
    for name in VIEWS:
        view = view_of(receipt, name)
        stored, nodes = profile_rows(view), required_nodes(view)
        missing = sorted(nodes - stored.keys())
        if any(x != math.log(view["free"]["h"]) for x in missing):
            raise ValueError(
                "a required anchor lacks both an exact profile and own-h free candidate"
            )
        views[name] = {
            "required_anchor_count": len(nodes),
            "required_log_h_hex_sha256": coordinate_digest(nodes),
            "reference_kinds": [
                {
                    "kind": "stored_profile_row",
                    "count": len(stored),
                    "log_h_hex_sha256": coordinate_digest(stored),
                },
                *[
                    {
                        "kind": "free_candidate_at_own_h",
                        "log_h_hex": x.hex(),
                        "criterion": view["free"]["criterion"],
                        "eligible": view["free"]["eligible"],
                    }
                    for x in missing
                ],
            ],
        }
    return views


def frozen_selection(original_results: Path, snapshot: Path, cache: Path) -> Json:
    import math

    progress = read(snapshot)
    selected = []
    for task_id in select_ids(progress):
        task_path = original_results / task_id / "_task.json"
        record = read(task_path)
        if record["status"] != "resolved" or record["source"]["commit"] != FROZEN:
            raise ValueError("selected task is not a resolved frozen-candidate attempt")
        receipt_path, search_path = (
            cache / task_id / "receipt.json",
            cache / task_id / "search_receipt.json",
        )
        for path, key in (
            (receipt_path, "fit/receipt.json"),
            (search_path, "fit/search_receipt.json"),
        ):
            if campaign.sha256(path) != record["output_sha256"][key]:
                raise ValueError(f"baseline output hash differs: {task_id}/{key}")
        receipt = read(receipt_path)
        if receipt["failure_class"] != "resolved" or receipt["source"]["commit"] != FROZEN:
            raise ValueError("selected baseline receipt is not resolved/frozen")
        if receipt["search"]["receipt_sha256"] != campaign.sha256(search_path):
            raise ValueError("nested baseline search receipt binding differs")
        arm, role = task_id.rsplit("-", 2)[-2:]
        selected.append(
            {
                "task_id": task_id,
                "arm": arm,
                "role": role,
                "selection_sha256": hashlib.sha256((SALT + task_id).encode()).hexdigest(),
                "original_task_record_sha256": campaign.sha256(task_path),
                "baseline_receipt_sha256": campaign.sha256(receipt_path),
                "baseline_search_receipt_sha256": campaign.sha256(search_path),
                "original_attempt": record["attempt"],
                "views": anchor_inventory(receipt),
            }
        )
    failed = []
    for row in progress["completed"]:
        if row["status"] != "scientific_failure":
            continue
        task_id = row["task_id"]
        task_path = original_results / task_id / "_task.json"
        record = read(task_path)
        path = original_results / task_id / record["attempt"] / "fit/receipt.json"
        if campaign.sha256(path) != record["output_sha256"]["fit/receipt.json"]:
            raise ValueError(f"failed baseline output differs: {task_id}")
        failed.append(
            {
                "task_id": task_id,
                "original_task_record_sha256": campaign.sha256(task_path),
                "baseline_receipt_sha256": campaign.sha256(path),
                "original_attempt": record["attempt"],
                "failure_class": record["failure_class"],
            }
        )
    if len(failed) != 27 or len({r["task_id"] for r in failed}) != 27:
        raise ValueError("exactly 27 original scientific-failure tasks are required")
    diagnostic = ROOT / "docs/evidence/paper1-sprint2-diagnostics-2026-11-12"
    spatial, witness = (
        diagnostic / "spatial-checkpoints.json",
        diagnostic / "inner-replay-plan.json",
    )
    constant = []
    for path in sorted(
        (ROOT / "artifacts/sprint2/diagnostics-20261112/results/constant").glob(
            "case-*/receipt.json"
        )
    ):
        row = read(path)
        gradient = next(
            r["central_difference"]
            for r in row["derivative_sweep"]["rows"]
            if r["direction"] == "coordinate_1" and r["t"] == 1e-6
        )
        if not math.isfinite(gradient):
            raise ValueError("constant gradient reference is unavailable")
        constant.append(
            {
                "dataset": row["dataset"],
                "task_id": row["task_id"],
                "fixed_h": 1.0,
                "reduced_parameters": row["final_reduced"],
                "reference_detection_sd_gradient": gradient,
                "reference_stencil_t": 1e-6,
                "receipt_sha256": campaign.sha256(path),
                "gradient_absolute_tolerance": 5e-6,
            }
        )
    if len(constant) != 4:
        raise ValueError("all four frozen constant endpoint references are required")
    return {
        "schema": "solver-repair-replay-selection-v1",
        "date": "2026-11-12",
        "frozen_before_repaired_candidate_outcomes": True,
        "accepted_specification_message": 3307,
        "original_candidate": FROZEN,
        "selection_rule": "Two lowest SHA256(" + SALT + "+task_id) per arm-by-role stratum.",
        "original_snapshot_sha256": campaign.sha256(snapshot),
        "resolved_pool_count": 417,
        "nonregression_count": 24,
        "development_failed_count": 27,
        "required_anchor_count": sum(
            v["required_anchor_count"] for r in selected for v in r["views"].values()
        ),
        "tolerances": {
            "criterion_absolute": 1e-6,
            "profile_lr_absolute": 1e-3,
            "eligibility_unchanged": True,
        },
        "nonregression": selected,
        "development_failed": sorted(failed, key=lambda r: r["task_id"]),
        "development_checkpoints": {
            "spatial_manifest": "../paper1-sprint2-diagnostics-2026-11-12/spatial-checkpoints.json",
            "spatial_manifest_sha256": campaign.sha256(spatial),
            "enriched_endpoints": read(spatial)["checkpoints"][:3],
            "witness_plan": "../paper1-sprint2-diagnostics-2026-11-12/inner-replay-plan.json",
            "witness_plan_sha256": campaign.sha256(witness),
            "witness": read(witness),
            "constant_endpoints": constant,
        },
        "limits": [
            "A free_candidate_at_own_h anchor is its recorded free candidate, "
            "not an archived fixed-profile maximum.",
            "Original profile meshes are bound by receipt hashes and compact "
            "exact-coordinate inventories; no interpolation or nearest-node matching.",
            "The 27 failed fits and diagnostic points are development evidence, "
            "not a qualification gate.",
        ],
    }


def original_record(selection_row: Json, original_results: Path) -> tuple[Path, Json]:
    path = (original_results / selection_row["task_id"] / "_task.json").resolve()
    if campaign.sha256(path) != selection_row["original_task_record_sha256"]:
        raise ValueError("original task record differs from frozen selection")
    record = read(path)
    if record["task_sha256"] != campaign.task_digest(record["task"]):
        raise ValueError("original task digest differs")
    if record["task"]["source_commit"] != FROZEN or record["source"]["commit"] != FROZEN:
        raise ValueError("original source identity differs")
    if record["attempt"] != selection_row["original_attempt"]:
        raise ValueError("original attempt changed")
    receipt = path.parent / record["attempt"] / record["task"]["result_path"]
    if campaign.sha256(receipt) != selection_row["baseline_receipt_sha256"]:
        raise ValueError("original fit receipt differs")
    if record["output_sha256"]["fit/receipt.json"] != selection_row["baseline_receipt_sha256"]:
        raise ValueError("original output binding differs")
    return path, record


def write_plan(output: Path, tasks: list[Json], metadata: Json) -> Json:
    output.mkdir(parents=True, exist_ok=False)
    taskfile = output / "tasks.jsonl"
    taskfile.write_text(
        "".join(json.dumps(t, sort_keys=True, allow_nan=False) + "\n" for t in tasks)
    )
    campaign.load_tasks(taskfile)
    plan = {
        "schema": "solver-repair-replay-plan-v1",
        **metadata,
        "tasks_sha256": campaign.sha256(taskfile),
        "tasks": tasks,
    }
    write(output / "plan.json", plan)
    return plan


def prepare_fits(
    selection_path: Path, original_results: Path, candidate_commit: str, output: Path
) -> Json:
    selection = read(selection_path)
    if selection["schema"] != "solver-repair-replay-selection-v1":
        raise ValueError("wrong selection schema")
    tasks = []
    for group, rows in (
        ("nonregression", selection["nonregression"]),
        ("development_failed", selection["development_failed"]),
    ):
        for row in rows:
            path, record = original_record(row, original_results)
            original = record["task"]
            if (record["status"] == "resolved") != (group == "nonregression"):
                raise ValueError("original task outcome does not match replay group")
            task = json.loads(json.dumps(original))
            task.update(
                task_id="repair-" + original["task_id"],
                source_commit=candidate_commit,
                original_task_id=original["task_id"],
                replay_group=group,
                candidate_import_root=str(ROOT.resolve()),
                original_fit_argv=original["argv"],
            )
            task["argv"] = [
                original["argv"][0],
                "scripts/prepare_solver_repair_replay.py",
                "run-fit",
                "--candidate-commit",
                candidate_commit,
                "--",
                *original["argv"][2:],
            ]
            task["input_sha256"].update(
                {
                    str(path): campaign.sha256(path),
                    str(selection_path.resolve()): campaign.sha256(selection_path),
                }
            )
            tasks.append(task)
    if len(tasks) != 51 or len({t["task_id"] for t in tasks}) != 51:
        raise ValueError("exactly 51 distinct fit replays are required")
    return write_plan(
        output,
        tasks,
        {
            "phase": "fits",
            "source_commit": candidate_commit,
            "selection_sha256": campaign.sha256(selection_path),
            "original_source_commit": FROZEN,
            "groups": dict(Counter(t["replay_group"] for t in tasks)),
            "runtime_policy": "original pinned interpreter/SIF with candidate source imports; "
            "data and original attempts unchanged",
        },
    )


def prepare_probes(
    selection_path: Path,
    original_results: Path,
    fits_plan_path: Path,
    fit_results: Path,
    checkpoint_root: Path,
    output: Path,
) -> Json:
    selection, fit_plan = read(selection_path), read(fits_plan_path)
    if campaign.sha256(selection_path) != fit_plan["selection_sha256"]:
        raise ValueError("selection differs from fit plan")
    tasks, pending = [], []
    source = fit_plan["source_commit"]
    replay_tasks = {t["original_task_id"]: t for t in fit_plan["tasks"]}
    for row in selection["nonregression"]:
        original_path, original = original_record(row, original_results)
        replay = replay_tasks[row["task_id"]]
        record_path = (fit_results / replay["task_id"] / "_task.json").resolve()
        if not record_path.exists():
            pending.append({"task_id": row["task_id"], "reason": "candidate_task_missing"})
            continue
        record = read(record_path)
        if record["task_sha256"] != campaign.task_digest(replay):
            raise ValueError("candidate task identity differs")
        if record["status"] not in {"resolved", "scientific_failure"}:
            pending.append({"task_id": row["task_id"], "reason": record["status"]})
            continue
        if record["source"]["commit"] != source or record["source"]["tracked_changes"]:
            raise ValueError("candidate terminal source identity differs")
        receipt = record_path.parent / record["attempt"] / replay["result_path"]
        expected = record["output_sha256"][replay["result_path"]]
        if campaign.sha256(receipt) != expected:
            raise ValueError("candidate receipt differs from task output binding")
        baseline = original_path.parent / original["attempt"] / "fit/receipt.json"
        search = original_path.parent / original["attempt"] / "fit/search_receipt.json"
        if campaign.sha256(search) != row["baseline_search_receipt_sha256"]:
            raise ValueError("baseline nested search receipt differs")
        inputs = {
            **replay["input_sha256"],
            str(record_path): campaign.sha256(record_path),
            str(receipt): expected,
            str(baseline): row["baseline_receipt_sha256"],
            str(search): row["baseline_search_receipt_sha256"],
        }
        candidate = read(receipt)
        if "search" in candidate:
            nested = Path(candidate["search"]["receipt"])
            if campaign.sha256(nested) != candidate["search"]["receipt_sha256"]:
                raise ValueError("candidate search receipt differs")
            inputs[str(nested)] = candidate["search"]["receipt_sha256"]
        argv = [
            replay["runtime"]["python"],
            "scripts/compare_solver_repair_replay.py",
            "--baseline-receipt",
            str(baseline),
            "--baseline-search",
            str(search),
            "--candidate-receipt",
            str(receipt),
            "--baseline-sha256",
            row["baseline_receipt_sha256"],
            "--baseline-search-sha256",
            row["baseline_search_receipt_sha256"],
            "--candidate-sha256",
            expected,
            "--candidate-commit",
            source,
            "--output-dir",
            "{attempt_dir}/probe",
            "--checkpoint-dir",
            str((checkpoint_root / row["task_id"]).resolve()),
        ]
        tasks.append(
            {
                "task_id": "repair-probe-" + row["task_id"],
                "original_task_id": row["task_id"],
                "replay_group": "nonregression_probe",
                "argv": argv,
                "source_commit": source,
                "runtime": replay["runtime"],
                "input_sha256": inputs,
                "result_path": "probe/receipt.json",
                "result_schema": "solver-repair-nonregression-v1",
                "candidate_import_root": str(ROOT.resolve()),
            }
        )
    return write_plan(
        output,
        tasks,
        {
            "phase": "probes",
            "source_commit": source,
            "selection_sha256": campaign.sha256(selection_path),
            "fit_plan_sha256": campaign.sha256(fits_plan_path),
            "pending": pending,
            "required_task_count": 24,
            "all_candidate_fits_terminal": not pending,
        },
    )


def imported_source_check(candidate_commit: str) -> None:
    import latent_landscapes.spatial_profile as spatial

    campaign.verify_source({"source_commit": candidate_commit})
    if not Path(spatial.__file__).resolve().is_relative_to(ROOT):
        raise ValueError("imported package is outside the candidate checkout")
    if campaign.ROOT != ROOT:
        raise ValueError("campaign source guard belongs to another checkout")


def summarize(
    selection_path: Path,
    fit_plan_path: Path,
    probe_plan_path: Path,
    fit_results: Path,
    probe_results: Path,
) -> Json:
    selection, plan, probe_plan = read(selection_path), read(fit_plan_path), read(probe_plan_path)
    if campaign.sha256(selection_path) != plan["selection_sha256"]:
        raise ValueError("summary selection changed")
    if (
        probe_plan["fit_plan_sha256"] != campaign.sha256(fit_plan_path)
        or probe_plan["selection_sha256"] != campaign.sha256(selection_path)
        or probe_plan["source_commit"] != plan["source_commit"]
    ):
        raise ValueError("summary probe plan belongs to another replay")
    probe_tasks = {task["original_task_id"]: task for task in probe_plan["tasks"]}
    rows = []
    for task in plan["tasks"]:
        path = fit_results / task["task_id"] / "_task.json"
        row: Json = {
            "original_task_id": task["original_task_id"],
            "replay_group": task["replay_group"],
        }
        if not path.exists():
            row["execution_status"] = "missing"
        else:
            record = read(path)
            if record["task_sha256"] != campaign.task_digest(task):
                raise ValueError("summary task identity differs")
            row.update(
                execution_status=record["status"],
                exit_code=record["exit_code"],
                wall_seconds=record["wall_seconds"],
                cpu_seconds=record["cpu_seconds"],
                task_record_sha256=campaign.sha256(path),
            )
            if record["status"] in {"resolved", "scientific_failure"}:
                if (
                    record["source"]["commit"] != plan["source_commit"]
                    or record["source"]["tracked_changes"]
                ):
                    raise ValueError("summary fit source differs")
                p = path.parent / record["attempt"] / task["result_path"]
                if campaign.sha256(p) != record["output_sha256"][task["result_path"]]:
                    raise ValueError("summary fit receipt differs")
                receipt = read(p)
                if (
                    receipt["source"]["commit"] != plan["source_commit"]
                    or receipt["source"]["working_tree_changes"]
                ):
                    raise ValueError("summary fit receipt source differs")
                row.update(
                    failure_class=receipt["failure_class"],
                    message=receipt["message"],
                    errors=receipt.get("errors", []),
                    messages=receipt.get("messages", []),
                    family_status={
                        k: {
                            key: v[key]
                            for key in ("status", "failure", "profile_nodes")
                            if key in v
                        }
                        for k, v in receipt["families"].items()
                    },
                    search_failure=receipt.get("search", {}).get("failure"),
                    cost=receipt.get("cost", {}),
                    receipt_sha256=campaign.sha256(p),
                )
        rows.append(row)
    probes = []
    for selected in selection["nonregression"]:
        path = probe_results / ("repair-probe-" + selected["task_id"]) / "_task.json"
        row = {"original_task_id": selected["task_id"], "status": "missing"}
        if path.exists():
            record = read(path)
            expected_task = probe_tasks.get(selected["task_id"])
            if expected_task is None or record["task_sha256"] != campaign.task_digest(
                expected_task
            ):
                raise ValueError("summary probe task identity differs")
            row.update(status=record["status"], wall_seconds=record["wall_seconds"])
            if record["status"] == "completed":
                if (
                    record["source"]["commit"] != plan["source_commit"]
                    or record["source"]["tracked_changes"]
                ):
                    raise ValueError("summary probe source differs")
                p = path.parent / record["attempt"] / "probe/receipt.json"
                if campaign.sha256(p) != record["output_sha256"]["probe/receipt.json"]:
                    raise ValueError("summary probe receipt differs")
                result = read(p)
                if (
                    result["source_commit"] != plan["source_commit"]
                    or result["baseline_sha256"] != selected["baseline_receipt_sha256"]
                    or result["baseline_search_sha256"]
                    != selected["baseline_search_receipt_sha256"]
                ):
                    raise ValueError("summary comparison references differ")
                row.update(
                    status=result["status"],
                    receipt_sha256=campaign.sha256(p),
                    failed_checks=result.get("failed_checks", []),
                    errors=result.get("errors", []),
                    required_anchor_count=result.get("required_anchor_count"),
                    completed_anchor_count=len(result.get("anchors", [])),
                )
        probes.append(row)
    return {
        "schema": "solver-repair-replay-summary-v1",
        "source_commit": plan["source_commit"],
        "selection_sha256": campaign.sha256(selection_path),
        "fit_replays": rows,
        "fit_execution_counts": dict(Counter(r["execution_status"] for r in rows)),
        "nonregression_probes": probes,
        "all_nonregression_passed": len(probes) == 24
        and all(r["status"] == "passed" for r in probes),
        "qualification_pass": False,
        "development_replay_is_gate": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select")
    select.add_argument("--original-results", type=Path, required=True)
    select.add_argument("--snapshot", type=Path, required=True)
    select.add_argument("--baseline-cache", type=Path, required=True)
    select.add_argument("--output", type=Path, required=True)
    fits = commands.add_parser("fits")
    fits.add_argument("--selection", type=Path, required=True)
    fits.add_argument("--original-results", type=Path, required=True)
    fits.add_argument("--candidate-commit", required=True)
    fits.add_argument("--output-dir", type=Path, required=True)
    probes = commands.add_parser("probes")
    probes.add_argument("--selection", type=Path, required=True)
    probes.add_argument("--original-results", type=Path, required=True)
    probes.add_argument("--fits-plan", type=Path, required=True)
    probes.add_argument("--fit-results", type=Path, required=True)
    probes.add_argument("--checkpoint-root", type=Path, required=True)
    probes.add_argument("--output-dir", type=Path, required=True)
    summary = commands.add_parser("summary")
    summary.add_argument("--selection", type=Path, required=True)
    summary.add_argument("--fits-plan", type=Path, required=True)
    summary.add_argument("--probe-plan", type=Path, required=True)
    summary.add_argument("--fit-results", type=Path, required=True)
    summary.add_argument("--probe-results", type=Path, required=True)
    summary.add_argument("--output", type=Path, required=True)
    run_fit = commands.add_parser("run-fit")
    run_fit.add_argument("--candidate-commit", required=True)
    run_fit.add_argument("fit_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command == "select":
        write(
            args.output, frozen_selection(args.original_results, args.snapshot, args.baseline_cache)
        )
    elif args.command == "fits":
        imported_source_check(args.candidate_commit)
        prepare_fits(args.selection, args.original_results, args.candidate_commit, args.output_dir)
    elif args.command == "probes":
        imported_source_check(read(args.fits_plan)["source_commit"])
        prepare_probes(
            args.selection,
            args.original_results,
            args.fits_plan,
            args.fit_results,
            args.checkpoint_root,
            args.output_dir,
        )
    elif args.command == "summary":
        write(
            args.output,
            summarize(
                args.selection,
                args.fits_plan,
                args.probe_plan,
                args.fit_results,
                args.probe_results,
            ),
        )
    else:
        import fit_dataset

        imported_source_check(args.candidate_commit)
        if not Path(fit_dataset.__file__).resolve().is_relative_to(ROOT):
            raise ValueError("fit adapter is outside the candidate checkout")
        forwarded = args.fit_args[1:] if args.fit_args[:1] == ["--"] else args.fit_args
        sys.argv = [str(Path(fit_dataset.__file__)), *forwarded]
        raise SystemExit(fit_dataset.main())


if __name__ == "__main__":
    main()
