"""Read-only reconciliation of old Sprint 2 fits and the frozen case reducer."""

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from pbs.campaign import task_digest  # noqa: E402

OLD = ROOT / "artifacts/sprint2/pilot-20261107"
OLD_RESULTS = OLD / "phase-results/qualification-results"
PANEL = ROOT / "docs/evidence/paper1-sprint1-2026-11-05/qualification-panel.json"
REPAIR = ROOT / "artifacts/sprint2/repair-20261112/final-20261115"
ACCEPT = ROOT / "artifacts/sprint2/boundary-resume-20261121"
REFS = {
    "original": "99af5206b6a4e53f5b8e9d71cbf348f95e9ae574",
    "nov15": "a77e849ce0b0381b5c378b222bacfadce9beaf96",
    "nov21": "432bb6e56e672f9e57f2f7bc369546023b07662e",
}
REDUCER_BYTES = subprocess.check_output(
    ["git", "show", f"{REFS['original']}:scripts/summarise_sprint2_qualification.py"], cwd=ROOT
)
q = ModuleType("frozen_sprint2_qualification")
exec(compile(REDUCER_BYTES, "scripts/summarise_sprint2_qualification.py", "exec"), q.__dict__)


def read(path):
    return json.loads(path.read_text())


def ref(path, expected=None):
    sha = q.digest(path)
    if expected is not None and sha != expected:
        raise ValueError(f"hash mismatch at {path}")
    return {"path": str(path), "sha256": sha}


class Mirror(q.Evidence):
    def __init__(self):
        super().__init__(ROOT)
        self.locations = {}

    def path(self, reference):
        return self.locations.get(reference["sha256"], super().path(reference))

    def fit(self, directory, record, original_task, observation):
        if (
            record["exit_code"] != 0
            or record["task_sha256"] != task_digest(record["task"])
            or record["source"]
            != {"commit": record["task"]["source_commit"], "tracked_changes": []}
        ):
            raise ValueError(f"invalid fit task record: {directory}")
        expected = record["output_sha256"]
        if not (directory / "fit/receipt.json").is_file():
            return None
        reference = ref(directory / "fit/receipt.json", expected["fit/receipt.json"])
        fit = self.load(reference)
        if (
            fit["source"] != {"commit": record["source"]["commit"], "working_tree_changes": []}
            or fit["failure_class"] != record["failure_class"]
        ):
            raise ValueError(f"fit receipt disagrees with task record: {directory}")
        original_obs = [
            value
            for name, value in original_task["input_sha256"].items()
            if Path(name).name == "observations.npz"
        ]
        actual_obs = [
            value
            for name, value in fit["input_sha256"].items()
            if Path(name).name == "observations.npz"
        ]
        if original_obs != [observation] or actual_obs != [observation]:
            raise ValueError(f"wrong frozen observation: {directory}")
        for name in ("fit/search_receipt.json", "fit/search/evaluations.jsonl"):
            path = directory / name
            if path.is_file() and name in expected:
                search_ref = ref(path, expected[name])
                self.locations[search_ref["sha256"]] = path
        return reference


def roles(row):
    return (
        ("dense", "lean")
        + (("independent_bank",) if row["independent_bank"] else ())
        + (("exhaustive",) if row["exhaustive_audit"] else ())
    )


def statuses(fit_roles):
    classes = [value["status"] for value in fit_roles.values()]
    if "scientific_failure" in classes:
        return "fit_failed"
    if all(value == "resolved" for value in classes):
        return "all_required_fits_resolved"
    return "fit_unknown"


def record_info(task_id, record, reference):
    return {
        "task_id": task_id,
        "status": record["status"],
        "failure_class": record["failure_class"],
        "source": record["source"]["commit"],
        "receipt_sha256": record["output_sha256"]["fit/receipt.json"],
        "reference": reference,
    }


def registered_comparison_obstacles(left, right, bank):
    """Record exact-node availability and failures whose witness already exists."""
    w_limit, root_limit = (0.10, 0.05) if bank else (0.01, 0.005)
    result = {}
    for name in q.VIEWS:
        try:
            lv, rv = (q.view_of(fit, name) for fit in (left, right))
            lp, rp = (q.profile_of(view) for view in (lv, rv))
            want = q.required_nodes(lv, lp) | q.required_nodes(rv, rp)
            shared = lp.keys() & rp.keys()
            criteria = [q.finite(view["free"]["criterion"]) for view in (lv, rv)]
            max_delta = max(
                abs(2 * ((criteria[0] - lp[x]["criterion"]) - (criteria[1] - rp[x]["criterion"])))
                for x in shared
            )
            failures = []
            if max_delta > w_limit + 4e-8:
                failures.append("shared registered node exceeds W tolerance")
            for marker in ("free", "null"):
                if q.contacts(lv[marker], name) != q.contacts(rv[marker], name):
                    failures.append(f"{marker} boundary contacts differ")
            ll, rl = (q.levels_of(view) for view in (lv, rv))
            for cutoff in q.CUTOFFS:
                a, b = ll[cutoff], rl[cutoff]
                if a["status"] != "available" or b["status"] != "available":
                    failures.append(f"{cutoff:g}: unavailable set")
                    continue
                for key in ("set_class", "touches_h1", "touches_h30", "empty"):
                    if a[key] != b[key]:
                        failures.append(f"{cutoff:g}: {key} differs")
                ac, bc = (
                    sorted(row["components"], key=lambda c: c["lower_log_h"]) for row in (a, b)
                )
                ar, br = (sorted(row["roots_log_h"]) for row in (a, b))
                if len(ac) != len(bc) or len(ar) != len(br):
                    failures.append(f"{cutoff:g}: topology differs")
                    continue
                for ca, cb in zip(ac, bc, strict=True):
                    for key in ("lower_domain_contact", "upper_domain_contact", "singleton"):
                        if ca[key] != cb[key]:
                            failures.append(f"{cutoff:g}: component {key} differs")
                    for key in ("lower_log_h", "upper_log_h"):
                        if abs(ca[key] - cb[key]) > root_limit:
                            failures.append(f"{cutoff:g}: component {key} moved")
                if any(abs(a - b) > root_limit for a, b in zip(ar, br, strict=True)):
                    failures.append(f"{cutoff:g}: root moved")
            result[name] = {
                "exact_shared_profile_nodes": len(shared),
                "required_exact_union": len(want),
                "missing_as_left_profile_nodes": len(want - lp.keys()),
                "missing_as_right_profile_nodes": len(want - rp.keys()),
                "max_abs_shared_w_difference": max_delta,
                "failure_witnesses": sorted(set(failures)),
            }
        except (KeyError, TypeError, ValueError) as error:
            result[name] = {"indeterminate": str(error)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--original-results", type=Path, default=OLD_RESULTS)
    args = parser.parse_args()
    evidence = Mirror()
    panel = read(PANEL)
    task_plan = OLD / "operations/fit-plan/tasks.jsonl"
    original = {
        task["task_id"]: task for task in map(json.loads, task_plan.read_text().splitlines())
    }
    observations = {}
    for row in panel["datasets"]:
        case = row["dataset_id"]
        history = OLD_RESULTS / f"history-{case}"
        record = read(history / "_task.json")
        assert record["status"] == "completed"
        assert record["task_sha256"] == task_digest(record["task"])
        observations[case] = ref(
            history / record["attempt"] / "history/observations.npz",
            record["output_sha256"]["history/observations.npz"],
        )["sha256"]
    accounted = {name: {} for name in (*REFS, "mixed")}
    for task_id, task in original.items():
        case = task_id.removeprefix("fit-").rsplit("-", 1)[0]
        source = task["source_commit"]
        assert source == REFS["original"]
        observation = observations[case]
        task_dir = OLD_RESULTS / task_id
        primary = task_dir / "_task.json"
        if primary.is_file():
            record = read(primary)
            assert record["task_id"] == task_id and record["task"] == task
            target_record = args.original_results / task_id / "_task.json"
            if target_record.is_file():
                ref(target_record, q.digest(primary))
            raw = args.original_results / task_id / record["attempt"]
            if not (raw / "fit/receipt.json").is_file():
                raw = task_dir / record["attempt"]
            reference = evidence.fit(raw, record, task, observation)
            accounted["original"][task_id] = record_info(task_id, record, reference)
        else:
            partial = task_dir / "attempt-0001/fit/search/evaluations.jsonl"
            assert partial.is_file()
            search = task_dir / "attempt-0001/fit/search_receipt.json"
            accounted["original"][task_id] = {
                "task_id": task_id,
                "status": "no_terminal_record",
                "source": source,
                "partial_evaluation_stream_sha256": q.digest(partial),
                "partial_search_status": read(search)["status"] if search.is_file() else None,
            }

    for name, root, summary in (
        ("nov15", REPAIR / "fit-results", REPAIR / "replay-summary.json"),
        ("nov21", ACCEPT / "raw/fit-results", ACCEPT / "indexes/replay-summary.json"),
    ):
        ledger = read(summary)
        assert ledger["source_commit"] == REFS[name]
        for row in ledger["fit_replays"]:
            task_id = row["original_task_id"]
            task = original[task_id]
            directory = root / f"repair-{task_id}"
            if row["execution_status"] == "missing":
                accounted[name][task_id] = {
                    "task_id": task_id,
                    "source": REFS[name],
                    "status": "no_terminal_record",
                }
                continue
            task_ref = ref(directory / "_task.json", row["task_record_sha256"])
            record = evidence.load(task_ref)
            assert record["task"]["original_task_id"] == task_id
            assert record["source"]["commit"] == REFS[name]
            assert record["output_sha256"]["fit/receipt.json"] == row["receipt_sha256"]
            case = task_id.removeprefix("fit-").rsplit("-", 1)[0]
            reference = evidence.fit(
                directory / record["attempt"], record, task, observations[case]
            )
            assert reference is not None
            accounted[name][task_id] = record_info(task_id, record, reference)
    for task_id, item in accounted["original"].items():
        accounted["mixed"][task_id] = accounted["nov21"].get(task_id, item)

    recovered = []
    for row in read(ACCEPT / "indexes/completion-index.json")["historical_recovery"]:
        task_id = row["case"]
        directory = ACCEPT / "raw/historical-results" / task_id / "attempt-0001"
        recovery_ref = ref(directory / "recovery.json", row["receipt_sha256"])
        recovery = evidence.load(recovery_ref)
        reference = ref(
            directory / "fit/receipt.json", recovery["output_sha256"]["fit/receipt.json"]
        )
        receipt = evidence.load(reference)
        assert receipt["source"]["commit"] == REFS["nov15"]
        assert receipt["failure_class"] == "resolved"
        case = task_id.removeprefix("fit-").rsplit("-", 1)[0]
        assert [
            value
            for name, value in receipt["input_sha256"].items()
            if Path(name).name == "observations.npz"
        ] == [observations[case]]
        recovered.append({"task_id": task_id, "recovery_receipt": recovery_ref, **reference})

    result = {
        "panel_sha256": q.digest(PANEL),
        "original_task_plan_sha256": q.digest(task_plan),
        "frozen_reducer_sha256": hashlib.sha256(REDUCER_BYTES).hexdigest(),
        "historical_recoveries_of_nov15": recovered,
        "analyses": {},
    }

    for name, case_records in accounted.items():
        assessment = result["analyses"][name] = {"source_commit": REFS.get(name), "cases": {}}
        for row in panel["datasets"]:
            case = row["dataset_id"]
            by_role = {
                role: case_records.get(f"fit-{case}-{role}", {"status": "not_in_replay"})
                for role in roles(row)
            }
            raw = {role: fit["reference"] for role, fit in by_role.items() if fit.get("reference")}
            sources = {fit.get("source") for fit in by_role.values()}
            source = REFS.get(name)
            if name == "mixed" and len(sources) == 1:
                source = next(iter(sources))
            assessed = None
            obstacles = {}
            if source is not None:
                entry = {"observation_sha256": observations[case], **raw}
                assessed = q.assess_case(row, entry, evidence, source)
            for label, lkey, rkey in (
                ("dense_lean", "dense", "lean"),
                ("bank", "lean", "independent_bank"),
            ):
                if lkey not in raw or rkey not in raw:
                    continue
                lrole, rrole = by_role[lkey], by_role[rkey]
                if (
                    lrole["status"] == rrole["status"] == "resolved"
                    and lrole["source"] == rrole["source"]
                ):
                    left, right = (evidence.load(raw[key]) for key in (lkey, rkey))
                    obstacles[label] = registered_comparison_obstacles(left, right, label == "bank")
            assessment["cases"][case] = {
                "map": row["map"],
                "stratum": row["stratum"],
                "arm": row["arm"],
                "fit_status": statuses(by_role),
                "fit_roles": by_role,
                "case_reducer": assessed,
                "registered_pair_fit_record_diagnostics": obstacles,
            }

    assert len(panel["datasets"]) == 207 and len(original) == 486
    assert len(observations) == 207
    expected_tasks = {
        f"fit-{row['dataset_id']}-{role}" for row in panel["datasets"] for role in roles(row)
    }
    assert set(original) == expected_tasks
    snapshot = read(OLD / "operations/qualification-fits-reconcile.json")
    for status in ("resolved", "scientific_failure", "no_terminal_record"):
        observed = {k for k, v in accounted["original"].items() if v["status"] == status}
        assert observed == set(snapshot["missing" if status == "no_terminal_record" else status])
    print(
        {
            name: Counter(v["status"] for v in fit_data.values())
            for name, fit_data in accounted.items()
        }
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
