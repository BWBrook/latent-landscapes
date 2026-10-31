import numpy as np
from scipy.special import logsumexp
arr = np.load("artifacts/goal060_execution/audit-repair/arrival_bank/arrivals.npy", mmap_mode="r")
rng = np.random.default_rng(0)
sites = rng.choice(arr.shape[1], 16, replace=False)
xs = np.geomspace(1e-2, 200, 40)
def emp(u, x): return logsumexp(-x * u) - np.log(u.size)
def binned(u, x, bins):
    edges = np.linspace(0, 1, bins + 1); w = np.histogram(u, edges)[0] / u.size
    a0, d = edges[:-1], 1.0 / bins
    lb = -x * a0 + np.log(-np.expm1(-x * d)) - np.log(x * d)
    return logsumexp(lb, b=w)
rows = []
for s in sites:
    a = np.asarray(arr[:, s], dtype=np.float64)
    for cat in range(6):
        lo = 10.0 * cat
        sel = (a >= lo) & (a < lo + 10.0)
        u = (a[sel] - lo) / 10.0
        if u.size < 200: continue
        half = rng.permutation(u.size) < u.size // 2
        for x in xs:
            full = emp(u, x)
            rows.append((x, abs(emp(u[half], x) - emp(u[~half], x)) / 2, abs(binned(u, x, 64) - full), abs(binned(u, x, 256) - full)))
r = np.array(rows)
for lo_, hi_ in ((0, 5), (5, 20), (20, 50), (50, 200)):
    m = (r[:, 0] > lo_) & (r[:, 0] <= hi_)
    print(f"x in ({lo_:>3},{hi_:>3}]: bank half-split MC |dlog| median {np.median(r[m,1]):.1e} p95 {np.quantile(r[m,1],.95):.1e} | 64-bin err median {np.median(r[m,2]):.1e} p95 {np.quantile(r[m,2],.95):.1e} | 256-bin err p95 {np.quantile(r[m,3],.95):.1e}")
