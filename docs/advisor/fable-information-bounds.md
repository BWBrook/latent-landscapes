# Complete-data information bounds for the predator effect

2 October 2026. Advisory note by Fable (external scientific advisor), written at
Astra's request in Correspondence thread 53, message 802, so that the advisory
calculations cited in Goals 053 and 055 have a durable source in the project.
This is not registered evidence and not a measured operating characteristic.

## Status and use

These are **ideal-observation** calculations. They assume every prey loss time
is observed exactly at sampled sites, with predator arrival times known from
archived histories. Real analyses integrate over latent arrival, use interval
surveys and imperfect detection, and estimate nuisances on finite grids. The
bounds therefore understate real costs. Goal 053 measured this directly: the
predicted free/known-slope SE ratio at h = 3 was 1.25 at beta = 0 and 1.05 at
beta = .60, against observed log-RMSE ratios of 1.40 and 1.08. The same style of
argument overstated the held-out predictive gain from adjustment by a factor of
about three to five. Use the bounds for direction, ordering and mechanism; do
not use them as precision or sensitivity forecasts.

Original posts: thread 53, messages 514 (slope cost) and 796 (background
level). A pre-release calculation in message 514 that held every site at release
while adding pre-release losses was withdrawn after Astra's correction in
message 578: it implicitly assumed replacement. Everything below follows one
cohort without replacement.

## Model and information

Training sites i = 1..120 have whole-map-normalised background hazard

    lambda_i(mu, beta) = mu * exp(beta * A_i) / mean_map(exp(beta * A)),

with hazard lambda_i before predator arrival T_i and h * lambda_i afterwards,
over a window ending at day 60. A is the registered normal-score exposure proxy
over all 6,048 map cells. Monitoring may start D days before release.

For a counting process with log-linear intensity, the Fisher information for
parameters theta is the sum over segments of expected events times x x', where
x is the gradient of the log intensity. Here, for theta = (log mu, log h, beta):

- pre-arrival segment: x = (1, 0, A_i - m(beta)), expected events
  e_pre,i = 1 - exp(-lambda_i P_i), with P_i = min(T_i, 60) + D;
- post-arrival segment: x = (1, 1, A_i - m(beta)), expected events
  e_post,i = exp(-lambda_i P_i) * (1 - exp(-h lambda_i Q_i)), Q_i = max(0, 60 - T_i);

where m(beta) = sum_map A exp(beta A) / sum_map exp(beta A) is the derivative of
the log normaliser. The standard error of log h with a given set of parameters
estimated is read from the inverse of the corresponding information submatrix.

**Rate-ratio identity.** With the level mu estimated and the slope known, the
information for (log mu, log h) is [[E_pre + E_post, E_post], [E_post, E_post]],
so var(log h) = 1/E_pre + 1/E_post exactly, where E are expected event counts.
The effect then behaves as a ratio of two Poisson rates, and its precision is set
by the smaller count. On the archived arrival maps E_pre is about 7.

**Supplied-level error.** With mu supplied as mu' and only h estimated, the
complete-data MLE is h-hat = n_post / (mu' tau_post), so log h-hat shifts by
log(mu / mu'). A 20% underestimate gives +log 1.25 = +0.223. Goal 055 observed
mean signed log-error shifts at h = 3 of about +0.24 for the constant model and
+0.26 to +0.27 for the adjusted model, with mirror-image shifts for a 25%
overestimate. The ratio mechanism explains most of the observed bias.

## Results on the six archived arrival maps

Means over the Goal 052 baseline arrival maps (blocks 0-5), beta = 0 unless
stated. Values are SE(log h).

Cost of estimating the spatial slope, level supplied, current survey:

| Generating beta | h | Slope known | Slope estimated | Ratio |
|---:|---:|---:|---:|---:|
| 0 | 1 | 0.395 | 0.473 | 1.20 |
| 0 | 3 | 0.237 | 0.299 | 1.26 |
| 0.6 | 1 | 0.345 | 0.362 | 1.05 |
| 0.6 | 3 | 0.214 | 0.225 | 1.05 |

Cost of estimating the background level, h = 3:

| Design | E_pre | E_post | Both known | Level estimated | Slope estimated | Both estimated |
|---|---:|---:|---:|---:|---:|---:|
| Current survey | 7.1 | 17.9 | 0.237 | 0.443 | 0.299 | 0.514 |
| Plus 30 days pre-release monitoring, same cohort | 13.7 | 16.8 | 0.244 | 0.364 | 0.291 | 0.401 |
| Plus 60 days pre-release monitoring, same cohort | 19.9 | 15.8 | 0.251 | 0.337 | 0.289 | 0.363 |
| Plus 40 never-invaded control sites | 11.7 | 17.9 | 0.237 | 0.377 | 0.283 | 0.496 |
| Plus 120 never-invaded control sites | 20.7 | 17.9 | 0.237 | 0.323 | 0.268 | 0.486 |

Reading: estimating the level nearly doubles SE(log h); estimating the slope as
well raises it about 2.2-fold. Monitoring the sites that will be invaded before
release recovers much of that loss even with the slope estimated, because it
measures background where the predator later acts. Control sites outside the
invasion help only when background does not vary with exposure. Pre-release
losses remove sites from the post-release risk set, which is why "both known"
rises slightly with D.

## Reproduction

Run from the repository root with the project environment
(`uv run python <file>`). Inputs are the authenticated Goal 052 pilot arrays.

```python
import numpy as np

z = np.load("artifacts/goal052_execution/output/evidence.npz")
cells = list(z["cell_ids"]); A = z["site_A"]; tr = z["training_mask"]
mapA = z["map_A"].ravel(); mu = 0.002
blocks = [i for i, c in enumerate(cells) if c == "B_h3"]   # six archived arrival maps

def information(T, beta, h, D=0.0, controls=0):
    w = np.exp(beta * mapA); m = (mapA * w).sum() / w.sum()
    As = A[tr]; Tt = np.where(np.isfinite(T[tr]), T[tr], np.inf)
    if controls:   # never-invaded sites, A resampled from training sites unreached by day 60
        pool = As[~np.isfinite(Tt) | (Tt > 60)]
        As = np.r_[As, np.random.default_rng(1).choice(pool, controls)]
        Tt = np.r_[Tt, np.full(controls, np.inf)]
    lam = mu * np.exp(beta * As) / w.mean(); a = As - m
    P = np.minimum(Tt, 60.0) + D; Q = np.maximum(0.0, 60.0 - Tt)
    e_pre = 1 - np.exp(-lam * P)
    e_post = np.exp(-lam * P) * (1 - np.exp(-h * lam * Q))
    X_pre = np.c_[np.ones_like(a), np.zeros_like(a), a]
    X_post = np.c_[np.ones_like(a), np.ones_like(a), a]
    I = (X_pre * e_pre[:, None]).T @ X_pre + (X_post * e_post[:, None]).T @ X_post
    def se(free):   # index 0 = log mu, 1 = log h, 2 = beta
        sub = np.linalg.inv(I[np.ix_(free, free)])
        return np.sqrt(sub[free.index(1), free.index(1)])
    return dict(E_pre=e_pre.sum(), E_post=e_post.sum(), known=se([1]),
                level=se([0, 1]), slope=se([1, 2]), both=se([0, 1, 2]))

def mean_over_maps(**kw):
    rows = [information(z["true_arrival"][i], **kw) for i in blocks]
    return {k: round(float(np.mean([r[k] for r in rows])), 3) for k in rows[0]}

for beta in (0.0, 0.6):
    for h in (1.0, 3.0):
        print("slope cost", beta, h, mean_over_maps(beta=beta, h=h))
for D, K in ((0, 0), (30, 0), (60, 0), (0, 40), (0, 120)):
    print("level cost h=3, D", D, "controls", K, mean_over_maps(beta=0.0, h=3.0, D=D, controls=K))
```
