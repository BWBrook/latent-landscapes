from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def segments(monkeypatch):
    directory = Path(__file__).resolve().parents[1] / "scripts/pbs"
    monkeypatch.syspath_prepend(str(directory))
    return importlib.import_module("submit_fit_segments")


def test_three_native_afterany_arrays_use_distinct_logs_and_fixed_resources(
    segments, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        segments.campaign,
        "load_tasks",
        lambda _: [{"max_segments": 3, "result_schema": "fit-dataset-v1"} for _ in range(51)],
    )
    env = {name: str(tmp_path / name) for name in segments.ENVIRONMENT}
    plan = segments.commands(
        tmp_path / "tasks.jsonl", tmp_path / "out", "science@example.invalid", env
    )
    assert len(plan) == 3
    assert all(cmd[cmd.index("-J") + 1] == "0-50" for cmd in plan)
    assert all("walltime=48:00:00" in cmd and "select=1:ncpus=1:mem=4gb" in cmd for cmd in plan)
    assert all("-h" in cmd and cmd[cmd.index("-m") + 1] == "aj" for cmd in plan)
    assert "-W" not in plan[0]
    assert plan[1][plan[1].index("-W") + 1] == "depend=afterany:{segment_1_job}"
    assert plan[2][plan[2].index("-W") + 1] == "depend=afterany:{segment_2_job}"
    assert len({cmd[cmd.index("-o") + 1] for cmd in plan}) == 3


def test_submission_records_every_held_job_before_any_release(segments, monkeypatch, tmp_path):
    calls, count = [], iter(range(101, 104))

    def qsub(cmd, **kwargs):
        calls.append(cmd)
        return f"{next(count)}[].cluster\n"

    monkeypatch.setattr(segments.subprocess, "check_output", qsub)
    monkeypatch.setattr(segments.subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))
    plan = [
        ["qsub"],
        ["qsub", "depend=afterany:{segment_1_job}"],
        ["qsub", "depend=afterany:{segment_2_job}"],
    ]
    journal = tmp_path / "journal.jsonl"
    assert segments.submit(plan, journal) == ["101[].cluster", "102[].cluster", "103[].cluster"]
    assert [c[0] for c in calls] == ["qsub"] * 3 + ["qrls"] * 3
    assert calls[1][-1] == "depend=afterany:101[].cluster"
    records = [json.loads(line) for line in journal.read_text().splitlines()]
    assert [r["submitted_held"] for r in records[:3]] == [
        "101[].cluster",
        "102[].cluster",
        "103[].cluster",
    ]


def test_partial_submission_keeps_jobs_held_and_preserves_their_ids(
    segments, monkeypatch, tmp_path
):
    calls = []

    def qsub(cmd, **kwargs):
        calls.append(cmd)
        if len(calls) == 2:
            raise OSError("scheduler unavailable")
        return "101[].cluster\n"

    monkeypatch.setattr(segments.subprocess, "check_output", qsub)
    monkeypatch.setattr(
        segments.subprocess, "run", lambda *args, **kwargs: pytest.fail("released early")
    )
    journal = tmp_path / "journal.jsonl"
    with pytest.raises(OSError, match="scheduler unavailable"):
        segments.submit([["qsub"], ["qsub"]], journal)
    assert json.loads(journal.read_text()) == {"segment": 1, "submitted_held": "101[].cluster"}
