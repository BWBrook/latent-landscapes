"""Run the original old-panel reducer against the archived target paths.

Run on the archived original checkout through its pinned Python runtime with
the old results directory as the sole argument. Output JSON to stdout.
"""

import hashlib
import json
import sys
from pathlib import Path

repo = Path.cwd()
sys.path.insert(0, str(repo / "scripts"))

import summarise_sprint2_qualification as q  # noqa: E402

SOURCE = "99af5206b6a4e53f5b8e9d71cbf348f95e9ae574"
REDUCER = "4f138512341825dbe348a227a4a9ac769707e38eb091e17ea14557f536563439"
PANEL = "51006aa0355ab4ce9f28e572a4272f09c0dc9fcdb52ae6ed0570aacbb1cf240d"


def read(path):
    return json.loads(path.read_text())


def output_ref(results, task_id, name):
    directory = results / task_id
    path = directory / "_task.json"
    if not path.is_file():
        return None
    record = read(path)
    if record["status"] not in {"completed", "resolved", "scientific_failure"}:
        return None
    assert record["source"] == {"commit": SOURCE, "tracked_changes": []}
    assert record["exit_code"] == 0
    return {
        "path": str(directory / record["attempt"] / name),
        "sha256": record["output_sha256"][name],
    }


class DerivedBankBindings(q.Evidence):
    def __init__(self, results):
        super().__init__(results)
        self.bank_bindings = {}

    def add(self, source):
        raw = json.dumps(source, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        self.bank_bindings[digest] = source
        return {"path": f"derived-bank-identity/{digest}", "sha256": digest}

    def load(self, reference):
        if reference["sha256"] in self.bank_bindings:
            return self.bank_bindings[reference["sha256"]]
        return super().load(reference)


def identity(row, entry, results):
    primary, independent = (
        output_ref(results, f"bank-{row['map']}-r{replicate}", "bank/manifest.json")
        for replicate in (0, 1)
    )
    return {
        "schema": "sprint2-bank-identity-v1",
        "primary_receipt_sha256": entry["lean"]["sha256"],
        "independent_receipt_sha256": entry["independent_bank"]["sha256"],
        "primary_manifest": primary,
        "independent_manifest": independent,
    }


def main():
    results = Path(sys.argv[1])
    evidence = DerivedBankBindings(results)
    panel_path = repo / "docs/evidence/paper1-sprint1-2026-11-05/qualification-panel.json"
    assert q.digest(panel_path) == PANEL
    assert q.digest(Path(q.__file__)) == REDUCER
    panel = read(panel_path)
    index = {
        "schema": "sprint2-qualification-index-v1",
        "panel_sha256": PANEL,
        "source_commit": SOURCE,
        "cases": {},
    }
    for row in panel["datasets"]:
        case = row["dataset_id"]
        obs = output_ref(results, f"history-{case}", "history/observations.npz")
        assert q.digest(Path(obs["path"])) == obs["sha256"]
        entry = index["cases"][case] = {"observation_sha256": obs["sha256"]}
        roles = ["dense", "lean"]
        if row["independent_bank"]:
            roles.append("independent_bank")
        if row["exhaustive_audit"]:
            roles.append("exhaustive")
        for role in roles:
            reference = output_ref(results, f"fit-{case}-{role}", "fit/receipt.json")
            if reference:
                entry[role] = reference
        if "independent_bank" in entry and "lean" in entry:
            entry["bank_identity"] = evidence.add(identity(row, entry, results))
    result = q.summarise(panel, index, evidence)
    result["derived_bank_bindings"] = evidence.bank_bindings
    result["original_fit_receipt_hashes"] = {
        case: {
            role: entry[role]["sha256"]
            for role in ("dense", "lean", "independent_bank", "exhaustive")
            if role in entry
        }
        for case, entry in index["cases"].items()
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
