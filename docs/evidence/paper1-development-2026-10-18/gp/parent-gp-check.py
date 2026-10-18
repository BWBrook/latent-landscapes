"""Independent endpoint arithmetic, direct-score and resolution checks."""
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

folder = Path(__file__).resolve().parent / "gp-prototype"
source = folder / "run_gp_prototype.py"
spec = importlib.util.spec_from_file_location("gp_checked", source)
gp = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gp
spec.loader.exec_module(gp)
results = json.loads((folder / "results.json").read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest() == results["manifest"]["script_sha256"]
checks = {}
initial_grid = gp.GRID.copy()
for case, saved in results["cases"].items():
    data = gp.load_data(case)
    endpoint_checks = {}
    for label, fit in saved["fits"].items():
        if fit.get("status") != "resolved":
            endpoint_checks[label] = {"status": "unresolved"}
            continue
        best = fit["best"]
        p = best["parameters"]
        fixed = 1.0 if label == "h1" else None
        zero = p["sigma"] == 0.0
        x = [p["alpha"], p["beta"]]
        if not zero:
            x.append(math.log(p["sigma"]))
        if fixed is None:
            x.append(math.log(p["h"]))
        x.append(p["detection_sd"])
        x = np.array(x)
        criterion = gp.Criterion(data)
        evaluator = criterion.logcriterion_sigma_zero if zero else criterion.logcriterion
        value, mode = evaluator(x, fixed_h=fixed)
        assert abs(-value - best["criterion"]) < 1e-7
        assert best["outer_fd"]["projected_gradient_inf"] <= 1e-3
        assert mode.success and mode.pd_ok and not mode.curve_bound_touch
        # Independent absolute-step differences, distinct from the fitted relative steps.
        bounds = [(-12.0, -3.0), (-2.0, 2.0)]
        if not zero:
            bounds.append((math.log(1e-4), math.log(2.0)))
        if fixed is None:
            bounds.append((0.0, math.log(30.0)))
        bounds.append((0.0, gp.SD_MAX * (1 - 1e-10)))
        derivatives = []
        for j, (lower, upper) in enumerate(bounds):
            a, b = x.copy(), x.copy()
            step = 5e-5
            if x[j] - step < lower:
                a[j] += step
                b[j] += 2 * step
                va, _ = evaluator(a, fixed_h=fixed)
                vb, _ = evaluator(b, fixed_h=fixed)
                derivatives.append((-3 * value + 4 * va - vb) / (2 * step))
                continue
            if x[j] + step > upper:
                a[j] -= step
                b[j] -= 2 * step
                va, _ = evaluator(a, fixed_h=fixed)
                vb, _ = evaluator(b, fixed_h=fixed)
                derivatives.append((3 * value - 4 * va + vb) / (2 * step))
                continue
            a[j] += step
            b[j] -= step
            va, _ = evaluator(a, fixed_h=fixed)
            vb, _ = evaluator(b, fixed_h=fixed)
            derivatives.append((va - vb) / (2 * step))
        projected = np.array(derivatives)
        for j, (lower, upper) in enumerate(bounds):
            if x[j] <= lower + 1e-8:
                projected[j] = min(projected[j], 0.0)
            if x[j] >= upper - 1e-8:
                projected[j] = max(projected[j], 0.0)
        assert np.isfinite(projected).all()
        assert np.max(np.abs(projected)) <= 1e-3
        eta = p["alpha"] + p["beta"] * data.A + mode.u
        hazards = np.exp(eta)
        exact = float(np.max(10 * hazards * (p["h"] - 1))) > gp.likelihood.SERIES_DOMAIN
        integration = gp.likelihood.build_integration(data.bank, [p["h"]], hazards,
            prey_times=data.observed.prey_times, cohort_start=data.observed.cohort_start,
            exact=exact, enforce_domain=not exact)
        direct = gp.likelihood.score_observations(data.observed, integration,
            detection_sd=p["detection_sd"]).joint_loglikelihood[0, 0]
        interpolated = criterion.curves(p["h"], p["detection_sd"]).evaluate(eta)[0]
        gp.GRID = np.linspace(initial_grid[0], initial_grid[-1], 2 * len(initial_grid) - 1)
        finer = gp.Criterion(data)
        eval_finer = finer.logcriterion_sigma_zero if zero else finer.logcriterion
        fine_value, fine_mode = eval_finer(x, fixed_h=fixed)
        gp.GRID = initial_grid
        assert fine_mode.success
        endpoint_checks[label] = {"status": "checked", "independent_absolute_step_gradient": derivatives,
            "independent_gradient_max": float(np.max(np.abs(derivatives))),
            "independent_projected_gradient_max": float(np.max(np.abs(projected))),
            "direct_site_max_error": float(np.max(np.abs(interpolated - direct))),
            "direct_sum_error": float(np.sum(interpolated - direct)),
            "criterion_change_on_grid_doubling": float(-fine_value + value),
            "recorded_grid_points": len(initial_grid), "check_grid_points": 2 * len(initial_grid) - 1}
    if all(v["status"] == "checked" for v in endpoint_checks.values()):
        lr = 2 * (saved["fits"]["free_h"]["best"]["criterion"] - saved["fits"]["h1"]["best"]["criterion"])
        assert lr >= -1e-7
        assert abs(lr - saved["profile"]["laplace_profile_lr"]) < 1e-10
        endpoint_checks["independently_reconstructed_LR"] = lr
    checks[case] = endpoint_checks
receipt = {"checks": checks, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "results_sha256": hashlib.sha256((folder / "results.json").read_bytes()).hexdigest(),
    "check_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "limits": "Two development histories and fixed fitted endpoints; no global optimum proof, profile endpoint coverage or statistical calibration."}
Path(__file__).with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
