"""Claude complete-data frailty/design check (thread 87). True loss and arrival times, perfect
detection, exposure weights w=exp(beta A) with the generating exposure loading. Compares
exponential (homogeneous residual) and gamma-frailty MLEs, for the full window (days -60..60,
baseline present) and a post-only window (sites alive at day 0, followed 0..60).
Run from the repository root with the project venv."""
import glob
import json
import math

import numpy as np
from scipy.optimize import minimize

PUB = "artifacts/goal060_execution/audit-repair/public_inputs/exposure.npz"
BASE = "artifacts/goal062_execution/completed-20261015/snapshot/production/evaluation"
A = np.load(PUB)["site_a"]
B100 = 0.7 * math.sqrt(math.log(2.0))


def pieces(loss, arrival, start):
    end = np.minimum(loss, 60.0)
    lost = loss <= 60.0
    pre = np.clip(np.minimum(end, arrival) - start, 0.0, None)
    post = np.clip(end - np.maximum(arrival, start), 0.0, None)
    post_event = lost & (loss > arrival)
    return lost, post_event, pre, post


def negloglik(theta, w, lost, post_event, pre, post, frailty):
    log_c, log_h = theta[0], theta[1]
    c, h = math.exp(log_c), math.exp(log_h)
    cum = c * w * (pre + h * post)
    rate = c * w * np.where(post_event, h, 1.0)
    if frailty is None:
        ll = np.where(lost, np.log(rate), 0.0) - cum
    else:
        k = math.exp(theta[2]) if frailty == "estimate" else frailty
        ll = np.where(lost, np.log(rate) - np.log1p(cum / k), 0.0) - k * np.log1p(cum / k)
    return -ll.sum()


def fit(w, lost, post_event, pre, post, frailty):
    x0 = [math.log(max(lost.sum(), 1) / max((w * (pre + post)).sum(), 1e-9)), 0.5]
    bounds = [(-15, 2), (0.0, math.log(10.0))]
    if frailty == "estimate":
        x0.append(0.5)
        bounds.append((math.log(0.05), math.log(1e4)))
    r = minimize(negloglik, x0, args=(w, lost, post_event, pre, post, frailty), method="L-BFGS-B", bounds=bounds)
    return r.x[1]


out = {}
for cell, load in (("04", 0.5), ("09", B100), ("01", 0.5), ("07", B100)):
    rows, label = [], None
    for rep in sorted(glob.glob(f"{BASE}/cell-{cell}/rep-*")):
        label = json.load(open(f"{rep}/main.json"))["cell_label"]
        ev = np.load(f"{rep}/evaluator.npz")
        tr = np.load(f"{rep}/observations.npz")["training_mask"]
        loss, arr, w = ev["loss"][tr], ev["arrival"][tr], np.exp(load * A[tr])
        lh = math.log(float(label[-1]))
        full = pieces(loss, arr, -60.0)
        alive0 = loss > 0.0
        po = pieces(loss[alive0], arr[alive0], 0.0)
        wpo = w[alive0]
        rows.append([
            fit(w, *full, None) - lh,
            fit(w, *full, "estimate") - lh,
            fit(wpo, *po, None) - lh,
            fit(wpo, *po, "estimate") - lh,
        ])
    a = np.array(rows)
    names = ["baseline_homogeneous", "baseline_gamma_frailty_k_estimated", "postonly_homogeneous", "postonly_gamma_frailty_k_estimated"]
    out[label] = {n: {"mean_log_error": float(a[:, j].mean()), "mcse": float(a[:, j].std(ddof=1) / math.sqrt(len(a))),
                      "mean_abs_log_error": float(np.abs(a[:, j]).mean())} for j, n in enumerate(names)}
    out[label]["n"] = len(a)
print(json.dumps(out, indent=1))
