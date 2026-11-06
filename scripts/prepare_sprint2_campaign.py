"""Prepare immutable PBS tasks for the frozen 207-case qualification panel.

Run on the staged target checkout after runtime preparation. This command only
checks files and writes plans/indexes; it never generates histories or runs fits.
Use separate output directories for banks, histories, fits, audits, integration and index.
Repeat --dependency-plan for the earlier plan.json files. Dependencies are
admitted only through their verified task receipts; missing evidence stays null.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from generate_history import MAP_FILES, verify_independent_banks
from pbs import campaign

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/paper1-sprint1-2026-11-05"
PANEL = EVIDENCE / "qualification-panel.json"
MAP_MANIFEST = EVIDENCE / "maps/qualification-manifest.json"
PANEL_SHA256 = "51006aa0355ab4ce9f28e572a4272f09c0dc9fcdb52ae6ed0570aacbb1cf240d"
COUNTS = {"base": 162, "boundary": 18, "enriched": 18, "trend": 9}
BANK_SIZE = 131072
Json = dict[str, Any]


def read(path: Path) -> Json:
    return json.loads(path.read_text())


def reference(path: Path) -> Json:
    return {"path": str(path.resolve()), "sha256": campaign.sha256(path)}


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def load_qualification(maps_root: Path) -> tuple[Json, dict[str, Json]]:
    if "validation" in {part.lower() for part in maps_root.resolve().parts}:
        raise ValueError("validation paths must remain unopened")
    if campaign.sha256(PANEL) != PANEL_SHA256:
        raise ValueError("qualification panel differs from the frozen 207-case manifest")
    panel = read(PANEL)
    if panel["map_manifest_sha256"] != campaign.sha256(MAP_MANIFEST):
        raise ValueError("qualification map manifest hash differs from the frozen panel")
    manifest = read(MAP_MANIFEST)
    if manifest["role"] != "qualification" or panel["address_namespace"] != 5:
        raise ValueError("only qualification maps and histories are permitted")
    rows = panel["datasets"]
    if len(rows) != 207 or Counter(r["stratum"] for r in rows) != COUNTS:
        raise ValueError("qualification denominators changed")
    if len({r["dataset_id"] for r in rows}) != len(rows):
        raise ValueError("duplicate dataset identity")
    maps = {}
    for compact in manifest["maps"]:
        if compact["role"] != "qualification" or compact["spawn_key"][0] != 2:
            raise ValueError("validation/development map access is forbidden in this producer")
        name = f"{compact['archetype']}-{compact['map_index']}"
        directory = (maps_root / name).resolve()
        record = read(directory / "record.json")
        if record["role"] != "qualification" or record["status"] != "ok":
            raise ValueError("staged map is not completed qualification geometry")
        for key, value in compact.items():
            actual = (
                hashlib.sha256(json.dumps(record[key.removesuffix("_sha256")]).encode()).hexdigest()
                if key.endswith("_site_ids_sha256")
                else record[key]
            )
            if actual != value:
                raise ValueError(f"staged map identity differs: {name}/{key}")
        for filename, digest in compact["files"].items():
            if campaign.sha256(directory / filename) != digest:
                raise ValueError(f"staged map payload differs: {name}/{filename}")
        maps[name] = {"directory": directory, "record": record}
    if len(maps) != 9 or set(r["map"] for r in rows) != maps.keys():
        raise ValueError("qualification map coverage differs")
    if any(r["address"][0] != 5 for r in rows):
        raise ValueError("non-qualification history address")
    return panel, maps


def runtime_context(args: argparse.Namespace) -> tuple[Json, dict[str, str]]:
    receipt = read(args.runtime_receipt)
    if receipt["schema"] != "sprint2-runtime-v1":
        raise ValueError("runtime preparation receipt required")
    if receipt["source_commit"] != args.source_commit:
        raise ValueError("runtime source differs from candidate commit")
    if args.execution_context != "apptainer" or args.python != receipt["python_executable"]:
        raise ValueError("explicit execution context differs from prepared runtime")
    if not Path(args.python).is_absolute() or not re.fullmatch(
        r"docker://.+@sha256:[0-9a-f]{64}", receipt["oci_uri"]
    ):
        raise ValueError("runtime interpreter/OCI image is not pinned")
    sif = Path(receipt["sif"]).resolve()
    if campaign.sha256(sif) != receipt["sif_sha256"]:
        raise ValueError("SIF changed after runtime preparation")
    lock = ROOT / "uv.lock"
    if campaign.sha256(lock) != receipt["uv_lock_sha256"]:
        raise ValueError("dependency lock differs from prepared runtime")
    context = {
        "context": args.execution_context,
        "python": args.python,
        "sif": str(sif),
        "sif_sha256": receipt["sif_sha256"],
    }
    paths = (PANEL, MAP_MANIFEST, lock, args.runtime_receipt, sif)
    return context, {str(p.resolve()): campaign.sha256(p) for p in paths}


def bank_id(name: str, replicate: int) -> str:
    return f"bank-{name}-r{replicate}"


def history_id(row: Json) -> str:
    return f"history-{row['dataset_id']}"


def fit_id(row: Json, role: str) -> str:
    return f"fit-{row['dataset_id']}-{role}"


def fit_roles(row: Json) -> tuple[str, ...]:
    return (
        ("dense", "lean")
        + (("independent_bank",) if row["independent_bank"] else ())
        + (("exhaustive",) if row["exhaustive_audit"] else ())
    )


def prepare(args: argparse.Namespace) -> Json:
    campaign.verify_source({"source_commit": args.source_commit})
    panel, maps = load_qualification(args.maps_root)
    context, common_inputs = runtime_context(args)
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    dependencies: dict[str, Json] = {}
    dependency_refs = []
    for path in args.dependency_plan:
        prior = read(path)
        if (
            prior["schema"] != "sprint2-task-plan-v1"
            or prior["panel_sha256"] != PANEL_SHA256
            or prior["source_commit"] != args.source_commit
            or prior["runtime"] != context
        ):
            raise ValueError("dependency plan belongs to another candidate/panel/runtime")
        dependency_refs.append(reference(path))
        for task in prior["tasks"]:
            if task["task_id"] in dependencies and dependencies[task["task_id"]] != task:
                raise ValueError("conflicting frozen dependency task")
            dependencies[task["task_id"]] = task
    args.output_dir.mkdir(parents=True)
    tasks: list[Json] = []
    pending: list[Json] = []
    cache: dict[str, tuple[Json | None, str | None]] = {}
    digests = dict(common_inputs)
    verified_banks: set[tuple[str, str, int]] = set()
    verified_pairs: set[tuple[str, str]] = set()

    def digest(path: Path) -> str:
        name = str(path.resolve())
        if name not in digests:
            digests[name] = campaign.sha256(path)
        return digests[name]

    def dependency(identifier: str) -> tuple[Json | None, str | None]:
        if identifier not in cache:
            try:
                task = dependencies[identifier]
                directory = args.results_root / identifier
                record = read(directory / "_task.json")
                campaign.verify_record(task, directory, record)
                if record["source"]["commit"] != args.source_commit:
                    raise ValueError("dependency source differs")
                path = directory / record["attempt"] / task["result_path"]
                cache[identifier] = (
                    {
                        "record": record,
                        "path": path,
                        "result": read(path),
                        "task_receipt": directory / record["attempt"] / "_task.json",
                    },
                    None,
                )
            except (KeyError, TypeError, ValueError, OSError) as exc:
                cache[identifier] = (None, f"{type(exc).__name__}: {exc}")
        return cache[identifier]

    def add(
        identifier: str,
        argv: list[str],
        schema: str,
        result_path: str,
        paths: list[Path],
    ) -> None:
        task = {
            "task_id": identifier,
            "argv": [args.python, *argv],
            "source_commit": args.source_commit,
            "runtime": context,
            "input_sha256": {
                **common_inputs,
                **{str(p.resolve()): digest(p) for p in paths},
            },
            "result_path": result_path,
            "result_schema": schema,
        }
        if identifier in dependencies and dependencies[identifier] != task:
            raise ValueError(f"previously frozen task changed: {identifier}")
        tasks.append(task)

    def ready(identifier: str, needs: list[str], accepted: set[str]) -> list[Json] | None:
        found = []
        problems = {}
        for name in needs:
            dep, error = dependency(name)
            if dep is None or dep["record"]["status"] not in accepted:
                problems[name] = error or dep["record"]["status"]
            else:
                found.append(dep)
        if problems:
            pending.append({"task_id": identifier, "dependencies": problems})
            return None
        return found

    def map_paths(name: str) -> list[Path]:
        return [maps[name]["directory"] / filename for filename in MAP_FILES]

    def bank(dep: Json, row: Json, replicate: int) -> None:
        key = (str(dep["path"]), row["map"], replicate)
        if key in verified_banks:
            return
        result = dep["result"]
        wanted = maps[row["map"]]["record"]
        if (
            result["schema"] != "sprint2-map-arrival-bank-v1"
            or result["bank_replicate"] != replicate
            or result["bank_size"] != BANK_SIZE
            or result["series_order"] != 192
            or result["map"]["role"] != "qualification"
            or result["map"]["spawn_key"] != wanted["spawn_key"]
            or result["map_input_sha256"] != {p.name: digest(p) for p in map_paths(row["map"])}
        ):
            raise ValueError("bank result differs from its frozen map/replicate")
        for key in ("raw", "compressed"):
            if digest(Path(result[key])) != result[f"{key}_sha256"]:
                raise ValueError("bank manifest payload checksum mismatch")
        verified_banks.add((str(dep["path"]), row["map"], replicate))

    def independent_banks(left: Json, right: Json) -> None:
        pair = (str(left["path"]), str(right["path"]))
        if pair not in verified_pairs:
            verify_independent_banks(left["path"], right["path"])
            verified_pairs.add(pair)

    def history(dep: Json, row: Json) -> Path:
        result = dep["result"]
        expected = {"address": row["address"], "background": row["background"], "arm": row["arm"]}
        wanted = maps[row["map"]]["record"]
        if (
            any(result[key] != value for key, value in expected.items())
            or any(result["truth"][key] != row[key] for key in ("mu", "h"))
            or any(
                result["map"][key] != wanted[key]
                for key in ("role", "archetype", "map_index", "seeds")
            )
        ):
            raise ValueError("history identity differs from registered dataset")
        if result["truth"]["detection_sd"] != 0.2 or result["map_input_sha256"] != {
            p.name: digest(p) for p in map_paths(row["map"])
        }:
            raise ValueError("history detection/map identity differs")
        observation = dep["path"].parent / "observations.npz"
        if digest(observation) != result["files"]["observations.npz"]:
            raise ValueError("history observation checksum mismatch")
        return observation

    def fit_inputs(found: list[Json]) -> list[Path]:
        return [
            p
            for dep in found
            for p in (
                dep["path"],
                dep["task_receipt"],
                *(Path(name) for name in dep["record"]["task"]["input_sha256"]),
                *(
                    args.results_root / dep["record"]["task_id"] / dep["record"]["attempt"] / name
                    for name in dep["record"]["output_sha256"]
                ),
            )
        ]

    if args.phase == "banks":
        for name in sorted(maps):
            for replicate in (0, 1):
                add(
                    bank_id(name, replicate),
                    [
                        "scripts/generate_history.py",
                        "--map-dir",
                        str(maps[name]["directory"]),
                        "--build-bank",
                        "--bank-size",
                        str(BANK_SIZE),
                        "--bank-replicate",
                        str(replicate),
                        "--workers",
                        "1",
                        "--output-dir",
                        "{attempt_dir}/bank",
                    ],
                    "sprint2-map-arrival-bank-v1",
                    "bank/manifest.json",
                    map_paths(name),
                )
    if args.phase == "histories":
        for row in panel["datasets"]:
            add(
                history_id(row),
                [
                    "scripts/generate_history.py",
                    "--map-dir",
                    str(maps[row["map"]]["directory"]),
                    "--address",
                    ",".join(map(str, row["address"])),
                    "--background",
                    row["background"],
                    "--mu",
                    str(row["mu"]),
                    "--h",
                    str(row["h"]),
                    "--detection-sd",
                    "0.2",
                    "--arm",
                    row["arm"],
                    "--output-dir",
                    "{attempt_dir}/history",
                ],
                "sprint1-history-v1",
                "history/receipt.json",
                map_paths(row["map"]),
            )
    if args.phase == "fits":
        for row in panel["datasets"]:
            for role in fit_roles(row):
                identifier = fit_id(row, role)
                replicate = int(role == "independent_bank")
                needs = [history_id(row), bank_id(row["map"], replicate)]
                if replicate:
                    needs.append(bank_id(row["map"], 0))
                found = ready(identifier, needs, {"completed"})
                if found is None:
                    continue
                hist, arrival = found[:2]
                bank(arrival, row, replicate)
                if replicate:
                    bank(found[2], row, 0)
                    independent_banks(found[2], arrival)
                observation = history(hist, row)
                argv = [
                    "scripts/fit_dataset.py",
                    "--input-dir",
                    str(maps[row["map"]]["directory"]),
                    "--observations",
                    str(observation.resolve()),
                    "--arrival-bank",
                    arrival["result"]["raw"],
                    "--compressed-bank",
                    arrival["result"]["compressed"],
                    "--search",
                    "dense" if role == "dense" else "lean",
                    "--output-dir",
                    "{attempt_dir}/fit",
                ]
                if role == "exhaustive":
                    argv.append("--exhaustive-audit")
                paths = [
                    *map_paths(row["map"]),
                    observation,
                    Path(arrival["result"]["raw"]),
                    Path(arrival["result"]["compressed"]),
                ]
                paths += [p for dep in found for p in (dep["path"], dep["task_receipt"])]
                add(identifier, argv, "fit-dataset-v1", "fit/receipt.json", paths)
    if args.phase == "audits":
        for row in panel["datasets"]:
            pairs = [("dense_lean", "dense", "lean")]
            if row["independent_bank"]:
                pairs.append(("bank", "lean", "independent_bank"))
            for label, left, right in pairs:
                identifier = f"anchors-{row['dataset_id']}-{label}"
                found = ready(identifier, [fit_id(row, left), fit_id(row, right)], {"resolved"})
                if found is None:
                    continue
                add(
                    identifier,
                    [
                        "scripts/audit_sprint2_pair.py",
                        "anchors",
                        "--kind",
                        "dense_lean" if label == "dense_lean" else "independent_bank",
                        "--left-receipt",
                        str(found[0]["path"].resolve()),
                        "--right-receipt",
                        str(found[1]["path"].resolve()),
                        "--output-dir",
                        "{attempt_dir}/audit",
                    ],
                    "sprint2-common-anchors-v1",
                    "audit/receipt.json",
                    fit_inputs(found),
                )
            identifier = f"gradient-{row['dataset_id']}"
            found = ready(identifier, [fit_id(row, "dense"), fit_id(row, "lean")], {"resolved"})
            if found is not None:
                add(
                    identifier,
                    [
                        "scripts/audit_sprint2_pair.py",
                        "gradients",
                        "--dense-receipt",
                        str(found[0]["path"].resolve()),
                        "--lean-receipt",
                        str(found[1]["path"].resolve()),
                        "--output-dir",
                        "{attempt_dir}/audit",
                    ],
                    "sprint2-free-gradient-v1",
                    "audit/receipt.json",
                    fit_inputs(found),
                )

    if args.phase == "integration":
        for row in panel["datasets"]:
            if not row["integration_screen"]:
                continue
            identifier = f"integration-{row['dataset_id']}"
            found = ready(identifier, [fit_id(row, "lean")], {"resolved", "scientific_failure"})
            if found is not None:
                add(
                    identifier,
                    [
                        "scripts/screen_sprint2_importance.py",
                        "--receipt",
                        str(found[0]["path"].resolve()),
                        "--identity",
                        row["dataset_id"],
                        "--output-dir",
                        "{attempt_dir}/integration",
                    ],
                    "sprint2-integration-screen-v1",
                    "integration/receipt.json",
                    fit_inputs(found),
                )

    index: Json = {
        "schema": "sprint2-qualification-index-v1",
        "panel_sha256": PANEL_SHA256,
        "source_commit": args.source_commit,
        "cases": {},
    }
    evidence_status = {}
    for row in panel["datasets"]:
        entry: Json = {
            "observation_sha256": None,
            "dense": None,
            "lean": None,
            "gradient": None,
            "anchors": {"dense_lean": None},
        }
        hist, _ = dependency(history_id(row))
        if hist is not None and hist["record"]["status"] == "completed":
            entry["observation_sha256"] = digest(history(hist, row))
        roles = {role: fit_id(row, role) for role in fit_roles(row)}
        roles["gradient"] = f"gradient-{row['dataset_id']}"
        roles["anchors.dense_lean"] = f"anchors-{row['dataset_id']}-dense_lean"
        if row["integration_screen"]:
            roles["integration"] = f"integration-{row['dataset_id']}"
        if row["independent_bank"]:
            roles["anchors.bank"] = f"anchors-{row['dataset_id']}-bank"
            entry["bank_identity"] = None
        for role, identifier in roles.items():
            dep, error = dependency(identifier)
            value = (
                reference(dep["path"])
                if dep is not None and dep["record"]["status"] in campaign.TERMINAL
                else None
            )
            evidence_status[identifier] = dep["record"]["status"] if dep is not None else error
            if role.startswith("anchors."):
                entry["anchors"][role.split(".")[1]] = value
            else:
                entry[role] = value
        if row["independent_bank"] and entry["lean"] and entry["independent_bank"]:
            primary, _ = dependency(bank_id(row["map"], 0))
            independent, _ = dependency(bank_id(row["map"], 1))
            if (
                primary is not None
                and independent is not None
                and all(d["record"]["status"] == "completed" for d in (primary, independent))
            ):
                bank(primary, row, 0)
                bank(independent, row, 1)
                independent_banks(primary, independent)
                sidecar = {
                    "schema": "sprint2-bank-identity-v1",
                    "primary_receipt_sha256": entry["lean"]["sha256"],
                    "independent_receipt_sha256": entry["independent_bank"]["sha256"],
                    "primary_manifest": reference(primary["path"]),
                    "independent_manifest": reference(independent["path"]),
                }
                path = args.output_dir / "bank-identities" / f"{row['dataset_id']}.json"
                write(path, sidecar)
                entry["bank_identity"] = reference(path)
        index["cases"][row["dataset_id"]] = entry
    plan = {
        "schema": "sprint2-task-plan-v1",
        "phase": args.phase,
        "source_commit": args.source_commit,
        "panel_sha256": PANEL_SHA256,
        "map_manifest_sha256": campaign.sha256(MAP_MANIFEST),
        "runtime": context,
        "dependency_plans": dependency_refs,
        "tasks": tasks,
        "pending": pending,
        "evidence_status": evidence_status,
        "integration_tasks": 9,
    }
    task_path = args.output_dir / "tasks.jsonl"
    campaign.verify_source({"source_commit": args.source_commit})
    with task_path.open("x") as handle:
        for task in tasks:
            handle.write(json.dumps(task, sort_keys=True) + "\n")
    campaign.load_tasks(task_path)
    write(args.output_dir / "plan.json", plan)
    write(args.output_dir / "qualification-index.json", index)
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase", choices=("banks", "histories", "fits", "audits", "integration", "index")
    )
    for name in ("maps-root", "results-root", "output-dir", "runtime-receipt"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--python", required=True)
    parser.add_argument("--execution-context", choices=("apptainer",), required=True)
    parser.add_argument("--dependency-plan", type=Path, action="append", default=[])
    plan = prepare(parser.parse_args())
    print(
        json.dumps(
            {"phase": plan["phase"], "ready": len(plan["tasks"]), "pending": len(plan["pending"])}
        )
    )


if __name__ == "__main__":
    main()
