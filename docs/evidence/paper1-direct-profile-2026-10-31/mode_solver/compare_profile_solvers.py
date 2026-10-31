from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy.linalg import cho_factor

ROOT = Path(__file__).resolve().parents[3]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts", nargs="+", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--observations", type=Path)
    args = parser.parse_args()
    data_driver = load(
        "solver_data",
        ROOT / "artifacts/paper1_fast_likelihood_20261031/kernel/check_laplace_gradient.py",
    )
    old_path = Path(__file__).with_name("spatial_profile-lbfgs.py")
    old = load("spatial_profile_lbfgs_reference", old_path)
    from latent_landscapes import spatial_profile as new
    from latent_landscapes.differentiable_likelihood import prepare_site_likelihood

    if args.observations is not None:
        data_driver.OBSERVATIONS = args.observations.resolve()
    data = data_driver.load_data()

    def factory(h, sd):
        return prepare_site_likelihood(data.observed, data.bank, h, detection_sd=sd)

    points = []
    for path in args.receipts:
        receipt = json.loads(path.read_text())
        profile = receipt["profile"]
        candidates = [profile["best_positive"]] + [
            row for row in profile["grid_statuses"] if row["family"] == "positive_sigma"
        ]
        for row in candidates:
            if row is None or row.get("status") == "unresolved":
                continue
            params = row["parameters"]
            point = np.array(
                [params[key] for key in ("alpha", "beta", "log_sigma", "detection_sd")]
            )
            signature = (row["h"], *point)
            if any(item[0] == signature for item in points):
                continue
            points.append((signature, point, path))
    rows = []
    started = time.perf_counter()
    for signature, point, source in points:
        h = signature[0]
        old_criterion = old.SpatialProfileCriterion(data, evaluator_factory=factory)
        new_criterion = new.SpatialProfileCriterion(data, evaluator_factory=factory)
        base = old_criterion.evaluate_positive(point, fixed_h=h)
        if not base.success:
            rows.append(
                {"h": h, "source": str(source), "old_base_success": False, "acceptance": False}
            )
            continue
        eta0 = point[0] + point[1] * data.exposure
        precision = old_criterion._k_inverse / math.exp(2 * point[2])
        starts = [np.zeros(len(eta0)), base.mode.u + 0.1 * np.sin(np.arange(len(eta0)))]
        branch_rows = []
        for start in starts:
            results = []
            for criterion in (old_criterion, new_criterion):
                evaluator = criterion.curves(h, point[-1])
                branch = criterion._mode_branch(eta0, precision, evaluator, start.copy())
                if branch is None:
                    results.append(None)
                    continue
                eta = eta0 + branch[0]
                curvature = evaluator.evaluate(eta)[2]
                factor = cho_factor(precision - np.diag(curvature), lower=True)
                logdet_h = 2 * np.log(np.diag(factor[0])).sum()
                laplace = branch[1] - 0.5 * (
                    len(eta0) * 2 * point[2] + criterion._logdet_k + logdet_h
                )
                stationary = branch[2] <= criterion.mode_tolerance or (
                    branch[2] <= 10 * criterion.mode_tolerance
                    and branch[3] <= criterion.mode_tolerance * max(1.0, np.max(np.abs(branch[0])))
                    and branch[4] <= criterion.mode_tolerance
                )
                results.append(
                    {
                        "eta": eta,
                        "mode_value": branch[1],
                        "laplace": laplace,
                        "score_inf": branch[2],
                        "step_inf": branch[3],
                        "decrement": branch[4],
                        "evaluations": branch[6],
                        "success": bool(stationary),
                    }
                )
            record = {"both_returned": all(result is not None for result in results)}
            if record["both_returned"]:
                left, right = results
                record.update(
                    eta_inf=float(np.max(np.abs(left["eta"] - right["eta"]))),
                    mode_value_difference=float(right["mode_value"] - left["mode_value"]),
                    laplace_difference=float(right["laplace"] - left["laplace"]),
                    old={k: v for k, v in left.items() if k != "eta"},
                    new={k: v for k, v in right.items() if k != "eta"},
                )
                record["acceptance"] = bool(
                    left["success"]
                    and right["success"]
                    and record["eta_inf"] <= 1e-6
                    and abs(record["mode_value_difference"]) <= 1e-8
                    and abs(record["laplace_difference"]) <= 1e-8
                )
            else:
                record["acceptance"] = False
            branch_rows.append(record)
        old_value = old_criterion.evaluate_positive(point, fixed_h=h, mode_start=starts[-1])
        new_value = new_criterion.evaluate_positive(point, fixed_h=h, mode_start=starts[-1])
        difference = new_value.criterion - old_value.criterion
        rows.append(
            {
                "h": h,
                "source": str(source),
                "parameters": point.tolist(),
                "old_base_success": True,
                "branches": branch_rows,
                "criterion_difference": float(difference),
                "new_criterion": float(new_value.criterion),
                "old_criterion": float(old_value.criterion),
                "new_success": new_value.success,
                "old_success": old_value.success,
                "branch_counts": [old_value.mode.branch_count, new_value.mode.branch_count],
                "old_stats": old_criterion.stats,
                "new_stats": new_criterion.stats,
                "acceptance": bool(
                    all(row["acceptance"] for row in branch_rows)
                    and new_value.success
                    and old_value.success
                    and abs(difference) <= 1e-8
                ),
            }
        )
    sources = [
        Path(__file__),
        old_path,
        ROOT / "src/latent_landscapes/spatial_profile.py",
        ROOT / "src/latent_landscapes/differentiable_likelihood.py",
        ROOT / "artifacts/paper1_fast_likelihood_20261031/kernel/check_laplace_gradient.py",
        *args.receipts,
    ]
    result = {
        "schema": "paper1-mode-solver-comparison-v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "scope": (
            "identical outer parameters and identical zero/perturbed-mode starts; "
            "one observed 120-site history"
        ),
        "observations_path": str(data_driver.OBSERVATIONS),
        "source_sha256": {str(path): sha(path) for path in [*sources, data_driver.OBSERVATIONS]},
        "rows": rows,
        "elapsed_seconds": time.perf_counter() - started,
        "all_passed": all(row["acceptance"] for row in rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "rows": len(rows),
                "all_passed": result["all_passed"],
                "elapsed_seconds": result["elapsed_seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()
