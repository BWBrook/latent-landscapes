# Constant-family first-fit diagnostics

Independent Codex review, 12 November 2026. These are development diagnostics
prescribed in board message 3288, using the rejected candidate `99af520`.
They do not replace the archived qualification attempts or their verdicts.
No repair, acceptance change, training or validation was run.

## What was checked

The four original dense-task datasets were each evaluated at the first
constant-family fit: fixed h = 1, beta = 0, sole default start
`(alpha, detection_sd) = (-5.5, 0.2)`, maximum 120 iterations, internal
gradient target `1e-5` and eligibility threshold `1e-4`. The actual frozen
`ReducedFamily._fit_constant` and `_trust_region` functions ran unchanged,
with an observer recording their numerical state. Each final point received
the registered coordinate/rejected-direction sweep and a fixed 13 by 13
criterion grid over the fitted alpha/detection-SD domain. These are newly
observed prescribed first fits, not recovered historical step traces. They
cover four datasets; the nine failed historical roles were not all rerun.

The archived result directory is
`artifacts/sprint2/diagnostics-20261112/results/constant/`. Independent checks
verified all four receipt hashes against `summary.json`, the four original
task-record hashes, all 20 input-hash bindings against those original task
records, and all 113 frozen-source identities against both Git `99af520` and
the current source. The seven distinct locally available observation/bank
files were also rehashed. Raw banks and public map arrays were not downloaded
or freshly rehashed remotely during this review; their recorded hashes match
the original task bindings. The four recorded diagnostic-driver/source hashes
also match the files inspected here.

Every `trace.jsonl` exactly matches its receipt's embedded trace. All four
traces have one curvature record per iteration and a final collapse record;
every recorded curvature is complete and positive definite. The repeated
baseline evaluations are identical. Each sweep contains all nine prescribed
step sizes in both coordinates and the final rejected-step direction. In all
four cases that rejected step originated exactly at the final swept point.

## Observed result

| Case | Dataset | Iterations | Final projected gradient | Local predicted remaining gain | Grid maximum below final by |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | connected-2 window-high A | 21 | 1.232e-5 | 1.454e-14 | 2.3922 |
| 2 | connected-2 trend A | 23 | 1.983e-5 | 3.621e-14 | 1.1711 |
| 3 | corridor-1 b100-anchor A | 21 | 3.034e-5 | 3.864e-13 | 0.5179 |
| 4 | barrier-1 trend A | 21 | 2.442e-5 | 5.752e-14 | 3.0913 |

All four report `trust region collapsed`, with successful criterion
evaluations but optimizer success and eligibility both false. Their gradients
lie between the internal stopping target and the eligibility threshold. The
objective improves by 1.40–2.70 from the prescribed start before stalling;
the observed failure is not simply an invalid initial evaluation.

Final curvature eigenvalues are positive: the smaller eigenvalues are
39.94–50.74 and the larger are 5061–5463. The table's gain is
`0.5 g' B^-1 g` from this local curvature model. It is a local quadratic
prediction, not a certified bound on remaining gain or global profile error.
Final trial predictions are only 1.42e-15–6.70e-15, while one representable
increment in the summed criterion is 2.27e-13. Three final trials have zero
recorded gain; the other loses 4.55e-13. Ordinary objective subtraction is
therefore unable to resolve those final predicted improvements reliably.

There is also a detection-SD derivative discrepancy; this is not solely an
objective noise-floor result:

| Case | Reported detection-SD gradient | Central difference at t = 1e-4 | Central difference at t = 1e-6 |
| --- | ---: | ---: | ---: |
| 1 | +1.232e-5 | +1.232e-5 | -6.867e-5 |
| 2 | +1.983e-5 | +1.983e-5 | -6.389e-5 |
| 3 | +3.034e-5 | +3.034e-5 | -4.093e-5 |
| 4 | +2.442e-5 | +2.442e-5 | -5.730e-5 |

The reported derivative agrees with the `1e-4` stencil used by the frozen
code, but smaller stencils settle near negative values over `1e-5`–`1e-7`
before rounding dominates. The discrepancy decreases approximately with the
square of stencil size at larger steps. This supports a fixed finite-difference
truncation bias, alongside the small-step subtraction floor. Detection-SD
one-sided differences approach each other as the step shrinks; there is no
latent mode in this constant family to switch branches. These diagnostics
do not assign the same mechanism to the positive-variance failures.

All 169 grid evaluations per dataset are valid, and every grid maximum is
below the final fitted criterion. A coarse grid cannot prove a global maximum,
rule out an unvisited better start, or certify that this family is resolved.

## Decision supported

The prescribed first-fit runs reproduce the stopping/eligibility mismatch in
all four datasets and expose two interacting numerical limits: a biased
detection-SD finite difference and objective increments below summed-criterion
resolution. A unified stopping/eligibility rule and a derivative-consistency
repair are supported proposals for review. Neither is implemented here.
Any gain-based certificate still needs its assumptions and error guarantee
checked; these tiny local predictions alone are not such a certificate.
The rejected qualification candidate remains rejected, and the spatial
diagnostics retain their separate interpretation and review.

Reproduction: invoke `scripts/diagnose_constant_stalls.py` with the four
original dense-task records and a new output directory in the frozen target
runtime. Input hashes are checked before execution and again before each
receipt is written; source identity is checked before task data are opened.
Bulk traces, grids and stencils remain in the ignored artifact directory.
The summary SHA-256 is
`846d2577c19a760cbbcb82c74a3ce27380a6823cd5c303cf3f7fee902b5d57e3`.
