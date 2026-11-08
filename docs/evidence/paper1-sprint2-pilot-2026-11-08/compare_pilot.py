"""Bounded historical pilot comparison; never exact-union qualification or fitting."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from summarise_sprint2_qualification import (  # noqa: E402
    CUTOFFS,
    LOG_MAX,
    VIEWS,
    contacts,
    digest,
    finite,
    levels_of,
    profile_of,
    view_of,
)

COMMIT = "99af5206b6a4e53f5b8e9d71cbf348f95e9ae574"
OLD_COMMIT = "583c1e3d9f012a90db57cbf11cbe6ea4d1b041cd"
OLD_RECEIPT = "19c0c686a8ef39a7e6c609764ad9b3530279b47e3584fb60e4e4c4dcfb641799"
OLD_PATCH = "d99c5c303aca61117f073393a060fe022b9d0d4bbdf7eed4da65f51ad95450eb"


def read(path):
    return json.loads(Path(path).read_text())


def within(root, relative):
    rel = PurePosixPath(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"unsafe relative path: {relative}")
    path = (Path(root) / str(rel)).resolve()
    path.relative_to(Path(root).resolve())
    return path


def mapped(path, root, prefix):
    remote = PurePosixPath(path)
    base = PurePosixPath(prefix)
    if not remote.is_absolute() or not base.is_absolute() or ".." in remote.parts:
        raise ValueError("remote paths and prefix must be absolute without traversal")
    return within(root, str(remote.relative_to(base)))


def child_of(receipt, root=None, prefix=None):
    path = Path(receipt["search"]["receipt"])
    if root is not None:
        path = mapped(str(path), root, prefix)
    if digest(path) != receipt["search"]["receipt_sha256"]:
        raise ValueError("parent-child receipt hash mismatch")
    child = read(path)
    if child["status"] != receipt["search"]["status"] or child["mode"] != receipt["search_mode"]:
        raise ValueError("child search status/mode disagrees with parent")
    if tuple(child["cutoffs"]) != CUTOFFS:
        raise ValueError("child cutoff grid differs")
    return path, child


def data_hashes(receipt):
    inputs = receipt["inputs"]
    paths = {
        name: str(PurePosixPath(inputs["input_dir"]) / name)
        for name in ("public_inputs.npz", "exposure.npz")
    }
    paths.update(
        {name: inputs[name] for name in ("observations", "arrival_bank", "compressed_bank")}
    )
    result = {role: receipt["input_sha256"][path] for role, path in paths.items()}
    if any(
        not isinstance(x, str) or len(x) != 64 or any(c not in "0123456789abcdef" for c in x)
        for x in result.values()
    ):
        raise ValueError("malformed data digest")
    return result


def verify_source(receipt, receipt_path, *, target):
    source = receipt["source"]
    if source["commit"] == COMMIT and source["working_tree_changes"] == []:
        return "clean_candidate_commit; full source inventory bound by parent audit"
    if not target and source["commit"] == OLD_COMMIT and digest(receipt_path) == OLD_RECEIPT:
        patch = ROOT / "docs/evidence/paper1-sprint2-2026-11-06/diagnostic-source.patch"
        if digest(patch) != OLD_PATCH:
            raise ValueError("historical source patch changed")
        return (
            "exact permitted historical 120-site receipt; "
            "numerical-procedure equivalent, source bytes differ"
        )
    raise ValueError(
        "source is neither clean frozen candidate nor exact permitted local 120-site reference"
    )


def verify_task(path, target_path, child_path):
    record = read(path)
    if PurePosixPath(record["attempt"]).name != record["attempt"] or record["attempt"] in (
        ".",
        "..",
    ):
        raise ValueError("unsafe task attempt name")
    base = path.parent if path.parent.name == record["attempt"] else path.parent / record["attempt"]
    checked = set()
    for name, expected in record["output_sha256"].items():
        output = within(base, name)
        if digest(output) != expected:
            raise ValueError(f"task output hash mismatch: {name}")
        checked.add(output)
    if not {target_path.resolve(), child_path.resolve()} <= checked:
        raise ValueError("task output inventory omits compared parent/child")
    if (
        record["exit_code"] != 0
        or record["status"] != "resolved"
        or record["failure_class"] != "resolved"
    ):
        raise ValueError("task did not resolve successfully")
    return {
        "path": str(path),
        "sha256": digest(path),
        "outputs_verified": len(checked),
        "task_sha256": record["task_sha256"],
        "host": record.get("host"),
        "wall_seconds": record.get("wall_seconds"),
        "cpu_seconds": record.get("cpu_seconds"),
        "worker_children_peak_rss_bytes": record.get("worker_children_peak_rss_bytes"),
        "pbs_job_id": record.get("pbs_job_id"),
    }


def contact_signature(row, view, x=None):
    nuisance = sorted(contacts(row, view))
    if view.startswith("spatial"):
        domain = sorted(
            (family, c) for family, values in row["h_domain_contacts"].items() for c in values
        )
    else:
        if x is None:
            domain = [(view, c) for c in row["h_domain_contacts"]]
        else:
            domain = [(view, "lower")] if x == 0 else [(view, "upper")] if x == LOG_MAX else []
    return nuisance + sorted(domain)


def node_summary(nodes):
    xs = sorted(nodes)
    return {"count": len(xs), "log_h_range": [xs[0], xs[-1]] if xs else None, "log_h": xs}


def compare_view(left, right, name, failures, unavailable=None):
    lv, rv = view_of(left, name), view_of(right, name)
    lp, rp = profile_of(lv), profile_of(rv)
    mandatory = set(np.linspace(0, LOG_MAX, 5).tolist())
    if not name.startswith("spatial"):
        mandatory |= set(np.linspace(0, LOG_MAX, 35).tolist())
    missing = {
        side: sorted(mandatory - set(points)) for side, points in (("local", lp), ("target", rp))
    }
    common = sorted(lp.keys() & rp.keys())
    result = {
        "local_nodes": len(lp),
        "target_nodes": len(rp),
        "common": node_summary(common),
        "local_only": node_summary(lp.keys() - rp.keys()),
        "target_only": node_summary(rp.keys() - lp.keys()),
        "missing_mandatory_mesh": missing,
    }
    if any(missing.values()) or not common:
        message = f"{name}: missing mandatory exact mesh: {missing}"
        if unavailable is None:
            raise ValueError(message)
        unavailable.append(message)
        if not common:
            return result
    lf, rf = finite(lv["free"]["criterion"]), finite(rv["free"]["criterion"])
    deltas = [
        abs(2 * (lf - finite(lp[x]["criterion"])) - 2 * (rf - finite(rp[x]["criterion"])))
        for x in common
    ]
    result["max_abs_delta_w"] = max(deltas)
    result["worst_log_h"] = common[deltas.index(max(deltas))]
    if max(deltas) > 0.01:
        failures.append(f"{name}: common-node W exceeds 0.01")
    mismatch = [
        x for x in common if contact_signature(lp[x], name, x) != contact_signature(rp[x], name, x)
    ]
    result["contact_mismatch_log_h"] = mismatch
    if mismatch:
        failures.append(f"{name}: common-node contacts differ")
    result["noncommon_contacts"] = {}
    for side, points, other in (("local", lp, rp), ("target", rp, lp)):
        result["noncommon_contacts"][side] = sorted(
            {
                tuple(c)
                for x in points.keys() - other.keys()
                for c in contact_signature(points[x], name, x)
            }
        )
    if result["noncommon_contacts"]["local"] != result["noncommon_contacts"]["target"]:
        failures.append(f"{name}: unmatched-node aggregate contacts differ; diagnosis required")
    result["locations"] = {}
    for loc in ("free", "null"):
        a, b = lv[loc], rv[loc]
        if contact_signature(a, name) != contact_signature(b, name):
            failures.append(f"{name}: {loc} contacts differ")
        result["locations"][loc] = {
            "local_criterion": finite(a["criterion"]),
            "target_criterion": finite(b["criterion"]),
            "delta_criterion": finite(b["criterion"]) - finite(a["criterion"]),
            "local_h": finite(a["h"] if loc == "free" else a.get("h", 1.0)),
            "target_h": finite(b["h"] if loc == "free" else b.get("h", 1.0)),
        }
    result["cutoffs"] = []
    ll, rl = levels_of(lv), levels_of(rv)
    for cutoff in CUTOFFS:
        a, b = ll[cutoff], rl[cutoff]
        prefix = f"{name}: cutoff {cutoff}"
        if a["status"] != "available" or b["status"] != "available":
            failures.append(f"{prefix}: unavailable set")
            continue
        for key in ("set_class", "touches_h1", "touches_h30", "empty"):
            if a[key] != b[key]:
                failures.append(f"{prefix}: {key} differs")
        ac, bc = [sorted(s["components"], key=lambda c: finite(c["lower_log_h"])) for s in (a, b)]
        ar, br = [sorted(map(finite, s["roots_log_h"])) for s in (a, b)]
        detail = {
            "cutoff": cutoff,
            "local_roots": ar,
            "target_roots": br,
            "local_components": ac,
            "target_components": bc,
        }
        result["cutoffs"].append(detail)
        if len(ac) != len(bc) or len(ar) != len(br):
            failures.append(f"{prefix}: topology differs")
            continue
        root_deltas = [abs(x - y) for x, y in zip(ar, br, strict=True)]
        endpoint_deltas = []
        for ca, cb in zip(ac, bc, strict=True):
            for key in ("lower_domain_contact", "upper_domain_contact", "singleton"):
                if ca[key] != cb[key]:
                    failures.append(f"{prefix}: endpoint type {key} differs")
            endpoint_deltas += [
                abs(finite(ca[k]) - finite(cb[k])) for k in ("lower_log_h", "upper_log_h")
            ]
        detail.update(
            max_root_delta=max(root_deltas, default=0),
            max_endpoint_delta=max(endpoint_deltas, default=0),
        )
        if any(d > 0.005 for d in root_deltas + endpoint_deltas):
            failures.append(f"{prefix}: root/component endpoint exceeds 0.005 log-h")
    return result


def compare(local_path, target_path, target_results_root, remote_results_prefix, task_path=None):
    failures, unavailable = [], []
    result = {
        "schema": "historical-pilot-comparison-v1",
        "qualification_evidence": False,
        "exact_union_audit": False,
        "source_commit": COMMIT,
        "views": {},
        "limitations": [
            "Only exact shared profile nodes are compared pointwise; no interpolation.",
            "Full source inventories/runtime/task-plan identities require parent audit.",
        ],
    }
    try:
        Path(target_path).resolve().relative_to(Path(target_results_root).resolve())
        left, right = read(local_path), read(target_path)
        result["receipt_sha256"] = {"local": digest(local_path), "target": digest(target_path)}
        result["source_disposition"] = {
            "local": verify_source(left, local_path, target=False),
            "target": verify_source(right, target_path, target=True),
        }
        child_of(left)
        child_path, _ = child_of(right, target_results_root, remote_results_prefix)
        lh, rh = data_hashes(left), data_hashes(right)
        result["data_sha256_by_role"] = {"local": lh, "target": rh}
        if lh != rh:
            raise ValueError("five data hashes differ by input role")
        if task_path:
            result["task"] = verify_task(Path(task_path), Path(target_path), child_path)
        else:
            result["task"] = {"status": "not_supplied; parent must bind task outputs separately"}
        result["resources"] = {
            side: {
                key: receipt.get(key) for key in ("cost", "host", "platform", "python", "threads")
            }
            for side, receipt in (("local", left), ("target", right))
        }
        for side, receipt in (("local", left), ("target", right)):
            if receipt["schema"] != "fit-dataset-v1" or tuple(receipt["cutoffs"]) != CUTOFFS:
                raise ValueError(f"{side}: invalid schema/cutoffs")
            if (
                receipt["search_mode"] != "lean"
                or receipt["tight_replay"] != "always_on_inside_PanelSearch.run"
            ):
                raise ValueError(f"{side}: changed search/tight settings")
            for variable in ("OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OMP_NUM_THREADS"):
                if receipt["threads"][variable] != "1":
                    raise ValueError(f"{side}: numerical thread setting {variable} is not one")
            if (
                receipt["failure_class"] != "resolved"
                or receipt["all_triggered"]
                or receipt["errors"]
            ):
                failures.append(f"{side}: failure, trigger or execution error")
            if (
                receipt["search"]["status"] != "profile_numerically_resolved"
                or receipt["search"]["failure"] is not None
            ):
                failures.append(f"{side}: search unresolved")
            guard = receipt["envelope_guard"]
            if guard["unresolved_fit_events"] or guard["anchor_guard_events"] or guard["events"]:
                failures.append(f"{side}: envelope guard events")
            if (
                receipt["latent_audit"]["multimodal_latent"] is not False
                or receipt["latent_audit"]["flagged"]
            ):
                failures.append(f"{side}: latent flag present")
        for key in ("lr_limit", "exhaustive"):
            if left["latent_audit"][key] != right["latent_audit"][key]:
                raise ValueError(f"latent audit setting {key} differs")
        for name in VIEWS:
            try:
                result["views"][name] = compare_view(left, right, name, failures, unavailable)
            except (KeyError, TypeError, ValueError, OverflowError) as exc:
                unavailable.append(f"{name}: {exc}")
    except (OSError, KeyError, TypeError, ValueError, OverflowError) as exc:
        unavailable.append(str(exc))
    result.update(
        status="indeterminate" if unavailable else "fail" if failures else "pass",
        failures=failures,
        unavailable=unavailable,
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("local_receipt", type=Path)
    parser.add_argument("target_receipt", type=Path)
    parser.add_argument("--target-results-root", type=Path, required=True)
    parser.add_argument("--remote-results-prefix", required=True)
    parser.add_argument("--target-task", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(
        args.local_receipt,
        args.target_receipt,
        args.target_results_root,
        args.remote_results_prefix,
        args.target_task,
    )
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "failures": result["failures"],
                "unavailable": result["unavailable"],
            }
        )
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
