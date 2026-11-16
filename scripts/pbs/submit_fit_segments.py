"""Prepare or submit three bounded PBS fit arrays with native afterany dependencies."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

import campaign

ENVIRONMENT = ("LL_REPO", "LL_IMAGE", "LL_PYTHON", "LL_DATA_ROOT", "LL_WORK_ROOT")


def commands(tasks: Path, out: Path, email: str, environment: dict[str, str]) -> list[list[str]]:
    rows = campaign.load_tasks(tasks)
    if not rows or any(
        t.get("max_segments") != 3 or t["result_schema"] != "fit-dataset-v1" for t in rows
    ):
        raise ValueError("every task must be a fit with a frozen three-segment limit")
    values = {name: environment[name] for name in ENVIRONMENT}
    values.update(
        TASKS=str(tasks.resolve()),
        OUT=str(out.resolve()),
        CHUNK="1",
        LL_WORKERS="1",
        LL_RESUME_SEGMENTS="3",
    )
    if any(not value or any(c in value for c in ",\n\r") for value in values.values()):
        raise ValueError("PBS variable values must be nonempty and contain no commas or newlines")
    worker = Path(values["LL_REPO"]) / "scripts/pbs/array.pbs"
    result = []
    for segment in range(1, 4):
        cmd = [
            "qsub",
            "-h",
            "-N",
            f"ll_fit_seg{segment}",
            "-J",
            f"0-{len(rows) - 1}",
            "-l",
            "select=1:ncpus=1:mem=4gb",
            "-l",
            "walltime=48:00:00",
            "-m",
            "aj",
            "-M",
            email,
            "-o",
            str(out.resolve() / f"segment-{segment}-^array_index^.log"),
            "-v",
            ",".join(f"{k}={v}" for k, v in values.items()),
        ]
        if segment > 1:
            cmd += ["-W", f"depend=afterany:{{segment_{segment - 1}_job}}"]
        result.append([*cmd, str(worker)])
    return result


def submit(plan: list[list[str]], journal: Path) -> list[str]:
    jobs: list[str] = []
    with journal.open("x") as handle:
        for index, template in enumerate(plan):
            cmd = [
                value.replace(f"{{segment_{index}_job}}", jobs[-1]) if index else value
                for value in template
            ]
            job = subprocess.check_output(cmd, text=True).strip()
            handle.write(json.dumps({"segment": index + 1, "submitted_held": job}) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            if not re.fullmatch(r"[0-9]+\[\](?:\.[A-Za-z0-9_.-]+)?", job):
                raise ValueError(
                    "unexpected PBS array job identifier; submitted arrays remain held"
                )
            jobs.append(job)
        for job in jobs:
            subprocess.run(["qrls", job], check=True)
            handle.write(json.dumps({"released": job}) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    return jobs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args()
    plan = commands(args.tasks, args.out, args.email, dict(os.environ))
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "segment-submission.json"
    with path.open("x") as handle:
        json.dump({"tasks_sha256": campaign.sha256(args.tasks), "commands": plan}, handle, indent=2)
        handle.write("\n")
    if args.submit:
        jobs = submit(plan, args.out / "segment-journal.jsonl")
        with (args.out / "segment-jobs.json").open("x") as handle:
            json.dump(
                {"jobs": jobs, "completion_dependency": f"afterany:{jobs[-1]}"}, handle, indent=2
            )
            handle.write("\n")


if __name__ == "__main__":
    main()
