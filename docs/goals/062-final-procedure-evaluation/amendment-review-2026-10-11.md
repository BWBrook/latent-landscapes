# Independent review: Goal 062 B100-A amendment

11 October 2026 (Hobart). This review audits the additive
[ten-cell amendment](amendment-2026-10-11.md) and
[amended compute estimate](compute-estimate-amended-2026-10-11.md). It retains
the conclusions and conditions of the original
[design review](design-review-2026-10-11.md). The reviewed amendment files are
bound to these SHA-256 identities:

- amendment: `a2a67f9fbc04ffa80640998ee68130b4d7574b1b3e86178a975b4e3dfb5c1657`;
- amended compute estimate: `b0abc97ebe6222a00a712f3cae434418e7c7b4446b2107abda8b2ae1e9288da7`.

The saved user decision selects amendment followed by review and launch, adds
B100-A `h=1` and `h=3` at both background levels, and does not select exact
`h=2`. I independently reproduced its canonical compact-JSON SHA-256,
`19cbc3060978354d40c4a9f34fef4832555439907b1ec8205cde8bd43f84ad69`.

## Claim audited

The amendment is intended to estimate the final procedure's false-declaration,
sensitivity, abstention, physical-effect error and held-out score behaviour
under one named residual-field misspecification. Each B100-A cell averages over
500 fresh background fields and process/observation histories, conditional on
the fixed map, design, numerical bank, algorithm and one realised exact-family
reference panel. The cost claim is that four added cells increase the planning
allowance from 42–50 to 46–57 elapsed hours while retaining the approved
72-hour ceiling.

For that claim to hold, the implementation must reproduce the capstone B100-A
law exactly, use one independent field stream per history, keep the truth out of
all analysis inputs, and retain the original procedure rather than recalibrate
it for B100-A. Scientific interpretation must treat these as robustness rates
for one misspecification law. Competing explanations include working-model
projection, changed hazard heterogeneity and alignment, numerical difficulty,
and the particular fixed map and reference panel.

## 1. Audit verdict

**Conditionally supported.** I found no fatal or material design error in the
amendment. It adds the four cells authorized by the saved decision, preserves
the six original cells and addresses, and defines an informative prospective
stress test of the final procedure. The design can proceed through the already
approved implementation, qualification and bounded launch sequence without a
further scientific decision, provided the registered qualification and
72-hour resource gates pass.

The amendment does not extend the exact-family null guarantee to B100-A and
cannot establish general robustness, background-family identification or
causal effects of misspecification. Its parameter summaries are deviations of
working-model estimates from named physical generating quantities.

## 2. Strongest supporting evidence

- The amendment fixes exactly four additions: B100-A `h=1,3` crossed with
  `mu=.001,.004`, detection SD `.20` and 500 histories. It explicitly excludes
  exact `h=2`, B100-A `h=5`, additional maps and additional reference panels.
- The generator is fully specified and agrees with the accepted capstone path:
  a correlation-length-10 unit-variance Gaussian field enters
  `z=.7A+sqrt(.51)G`; `exp(sqrt(log(2))z)` is normalized over all 6,048 cells to
  mean `mu`. Individual Gaussian draws are not recentered or rescaled.
- A fresh stage-6 field stream is assigned to every B100-A history and is
  independent of spread, loss and observation streams. The original exact-cell
  indices and 15,000 addresses remain unchanged; the amended ledger has 27,000
  stage addresses in a common explicit scheme.
- Applicability is handled correctly. B100-A has no generating beta and no true
  nuisance-grid node, so beta error and true-node retention are unavailable.
  Physical `h`, whole-map mean `mu` and detection SD remain known generating
  quantities, while their fitted deviations are labelled descriptive under
  misspecification.
- Reusing the exact-family reference panel is the right way to evaluate the
  already frozen procedure. Adding B100-A-specific references would instead
  change the procedure. The amendment clearly states that reuse confers no
  B100-A calibration guarantee.
- All ten cells retain denominator 500, fail-closed abstentions, whole-history
  bootstrap resampling, no outcome-dependent stopping and complete independent
  reconstruction. The amendment also prevents exact/B100-A comparisons from
  being described as paired stochastic contrasts.

## 3. Strongest threats, ranked by scientific consequence

| Rank | Threat | Consequence and disposition |
| ---: | --- | --- |
| 1 | Nominal validity does not transport to B100-A | **Major if overclaimed.** The screening confidence-set and effect-reference arguments assume an exact on-grid nuisance truth. B100-A has neither. Its `h=1` rate is a descriptive false-declaration rate for the fixed procedure and panel; being below .05 would not establish control, and being above .05 would not contradict the exact-family theorem. The amendment states this correctly. |
| 2 | Working-model estimates need not target the physical generating values | **Major for recovery language.** Both fitted background candidates omit the residual field. Bias in fitted `h` or `mu` can reflect the pseudo-true projection and parameter trade-offs as well as finite-data error. Detection SD belongs to the correctly specified observation component but can still trade off against the misspecified process. Report physical-truth deviations, not structural parameter recovery or confidence coverage. |
| 3 | Exact/B100-A contrasts do not isolate misspecification | **Major if interpreted causally.** The families differ in residual structure, realised heterogeneity and their relationship to exposure. Histories are deliberately independent rather than common-random-number pairs. The contrast estimates a difference between two complete generating regimes, not the effect of adding a residual field alone. |
| 4 | Scope remains one stress law on one landscape | **Major for generality.** Fresh fields give replication over the registered Gaussian-field law, but not over correlation lengths, mixing weights, nonlinear fields, maps, sampling designs or reference panels. The two `mu` anchors and `h=1,3` do not map a general robustness surface. |
| 5 | A single shared reference panel remains a common condition | **Moderate.** Cellwise resampling is valid conditional on that panel. It does not propagate reference-generation uncertainty, and common table failures can affect many histories together. |
| 6 | Runtime and numerical behaviour are extrapolated | **Moderate operational threat.** The 46–57-hour range scales an uncertain six-cell allowance. Fresh FFT fields are small, but positive-effect and misspecified fits may optimize differently. The mandatory two-family benchmark and 72-hour pending-work rule are necessary. |
| 7 | Held-out contrasts have a narrow prediction target | **Moderate if generalized.** They condition on the same map and realised process, paired score availability and observed holdout predator data. They do not show new-map or new-field-family transfer and cannot identify the true background family. |

## 4. Independent checks and outcomes

- I checked the saved decision in both Markdown and JSON. Compact sorted-key
  serialization reproduces the stated canonical digest and the selected choices
  exactly.
- I traced the B100-A formula to `capstone_public.generate_b100_history`, its
  hazard helper and the inherited circulant field sampler. The amendment matches
  the source covariance, mixing, lognormal scale, whole-map normalization and
  independent-stream use. The source makes map mean hazard exactly `mu`; it does
  not make the realised spatial CV exactly one.
- I recomputed the amended workload: 10 cells, 5,000 histories, 20,000 main
  fits, 3,825,000 screen-node scores, 20,000 held-out totals and 5,000 generator
  replays. Five diagnostic histories per cell give 22,150 profile points and
  67,500 lattice points. The full reference counts and 1,398 reference replays
  are unchanged.
- The 27,000-stage count is correct: five streams for all 5,000 histories plus
  one field stream for the 2,000 B100-A histories. I did not derive production
  seeds; the registered locked-runtime ledger and uniqueness check remain a
  preproduction gate.
- The cost arithmetic is internally consistent. Scaling 6–10 hours by 5/3
  yields 10–16.67 hours, rounded to 10–17; adding the unchanged 36–40-hour
  reference allowance yields 46–57 hours. Diagnostic scaling gives 8.72 hours
  and main-fit-only ideal scaling gives 1.85 hours. Storing 2,000 full float64
  fields requires 96,768,000 bytes before metadata or compression.
- The original registration, estimate and review retain their reviewed hashes.
  The amendment changes their cell counts, scope, estimate and authority only
  through an explicit additive document.

No simulation, model fit, production-seed preview, benchmark or remote-host
probe was performed for this review. The amended estimate's host observation is
a point-in-time producer check and must be repeated before launch.

## 5. Required checks before relying on the result

No amendment-text correction or additional experiment is required for the
registered B100-A stress claim. The approved execution still depends on these
gates:

1. Implement and independently qualify both generator branches and the ten-cell
   adapter. Freeze the 27,000-stage ledger and extended bootstrap addresses in
   the locked runtime; verify uniqueness, truth isolation, unchanged exact-cell
   addresses, failure propagation, cached-rank equivalence and checkpoint
   resume.
2. Reconstruct every B100-A field and hazard map from its address during audit.
   Verify the field-law identity, independence from the other streams, finite
   hazards and whole-map mean `mu`; preserve either the fields or exact replay
   bindings.
3. Recheck source, runtime, bank and reference custody and live deep-server
   capacity. Benchmark exact and B100-A generation, fits, screens, diagnostics,
   audits and I/O without previewing production streams. A projection above the
   72-hour ceiling returns for a resource decision; it cannot reduce registered
   histories or checks.
4. Complete and audit the unchanged 765-node exact-family panel before drawing
   evaluation histories. Then complete all 500 histories in all ten cells and
   preserve numerical failures, abstentions and pending work at their addresses.
5. In the final report, display every B100-A `h=3` result beside its same-`mu`
   B100-A null rate; retain all ten denominators and missing-score counts; mark
   beta error and true-node retention as not applicable; and label fitted beta,
   `mu`, `h` and SD summaries with their registered working-model or physical
   meanings.

Separate prospective studies would be needed for performance averaged over new
reference panels, multiple maps or other residual-field laws, and for calibrated
effect intervals. Those studies are outside this approved amendment.

## 6. Residual uncertainty

Each new cell retains the original `n=500` precision: approximate 95% half-widths
are 4.4 percentage points near a rate of .5 and 1.9 points near .05; an
independent exact/B100-A difference can have a worst-case half-width of about
6.2 points. Results remain conditional on one reference panel and one map even
though they average over fresh B100-A fields. The design cannot distinguish
residual-field misspecification from its associated heterogeneity and alignment,
nor determine whether another field covariance or landscape would behave
similarly. Exhaustive reconstruction detects realised numerical failures, while
profiles on 50 histories cannot bound rare optimizer pathologies. The amended
runtime range also remains a planning allowance until the qualified adapter is
benchmarked.

