"""Independent arithmetic and scalar-integration check of the frailty diagnostic."""
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.special import gammaln

root = Path(__file__).resolve().parent
folder = root / "frailty-repair"
rows = list(csv.DictReader((folder / "per_history.csv").open()))
summary = json.loads((folder / "summary.json").read_text())
assert len(rows) == 4000
assert len({(r["cell"], r["history_index"]) for r in rows}) == 4000
max_summary_error = 0.0
paired = {}
minimum_T = math.inf
for cell, expected in summary["cells"].items():
    subset = [r for r in rows if r["cell"] == cell]
    assert len(subset) == 500
    for model in ("homogeneous", "iid_gamma", "cluster_gamma"):
        estimates = np.array([float(r[f"{model}_free_h"]) for r in subset])
        truth = np.array([float(r["truth_h"]) for r in subset])
        errors = np.log(estimates / truth)
        T = np.array([2 * (float(r[f"{model}_h1_objective"]) - float(r[f"{model}_free_objective"])) for r in subset])
        minimum_T = min(minimum_T, float(T.min()))
        reported = expected["models"][model]
        for key, value in [("mean_signed_log_error", errors.mean()), ("mean_absolute_log_error", np.abs(errors).mean()), ("raw_T_gt_2_71_rate", np.mean(T > 2.71))]:
            max_summary_error = max(max_summary_error, abs(value - reported[key]))
    for alternative in ("iid_gamma", "cluster_gamma"):
        delta = np.array([abs(math.log(float(r[f"{alternative}_free_h"]) / float(r["truth_h"]))) - abs(math.log(float(r["homogeneous_free_h"]) / float(r["truth_h"]))) for r in subset])
        paired[f"{cell}_{alternative}_minus_homogeneous_MALE"] = {"mean": float(delta.mean()), "mcse": float(delta.std(ddof=1) / math.sqrt(len(delta)))}
assert max_summary_error < 1e-12
assert minimum_T >= -1e-7

# Integrate directly on the positive frailty axis, independently of the fitted code.
quad_checks = []
for k in (.3, 1.65, 20.):
    for d in (0, 1, 5):
        exposure = 1.7
        log_constant = k * math.log(k) - gammaln(k)
        value, error = quad(lambda v: math.exp(log_constant + (k + d - 1) * math.log(v) - (k + exposure) * v), 0, np.inf, epsabs=1e-10, epsrel=1e-10)
        analytic = math.exp(sum(math.log1p(j / k) for j in range(d)) - (k + d) * math.log1p(exposure / k))
        discrepancy = abs(value - analytic)
        assert discrepancy < 1e-8
        quad_checks.append({"k": k, "events": d, "absolute_error": discrepancy, "quadrature_error": error})

receipt = {"histories": len(rows), "max_summary_discrepancy": max_summary_error, "minimum_raw_T": minimum_T, "paired_absolute_error_changes": paired, "independent_gamma_quadrature": quad_checks, "inputs_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (folder / "per_history.csv", folder / "summary.json")}, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
Path(__file__).with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({k: v for k, v in receipt.items() if k not in ("paired_absolute_error_changes", "inputs_sha256")}))
