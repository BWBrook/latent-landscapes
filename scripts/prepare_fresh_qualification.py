"""Freeze the next qualification replicate and adapt the registered phase planner."""

from __future__ import annotations

import argparse
import importlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

NUMERIC_BASE = "432bb6e56e672f9e57f2f7bc369546023b07662e"
REPLICATE = 1
RUNTIME_SHA256 = "e71239ad4246ba7a1037d3dd3bc3d29667b7c3081992d95ab33d5d979e3f12ce"
RUNTIME_OCI = "docker://ghcr.io/astral-sh/uv@sha256:9aa60c50016c0485636ab9a830246a6ef3399aa4a8bab3d17ef4a2358fba2ca7"
COUNTS = {"banks": 18, "histories": 207, "fits": 486, "audits": 468, "integration": 9}
Json = dict[str, Any]


def read(path: Path) -> Json:
    return json.loads(path.read_text())


def next_replicate(old: Json) -> Json:
    """Keep every registered design field and advance the sole replicate coordinate."""
    if len(old["datasets"]) != 207 or old["address_namespace"] != 5:
        raise ValueError("not the registered 207-row qualification panel")
    rows = []
    for row in old["datasets"]:
        address = row["address"]
        if len(address) != 6 or address[0] != 5 or address[-1] != 0:
            raise ValueError("old qualification row has an unexpected history address")
        rows.append({**row, "address": [*address[:-1], REPLICATE]})
    return {**old, "datasets": rows}


def load_producer(candidate: Path, source_commit: str) -> Any:
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("full frozen source commit required")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", NUMERIC_BASE, source_commit],
        cwd=candidate,
        check=True,
    )
    sys.path[:0] = [str(candidate / "scripts"), str(candidate / "src")]
    producer = importlib.import_module("prepare_sprint2_campaign")
    for module in (
        producer,
        producer.campaign,
        importlib.import_module("generate_history"),
        importlib.import_module("latent_landscapes"),
    ):
        if not Path(module.__file__).resolve().is_relative_to(candidate):
            raise ValueError("qualification imports must resolve within the candidate checkout")
    producer.campaign.verify_source({"source_commit": source_commit})
    return producer


def check_source_runtime(producer: Any, runtime_path: Path, python: str, commit: str) -> None:
    runtime = read(runtime_path)
    if (runtime["sif_sha256"], runtime["oci_uri"]) != (RUNTIME_SHA256, RUNTIME_OCI):
        raise ValueError("original Kunanyi SIF and OCI image required")
    if runtime["source_commit"] != commit or python != runtime["python_executable"]:
        raise ValueError("runtime receipt and interpreter must bind the accepted source")
    producer.campaign.verify_runtime(
        {"runtime": {"context": "apptainer", "python": python, "sif_sha256": RUNTIME_SHA256}}
    )


def check_map_paths(producer: Any, root: Path) -> None:
    root = root.resolve(strict=True)
    if {"training", "validation"}.intersection(p.lower() for p in root.parts):
        raise ValueError("only the registered qualification-map directory can be opened")
    for row in read(producer.MAP_MANIFEST)["maps"]:
        directory = root / f"{row['archetype']}-{row['map_index']}"
        for name in producer.MAP_FILES:
            target = (directory / name).resolve(strict=True)
            if not target.is_relative_to(root):
                raise ValueError("qualification map payload resolves outside its staged root")


def memoise_input_hashes(producer: Any) -> Any:
    original = producer.campaign.sha256
    cached: dict[Path, tuple[Any, str]] = {}

    def signature(path: Path) -> tuple[int, ...]:
        info = path.stat()
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns

    def digest(path: Path) -> str:
        path = path.resolve(strict=True)
        witness = signature(path)
        if path not in cached:
            cached[path] = witness, original(path)
        prior, value = cached[path]
        if witness != prior or signature(path) != witness:
            raise ValueError(f"input changed while preparing the qualification plan: {path}")
        return value

    def check() -> None:
        for path, (prior, _) in cached.items():
            if signature(path) != prior:
                raise ValueError(f"input changed before the qualification plan was sealed: {path}")

    producer.campaign.sha256 = digest
    return check


def freeze(producer: Any, args: argparse.Namespace) -> Json:
    old, _ = producer.load_qualification(args.maps_root)
    producer.runtime_context(args)
    from generate_history import family_stream_seeds

    panel = next_replicate(old)
    previous = {tuple(r["address"]) for r in old["datasets"]}
    fresh = {tuple(r["address"]) for r in panel["datasets"]}
    past_seeds = {seed for address in previous for seed in family_stream_seeds(address).values()}
    seeds = [seed for address in sorted(fresh) for seed in family_stream_seeds(address).values()]
    if fresh & previous or past_seeds.intersection(seeds) or len(seeds) != len(set(seeds)):
        raise ValueError("fresh history generator streams overlap")
    args.output.mkdir(parents=True)
    path = args.output / "panel.json"
    producer.write(path, panel)
    record = {
        "schema": "sprint2-next-qualification-freeze-v1",
        "panel": producer.reference(path),
        "registered_previous_panel": producer.reference(producer.PANEL),
        "registered_map_manifest": producer.reference(producer.MAP_MANIFEST),
        "numerical_base_commit": NUMERIC_BASE,
        "source_commit": args.source_commit,
        "runtime_receipt": producer.reference(args.runtime_receipt),
        "preregistration": [producer.reference(path) for path in args.registration],
        "replicate": REPLICATE,
        "distinct_history_addresses": len(fresh),
        "distinct_history_streams": len(seeds),
        "design": "Nine fixed qualification maps and fixed bank seed recipes; new history streams.",
    }
    producer.write(args.output / "panel-freeze.json", record)
    return record


def bind_panel(producer: Any, args: argparse.Namespace) -> None:
    old_loader = producer.load_qualification
    receipt = read(args.freeze)
    for ref in [receipt["panel"], receipt["runtime_receipt"], *receipt["preregistration"]]:
        if producer.reference(Path(ref["path"])) != ref:
            raise ValueError(f"frozen registration/panel/runtime changed: {ref['path']}")
    if (
        receipt["schema"] != "sprint2-next-qualification-freeze-v1"
        or receipt["source_commit"] != args.source_commit
        or receipt["numerical_base_commit"] != NUMERIC_BASE
        or receipt["registered_previous_panel"] != producer.reference(producer.PANEL)
        or receipt["registered_map_manifest"] != producer.reference(producer.MAP_MANIFEST)
        or receipt["runtime_receipt"] != producer.reference(args.runtime_receipt)
        or not receipt["preregistration"]
    ):
        raise ValueError(
            "frozen panel record does not bind the registered design, source and runtime"
        )
    old, maps = old_loader(args.maps_root)
    panel_path = Path(receipt["panel"]["path"])
    fresh = read(panel_path)
    if fresh != next_replicate(old):
        raise ValueError("fresh panel differs outside the prospectively frozen replicate")
    producer.load_qualification = lambda _root: (fresh, maps)
    producer.PANEL, producer.PANEL_SHA256 = panel_path, receipt["panel"]["sha256"]
    original_runtime = producer.runtime_context

    def runtime_context(runtime_args: argparse.Namespace) -> tuple[Json, Json]:
        context, hashes = original_runtime(runtime_args)
        return context, {
            **hashes,
            str(args.freeze.resolve()): producer.campaign.sha256(args.freeze),
        }

    producer.runtime_context = runtime_context


def resumable_fit(task: Json) -> Json:
    python, entry, *argv = task["argv"]
    if entry != "scripts/fit_dataset.py" or task["result_schema"] != "fit-dataset-v1":
        raise ValueError("unexpected producer fit entry point")
    return {
        **task,
        "max_segments": 3,
        "argv": [
            python,
            "scripts/prepare_solver_repair_replay.py",
            "run-fit",
            "--candidate-commit",
            task["source_commit"],
            "--",
            *argv,
            "--checkpoint-dir",
            "{checkpoint_dir}",
        ],
    }


def verify_fixed_bank_pairs(producer: Any, args: argparse.Namespace) -> None:
    plans = [read(path) for path in args.dependency_plan]
    tasks = {task["task_id"]: task for plan in plans for task in plan["tasks"]}
    verifier = producer.verify_independent_banks
    checked = set()

    def verify(left: Path, right: Path) -> None:
        key = left.resolve(), right.resolve()
        if key not in checked:
            verifier(*key)
            checked.add(key)

    producer.verify_independent_banks = verify
    for row in read(producer.MAP_MANIFEST)["maps"]:
        name = f"{row['archetype']}-{row['map_index']}"
        paths = []
        for replicate in (0, 1):
            identifier = producer.bank_id(name, replicate)
            task = tasks[identifier]
            directory = args.results_root / identifier
            result = read(directory / "_task.json")
            producer.campaign.verify_record(task, directory, result)
            if result["status"] != "completed":
                raise ValueError(f"bank failed its verification: {identifier}")
            path = directory / result["attempt"] / task["result_path"]
            manifest = read(path)
            if (
                manifest["map"]["role"] != "qualification"
                or manifest["map"]["spawn_key"] != row["spawn_key"]
                or manifest["bank_replicate"] != replicate
                or manifest["bank_size"] != producer.BANK_SIZE
                or manifest["series_order"] != 192
                or manifest["map_input_sha256"]
                != {
                    filename: producer.campaign.sha256(args.maps_root / name / filename)
                    for filename in producer.MAP_FILES
                }
            ):
                raise ValueError(f"bank design differs: {identifier}")
            paths.append(path)
        verify(*paths)


def prepare(producer: Any, args: argparse.Namespace) -> Json:
    check_inputs = memoise_input_hashes(producer)
    bind_panel(producer, args)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True)
    args.output_dir = output_dir / "registered-planner"
    if args.phase == "fits":
        verify_fixed_bank_pairs(producer, args)
    plan = producer.prepare(args)
    if args.phase in ("banks", "histories", "fits") and (
        len(plan["tasks"]) != COUNTS[args.phase] or plan["pending"]
    ):
        raise ValueError("required input/fit batch is incomplete; original planner evidence saved")
    if args.phase == "fits":
        plan["tasks"] = [resumable_fit(task) for task in plan["tasks"]]
        roles = Counter(t["task_id"].rsplit("-", 1)[-1] for t in plan["tasks"])
        if roles != {"dense": 207, "lean": 207, "independent_bank": 54, "exhaustive": 18}:
            raise ValueError("registered fit role counts changed")
    if (
        args.phase in ("audits", "integration")
        and len(plan["tasks"]) + len(plan["pending"]) != COUNTS[args.phase]
    ):
        raise ValueError("registered auxiliary count changed")
    check_inputs()
    path = output_dir / "tasks.jsonl"
    with path.open("x") as handle:
        for task in plan["tasks"]:
            handle.write(json.dumps(task, sort_keys=True) + "\n")
    producer.campaign.load_tasks(path)
    producer.write(output_dir / "plan.json", plan)
    shutil.copyfile(
        args.output_dir / "qualification-index.json", output_dir / "qualification-index.json"
    )
    return {"phase": args.phase, "ready": len(plan["tasks"]), "pending": len(plan["pending"])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--maps-root", type=Path)
    parser.add_argument("--runtime-receipt", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--python", default=sys.executable)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("design", help="print only the registered design counts, without drawing")
    commands.add_parser("verify-runtime", help="verify the candidate runtime without drawing")
    draw = commands.add_parser("freeze")
    draw.add_argument("--output", type=Path, required=True)
    draw.add_argument("--registration", type=Path, action="append", required=True)
    phase = commands.add_parser("prepare")
    phase.add_argument("phase", choices=(*COUNTS, "index"))
    for name in ("freeze", "results-root", "output-dir"):
        phase.add_argument(f"--{name}", type=Path, required=True)
    phase.add_argument("--dependency-plan", type=Path, action="append", default=[])
    args = parser.parse_args()
    if args.command == "design":
        print(json.dumps({"numerical_base": NUMERIC_BASE, "replicate": REPLICATE, "tasks": COUNTS}))
        return
    if any(value is None for value in (args.candidate, args.runtime_receipt, args.source_commit)):
        parser.error("candidate, source commit and runtime receipt are required")
    args.execution_context = "apptainer"
    producer = load_producer(args.candidate.resolve(), args.source_commit)
    check_source_runtime(producer, args.runtime_receipt, args.python, args.source_commit)
    if args.command == "verify-runtime":
        context, _ = producer.runtime_context(args)
        print(json.dumps({"source_commit": args.source_commit, "runtime": context}))
        return
    if args.maps_root is None:
        parser.error("freeze and prepare require the registered staged maps")
    check_map_paths(producer, args.maps_root)
    print(
        json.dumps(freeze(producer, args) if args.command == "freeze" else prepare(producer, args))
    )


if __name__ == "__main__":
    main()
