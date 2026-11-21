"""Reconcile the copied task receipts with the registered inputs and PBS accounting."""

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from functools import cache
from pathlib import Path

CANDIDATE = "432bb6e56e672f9e57f2f7bc369546023b07662e"
SELECTION = "099f28d9a45a8a4eb12b103ddaf23714ed3ced72120bb5c9184c9c75e514dfaf"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def digest(record):
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


@cache
def source_digest(name):
    source = subprocess.check_output(["git", "show", f"{CANDIDATE}:{name}"])
    return hashlib.sha256(source).hexdigest()


def verify_checkpoints(folder, task, receipt):
    checkpoints = folder / "checkpoints"
    header = read(checkpoints / "identity.json")
    identity = header["identity"]
    assert header["identity_sha256"] == digest(identity)
    assert header["header_sha256"] == digest(
        {k: v for k, v in header.items() if k != "header_sha256"}
    )
    assert identity["source"] == receipt["source"]
    assert identity["runtime_sif_sha256"] == task["runtime"]["sif_sha256"]
    source = Path(task["candidate_import_root"])
    for name, expected in identity["input_sha256"].items():
        path = Path(name)
        actual = (
            source_digest(str(path.relative_to(source)))
            if path.is_relative_to(source)
            else task["input_sha256"][name]
        )
        assert actual == expected, name
    counts = Counter()
    for group in ("search", "stages"):
        for path in sorted((checkpoints / group).glob("*.json")):
            data = read(path)
            assert data["identity_sha256"] == header["identity_sha256"]
            assert data["payload_sha256"] == digest(data["payload"]), path
            if group == "search" and path.stem == "head":
                committed_operations = data["payload"]["count"]
                continue
            if group == "search":
                i = counts[group]
                assert path.stem == f"operation-{i:06d}" and data["payload"]["operation_index"] == i
            counts[group] += 1
    assert counts["search"] == committed_operations
    assert (checkpoints / "stages/fit_receipt.json").is_file()
    return counts


def seconds(native):
    h, m, s = map(int, native["resources_used.walltime"].split(":"))
    return h * 3600 + m * 60 + s


def uninterrupted_stage_times(receipt, event_file):
    times = {k: stage["wall_seconds"] for k, stage in receipt["cost"]["stages"].items()}
    times["full_fit"] = receipt["cost"]["total_wall_seconds"]
    previous = tight = 0.0
    for line in event_file.read_text().splitlines():
        event = json.loads(line)
        elapsed = event["elapsed_seconds"]
        assert elapsed >= previous
        if (
            event["kind"] in ("fixed_fit", "free_fit")
            and event.get("tight", event.get("fit", {}).get("tight")) is True
        ):
            tight += elapsed - previous
        previous = elapsed
    times["tight_event_intervals"] = tight
    return times


def verify_task(task, directory):
    record = read(directory / "_task.json")
    attempts = sorted(directory.glob("attempt-*"))
    assert attempts and attempts[-1].name == record["attempt"]
    assert len(attempts) <= task.get("max_segments", 1)
    expected_digest = digest(task)
    for attempt in attempts:
        assert read(attempt / "_started.json") == {"task": task, "task_sha256": expected_digest}
    attempt = attempts[-1]
    assert (attempt / "_task.json").read_bytes() == (directory / "_task.json").read_bytes()
    assert record["task"] == task and record["task_sha256"] == expected_digest
    assert record["source"] == {"commit": CANDIDATE, "tracked_changes": []}
    assert record["exit_code"] == 0 and record["error"] is None
    files = {str(path.relative_to(attempt)) for path in attempt.rglob("*") if path.is_file()}
    assert files == set(record["output_sha256"]) | {"_task.json"}
    for name, expected in record["output_sha256"].items():
        assert sha(attempt / name) == expected, (task["task_id"], name)
    result = read(attempt / task["result_path"])
    assert result["schema"] == task["result_schema"]
    return record, result, len(attempts)


def summarize(root):
    raw = root / "raw"
    index = read(raw / "completion-index.json")
    assert (
        index["source_commit"] == CANDIDATE and index["status"] == "completed_for_scientific_review"
    )
    for name, expected in index["files"].items():
        assert sha(raw / name) == expected, name
    assert all(code == 0 for code in index["phase_exit_codes"].values())
    assert not index["errors"] and index["scientific_review_required"]
    assert not any(index[k] for k in ("training_opened", "validation_opened", "qualification_pass"))

    native = read(root / "audit/native-jobs.json")["native_jobs"]
    jobs = {job: fields for group in native.values() for job, fields in group["jobs"].items()}
    assert len(native) == 12 and all(group["exit"] == 0 for group in native.values())
    assert all(row["job_state"] == "F" for row in jobs.values())
    registered = read(raw / "operations/execution-jobs.json")
    assert jobs[registered["completion_email"]]["Exit_status"] == "0"

    inputs = read(root / "audit/input-rehash.json")
    bound_inputs = {}
    fit_outcomes = []
    inventories = Counter()
    branches = Counter()
    checkpoints = Counter()
    actual_iterations = Counter()
    unbroken_timing = Counter()
    summary = read(raw / "replay-summary.json")
    reported = {row["original_task_id"]: row for row in summary["fit_replays"]}
    for phase, count in (("fit", 51), ("probe", 24)):
        plan_dir = raw / (phase + "-plan")
        result_dir = raw / (phase + "-results")
        plan = read(plan_dir / "plan.json")
        assert plan["source_commit"] == CANDIDATE and plan["selection_sha256"] == SELECTION
        assert plan["tasks_sha256"] == sha(plan_dir / "tasks.jsonl")
        tasks = [json.loads(line) for line in (plan_dir / "tasks.jsonl").read_text().splitlines()]
        assert len(tasks) == count and tasks == plan["tasks"]
        assert set(t["task_id"] for t in tasks) == {
            p.name for p in result_dir.iterdir() if p.is_dir()
        }
        for i, task in enumerate(tasks):
            assert task["source_commit"] == CANDIDATE
            for name, expected in task["input_sha256"].items():
                assert bound_inputs.setdefault(name, expected) == expected
            folder = result_dir / task["task_id"]
            record, receipt, attempts = verify_task(task, folder)
            inventories[phase] += len(record["output_sha256"])
            if phase == "probe":
                assert record["status"] == "completed" and receipt["status"] == "passed"
                continue
            assert record["failure_class"] == receipt["failure_class"]
            assert receipt["source"] == {"commit": CANDIDATE, "working_tree_changes": []}
            checkpoints.update(verify_checkpoints(folder, task, receipt))
            rollup = reported[task["original_task_id"]]
            assert rollup["receipt_sha256"] == record["output_sha256"]["fit/receipt.json"]
            assert rollup["failure_class"] == receipt["failure_class"]
            subjobs = [j.replace("[]", f"[{i}]") for j in registered["fit_segments"]]
            terminal_segment = subjobs.index(record["pbs_job_id"]) + 1
            assert terminal_segment <= attempts <= task["max_segments"]
            statuses = [int(jobs[j]["Exit_status"]) for j in subjobs]
            assert all(code != 0 for code in statuses[: terminal_segment - 1])
            assert all(code == 0 for code in statuses[terminal_segment - 1 :])
            omitted_seconds = 0
            if terminal_segment < attempts:
                assert (terminal_segment, attempts) == (1, 2)
                previous = folder / "attempt-0001"
                assert not (previous / "_task.json").exists()
                assert receipt["checkpoint_origin_host"] != record["host"]
                events = previous / "fit/search/evaluations.jsonl"
                omitted_seconds = max(
                    json.loads(line)["elapsed_seconds"] for line in events.read_text().splitlines()
                )
            if attempts == 1:
                events = folder / record["attempt"] / "fit/search/evaluations.jsonl"
                unbroken_timing.update(uninterrupted_stage_times(receipt, events))
            stats = receipt["cost"]["criterion_stats"]
            hist = {
                k.removeprefix("mode_branch_converged_iterations_"): v
                for k, v in stats.items()
                if k.startswith("mode_branch_converged_iterations_")
            }
            actual_iterations.update(hist)
            branches.update(
                {
                    k: stats.get(k, 0)
                    for k in (
                        "mode_branch_calls",
                        "mode_branch_termination_converged",
                        "mode_branch_invalid_trial_rejections",
                        "mode_failures",
                        "pd_failures",
                    )
                }
            )
            fit_outcomes.append(
                dict(
                    task=task["original_task_id"],
                    group=task["replay_group"],
                    outcome=receipt["failure_class"],
                    reason=receipt["message"],
                    attempts=attempts,
                    terminal_pbs_segment=terminal_segment,
                    native_exit_codes=statuses,
                    allocation_seconds=[seconds(jobs[j]) for j in subjobs],
                    earlier_wall_seconds_missing_from_pbs_at_least=omitted_seconds,
                    invalid_inner_trials=stats.get("mode_branch_invalid_trial_rejections", 0),
                    converged_branch_iterations=hist,
                    fit_sha256=rollup["receipt_sha256"],
                )
            )
    assert inputs["files"] == bound_inputs and not inputs["hash_mismatches"]
    assert sum(actual_iterations.values()) == branches["mode_branch_termination_converged"]
    return dict(
        source_commit=CANDIDATE,
        completion_index_sha256=sha(raw / "completion-index.json"),
        selection_sha256=SELECTION,
        target_input_files=len(bound_inputs),
        checkpoint_payloads=dict(checkpoints),
        target_input_bytes=inputs["unique_bytes"],
        output_files_verified=dict(inventories),
        branch_counts=dict(branches),
        branch_iteration_histogram=dict(actual_iterations),
        uninterrupted_stage_seconds=dict(unbroken_timing),
        native_graph_seconds=sum(
            seconds(row) for row in jobs.values() if "resources_used.walltime" in row
        ),
        fit_outcomes=fit_outcomes,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.evidence_directory), sort_keys=True, indent=2))
