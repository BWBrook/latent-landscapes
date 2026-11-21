"""Exercise a real interrupted numerical audit on the registered development task."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

import run_interrupted_twin as legacy

ROOT = Path(__file__).resolve().parents[1]
TASK = "fit-q-base-barrier-0-increased_heterogeneity-mu0.004-h1-A-exhaustive"
RECORD_SHA = "52a0a3f56b85ea1bc0495d43af801772c24763838aa28d55546e2f86ebfe141a"
PRIOR = "432bb6e56e672f9e57f2f7bc369546023b07662e"
NUMERICAL_ROWS = [72, 73, 74, 75, 146, 147, 148, 149]
STOP = NUMERICAL_ROWS[1]
ROLES = ("reference", "interrupt", "resume", "compare")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def prefix(directory: Path) -> str:
    files = sorted((directory / "audit").glob("row-*.json"))
    require(len(files) >= STOP, "incomplete durable audit prefix")
    committed = files[:STOP]
    require(
        [p.name for p in committed] == [f"row-{i:06d}.json" for i in range(STOP)],
        "noncontiguous durable audit prefix",
    )
    return legacy.digest([(p.name, legacy.sha(p)) for p in committed])


def output(
    directory: Path, checkpoint: Any, source: str
) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    receipt = directory / "fit/receipt.json"
    fit = legacy.read(receipt)
    search_path = directory / "fit/search_receipt.json"
    search = legacy.read(search_path)
    events_path = directory / "fit/search/evaluations.jsonl"
    require(fit["source"] == {"commit": source, "working_tree_changes": []}, "fit source differs")
    require(fit["failure_class"] == "resolved", "selected development fit did not resolve")
    require(
        Path(fit["search"]["receipt"]) == search_path
        and fit["search"]["receipt_sha256"] == legacy.sha(search_path)
        and Path(search["evaluation_stream"]["path"]) == events_path
        and search["evaluation_stream"]["sha256"] == legacy.sha(events_path),
        "nested search or event identity differs",
    )
    require(
        [i for i, row in enumerate(fit["latent_audit"]["rows"]) if row["performed"]]
        == NUMERICAL_ROWS,
        "real numerical audit locations differ from registration",
    )
    science = {
        kind: checkpoint.digest(checkpoint.scientific_payload(value, artifact=kind))
        for kind, value in (
            ("fit", fit),
            ("search", search),
            ("events", legacy.task_rows(events_path)),
        )
    }
    raw = {p.name: legacy.sha(p) for p in (receipt, search_path, events_path)}
    return fit, science, raw


def interrupt_child(
    cmd: list[str], stage: Path, store: Path, binding: dict[str, Any], job: str
) -> None:
    paused = stage / "paused.json"
    killed = stage / "killed.json"
    child = subprocess.Popen(cmd)
    pid, status = os.waitpid(child.pid, os.WUNTRACED)
    require(
        os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGSTOP,
        "worker failed to pause inside audit",
    )
    try:
        proof = legacy.unseal(paused)
        require(
            proof["binding"] == binding
            and proof["pid"] == pid
            and proof["job"] == job
            and proof["row_index"] == STOP
            and proof["row"]["performed"]
            and proof["prefix_sha256"] == prefix(store)
            and not (stage / "fit/receipt.json").exists()
            and not (store / f"audit/row-{STOP:06d}.json").exists(),
            "invalid live interruption witness",
        )
    finally:
        os.kill(pid, signal.SIGKILL)
        code = child.wait()
    require(code == -signal.SIGKILL, "native worker was not killed by signal 9")
    legacy.seal(killed, {**proof, "signal_exit": code, "pause_sha256": legacy.sha(paused)})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-results", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--role", choices=(*ROLES, "child"), required=True)
    args = parser.parse_args()
    work, role = args.work.resolve(), args.role
    registered = legacy.unseal(work / "jobs.json")
    jobs = registered["jobs"]
    job = os.environ["PBS_JOBID"]
    require(
        set(jobs) == set(ROLES)
        and len(set(jobs.values())) == len(ROLES)
        and registered["source"] == args.source
        and jobs["interrupt" if role == "child" else role] == job,
        "native job or candidate source differs from registration",
    )
    fit, checkpoint, campaign = legacy.pinned_modules(ROOT, args.source)
    prior = args.prior_results.resolve() / ("repair-" + TASK) / "_task.json"
    require(legacy.sha(prior) == RECORD_SHA, "historical task record differs from selection")
    previous = legacy.read(prior)
    task = previous["task"]
    require(
        task["original_task_id"] == TASK
        and task["replay_group"] == "nonregression"
        and task["source_commit"] == PRIOR
        and previous["attempt"] == "attempt-0001",
        "incorrect development task",
    )
    campaign.verify_record(task, prior.parent, previous)
    campaign.verify_runtime(task)
    stage = work / ("interrupt" if role == "child" else role)
    if role != "child":
        stage.mkdir()
    store = (work / ("reference" if role == "reference" else "interrupt")) / "checkpoints"
    binding = {
        "source": args.source,
        "record_sha256": RECORD_SHA,
        "jobs_sha256": legacy.sha(work / "jobs.json"),
    }
    paused = work / "interrupt/paused.json"
    killed = work / "interrupt/killed.json"
    if role == "interrupt":
        cmd = [
            sys.executable,
            __file__,
            "--prior-results",
            str(args.prior_results),
            "--source",
            args.source,
            "--work",
            str(work),
            "--role",
            "child",
        ]
        interrupt_child(cmd, stage, store, binding, job)
        return
    if role == "compare":
        proof = legacy.unseal(killed)
        resume = legacy.unseal(work / "resume/reused.json")
        require(
            proof["binding"] == resume["binding"] == binding
            and proof["job"] == jobs["interrupt"]
            and resume["job"] == jobs["resume"]
            and proof["signal_exit"] == -signal.SIGKILL
            and proof["pause_sha256"] == legacy.sha(paused)
            and proof["prefix_sha256"] == resume["prefix_sha256"] == prefix(store)
            and resume["saved_rows"] == list(range(STOP, 150)),
            "interruption or reuse evidence differs",
        )
        old_dir = prior.parent / previous["attempt"]
        historical, old_science, _ = output(old_dir, checkpoint, PRIOR)
        baseline, base_science, base_raw = output(work / "reference", checkpoint, args.source)
        _, twin_science, twin_raw = output(work / "resume", checkpoint, args.source)
        require(
            base_science == twin_science,
            "resumed scientific records differ from the uninterrupted candidate",
        )
        require(
            old_science["search"] == base_science["search"]
            and old_science["events"] == base_science["events"],
            "new candidate search or event results differ from accepted development source",
        )
        old_repo = Path(task["candidate_import_root"])

        def inventory(value: dict[str, Any], repo: Path) -> dict[str, str]:
            result = {}
            for name, expected in value["input_sha256"].items():
                path = Path(name)
                require(legacy.sha(path) == expected, "fit input digest differs")
                result[str(path.relative_to(repo)) if path.is_relative_to(repo) else str(path)] = (
                    expected
                )
            return result

        old_files, new_files = inventory(historical, old_repo), inventory(baseline, ROOT)
        modified = sorted(k for k in old_files if old_files[k] != new_files.get(k))
        require(
            set(old_files) == set(new_files)
            and set(modified) <= {"scripts/fit_dataset.py", "scripts/run_development_profile.py"},
            "unexpected numerical source or data drift",
        )
        for item in (historical, baseline):
            del item["source"], item["input_sha256"]
        require(
            checkpoint.digest(checkpoint.scientific_payload(historical))
            == checkpoint.digest(checkpoint.scientific_payload(baseline)),
            "new source changed historical scientific output",
        )
        legacy.seal(
            stage / "result.json",
            {
                **binding,
                "passed": True,
                "numerical_rows": NUMERICAL_ROWS,
                "modified_source_files": modified,
                "reference_raw": base_raw,
                "resumed_raw": twin_raw,
                "scientific": base_science,
                "prefix_sha256": proof["prefix_sha256"],
                "kill_receipt_sha256": legacy.sha(killed),
                "reuse_receipt_sha256": legacy.sha(work / "resume/reused.json"),
            },
        )
        return
    saved_rows: list[int] = []
    original_save = checkpoint.FitCheckpoints.save

    def observe(obj: Any, name: str, payload: Any) -> None:
        if name.startswith("audit/row-"):
            index = int(name.split("-")[-1])
            if role == "child" and index == STOP:
                prior_row = obj.load(f"audit/row-{NUMERICAL_ROWS[0]:06d}")
                require(
                    prior_row["row"]["performed"] and payload["row"]["performed"],
                    "expected numerical rows absent",
                )
                legacy.seal(
                    paused,
                    {
                        "binding": binding,
                        "row_index": index,
                        "row": payload["row"],
                        "job": job,
                        "pid": os.getpid(),
                        "prefix_sha256": prefix(store),
                        "identity_sha256": legacy.sha(store / "identity.json"),
                    },
                )
                os.kill(os.getpid(), signal.SIGSTOP)
                raise RuntimeError("interrupted child resumed unexpectedly")
            saved_rows.append(index)
        original_save(obj, name, payload)

    if role in ("child", "resume"):
        checkpoint.FitCheckpoints.save = observe
    if role == "resume":
        proof = legacy.unseal(killed)
        require(
            proof["binding"] == binding
            and proof["prefix_sha256"] == prefix(store)
            and proof["identity_sha256"] == legacy.sha(store / "identity.json")
            and proof["signal_exit"] == -signal.SIGKILL,
            "resume lacks verified killed numerical worker",
        )
    argv = [
        str(stage / "fit") if s == "{attempt_dir}/fit" else s for s in task["original_fit_argv"][2:]
    ]
    sys.argv = ["fit_dataset.py", *argv, "--checkpoint-dir", str(store)]
    if role == "resume":
        sys.argv.append("--resume")
    require(fit.main() == 0, "fit execution failed")
    if role == "resume":
        require(
            saved_rows == list(range(STOP, 150)),
            "resume recomputed a committed location or missed a row",
        )
        legacy.seal(
            stage / "reused.json",
            {
                "binding": binding,
                "job": job,
                "saved_rows": saved_rows,
                "prefix_sha256": prefix(store),
            },
        )


if __name__ == "__main__":
    main()
