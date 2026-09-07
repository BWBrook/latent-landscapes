# Goal 045 final independent scientific acceptance review

8 September 2026.

## Claim audited

Under the frozen six-case synthetic experiment, replacing the true predator
spread speed with a jointly estimated speed produced no detected systematic
deterioration in prey-effect recovery across the five declared paired metrics.
The accepted evidence is the 65536-draw, 250-calibration plus 250-evaluation
profile bundle per case, and the secondary rho supports are numerically stable
against its nested 131072-draw reference under the recorded criteria.

For that claim to hold, the two analyses must use identical observations; the
calibration and evaluation ensembles must remain independent; fits must exclude
holdout prey data; calibration, support construction and whole-dataset paired
bootstrap resampling must be correct; and the final bank comparison must preserve
the source, histories, grids and review limits. Plausible overturning explanations
were numerical cancellation between analysis lanes, unstable tail calibration,
mis-pairing, holdout leakage, calibration that was treated as portable, and low
power being misreported as equivalence.

## Audit verdict

**SUPPORTED — PASS within the stated synthetic scope.** I found no fatal flaw or
major weakness in the operational claim, and no scientific repair or further
simulation is required before Goal 045 is closed. The result supports the phrase
“no detected systematic deterioration” only as a descriptive summary of the 30
separate paired contrasts. It does not support equivalence, absence of any cost,
general prey-effect recoverability, continuous-grid inference, or a field claim.

## Strongest supporting evidence

- An independent replay from the saved profile arrays reproduced every published
  point contrast and every endpoint of the 1000-resample percentile intervals
  exactly. All 30 intervals include zero at both 65536 and 131072 draws. An
  audit-only extension to 10000 resamples also left all 30 intervals including
  zero.
- Point changes are small and mixed: effect-error change ranges from -0.001999 to
  +0.000270 log units, log-width change from -0.02256 to +0.01585, coverage change
  from -1.2 to 0 percentage points, exclusion change from -2.0 to +1.6 points,
  and conditional prey-score change from -0.0000014 to +0.000235 nats per holdout
  site. The most adverse separate 95% bounds still allow modest penalties:
  +0.00314 error, +0.05376 log width, 3.2 percentage points of coverage or
  non-null exclusion, 2.4 points of added null false exclusion, and 0.000223
  nats/site of prey-score loss.
- The full-ensemble rho comparison independently passes every recorded limit.
  The largest cutoff movement is 0.12431 LR against 0.5; evaluation endpoints
  move by at most one G201 cell; component counts, boundary classifications and
  coverage counts do not change; and the largest mean log-width movement is
  0.000277 versus a 0.013863 grid cell.
- Recalculation of the four retained histories gives maximum changes of 0 for
  effect and rho MLEs, 0.005693 for the known-speed effect profile, 0.011683 for
  the profiled effect, 0.101771 for the rho profile, and 0.062585 for a truth LR.
  All 72 rho topology checks pass.
- The absolute result is reported honestly. Both lanes are weak in the two
  threefold cases and the slow fivefold case. The usual fivefold case has 229/250
  effect-coverage successes in both lanes (91.6%), despite informative error,
  width and exclusion. This prevents the paired null result from being mistaken
  for uniformly successful recovery.

## Independent checks performed

I inspected the active design, likelihood, campaign and synthesis paths. Candidate
arrival is shared between species before site-wise marginalisation; parameter
fits use the 120 training sites; holdout predator observations are used only as
permitted conditioning information and holdout prey observations only for score;
and truth-assisted event counts do not enter fitting or calibration. The 239th
order statistic is applied separately to each truth and analysis lane, and each
bootstrap draw resamples complete calibration and evaluation histories separately
while preserving pairing across lanes and cases.

Both profile files match their recorded SHA-256 digests and frozen source
`e8c08f10f7b67118a85ee37770d8ee48ee2c213a`. Calibration and evaluation seed
records are identical between references, the 65536 integration-seed list is the
exact prefix of the 131072 list, and event-diagnostic arrays are byte-identical.
The compact comparison JSON files and all seven published synthesis artefacts are
byte-identical to their retained audit/synthesis copies. The current scientific
source change is confined to the accepted bank-size default; the original
`timing`/nonproduction receipts remain unaltered and are explained by the explicit
amendment. Raw bank arrays were deliberately not copied locally, so exact array
prefix identity was checked through the retained generation receipts, checksums
and run logs rather than a new local byte comparison.

## Strongest threats, ranked by scientific consequence

1. **Scope extrapolation:** calibration knows the generating condition and is
   lane-specific; detection, background hazard, resistance, landscape and survey
   design are fixed and known. The site-marginal composite likelihood is calibrated
   only under this generating system. General or field-ready inference would not
   be supported.
2. **Absence-of-evidence inflation:** zero lies in separate intervals without a
   prespecified equivalence margin or omnibus test. The adverse bounds above remain
   scientifically possible, and the usual-fivefold exclusion comparison is at a
   ceiling. “Systematic” must remain descriptive.
3. **Residual numerical uncertainty:** the final comparison uses correlated nested
   banks, not independent integration replicates. Earlier 16k/32k and 32k/64k
   cutoff failures show genuine tail sensitivity. The final pass establishes the
   bounded contract at G201, not exact Monte Carlo or continuous-profile convergence.
4. **Weak absolute recovery:** the paired comparison can be stable when both lanes
   are poor. The synthesis exposes this rather than attributing shared weakness to
   speed estimation.

## Required corrections and residual uncertainty

No correction to the analysis, source, tables or figures is required. Closeout
should replace the provisional “final review pending” wording with this verdict,
link this review, and retain the narrow claim, adverse bounds, weak-case results,
discrete-grid qualification and failed earlier bank comparisons.

Residual uncertainty comes from 250 calibration and 250 evaluation histories per
case, percentile-bootstrap Monte Carlo error, conditioning on one accepted
integration bank, discrete support endpoints, one fixed synthetic landscape, and
the assumed generating model. Those limits remain after closeout; resolving them
would require a separately designed generality or numerical-method study, not more
work under Goal 045.
