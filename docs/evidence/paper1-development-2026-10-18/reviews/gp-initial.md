# Independent numerical audit of the initial sampled-site GP prototype

**Audit date:** 2026-10-18  
**Scope:** read-only audit of the frozen initial prototype under
`gp-prototype/initial/`; bounded numerical spot checks only. This is development
evidence from two archived histories, not a Goal 062 rerun, a calibration, or a
production qualification.

## Frozen evidence identity

| File | SHA-256 |
|---|---|
| `gp-prototype/initial/run_gp_prototype.py` | `8fc0fb391b0d32d6ed67871a7680051a35ca2c1da8fdfc099da4344d1f318d61` |
| `gp-prototype/initial/results.json` | `382d320a7cbfe2c741a2786c3b69a4e02bffeb970aa6671e907bc6a7d86ce3d2` |
| `gp-prototype/initial/b_h3-results.json` | `56cbc692dc91d0eed6661d771718ebb2d4e0bd84cf75b4d44d764b19f9ccbcc6` |
| `gp-prototype/initial/h3-results.json` | `9fd7a3f1134532659f8ff91833e65e1a9eaa3629fb88b029feb55ec256d75de1` |
| `gp-prototype/initial/manifest.json` | `e4dcb8909295d021823952c7ce5ba6299c948db013acb591859bf60bee801085` |

The manifest's recorded script hash agrees with the frozen script hash.

## Scientific and numerical target

The prototype compares a neutral `h=1` fit with a free `1 <= h <= 30` fit for
one archived `B_H3` history and one archived `H3` history, using the 120 training
sites. At sampled site `i`, it models

`log(lambda_i) = alpha + beta A_i + u_i`,

with `u ~ N(0, sigma^2 K)` and fixed exponential correlation range 10 cells.
It profiles `alpha`, `beta`, `sigma`, prey-detection SD and, for the alternative,
`h`. The target is a working composite criterion: each site's predator-arrival
bank contribution is integrated marginally, while the Gaussian field couples
the site hazards. It is not the exact unconditional normalised generating law.
The two histories therefore assess numerical feasibility at two development
points only; they do not estimate repeated-sampling error, calibration, power,
coverage, or generality.

The actual calculation is otherwise coherent in form. Site log-likelihood
curves are recomputed for each outer `(h, detection_sd)` point (lines 141-181).
The inner log posterior is the sum of site curves minus
`u' C^-1 u / 2` (lines 240-255). Its negative Hessian is correctly formed as
`H = C^-1 - diag(ell_i''(eta_i))` (lines 257-260). The Laplace criterion used
for fitting correctly subtracts both `log|C|/2` and `log|H|/2` (lines 280-297).
The sampled correlation matrix is not numerically problematic in these data:
its smallest eigenvalue is 0.11515 and its 2-norm condition number is 100.10.

## Decisive defects in the initial prototype

1. **The importance diagnostic has the Hessian determinant sign wrong.**
   Dividing the Gaussian target by the proposal requires
   `-0.5 * logdet_H` in the log weight, and the Laplace approximation also
   requires `-0.5 * logdet_H`. Lines 420 and 422 instead add it. The two
   reported absolute log criteria are consequently wrong. Because the same
   constant error is added to both, `importance - Laplace`, normalised weights,
   and ESS are algebraically unchanged at that fixed parameter point.

2. **An outer optimiser success flag is demonstrably false.** The second
   free-`h` start is returned unchanged after one iteration for both histories.
   At the `B_H3` start its central finite-difference gradient was
   `[-11.89, -20.90, -2.11, -14.02, -733.38]`; the SciPy line search emitted
   an invalid-subtraction warning after trial evaluations returned infinity,
   yet reported relative-function convergence. Lines 337-360 store that result,
   and lines 361-362 accept every finite final point regardless of outer
   `success`. Rounding `(h, detection_sd)` to eight decimal places in the cache
   (lines 141-144) also needlessly interacts with default finite differences.

3. **The selected optima are too loose for a profile-likelihood claim.** At
   the four stored best points, central finite differences with step `1e-4`
   gave outer gradient infinity norms of 0.053 (`B_H3`, h=1), 0.0073 (`B_H3`,
   free h), 0.132 (`H3`, h=1), and 0.275 (`H3`, free h). The stored inner mode
   score norms are `3.1e-4` to `1.5e-3`. L-BFGS-B commonly stopped on relative
   function reduction rather than a tight score. The reported values are
   plausible approximate fits, not qualified maxima.

4. **The spatial-variance boundary is excluded.** Positive-sigma fits are
   bounded below at `sigma=1e-4` (lines 331-336), although the code contains an
   analytic `sigma=0` limit (lines 220-230). No exact lower-dimensional boundary
   fit is compared, so selection over the stated parameter space is incomplete.

5. **Interpolation checks do not establish profile-wide accuracy.** Lines
   183-211 evaluate only six global grid midpoints and report the maximum
   *single-site* log-likelihood error. They do not check summed criterion error,
   derivatives, Hessian/log-determinant error, fitted modes, or profile
   endpoints. The reported 0.0099-0.0157 maxima occur at the last midpoint near
   `log(lambda)=-3.075`, outside all fitted mode ranges (maximum fitted eta is
   -4.25 to -4.83). At `h=30`, the analogous tail errors rise to 0.081-0.091.

6. **Input order is assumed rather than asserted.** `load_data` combines the
   public split and exposure arrays with observation IDs and the arrival bank
   by position (lines 303-326). The live archived inputs are aligned, as
   confirmed by explicit identifier/exposure checks during this audit, so the
   reported run is not corrupted. The initial source would silently misassign
   sites if a future input order changed.

## Bounded verification results

At each stored best parameter point, I recomputed the latent mode, evaluated a
single direct site-specific-hazard integration at that mode, and compared it
with the 61-node cubic interpolation:

| Case and fit | max site abs error | summed signed error | summed abs error |
|---|---:|---:|---:|
| `B_H3`, h=1 | 1.42e-6 | 3.80e-5 | 3.80e-5 |
| `B_H3`, free h | 1.76e-6 | 3.98e-5 | 3.98e-5 |
| `H3`, h=1 | 1.44e-6 | 3.55e-5 | 3.55e-5 |
| `H3`, free h | 1.43e-6 | 3.68e-5 | 3.68e-5 |

Recomputing the full Laplace criterion at the stored parameters with 61, 121,
and 241 grid nodes changed it by at most 0.000361 from 61 to 121 nodes and
0.000083 from 121 to 241 nodes. Thus the published 0.01-0.016 values are valid
sparse tail site-error diagnostics, while local fitted-point interpolation
error is negligible relative to the observed profile differences. This does
not qualify profile tails or interval endpoints.

The importance refinement used 16,384 draws and reported ESS 14,203 (`B_H3`)
and 14,303 (`H3`). The determinant-sign error does not affect these ESS values
or the differences. The resulting `importance - Laplace` discrepancies of
-0.03691 and -0.04013 have rough log-mean Monte Carlo standard errors of about
0.0031 and 0.0030, estimated from `sqrt((N/ESS - 1)/N)`. They support a local
Laplace discrepancy of roughly -0.04 at the single fixed point
`alpha=-5.5, beta=0.5, sigma=0.4, h=3, detection_sd=0.2`. They do not establish
accuracy at either optimum, along a profile, near `sigma=0`, or under weak
information.

The stored raw profile statistics are

- `B_H3`: `2 * (-1716.44718 + 1724.60242) = 16.3105`;
- `H3`: `2 * (-1737.32761 + 1739.74399) = 4.83275`.

These are descriptive diagnostics only. Statistical significance is not
defensible: the criterion is composite, the raw statistic is uncalibrated,
`h=1` is a boundary null, nuisance estimation includes a variance boundary,
and the maxima are numerically loose. In particular, the `H3` value is close
enough to conventional reference cutoffs that optimisation or adjustment can
matter. No existing spatial cutoff or protection claim transfers to it.

The reported pair times, 39.82 seconds (`B_H3`) and 28.82 seconds (`H3`), are
real elapsed times on the recorded Mac runtime for data loading, both
`fit_case` calls, and the `h=30` curve stress (lines 448-460). Each `fit_case`
invoked two starts. The importance sampler runs after the pair timer (lines
461-463). These numbers demonstrate prototype throughput, but they time weak
optimiser invocations, including one false-converged start per free fit; they
are not timings for two reliably converged fit pairs.

## Smallest defensible next step

Repair the diagnostic in place while preserving this frozen initial evidence:

1. correct both importance-determinant signs;
2. remove cache aliasing, use controlled finite-difference steps, and require
   outer success plus an explicit projected-gradient/KKT check;
3. tighten and independently score-check the latent mode;
4. fit the exact `sigma=0` lower-dimensional boundary candidate;
5. rerun the two archived fit pairs with at least two genuinely moving starts;
6. compare the resulting profile statistics at 61/121-node resolution and add
   direct/importance checks at the selected optima and one relevant profile
   tail or endpoint.

This is sufficient to decide whether the working implementation is numerically
credible for a later qualification design. It is not sufficient to reopen Goal
062, calibrate a declaration threshold, or make a scientific performance claim.
Independent scientific review would materially affect any decision about the
future calibration design or inferential cutoff, but it is not needed to
recognise and repair the numerical defects above.
