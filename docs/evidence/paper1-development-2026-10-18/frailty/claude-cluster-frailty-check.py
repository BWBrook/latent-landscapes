"""Claude complete-data cluster-frailty check (thread 87). Same data as claude-frailty-check.py;
training sites are grouped into their five-site clusters by spatial proximity, and a gamma
frailty shared within each cluster (variance estimated) replaces the site-level frailty.
Run from the repository root with the project venv."""
import glob
import json
import math

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln

PUB = "artifacts/goal060_execution/audit-repair/public_inputs"
BASE = "artifacts/goal062_execution/completed-20261015/snapshot/production/evaluation"
A = np.load(f"{PUB}/exposure.npz")["site_a"]
P = np.load(f"{PUB}/public_inputs.npz")
RC = np.c_[P["site_rows"], P["site_cols"]].astype(float)
B100 = 0.7 * math.sqrt(math.log(2.0))


def clusters(idx, radius=4.0):
    lab = -np.ones(len(idx), int)
    nxt = 0
    for i in range(len(idx)):
        if lab[i] >= 0:
            continue
        stack, lab[i] = [i], nxt
        while stack:
            j = stack.pop()
            d = np.abs(RC[idx] - RC[idx[j]]).max(1)
            for m in np.where((d <= radius) & (lab < 0))[0]:
                lab[m] = nxt
                stack.append(m)
        nxt += 1
    return lab


def pieces(loss, arrival, start):
    end = np.minimum(loss, 60.0)
    lost = loss <= 60.0
    pre = np.clip(np.minimum(end, arrival) - start, 0.0, None)
    post = np.clip(end - np.maximum(arrival, start), 0.0, None)
    return lost, lost & (loss > arrival), pre, post


def nll(theta, w, lost, pe, pre, post, cl, ncl):
    c, h, k = math.exp(theta[0]), math.exp(theta[1]), math.exp(theta[2])
    cum = c * w * (pre + h * post)
    lograte = np.where(lost, np.log(c * w * np.where(pe, h, 1.0)), 0.0)
    D = np.bincount(cl, weights=lost.astype(float), minlength=ncl)
    L = np.bincount(cl, weights=cum, minlength=ncl)
    ll = lograte.sum() + (gammaln(k + D) - gammaln(k) + k * math.log(k) - (k + D) * np.log(k + L)).sum()
    return -ll


def fit(w, lost, pe, pre, post, cl):
    ncl = cl.max() + 1
    x0 = [math.log(max(lost.sum(), 1) / max((w * (pre + post)).sum(), 1e-9)), 0.5, 0.5]
    b = [(-15, 2), (0.0, math.log(10.0)), (math.log(0.05), math.log(1e4))]
    return minimize(nll, x0, args=(w, lost, pe, pre, post, cl, ncl), method="L-BFGS-B", bounds=b).x[1]


out, sizes = {}, None
for cell, load in (("04", 0.5), ("09", B100), ("01", 0.5), ("07", B100)):
    rows, label = [], None
    for rep in sorted(glob.glob(f"{BASE}/cell-{cell}/rep-*")):
        label = json.load(open(f"{rep}/main.json"))["cell_label"]
        ev = np.load(f"{rep}/evaluator.npz")
        tr = np.load(f"{rep}/observations.npz")["training_mask"]
        idx = np.where(tr)[0]
        cl = clusters(idx)
        sizes = np.bincount(np.bincount(cl)).tolist()
        loss, arr, w = ev["loss"][tr], ev["arrival"][tr], np.exp(load * A[tr])
        lh = math.log(float(label[-1]))
        alive0 = loss > 0.0
        _, cl0 = np.unique(cl[alive0], return_inverse=True)
        rows.append([fit(w, *pieces(loss, arr, -60.0), cl) - lh,
                     fit(w[alive0], *pieces(loss[alive0], arr[alive0], 0.0), cl0) - lh])
    a = np.array(rows)
    out[label] = {n: {"mean_log_error": float(a[:, j].mean()), "mcse": float(a[:, j].std(ddof=1) / math.sqrt(len(a))),
                      "mean_abs_log_error": float(np.abs(a[:, j]).mean())}
                  for j, n in enumerate(["baseline_cluster_frailty", "postonly_cluster_frailty"])}
out["training_cluster_size_histogram"] = sizes
print(json.dumps(out, indent=1))
