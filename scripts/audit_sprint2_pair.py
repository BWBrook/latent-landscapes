"""Produce exact common-anchor and free-gradient evidence from frozen fit receipts.

The input data and source must still match their recorded hashes and clean Git
commit. Additional fixed-profile fits are diagnostics: original nodes and free
normalisers are never replaced. No histories or banks are generated here.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import benchmark_spatial_profile as adapter
import fit_dataset as fit
import numpy as np
from qualify_spatial_profiles import FAMILIES, LOG_MAX, ROOT, parameters, write_json
from run_development_profile import frozen_membership_check, load_panel_data

VIEWS = ("spatial.standard", "spatial.tight", "exposure", "constant")
STEP_SCALES = (1e-4, 3e-5)
Json = dict[str, Any]


def finite(value: Any) -> float:
    if isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError("nonfinite or boolean numerical evidence")
    return float(value)


def read_json(path: Path) -> Json:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def view_of(receipt: Json, name: str) -> Json:
    family, _, regime = name.partition(".")
    value = receipt["families"][family]
    if value["status"] != "available":
        raise ValueError(f"unavailable family: {family}")
    return cast(Json, value[regime] if regime else value)


def profile_rows(view: Json) -> dict[float, Json]:
    rows = {finite(row["log_h"]): row for row in view["profile"]}
    if len(rows) != len(view["profile"]) or not {0.0, LOG_MAX} <= rows.keys():
        raise ValueError("duplicate profile nodes or missing domain endpoints")
    return rows


def required_nodes(view: Json) -> set[float]:
    rows = profile_rows(view)
    nodes = set(rows) | {math.log(finite(view["free"]["h"]))}
    levels = view["level_sets"]
    if len(levels) != len(fit.CUTOFF_GRID) or {r["cutoff"] for r in levels} != set(fit.CUTOFF_GRID):
        raise ValueError("changed or incomplete cutoff grid")
    for level in levels:
        if level["status"] != "available":
            raise ValueError("unavailable frozen level set")
        nodes.update(finite(x) for x in level["roots_log_h"])
        for component in level["components"]:
            nodes.update(finite(component[k]) for k in ("lower_log_h", "upper_log_h"))
    if any(not 0.0 <= x <= LOG_MAX for x in nodes):
        raise ValueError("anchor outside fitted domain")
    return nodes


def contacts(row: Json, name: str) -> list[list[str]]:
    if name.startswith("spatial."):
        return sorted(
            [family, contact]
            for family, values in row["nuisance_contacts"].items()
            for contact in values
            if not (row["tied"] and family == "positive_sigma" and contact == "log_sigma:lower")
        )
    return sorted([name, contact] for contact in row["nuisance_bound_contacts"])


@dataclass
class Evidence:
    path: Path
    receipt: Json
    search: Json
    args: argparse.Namespace
    sha256: str

    @classmethod
    def load(cls, path: Path) -> Evidence:
        path = path.resolve()
        receipt = read_json(path)
        if receipt["schema"] != fit.SCHEMA or receipt["failure_class"] != "resolved":
            raise ValueError("audit requires a resolved fit-dataset-v1 receipt")
        source = receipt["source"]
        current = adapter._git_identity(ROOT)
        if (
            not source["commit"]
            or source["working_tree_changes"] != []
            or current["commit"] != source["commit"]
            or current["working_tree_changes"] != []
        ):
            raise ValueError("audit requires the original clean source commit")
        args = argparse.Namespace(**{k: Path(v) for k, v in receipt["inputs"].items()})
        actual = fit.input_hashes(args)
        if actual != receipt["input_sha256"]:
            raise ValueError("fit input/source bytes changed or hash inventory is incomplete")
        nested = Path(receipt["search"]["receipt"])
        if adapter.sha256_file(nested) != receipt["search"]["receipt_sha256"]:
            raise ValueError("nested search receipt hash changed")
        search = read_json(nested)
        if search["status"] != "profile_numerically_resolved":
            raise ValueError("nested search is unresolved")
        for regime, tight in (("standard", False), ("tight", True)):
            original = view_of(receipt, f"spatial.{regime}")["free"]
            stored = search["free"][str(tight)]
            if finite(original["criterion"]) != finite(stored["criterion"]):
                raise ValueError("root and search receipts disagree on the frozen maximum")
            for family in FAMILIES:
                if original[family]["parameters"] != stored[family]["parameters"]:
                    raise ValueError("root and search receipts disagree on free parameters")
        for name in VIEWS:
            required_nodes(view_of(receipt, name))
        return cls(path, receipt, search, args, adapter.sha256_file(path))

    def identity(self) -> Json:
        return {
            "path": str(self.path),
            "sha256": self.sha256,
            "source": self.receipt["source"],
            "input_sha256": self.receipt["input_sha256"],
            "search_receipt": self.receipt["search"]["receipt"],
            "search_receipt_sha256": self.receipt["search"]["receipt_sha256"],
        }

    def verify_unchanged(self) -> None:
        checked = Evidence.load(self.path)
        if checked.sha256 != self.sha256:
            raise ValueError("fit receipt changed during audit")


def verify_pair(left: Evidence, right: Evidence, kind: str) -> None:
    wanted_modes = ("dense", "lean") if kind == "dense_lean" else ("lean", "lean")
    if (left.receipt["search_mode"], right.receipt["search_mode"]) != wanted_modes:
        raise ValueError("wrong search modes for comparison")
    if left.receipt["source"] != right.receipt["source"]:
        raise ValueError("paired source identities differ")
    if left.receipt["data_identity"] != right.receipt["data_identity"]:
        raise ValueError("paired site/design identities differ")
    for name in (
        "public_inputs.npz",
        "exposure.npz",
        "observations",
        "arrival_bank",
        "compressed_bank",
    ):
        values = []
        for evidence in (left, right):
            path = (
                evidence.args.input_dir / name
                if name.endswith(".npz")
                else getattr(evidence.args, name)
            )
            values.append(evidence.receipt["input_sha256"][str(path.resolve())])
        different_bank = kind == "independent_bank" and name in ("arrival_bank", "compressed_bank")
        if (values[0] == values[1]) == different_bank:
            raise ValueError(f"unexpected paired input identity: {name}")


class AnchorSearch(fit.FitSearch):
    original_points: dict[bool, dict[float, Json]]

    def neighbours(self, log_h: float, family: str, tight: bool) -> list[np.ndarray]:
        original = self.original_points[tight]
        left, right = [x for x in original if x < log_h], [x for x in original if x > log_h]
        near = (
            ([log_h] if log_h in original else [])
            + ([max(left)] if left else [])
            + ([min(right)] if right else [])
        )
        candidates = [parameters(original[x][family]) for x in near]
        candidates.append(parameters(self.free[tight][family]))
        candidates.extend(super().neighbours(log_h, family, tight))
        starts: list[np.ndarray] = []
        for candidate in candidates:
            if not any(np.array_equal(candidate, old) for old in starts):
                starts.append(candidate)
        return starts


class Probe:
    def __init__(self, evidence: Evidence, output: Path):
        self.evidence = evidence
        data, identity = load_panel_data(evidence.args)
        if identity != evidence.receipt["data_identity"]:
            raise ValueError("loaded data identity differs from the recorded fit")
        output.mkdir(parents=True, exist_ok=False)
        self.search = AnchorSearch(data, evidence.receipt["search_mode"], output)
        self.search.free = {
            tight: copy.deepcopy(evidence.search["free"][str(tight)]) for tight in (False, True)
        }
        self.search.original_points = {
            tight: {
                finite(row["log_h"]): copy.deepcopy(row)
                for row in evidence.search["points"][str(tight)]
            }
            for tight in (False, True)
        }
        self.reduced = {
            name: fit.ReducedFamily(name, self.search.criterion, beta_free=name == "exposure")
            for name in ("exposure", "constant")
        }

    def evaluate(self, name: str, x: float, budget: int) -> Json:
        if name.startswith("spatial."):
            tight = name == "spatial.tight"
            self.search.point_limit = max(self.search.point_limit, budget)
            row = self.search.point(x, tight=tight, refresh=True)
            details = fit.owner_contacts(row)
            return {
                "criterion": finite(row["criterion"]),
                "eligible": all(row[f]["eligible"] for f in FAMILIES),
                "nuisance_contacts": contacts(details, name),
                "fit": {f: fit.family_row(row[f]) for f in FAMILIES},
            }
        view = view_of(self.evidence.receipt, name)
        original = profile_rows(view)
        family = self.reduced[name]
        starts = [parameters(view["free"]), parameters(view["null"])]
        left, right = [a for a in original if a < x], [a for a in original if a > x]
        nearby = (
            ([x] if x in original else [])
            + ([max(left)] if left else [])
            + ([min(right)] if right else [])
        )
        starts.extend(parameters(original[a]) for a in nearby)
        starts.extend(family._starts(x, free=False))
        row = family._fit(min(30.0, math.exp(x)), starts, f"audit_{name}_{x.hex()}")
        family.points[x] = row
        return {
            "criterion": finite(row["criterion"]),
            "eligible": row["eligible"],
            "nuisance_contacts": contacts(row, name),
            "fit": fit.family_row(row),
        }


def membership_checks(evidence: Evidence, name: str, x: float, w: float) -> list[Json]:
    view = view_of(evidence.receipt, name)
    if name.startswith("spatial."):
        key = "tight_level_sets" if name == "spatial.tight" else "level_sets"
        return [frozen_membership_check(level, x, w) for level in evidence.search[key]]
    checks = []
    for level in view["level_sets"]:
        inside = any(c["lower_log_h"] <= x <= c["upper_log_h"] for c in level["components"])
        root = x in level["roots_log_h"]
        residual = w - level["cutoff"]
        checks.append(
            {
                "cutoff": level["cutoff"],
                "inside_frozen_set": inside,
                "residual": residual,
                "at_recorded_root": root,
                "passed": (root and abs(residual) <= 0.01) or inside == (residual <= 0.0),
            }
        )
    return checks


def anchor_record(evidence: Evidence, name: str, x: float, probe: Json) -> tuple[Json, list[str]]:
    view = view_of(evidence.receipt, name)
    maximum = finite(view["free"]["criterion"])
    fresh = finite(probe["criterion"])
    checks = membership_checks(evidence, name, x, 2.0 * (maximum - fresh))
    failures = []
    if probe["eligible"] is not True:
        failures.append("fresh fixed-profile fit is ineligible")
    if fresh > maximum + 1e-4:
        failures.append("fresh fixed-profile score exceeds frozen free maximum")
    if not all(row["passed"] for row in checks):
        failures.append("fresh fixed-profile score contradicts frozen level sets")
    original = profile_rows(view).get(x)
    value, cs = fresh, probe["nuisance_contacts"]
    if original is not None:
        value, cs = finite(original["criterion"]), contacts(original, name)
        if 2.0 * abs(fresh - value) > 0.01:
            failures.append("fresh replay differs from original node by more than 0.01 W")
        if 2.0 * (maximum - value) <= max(fit.CUTOFF_GRID) and cs != probe["nuisance_contacts"]:
            failures.append("fresh replay changes nuisance contacts inside frozen sets")
    return {
        "criterion": value,
        "nuisance_contacts": cs,
        "eligible": probe["eligible"],
        "original_node_preserved": original is not None,
        "probe_criterion": fresh,
        "probe_nuisance_contacts": probe["nuisance_contacts"],
        "probe_fit": probe["fit"],
        "probe_w": 2.0 * (maximum - fresh),
        "membership_checks": checks,
        "failures": failures,
    }, failures


def error_record(stage: str, error: Exception, *, numerical: bool = False) -> Json:
    status = "unavailable"
    if isinstance(error, (MemoryError, OSError)):
        status = "execution_error"
    elif numerical and isinstance(error, (RuntimeError, FloatingPointError, np.linalg.LinAlgError)):
        status = "scientific_failure"
    return {
        "stage": stage,
        "status": status,
        "type": type(error).__name__,
        "message": str(error),
    }


def status_of(result: Json) -> str:
    if any(error["status"] == "execution_error" for error in result["errors"]):
        return "execution_error"
    if any(error["status"] == "unavailable" for error in result["errors"]):
        return "unavailable"
    return "scientific_failure" if result["failures"] or result["errors"] else "available"


def audit_anchors(left: Evidence, right: Evidence, kind: str, output: Path) -> Json:
    verify_pair(left, right, kind)
    result: Json = {
        "schema": "sprint2-common-anchors-v1",
        "kind": kind,
        "left_receipt_sha256": left.sha256,
        "right_receipt_sha256": right.sha256,
        "identities": {"left": left.identity(), "right": right.identity()},
        "normalisers": "original free criteria, never refitted or updated",
        "views": {},
        "errors": [],
        "failures": [],
    }
    probes = {"left": Probe(left, output / "left"), "right": Probe(right, output / "right")}
    for name in VIEWS:
        nodes = sorted(
            required_nodes(view_of(left.receipt, name))
            | required_nodes(view_of(right.receipt, name))
        )
        rows: list[Json] = []
        result["views"][name] = {
            "frozen_free_criteria": {
                "left": finite(view_of(left.receipt, name)["free"]["criterion"]),
                "right": finite(view_of(right.receipt, name)["free"]["criterion"]),
            },
            "rows": rows,
        }
        for x in nodes:
            row: Json = {"log_h": x}
            rows.append(row)
            for label, evidence in (("left", left), ("right", right)):
                stage = f"{name}/{label}/{x.hex()}"
                try:
                    raw = probes[label].evaluate(name, x, len(nodes))
                    row[label], failures = anchor_record(evidence, name, x, raw)
                    result["failures"].extend(f"{stage}: {failure}" for failure in failures)
                except Exception as error:
                    result["errors"].append(error_record(stage, error, numerical=True))
                    row[label] = {"eligible": False, "error": result["errors"][-1]}
    for label, evidence in (("left", left), ("right", right)):
        try:
            evidence.verify_unchanged()
        except Exception as error:
            result["errors"].append(error_record(f"{label}/final_identity", error))
    result["status"] = status_of(result)
    return result


def gradient_check(criterion: Any, row: Json, step_scale: float) -> Json:
    family = row["family"]
    zero = family == "sigma_zero"
    names = ["alpha", "beta", *([] if zero else ["log_sigma"]), "log_h", "detection_sd"]
    theta = np.array([finite(row["parameters"][name]) for name in names])
    bounds = criterion._bounds(None, zero)
    evaluate = criterion.evaluate_sigma_zero if zero else criterion.evaluate_positive
    base = evaluate(theta, nuisance_fd=True)
    if not base.success or not np.isfinite(base.criterion_gradient).all():
        raise ValueError("analytic base evaluation is unavailable")
    if abs(finite(base.criterion) - finite(row["criterion"])) > 1e-8:
        raise ValueError("deterministic score at the recorded free parameters changed")
    steps, differences, stencils, evaluations = [], [], [], []
    offsets: tuple[int, ...]
    weights: tuple[int, ...]
    for i, (lower, upper) in enumerate(bounds):
        value = theta[i]
        step = step_scale * max(1.0, abs(value))
        if not lower <= value <= upper:
            raise ValueError("recorded free coordinate is outside its bounds")
        if value - step < lower:
            offsets, weights, stencil = (0, 1, 2), (-3, 4, -1), "forward_second_order"
        elif value + step > upper:
            offsets, weights, stencil = (0, -1, -2), (3, -4, 1), "backward_second_order"
        else:
            offsets, weights, stencil = (-1, 1), (-1, 1), "central"
        values = []
        for offset in offsets:
            trial = theta.copy()
            trial[i] += offset * step
            if not lower <= trial[i] <= upper:
                raise ValueError("second-order inward stencil crosses the opposite bound")
            evaluated = evaluate(trial, nuisance_fd=False)
            if not evaluated.success:
                raise ValueError(f"unavailable reoptimised stencil: {names[i]}/{offset}")
            values.append(finite(evaluated.criterion))
        differences.append(float(np.dot(weights, values) / (2.0 * step)))
        steps.append(step)
        stencils.append(stencil)
        evaluations.append({"offsets": list(offsets), "criterion": values})
    analytic = [finite(value) for value in base.criterion_gradient]
    passed = [
        abs(a - b) <= 1e-5 + 1e-4 * max(abs(a), abs(b))
        for a, b in zip(analytic, differences, strict=True)
    ]
    return {
        "family": family,
        "coordinates": names,
        "parameters": copy.deepcopy(row["parameters"]),
        "step_scale": step_scale,
        "analytic": analytic,
        "finite_difference": differences,
        "steps": steps,
        "stencils": stencils,
        "reoptimized": True,
        "stencil_evaluations": evaluations,
        "component_passed": passed,
    }


def audit_gradients(dense: Evidence, lean: Evidence, output: Path) -> Json:
    verify_pair(dense, lean, "dense_lean")
    result: Json = {
        "schema": "sprint2-free-gradient-v1",
        "dense_receipt_sha256": dense.sha256,
        "lean_receipt_sha256": lean.sha256,
        "identities": {"dense": dense.identity(), "lean": lean.identity()},
        "checks": [],
        "errors": [],
        "failures": [],
    }
    for search, evidence in (("dense", dense), ("lean", lean)):
        probe = Probe(evidence, output / search)
        for regime in ("standard", "tight"):
            free = view_of(evidence.receipt, f"spatial.{regime}")["free"]
            row = free[free["selected_family"]]
            for step in STEP_SCALES:
                identity = {"search": search, "regime": regime, "step_scale": step}
                stage = f"{search}/{regime}/{step}"
                try:
                    check = gradient_check(probe.search.criterion, row, step)
                    result["checks"].append({**identity, **check})
                    result["failures"].extend(
                        f"{stage}/{name}: unprojected gradient disagrees"
                        for name, passed in zip(
                            check["coordinates"], check["component_passed"], strict=True
                        )
                        if not passed
                    )
                except Exception as error:
                    result["errors"].append(error_record(stage, error, numerical=True))
                    result["checks"].append({**identity, "error": result["errors"][-1]})
        try:
            evidence.verify_unchanged()
        except Exception as error:
            result["errors"].append(error_record(f"{search}/final_identity", error))
    result["status"] = status_of(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    anchors = commands.add_parser("anchors")
    anchors.add_argument("--kind", choices=("dense_lean", "independent_bank"), required=True)
    anchors.add_argument("--left-receipt", type=Path, required=True)
    anchors.add_argument("--right-receipt", type=Path, required=True)
    gradients = commands.add_parser("gradients")
    gradients.add_argument("--dense-receipt", type=Path, required=True)
    gradients.add_argument("--lean-receipt", type=Path, required=True)
    for command in (anchors, gradients):
        command.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if any(os.environ.get(name) != "1" for name in fit.THREAD_ENVIRONMENT):
        raise ValueError("set all numerical thread environment variables to 1")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    schema = (
        "sprint2-common-anchors-v1" if args.command == "anchors" else "sprint2-free-gradient-v1"
    )
    try:
        if args.command == "anchors":
            result = audit_anchors(
                Evidence.load(args.left_receipt),
                Evidence.load(args.right_receipt),
                args.kind,
                args.output_dir,
            )
        else:
            result = audit_gradients(
                Evidence.load(args.dense_receipt), Evidence.load(args.lean_receipt), args.output_dir
            )
    except Exception as error:
        result = {"schema": schema, "errors": [error_record("setup", error)], "failures": []}
        result["status"] = status_of(result)
    result["producer"] = {
        "path": str(Path(__file__).resolve()),
        "sha256": adapter.sha256_file(Path(__file__)),
        "source": adapter._git_identity(ROOT),
    }
    result["elapsed_seconds"] = time.perf_counter() - started
    write_json(args.output_dir / "receipt.json", result)
    print(json.dumps({"schema": result["schema"], "status": result["status"]}))
    return 2 if result["status"] == "execution_error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
