# Independent design review: Goal 062 final-procedure evaluation

11 October 2026 (Hobart). This review audits the prospective
[registration](registration-2026-10-11.md) and
[compute estimate](compute-estimate.md), not results from an executed campaign.
The reviewed files are bound to these SHA-256 identities:

- registration: `b974c9bbeb15b7644b3c366f9787ad12a2d7e4bedd9e7625aafb58fc7a7a79f9`;
- compute estimate: `f60a0745b3f8f85e85891be2904493994782b1d8ccfd8d681ad897a26e90378d`.

## Claim audited

If implemented exactly as registered, the campaign is intended to estimate the
declaration, abstention, thresholded effect-recovery and held-out score
distributions of the frozen procedure at six known truths. Those estimands are
over fresh complete histories, conditional on one fixed map and design, one
numerical bank, the frozen algorithm and one realised full reference panel. The
associated compute claim is that 42–50 elapsed hours on deep-server at up to
51 workers is a defensible planning allowance, with a 72-hour checkpointing
ceiling rather than a guaranteed completion time.

For that claim to hold, the new adapter must preserve the registered generator,
fit, screening, rank, scoring and failure semantics; all 3,000 histories must
remain independent at the complete-history level; the full reference panel and
fixed inputs must pass custody and compatibility checks; and resource stops
must leave work pending rather than remove difficult histories. The main
alternative explanations are numerical or adapter failure, dependence or
selection introduced during execution, an atypical fixed reference panel, and
over-interpretation of a deliberately narrow exact-family, fixed-landscape
experiment.

## 1. Audit verdict

**Conditionally supported.** I found no fatal inferential flaw in the registered
design. It is a strong prospective evaluation of the procedure's *conditional
operating characteristics* at the six named truths, and 500 whole histories per
cell provide useful Monte Carlo precision for those cellwise quantities. The
cost estimate is adequate for a launch decision as an engineering allowance,
provided the required wrapper benchmark and live resource checks occur first.

This design does not support claims of landscape generality, robustness to
model misspecification or off-grid nuisance values, performance averaged over
reference-panel generation, calibrated confidence intervals for `h`, or fully
observed-nuisance inference. It also does not itself authorize implementation
or launch.

## 2. Strongest supporting evidence

- The six cells, 500-history denominators, complete-history experimental unit,
  seed addresses, model fits, declaration rule, failure propagation, endpoints
  and stopping rule are fixed before any Goal 062 draw. Negative and invalid
  outcomes cannot be replaced, hidden or used to change the sample size.
- The study separates false declaration at `h=1`, sensitivity at `h=3` and
  `h=5`, abstention and magnitude recovery. The recovery categories partition
  all 500 histories, so failed estimates cannot silently disappear from a
  complete-case denominator.
- The registered nuisance truths are on the canonical grid and the data come
  from the exact adjusted family. This gives a clean test of the final
  observed-nuisance procedure at the chosen anchors. The registration correctly
  retains supplied `rho`, `eta` and mean detection and therefore avoids claiming
  a more general nuisance problem than it runs.
- The full 765-node reference panel is now the binding path. All reference work
  precedes evaluation, and switching to selective materialisation requires a
  revised prospective registration and independent review. This removes an
  outcome-dependent cost or panel-selection route.
- Inference respects the dependence structure: Wilson intervals use all 500
  histories; bootstrap resampling acts on whole histories and preserves model
  pairing and missingness; independent cells are resampled independently; and
  the shared reference panel is held fixed rather than falsely treated as 500
  independent calibration panels.
- The numerical plan is unusually auditable: all 12,000 main fits and scores
  are reconstructed, all 3,000 generators are replayed, predefined diagnostic
  histories are profiled, and every new reference table receives exhaustive
  row checks plus address-based generator replays.

## 3. Strongest threats, ranked by scientific consequence

| Rank | Threat | Consequence and disposition |
| ---: | --- | --- |
| 1 | Scope inflation beyond the registered population | **Major if claims expand.** One map, one design and bank, two `mu` anchors, fixed `beta=.5` and detection SD `.2`, exact model family and supplied `rho`, `eta` and mean detection cannot establish general recovery or robustness. The registration states these limits; the final paper must retain them. |
| 2 | Conditioning on one shared reference realisation | **Major if treated as marginal calibration.** Both null and non-null results condition on one panel, and table failures are common causes. Null rates can reveal an elevated conditional false-declaration rate for this panel, but cannot validate or refute the theorem that averages over reference generation. Independent-panel variability is not measured. |
| 3 | The production adapter and audit path do not yet exist | **Major operational threat.** The current four-case adapters cannot establish that the 3,000-history runner preserves masks, truth isolation, scalar ranks, cache semantics, failures or checkpoint recovery. The preregistration is scientifically sound only conditional on successful implementation qualification. |
| 4 | Evaluation runtime is weakly measured | **Moderate operational threat.** The reference estimate is receipt-based, but the 6–10-hour evaluation allowance has no persisted 3,000-history benchmark and positive-effect geometry may change optimization cost. The 72-hour ceiling controls resource exposure; it is not evidence that execution will finish within 50 hours. |
| 5 | Predictive contrasts have a narrower target than “predictive performance” may suggest | **Moderate if generalised.** Contrasts condition on paired valid scores, the same realised map and process history, and observed holdout predator data. They do not estimate new-landscape transfer. Every contrast must retain its unavailable-pair count. |
| 6 | Magnitude claims could exceed the endpoint | **Major only if over-interpreted.** The study estimates bias/error summaries and a prespecified within-1.5-fold recovery probability. It defines no confidence-set procedure or coverage target; profiles are diagnostics. Boundary mass at `h=1` also limits ordinary bias interpretation. |

Completing unused reference nodes is expensive but is not an inferential flaw.
It buys a simple immutable panel and a definite workload; it does not add
replication or robustness evidence.

An initial minor ambiguity over secondary empirical quantiles was resolved
during review: the registration now fixes the .05, .25, .50, .75 and .95
quantiles of absolute log error among valid free-`h` estimates.

## 4. Independent checks and outcomes

- I traced the exact generator, fit candidates, validity checks, screening,
  inclusive plus-one ranks, Berger--Boos construction, holdout scoring and
  failure propagation against the frozen source and accepted receipts. The
  prose matches those scientific paths.
- I verified that nuisance nodes 457 and 482 encode the registered anchors and,
  in a non-production recreation, that all 15,000 derived evaluation-stage
  seeds are unique. The definitive ledger still requires freezing under the
  locked runtime. The new root and address domain are separated from the frozen
  public, bank and reference domains.
- I recomputed the principal counts: 3,000 histories, 12,000 main fits,
  2,295,000 observed screen-node scores, 465,534 new effect references, 764,235
  full-panel effect rows, 13,290 profile points, 40,500 lattice points and 1,398
  scheduled new-reference generator replays. They are internally consistent.
- I recomputed the stated Monte Carlo precision. At `n=500`, the approximate
  95% half-widths are 4.38 percentage points at probability .5, 3.51 at .8 and
  1.91 at .05; the worst-case independent-cell difference is about 6.20 points.
  The two-sided Wilson upper endpoint after zero events is 0.762%, as stated.
- I independently reproduced the reference-time extrapolation (22.96 hours
  before margin; 34.44 hours after the stated 1.5 factor), the 33.05-hour stress
  scenario, the 9.424 GB incremental storage estimate and the 15.471 GB total.
  These support planning, not a worst-case time bound.
- The cited Goal 061 source manifest has 258 source/script/test entries, all
  present and matching at review time. The named map, exposure, arrival,
  address, nuisance-grid and runtime hashes match their current files. The 299
  existing effect-table receipts report 999 complete rows and no invalid row;
  the actual multi-gigabyte database payloads were not rehashed in this review,
  so the registered prelaunch custody check remains necessary.
- The bootstrap repair now fixes the original-sample point estimate, 2,000
  whole-history draws, two-sided 95% percentile endpoints, NumPy linear/Type-7
  quantiles and fail-closed handling of undefined draws. This closes the only
  material uncertainty-construction ambiguity found in the first pass.
- The final revision fixes the five secondary empirical error quantiles. No
  outcome-summary convention identified in this review remains unresolved.

No new simulation, model fit, production benchmark, remote-host probe or launch
was performed for this review.

## 5. Required corrections and checks before relying on the result

No document-level correction remains. The following are execution prerequisites
after approval:

1. Build and independently qualify the narrow six-cell adapter. Qualification
   must cover seed-ledger uniqueness, truth isolation, counts and masks,
   scalar-versus-batched rank equivalence including ties and invalid tables,
   score reconstruction, failure categories and exact-address checkpoint
   resume.
2. Verify the full payload custody chain, original reference audits, source and
   runtime bindings, live deep-server capacity and scratch space. Benchmark the
   actual adapter on mechanical or existing public fixtures. If it exceeds the
   registered resource envelope, return for a resource decision before drawing
   Goal 062 histories.
3. Complete and independently audit all 466 missing reference tables before
   evaluation. Do not substitute selective materialisation under this
   registration.
4. Execute all 500 histories in every cell and preserve pending, abstention and
   numerical-failure states. Release scientific results only after independent
   reconstruction and audit, with the conditioning population and all six cell
   outcomes kept visible.

No extra experiment is needed for the narrow registered estimand. Broader
claims require separate prospective work: multiple landscapes for landscape
generality, independently regenerated reference panels for panel-marginal
operating rates, misspecified/off-grid generators for robustness, or a defined
interval procedure with replicated truth coverage for interval calibration.

## 6. Residual uncertainty

Even after those checks, sampling uncertainty remains several percentage points
per cell and about six points for a worst-case independent-cell contrast. The
results will remain conditional on one landscape, design, bank and reference
panel. The study will not quantify variation across those objects, and its two
background anchors cannot map a continuous nuisance surface. Exhaustive replay
can detect realised numerical failures, while the 30-history profile/lattice
subset cannot bound rare optimizer failure rates. Finally, a completed campaign
can establish operating performance only under its exact synthetic generator;
it cannot show that the ecological process model is adequate for a real
landscape.

