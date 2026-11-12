"""Compare repaired fits on exact frozen baseline anchors, with resumable probes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any

import audit_sprint2_pair as audit
import benchmark_spatial_profile as adapter
from pbs import campaign
from prepare_solver_repair_replay import imported_source_check

ROOT = Path(__file__).resolve().parents[1]
FROZEN = "99af5206b6a4e53f5b8e9d71cbf348f95e9ae574"
SCHEMA = "solver-repair-nonregression-v1"
CRITERION_TOLERANCE = 1e-6
LR_TOLERANCE = 1e-3
Json = dict[str, Any]


def read(path: Path) -> Json:
    return json.loads(path.read_text())


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(adapter._jsonable(value), indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def checked(path: Path, expected: str) -> Json:
    if campaign.sha256(path) != expected:
        raise ValueError(f"frozen receipt hash differs: {path.name}")
    return read(path)


def checkpoint_digest(saved: Json) -> str:
    payload = {key: value for key, value in saved.items() if key != "payload_sha256"}
    encoded = json.dumps(
        adapter._jsonable(payload), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def finite(value: Any) -> float:
    if isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError("criterion/LR evidence must be finite and non-boolean")
    return float(value)


def eligibility(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError("eligibility must be an explicit boolean")
    return value


def check_values(label: str, left: Json, right: Json) -> Json:
    delta = finite(right["criterion"]) - finite(left["criterion"])
    failures = []
    if abs(delta) > CRITERION_TOLERANCE:
        failures.append("criterion_shift")
    old_eligible, new_eligible = eligibility(left["eligible"]), eligibility(right["eligible"])
    if old_eligible != new_eligible:
        failures.append("eligibility_changed")
    row = {
        "location": label,
        "baseline_criterion": left["criterion"],
        "candidate_criterion": right["criterion"],
        "delta_criterion": delta,
        "baseline_eligible": old_eligible,
        "candidate_eligible": new_eligible,
        "failures": failures,
    }
    if "w" in left and "w" in right:
        shift = finite(right["w"]) - finite(left["w"])
        row["delta_profile_lr"] = shift
        if abs(shift) > LR_TOLERANCE:
            failures.append("profile_lr_shift")
    return row


def envelope(row: Json, spatial: bool) -> Json:
    return (
        {
            "criterion": row["criterion"],
            "eligible": all(eligibility(row[f]["eligible"]) for f in audit.FAMILIES),
        }
        if spatial
        else row
    )


def compare_free(baseline: Json, candidate: Json) -> list[Json]:
    rows = []
    for name in audit.VIEWS:
        old, new = audit.view_of(baseline, name), audit.view_of(candidate, name)
        spatial = name.startswith("spatial.")
        for location in ("free", "null"):
            rows.append(
                check_values(
                    f"{name}/{location}/envelope",
                    envelope(old[location], spatial),
                    envelope(new[location], spatial),
                )
            )
            if spatial:
                for family in audit.FAMILIES:
                    rows.append(
                        check_values(
                            f"{name}/{location}/{family}",
                            old[location][family],
                            new[location][family],
                        )
                    )
        shift = finite(new["lr1"]) - finite(old["lr1"])
        rows.append(
            {
                "location": f"{name}/lr1",
                "delta_profile_lr": shift,
                "failures": ["profile_lr_shift"] if abs(shift) > LR_TOLERANCE else [],
            }
        )
    return rows


def reference_at(receipt: Json, search: Json, name: str, x: float) -> Json:
    view = audit.view_of(receipt, name)
    rows = audit.profile_rows(view)
    if x in rows:
        row = rows[x]
        result = {"kind": "stored_profile_row", "criterion": finite(row["criterion"])}
        expected_w = 2 * (finite(view["free"]["criterion"]) - result["criterion"])
        if "w" in row and finite(row["w"]) != expected_w:
            raise ValueError("baseline profile LR differs from its frozen normalizer")
        result["w"] = finite(row["w"]) if "w" in row else expected_w
        if name.startswith("spatial."):
            original = {
                finite(r["log_h"]): r for r in search["points"][str(name == "spatial.tight")]
            }
            raw = original[x]
            if finite(raw["criterion"]) != result["criterion"]:
                raise ValueError("baseline root/search point criteria differ")
            result["fit"] = {f: raw[f] for f in audit.FAMILIES}
            result["eligible"] = all(eligibility(raw[f]["eligible"]) for f in audit.FAMILIES)
        else:
            result.update(eligible=eligibility(row["eligible"]), fit=row)
        return result
    if x != math.log(finite(view["free"]["h"])) or name.startswith("spatial."):
        raise ValueError("no exact archived reference at required location")
    row = view["free"]
    return {
        "kind": "free_candidate_at_own_h",
        "criterion": finite(row["criterion"]),
        "eligible": eligibility(row["eligible"]),
        "fit": row,
    }


def compare_anchor(
    baseline: Json, search: Json, candidate: Json, name: str, x: float, probe: Json
) -> Json:
    old = reference_at(baseline, search, name, x)
    old_max = finite(audit.view_of(baseline, name)["free"]["criterion"])
    new_max = finite(audit.view_of(candidate, name)["free"]["criterion"])
    left = {"w": 2 * (old_max - old["criterion"]), **old}
    right = {**probe, "w": 2 * (new_max - finite(probe["criterion"]))}
    checks = [check_values(f"{name}/{x.hex()}/envelope", left, right)]
    if name.startswith("spatial."):
        for family in audit.FAMILIES:
            old_family_max = finite(audit.view_of(baseline, name)["free"][family]["criterion"])
            new_family_max = finite(audit.view_of(candidate, name)["free"][family]["criterion"])
            checks.append(
                check_values(
                    f"{name}/{x.hex()}/{family}",
                    {
                        **old["fit"][family],
                        "w": 2 * (old_family_max - finite(old["fit"][family]["criterion"])),
                    },
                    {
                        **probe["fit"][family],
                        "w": 2 * (new_family_max - finite(probe["fit"][family]["criterion"])),
                    },
                )
            )
    return {
        "view": name,
        "log_h": x,
        "log_h_hex": x.hex(),
        "reference_kind": old["kind"],
        "checks": checks,
        "probe": probe,
    }


def check_data_identity(baseline: Json, candidate: Json) -> None:
    if baseline["data_identity"] != candidate["data_identity"]:
        raise ValueError("data/site/design identity changed")
    if (
        baseline["search_mode"] != candidate["search_mode"]
        or baseline["cutoffs"] != candidate["cutoffs"]
    ):
        raise ValueError("search mode or cutoff grid changed")
    if baseline["tight_replay"] != candidate["tight_replay"]:
        raise ValueError("tight replay contract changed")
    for key in ("observations", "arrival_bank", "compressed_bank"):
        old, new = baseline["inputs"][key], candidate["inputs"][key]
        if baseline["input_sha256"][old] != candidate["input_sha256"][new]:
            raise ValueError(f"input payload changed: {key}")
    for key in ("public_inputs.npz", "exposure.npz"):
        old = str(Path(baseline["inputs"]["input_dir"]) / key)
        new = str(Path(candidate["inputs"]["input_dir"]) / key)
        if baseline["input_sha256"][old] != candidate["input_sha256"][new]:
            raise ValueError(f"public input payload changed: {key}")


def save_state(probe: audit.Probe, name: str, x: float) -> Json:
    if name.startswith("spatial."):
        return probe.search.points[name == "spatial.tight"][x]
    return probe.reduced[name].points[x]


def restore_state(probe: audit.Probe, name: str, x: float, state: Json) -> None:
    if name.startswith("spatial."):
        probe.search.points[name == "spatial.tight"][x] = state
    else:
        probe.reduced[name].points[x] = state


def run_probe(args: argparse.Namespace) -> Json:
    started = time.perf_counter()
    imported_source_check(args.candidate_commit)
    baseline = checked(args.baseline_receipt, args.baseline_sha256)
    old_search = checked(args.baseline_search, args.baseline_search_sha256)
    candidate = checked(args.candidate_receipt, args.candidate_sha256)
    if baseline["failure_class"] != "resolved" or baseline["source"]["commit"] != FROZEN:
        raise ValueError("baseline is not a resolved frozen-candidate receipt")
    if candidate["source"]["commit"] != args.candidate_commit:
        raise ValueError("candidate receipt source differs")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    result: Json = {
        "schema": SCHEMA,
        "status": "incomplete",
        "source_commit": args.candidate_commit,
        "baseline_sha256": args.baseline_sha256,
        "baseline_search_sha256": args.baseline_search_sha256,
        "candidate_sha256": args.candidate_sha256,
        "tolerances": {
            "criterion_absolute": CRITERION_TOLERANCE,
            "profile_lr_absolute": LR_TOLERANCE,
        },
        "normalisers": "each version's original free criteria; never refitted or updated",
        "free_checks": [],
        "anchors": [],
        "errors": [],
        "checkpoint_hits": 0,
    }
    check_data_identity(baseline, candidate)
    if candidate["failure_class"] != "resolved":
        result.update(
            status="nonregression_failure",
            failure="candidate_fit_unresolved",
            candidate_failure_class=candidate["failure_class"],
        )
        write(args.output_dir / "receipt.json", result)
        return result
    evidence = audit.Evidence.load(args.candidate_receipt)
    if evidence.sha256 != args.candidate_sha256:
        raise ValueError("candidate changed while loading")
    result["free_checks"] = compare_free(baseline, candidate)
    identity = {
        "baseline": args.baseline_sha256,
        "baseline_search": args.baseline_search_sha256,
        "candidate": args.candidate_sha256,
        "source": args.candidate_commit,
        "anchors": {
            name: [x.hex() for x in sorted(audit.required_nodes(audit.view_of(baseline, name)))]
            for name in audit.VIEWS
        },
    }
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    identity_sha = hashlib.sha256(canonical).hexdigest()
    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    identity_path = args.checkpoint_dir / "identity.json"
    if identity_path.exists():
        if read(identity_path) != identity:
            raise ValueError("probe checkpoint belongs to another frozen comparison")
    else:
        write(identity_path, identity)
    probe = audit.Probe(evidence, args.output_dir / "new-probes")
    checkpoint_hashes = {}
    for name in audit.VIEWS:
        nodes = sorted(audit.required_nodes(audit.view_of(baseline, name)))
        for x in nodes:
            path = args.checkpoint_dir / (name + "--" + x.hex() + ".json")
            if path.exists():
                saved = read(path)
                if saved.get("payload_sha256") != checkpoint_digest(saved):
                    raise ValueError("checkpoint numerical payload hash differs")
                if (saved["identity_sha256"], saved["view"], saved["log_h_hex"]) != (
                    identity_sha,
                    name,
                    x.hex(),
                ):
                    raise ValueError("checkpoint row identity differs")
                if saved.get("state") is not None:
                    restore_state(probe, name, x, saved["state"])
                result["checkpoint_hits"] += 1
            else:
                try:
                    raw = probe.evaluate(name, x, len(nodes))
                    saved = {
                        "identity_sha256": identity_sha,
                        "view": name,
                        "log_h_hex": x.hex(),
                        "probe": raw,
                        "state": save_state(probe, name, x),
                    }
                except (MemoryError, OSError) as error:
                    result.update(
                        status="execution_error", elapsed_seconds=time.perf_counter() - started
                    )
                    result["errors"].append(
                        {
                            "view": name,
                            "log_h": x,
                            "type": type(error).__name__,
                            "message": str(error),
                        }
                    )
                    write(args.output_dir / "receipt.json", result)
                    return result
                except (RuntimeError, ValueError, FloatingPointError) as error:
                    saved = {
                        "identity_sha256": identity_sha,
                        "view": name,
                        "log_h_hex": x.hex(),
                        "error": {"type": type(error).__name__, "message": str(error)},
                    }
                saved["payload_sha256"] = checkpoint_digest(saved)
                write(path, saved)
            checkpoint_hashes[str(path)] = campaign.sha256(path)
            if "error" in saved:
                result["errors"].append({"view": name, "log_h": x, **saved["error"]})
            else:
                result["anchors"].append(
                    compare_anchor(baseline, old_search, candidate, name, x, saved["probe"])
                )
    evidence.verify_unchanged()
    failures = [row for row in result["free_checks"] if row["failures"]]
    failures.extend(
        check for row in result["anchors"] for check in row["checks"] if check["failures"]
    )
    result.update(
        status="nonregression_failure" if failures or result["errors"] else "passed",
        failed_checks=failures,
        elapsed_seconds=time.perf_counter() - started,
        checkpoint_sha256=checkpoint_hashes,
        criterion_stats=dict(probe.search.criterion.stats),
        required_anchor_count=sum(len(v) for v in identity["anchors"].values()),
    )
    write(args.output_dir / "receipt.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "baseline-receipt",
        "baseline-search",
        "candidate-receipt",
        "output-dir",
        "checkpoint-dir",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in (
        "baseline-sha256",
        "baseline-search-sha256",
        "candidate-sha256",
        "candidate-commit",
    ):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    result = run_probe(args)
    print(
        json.dumps(
            {"schema": SCHEMA, "status": result["status"], "anchors": len(result["anchors"])}
        )
    )
    return 2 if result["status"] == "execution_error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
