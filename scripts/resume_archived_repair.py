"""Recover only the two frozen a77e849 fits whose complete searches survived.

The adapter is separate from the numerical checkout. It restores hash-bound
complete search state, forbids further search operations and invokes the
unchanged historical fit entry point for the remaining families and audit.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, ClassVar, cast

FROZEN = "a77e849ce0b0381b5c378b222bacfadce9beaf96"
CASE_BINDINGS = {
    "fit-q-base-corridor-0-increased_heterogeneity-mu0.001-h1-C-dense": {
        "task_sha256": "53c54d7a557ba60a89a604d562b84833da520e5b50535d30470a15f6fbb3e1f0",
        "_started.json": "c975b2bdaaaad8754a768ecb6c8272ef4836497e5fae1496aee9eaa3456692ae",
        "fit/search_receipt.json": (
            "ecce3ec4a9cb6d7bdef0815108ab95e818557dc1081ee66ec4f75e38b9f9128b"
        ),
        "fit/search/evaluations.jsonl": (
            "5fff9614ba398949271e5855eb14f9f00838b8f7a022e9088983757f6e06e780"
        ),
    },
    "fit-q-base-corridor-2-b100_anchor-mu0.004-h1-C-dense": {
        "task_sha256": "b160936f33dfa6de28d5715fecf1c99d2f29528160fc180927ae0933bb3ce72c",
        "_started.json": "d2680a909012fbca9c06116b633016172c8613add265ea5fbf5e48321f946c5e",
        "fit/search_receipt.json": (
            "de304151183cf375e552d25344d0a24c3413e08528c29f0bce92ef3ed4335887"
        ),
        "fit/search/evaluations.jsonl": (
            "7ee64c836764fccc8b1c3b5b9078b6fed0adc6ebbdc98dc0397e72d9df2fb42f"
        ),
    },
}
SNAPSHOT_FIELDS = {
    "free",
    "points",
    "maximum",
    "mesh_log_h",
    "tight_mesh_log_h",
    "midpoint_triggers",
    "closure_history",
    "backend_diagnostics",
    "criterion_stats",
    "cost",
    "evaluation_stream",
}


class RecoveryExecutionError(SystemExit):
    """Abort recovery outside the historical solver's Exception handlers."""


def sha(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def compact(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "candidates"}


def restore_rows(snapshot: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    if snapshot.get("status") != "profile_numerically_resolved":
        raise ValueError("historical search is not complete and resolved")
    points: dict[bool, dict[float, Any]] = {False: {}, True: {}}
    free: dict[bool, Any] = {}
    last, fixed = 0.0, 0
    for event in events:
        elapsed = event["elapsed_seconds"]
        if not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed) or elapsed < last:
            raise ValueError("historical event clock is invalid or reordered")
        last = elapsed
        fit = event["fit"]
        if not isinstance(fit.get("candidates"), list) or not fit["candidates"]:
            raise ValueError("historical event lacks complete candidate history")
        if event["kind"] == "fixed_fit":
            tight = fit["tight"]
            if not isinstance(tight, bool):
                raise ValueError("historical point regime is invalid")
            points[tight][fit["log_h"]] = fit
            fixed += 1
        elif event["kind"] == "free_fit":
            tight = event["tight"]
            if not isinstance(tight, bool):
                raise ValueError("historical free regime is invalid")
            free[tight] = fit
        else:
            raise ValueError("unsupported historical event kind")
    projected_points = {
        str(t): [compact(row) for _, row in sorted(group.items())] for t, group in points.items()
    }
    projected_free = {str(t): compact(row) for t, row in free.items()}
    if canonical(projected_points) != canonical(snapshot["points"]):
        raise ValueError("event points differ from complete search receipt")
    if canonical(projected_free) != canonical(snapshot["free"]) or set(free) != {False, True}:
        raise ValueError("event free fits differ from complete search receipt")
    cost = snapshot["cost"]
    if fixed != cost["total_fixed_fit_events"] or fixed != cost["search"]["fixed_fit_events"]:
        raise ValueError("historical fixed-fit event count differs")
    if last > cost["search"]["elapsed_seconds"]:
        raise ValueError("historical event clock exceeds completed search")
    for tight, key in ((False, "level_sets"), (True, "tight_level_sets")):
        if 0.0 not in points[tight]:
            raise ValueError("historical search lacks its null point")
        for level in snapshot[key]:
            if any(root["log_h"] not in points[tight] for root in level["roots"]):
                raise ValueError("historical search lacks a retained cutoff root")
    return {"points": points, "free": free, "fixed_fit_events": fixed}


def inspect_archive(case: str, attempt: Path) -> dict[str, Any]:
    if (attempt / "fit/receipt.json").exists():
        raise ValueError("historical attempt already has a terminal fit receipt")
    binding = CASE_BINDINGS[case]
    hashes = {}
    for name in ("_started.json", "fit/search_receipt.json", "fit/search/evaluations.jsonl"):
        actual = sha(attempt / name)
        if actual != binding[name]:
            raise ValueError(f"frozen historical file differs: {name}")
        hashes[name] = actual
    started = json.loads((attempt / "_started.json").read_text())
    task = started["task"]
    digest = hashlib.sha256(canonical(task)).hexdigest()
    if digest != binding["task_sha256"] or digest != started["task_sha256"]:
        raise ValueError("historical task digest differs")
    if task["source_commit"] != FROZEN or task["original_task_id"] != case:
        raise ValueError("historical task source or case differs")
    if task["replay_group"] != "development_failed" or task["task_id"] != "repair-" + case:
        raise ValueError("historical task is outside the recovery scope")
    snapshot = json.loads((attempt / "fit/search_receipt.json").read_text())
    if snapshot["evaluation_stream"]["sha256"] != hashes["fit/search/evaluations.jsonl"]:
        raise ValueError("search receipt does not bind the historical event stream")
    events = [
        json.loads(line)
        for line in (attempt / "fit/search/evaluations.jsonl").read_text().splitlines()
    ]
    state = restore_rows(snapshot, events)
    return {
        "task": task,
        "snapshot": snapshot,
        "state": state,
        "archive_sha256": hashes,
        "task_sha256": digest,
    }


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=root)


def verify_source(root: Path) -> dict[str, str]:
    if git(root, "rev-parse", "HEAD").decode().strip() != FROZEN:
        raise ValueError("historical numerical checkout is not pinned at a77e849")
    if git(root, "status", "--porcelain", "--untracked-files=no").strip():
        raise ValueError("historical numerical checkout has tracked changes")
    names = (
        git(
            root,
            "ls-tree",
            "-r",
            "--name-only",
            FROZEN,
            "src/latent_landscapes",
            "scripts",
            "pyproject.toml",
            "uv.lock",
        )
        .decode()
        .splitlines()
    )
    hashes = {}
    for name in names:
        if not name.endswith(".py") and name not in ("pyproject.toml", "uv.lock"):
            continue
        expected = hashlib.sha256(git(root, "show", FROZEN + ":" + name)).hexdigest()
        if sha(root / name) != expected:
            raise ValueError(f"historical numerical source file differs: {name}")
        hashes[name] = expected
    if (
        "scripts/fit_dataset.py" not in hashes
        or "src/latent_landscapes/spatial_profile.py" not in hashes
    ):
        raise ValueError("historical numerical source inventory is incomplete")
    return hashes


def verify_imports(root: Path, hashes: dict[str, str]) -> None:
    names = {
        "fit_dataset",
        "run_development_profile",
        "qualify_spatial_profiles",
        "benchmark_spatial_profile",
        "mode_diagnosis",
        "profile_level_sets",
        "prepare_solver_repair_replay",
    }
    for name, module in sys.modules.copy().items():
        if name not in names and not name.startswith(("latent_landscapes", "pbs")):
            continue
        path = getattr(module, "__file__", None)
        if path is None:
            continue
        path = Path(path).resolve()
        if not path.is_relative_to(root) or str(path.relative_to(root)) not in hashes:
            raise ValueError(f"historical import is outside the verified source: {name}")


def restored_search_class(base: type, archive: dict[str, Any], attempt: Path) -> type:
    """Subclass the verified runtime-loaded historical class, not the live candidate."""

    class HistoricalSearch(base):  # type: ignore[misc]
        blocked_operations: ClassVar[list[str]] = []

        def run(self) -> dict[str, Any]:
            snapshot, state = archive["snapshot"], archive["state"]
            if self.mode != snapshot["mode"] or list(self.cutoffs) != snapshot["cutoffs"]:
                raise ValueError("historical search mode or cutoffs differ")
            self.points, self.free = copy.deepcopy(state["points"]), copy.deepcopy(state["free"])
            self.result = {
                k: copy.deepcopy(v) for k, v in snapshot.items() if k not in SNAPSHOT_FIELDS
            }
            self.mesh, self.tight_mesh = snapshot["mesh_log_h"][:], snapshot["tight_mesh_log_h"][:]
            self.midpoint_triggers = copy.deepcopy(snapshot["midpoint_triggers"])
            self.closure_history = copy.deepcopy(snapshot["closure_history"])
            self.search_cost = copy.deepcopy(snapshot["cost"]["search"])
            self.post_search_seconds = snapshot["cost"]["post_search_seconds"]
            self.fixed_fit_events = state["fixed_fit_events"]
            self.stats.clear()
            self.stats.update(copy.deepcopy(snapshot["backend_diagnostics"]))
            self.criterion.stats.clear()
            self.criterion.stats.update(copy.deepcopy(snapshot["criterion_stats"]))
            shutil.copyfile(attempt / "fit/search/evaluations.jsonl", self.events)
            if sha(self.events) != archive["archive_sha256"]["fit/search/evaluations.jsonl"]:
                raise RecoveryExecutionError("historical event stream changed during recovery")
            return cast(dict[str, Any], self.receipt())

        def point(
            self,
            log_h: float,
            *,
            tight: bool = False,
            refresh: bool = False,
            direction: str | None = None,
        ) -> dict[str, Any]:
            if refresh or direction is not None or float(log_h) not in self.points[tight]:
                self.blocked_operations.append("point")
                raise RecoveryExecutionError(
                    "historical recovery forbids a new or refreshed search point"
                )
            return cast(dict[str, Any], self.points[tight][float(log_h)])

        def fit_free(self, *, tight: bool = False) -> None:
            self.blocked_operations.append("fit_free")
            raise RecoveryExecutionError("historical recovery forbids a free search refit")

    return HistoricalSearch


def write(path: Path, value: Any) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def recover(
    case: str, attempt: Path, root: Path, output: Path, adapter_sha256: str
) -> dict[str, Any]:
    if sha(Path(__file__)) != adapter_sha256:
        raise ValueError("recovery adapter differs from its execution freeze")
    archive = inspect_archive(case, attempt)
    root, output, attempt = root.resolve(), output.resolve(), attempt.resolve()
    if output.is_relative_to(attempt) or output.is_relative_to(root):
        raise ValueError(
            "recovery output must be outside the archived attempt and numerical checkout"
        )
    if output.exists():
        raise FileExistsError(output)
    task = archive["task"]
    if root != Path(task["candidate_import_root"]).resolve():
        raise ValueError("historical import root differs from the original task")
    hashes = verify_source(root)
    verify_imports(root, hashes)
    sys.path[:0] = [str(root / "scripts"), str(root / "src")]
    fit: Any = importlib.import_module("fit_dataset")
    campaign = importlib.import_module("pbs.campaign")
    verify_imports(root, hashes)
    campaign.verify_source(task)
    campaign.verify_runtime(task)
    campaign.verify_inputs(task)
    if any(os.environ.get(name) != "1" for name in fit.THREAD_ENVIRONMENT):
        raise ValueError("historical numerical thread environment differs")
    forwarded = task["original_fit_argv"][2:]
    parser = argparse.ArgumentParser()
    for name in ("input-dir", "observations", "arrival-bank", "compressed-bank", "output-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--search", choices=("dense", "lean"), required=True)
    parser.add_argument("--exhaustive-audit", action="store_true")
    args = parser.parse_args(forwarded)
    args.output_dir = output / "fit"
    output.mkdir(parents=True)
    args.output_dir.mkdir()
    shutil.copyfile(attempt / "_started.json", output / "original-started.json")
    shutil.copyfile(attempt / "fit/search_receipt.json", output / "original-search-receipt.json")
    report = {
        "schema": "historical-repair-recovery-v1",
        "status": "started",
        "case": case,
        "numerical_source_commit": FROZEN,
        "adapter_sha256": adapter_sha256,
        "archive_sha256": archive["archive_sha256"],
        "task_sha256": archive["task_sha256"],
        "source_file_sha256": hashes,
        "runtime": task["runtime"],
        "input_sha256": task["input_sha256"],
        "python": sys.version,
        "platform": platform.platform(),
        "search_refits_allowed": False,
        "original_attempt_preserved": True,
        "execution_scope": "complete historical search reused; original remaining stages rerun",
        "reused_search_elapsed_seconds": archive["snapshot"]["cost"]["search"]["elapsed_seconds"],
    }
    report_path = output / "recovery.json"
    write(report_path, report)
    original = fit.FitSearch
    restored: Any = restored_search_class(original, archive, attempt)
    fit.FitSearch = restored
    try:
        receipt = fit.fit_dataset(args)
        if restored.blocked_operations:
            raise RecoveryExecutionError(
                "historical continuation requested an unretained search operation"
            )
        verify_source(root)
        verify_imports(root, hashes)
        campaign.verify_inputs(task)
        campaign.verify_runtime(task)
        report.update(status="completed", failure_class=receipt["failure_class"])
    except BaseException as error:
        report.update(
            status="execution_failure"
            if isinstance(error, RecoveryExecutionError)
            else "interrupted_or_failed",
            error_type=type(error).__name__,
            error=str(error),
        )
        write(report_path, report)
        raise
    finally:
        fit.FitSearch = original
    report["output_sha256"] = {
        str(path.relative_to(output)): sha(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path != report_path
    }
    write(report_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "run"))
    parser.add_argument("--case", choices=sorted(CASE_BINDINGS), required=True)
    parser.add_argument("--archived-attempt", type=Path, required=True)
    parser.add_argument("--pinned-repo", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--adapter-sha256")
    args = parser.parse_args()
    if args.command == "inspect":
        archive = inspect_archive(args.case, args.archived_attempt)
        result = {
            "case": args.case,
            "archive_sha256": archive["archive_sha256"],
            "task_sha256": archive["task_sha256"],
            "point_counts": {str(t): len(v) for t, v in archive["state"]["points"].items()},
            "fixed_fit_events": archive["state"]["fixed_fit_events"],
            "runtime_and_numerical_source_checked": False,
        }
    else:
        if not all((args.pinned_repo, args.output_dir, args.adapter_sha256)):
            parser.error("run requires --pinned-repo, --output-dir and --adapter-sha256")
        result = recover(
            args.case, args.archived_attempt, args.pinned_repo, args.output_dir, args.adapter_sha256
        )
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
