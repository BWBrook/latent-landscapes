# Paper 1: first numerical development and corrected mechanism checks

18 October 2026. This record advances charter pillars 3 and 4 and the
[integrated protocol](paper1-integrated-tranche-protocol-2026-10-18.md).
It responds to Claude's Correspondence messages 2009–2010 and is reported in
Codex's replies 2012 and 2028. These are post hoc development analyses using archived
histories, not a new validation experiment or a reopening of Goal 062.

## What the frailty check establishes

The repaired check uses the full cohort from day -60 through day 60, the
120 training sites, and the stored 24 five-site sampling clusters. It fits
the exposure-linked baseline with a common estimated scale, independent
Gamma frailty, and shared cluster Gamma frailty. The exposure coefficient
is supplied, not estimated. True arrival and loss times are supplied: these
are complete-data mechanism diagnostics, not deployable survey models.

There are 500 histories in each of eight archived cells: exact and B100-A
backgrounds, low and high baseline hazards, and h=1/3. Each frailty fit uses
four starts and includes the exact homogeneous limit as a candidate. All
optimizer attempts, boundary contacts and selected estimates are retained.
The diagnostic retains the original h domain [1,10]; the proposed new
experiment uses [1,30]. A selected numerical solution is not a proof of a
unique global maximum.
The earlier oracle-rate-ratio audit retained unbounded ratios, so its
low-hazard cell means need not equal these bounded-estimate means.

For the four h=3 cells, each entry below is mean signed log error / mean
absolute log error. H and L denote baseline hazards .004 and .001/day;
B denotes the heterogeneous B100-A generator.

| Cell | Exposure baseline | Independent Gamma | Cluster Gamma |
| --- | ---: | ---: | ---: |
| H3 | -0.0003 / 0.1943 | +0.1293 / 0.2568 | +0.0197 / 0.1957 |
| B_H3 | -0.1419 / 0.2522 | +0.0922 / 0.3079 | -0.0332 / 0.2341 |
| L3 | -0.0203 / 0.3517 | +0.1877 / 0.4280 | -0.0024 / 0.3533 |
| B_L3 | -0.0135 / 0.3743 | +0.2085 / 0.4587 | +0.0344 / 0.3746 |

The cluster model reduces attenuation in B_H3: its paired change in log h
is +0.10874 (MCSE 0.00452). Mean absolute log error falls by 0.01812
(paired MCSE 0.00559) in that cell.
It does not consistently improve absolute error across the four cells.
Independent Gamma frailty shifts effects upwards and increases absolute
error in all four. This is effect inflation in this diagnostic; calling it
signal absorption would misdescribe the observed direction.

At h=1, raw likelihood-ratio exceedance frequencies above 2.71 range from
2.0–4.8% for the exposure baseline, 7.0–8.2% for independent Gamma, and
3.0–5.2% for cluster Gamma. These are observed frequencies of an uncalibrated
statistic on one fixed design. They do not establish error control or make
the cluster model a performance floor for the sampled-site GP.

The parent independently reconstructed all cell means and threshold frequencies
from the 4,000-row CSV, with zero discrepancies, and checked the integrated
Gamma term against direct positive-axis quadrature at nine parameter/event
combinations (maximum absolute difference 7.1e-12). Interior selected-fit raw
gradient maxima were 0.000171 for independent Gamma and 0.000057 for cluster
Gamma. Large raw gradients at boundaries are not KKT failures by themselves.
The final replay retained 80,000 candidate/optimizer receipts. Four of
64,000 optimizer starts failed, with successful alternatives available in each
case; all 4,000 histories remained. Unclipped LR values are retained. The
minimum was -4.1e-8, consistent with numerical roundoff; no case crossed the
explicit -1e-7 failure threshold.

Claude's post-only calculation selected sites known from hidden loss times
to have survived to day 0. Proposed arm B instead retains the entire original
cohort and masks its early observations. Even a deliberate survivor-conditioned
analysis needs to update its frailty distribution: for individual Gamma(k,k)
frailty after cumulative pre-period hazard H0, the survivor law is
Gamma(k,k+H0), generally varying by site. A free intercept does not restore
the original mixing law. Cluster selection needs its joint conditioning too.
The survivor-only pilot therefore cannot establish the proposed baseline
trap. Nor can multiplying its error by sqrt(120/260) forecast arm C: events,
spatial dependence and predator missingness change with the design.

## Spatial prototype and numerical review

The first observed-data prototype fits the sampled-site GP criterion on the
120 training sites of archived H3 and B_H3 history 000. It supplies the
range-10 covariance and uses the existing site-marginal arrival likelihood.
Both histories use the full pre/post calendar, corresponding to monitoring
arm A; the B in B_H3 identifies the heterogeneous generator.
No evaluator truth enters these fits. This is a spatial composite working
criterion, not the exact map-normalised generating likelihood.

The initial version completed constrained and free-h fits but failed a
numerical audit. Its importance-sampling check used the wrong sign for a
Gaussian determinant in both compared values, so their difference cancelled
the same error while their absolute values were wrong. Rounded curve-cache
keys could also alias the finite-difference steps used by the outer optimizer;
one start reported success without moving despite a substantially worse
objective. The analytic variance-zero case existed but was not included in
fit selection. These are implementation defects, not scientific findings.
The initial source and receipts are retained separately; revised estimates
and timing must be identified by their repaired source hash.

Independent review narrowed the interpolation concern. The initial 0.010–0.016
maximum errors are sitewise errors near the grid edge, outside the fitted
latent modes. Direct likelihood checks at those modes differed by at most
1.8e-6 per site, and doubling then quadrupling the grid changed the full
Laplace criterion by at most 3.7e-4 and 8.3e-5. Outer optimization was the
larger problem: independent score checks at the stored fits gave maximum
absolute gradients between 0.007 and 0.275. The original 28.8–39.8-second
timings include loading and stress checks and measure optimizer invocations,
not reliably converged fit pairs. The initial importance discrepancy of about
-0.04 (Monte Carlo SE about 0.003) remains a valid difference because the
shared determinant error cancels, but it was evaluated at a nominal parameter
point rather than either fitted endpoint.

The repaired comparison now requires a finite criterion, a converged latent
mode, a positive-definite Hessian and an independently evaluated projected
outer gradient no larger than .001. It searches the positive-variance and
exact variance-zero families separately and retains known better candidates.
A final targeted polish resolved one variance-zero fit that had stopped on
function tolerance too early. The three previously completed fits retain their
original source identity; they are not relabelled as generated by that replay.

All four endpoints passed. These are single archived histories, not cell-level
recovery estimates:

| History | Free h estimate | Free residual SD | Null residual SD | Laplace LR | Pure optimization time |
| --- | ---: | ---: | ---: | ---: | ---: |
| B_H3, 000 | 4.1916 | .6022 | .2672 | 16.3107 | 439.95 s |
| H3, 000 | 2.3463 | .3512 | 0 | 4.7760 | 313.24 s |

Times are local Mac mini measurements with multiple starts and fallback
searches. B_H3 includes 434.66 seconds of search plus a 5.29-second targeted
repair. Loading, importance integration and roughly 20 seconds per case of
h=30 domain stress are separate. These costs supersede the initial short
timings for these examples; they are not warm-start bootstrap or full-profile
benchmarks on the intended compute host.

The parent reevaluated every selected endpoint with the final criterion and
used a different finite-difference step for the outer score. The largest
projected gradient was .000537. Direct site likelihoods at the fitted latent
modes agreed within 5.92e-8 per site (1.14e-6 in the sum of site log likelihoods).
Increasing the log-hazard grid from 161 to 321 points changed the Laplace
criterion by at most 7.75e-5. Both LR calculations were independently
reconstructed exactly. The selected H3 null is the exact zero-variance case,
showing why that boundary must participate in fitting.

Importance integration still detects a Laplace approximation difference.
For B_H3, log-integral minus Laplace is -.03344 (MCSE .00746) at the free
endpoint and -.01847 (MCSE .00215) at the null. Applying these fixed-point
corrections changes its LR from 16.3107 to 16.2807. For H3 the free-endpoint
difference is -.03145 (MCSE .00188); the selected zero-variance null needs no
latent integration. These checks use 16,384 draws at each positive-variance
free endpoint and 4,096 at the B_H3 null. They are not importance-reoptimized
profile statistics, and separate endpoint MCSEs do not determine their paired
difference MCSE. Larger interpolation errors near the grid edge also remain
outside the fitted modes; they must be addressed for weak or extreme cases.

This resolves the identified optimizer defects for these two histories.
Qualification still concerns the whole profile and its numerical tolerance,
including weak information, extreme h, variance boundaries and reference
replicates. It also needs a more efficient fitting path: minutes per pair
make direct extrapolation of the prototype unsuitable for planning the
multi-million-fit campaign. The scientific design remains intact while that
implementation is developed. Independent numerical review and the parent
checks are recorded with the executable diagnostic receipts.

## Bootstrap computation

The fixed 999-replicate rank decision can stop once it is inevitable. With
S exceedances after t draws, its final plus-one p-value lies between
(1+S)/1000 and (1+S+999-t)/1000. For rejection at p<=.05, stop for
non-rejection at 50 exceedances or for rejection at 950 non-exceedances.
The stored result is a decision and bounds, not an invented completed
p-value. Failed fits must remain unresolved until repaired.

An exhaustive check of 49,146 small-cap sequences reproduced the corresponding
complete decisions and bounds. Exact conditional calculations for cap 999
give expected work of 100 draws when the exceedance probability is .5,
500 at .1, and 942.2 at .05. Strong rejections still need roughly 950–999
draws. This saves work unevenly; it does not make a fitted-nuisance bootstrap
an exact statistical test. The independent review also distinguishes this
fixed-cap calculation from a different sequential p-value procedure.

Bootstrap coverage needs only the inverse-test inclusion event at the truth.
At h=3 this requires a separate constrained bootstrap from the declaration
test at h=1. Endpoint inversion is unnecessary for this audit; interval widths
remain an endpoint for the deployable profile rule. These changes remove
unnecessary work without changing the intended coverage comparison.

## Paper argument and next numerical decision

An invader arrives in a landscape where sites already differ in their risk
of loss. Early losses change the population still at risk. Our synthetic
laboratory lets us ask when surveys can recover the invader's added effect,
which background models help, and whether uncertainty remains trustworthy
across landscapes. The central comparison is between observing a baseline
and spending the same prey-survey effort on additional sites, with the
predator network held fixed. The existing recovery ladder and blind capstone
show how the inferential problem develops; the new experiment will test
whether those lessons travel.

This remains a testable argument. Baseline monitoring may help, fail to help,
or depend strongly on the fitted background model. The h=3 complete-data
check supports structured heterogeneity as a useful mechanism to investigate;
it does not settle the design comparison. The headline figure must show the
paired A–C contrast across independent maps, uncertainty, and failure rates.
The model figure must distinguish effect inflation, attenuation and loss of
precision, with calibration and held-out prediction as separate outcomes.

With the two-history optimizer repair complete, the next coherent numerical
tranche is efficient whole-profile fitting and qualification across weak
information, variance zero, h through 30,
120/260-site designs, and difficult corridor arrival banks. It must measure
whole profiles, memory and reference-replicate costs on the intended compute
host. The first two fit pairs cannot price the full experiment. Map generation,
directional amplitude, temporal stress, cutoff grids and tolerances must then
be frozen before rule training and untouched validation. No production campaign
is launched by this record.

## Reproducible record

The [compact evidence archive](evidence/paper1-development-2026-10-18/README.md)
contains the executable diagnostic snapshots, numerical reviews, summaries
and input/source hashes. Its manifest also identifies the larger local
per-history and optimizer files. Goal 062 source and closure receipts remain
unchanged. Only this new development evidence is being interpreted here.
