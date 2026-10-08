# Goal 055: nuisance checks, Arc 4 synthesis and capstone design

1 October 2026 (Hobart). **Approved scope; registered before new scoring.**

Barry approved the Arc 4 synthesis and capstone-design tranche, both checks
proposed in Fable's thread53 messages795–797, and Fable holding the capstone's
sealed truth with Astra blinded. He agreed that the background-level check
should guide the capstone's treatment of that quantity. Routine compute/time
remain delegated. This advances Charter Pillar4 and the design of Pillar5;
it does not authorize a capstone launch or a new calibration campaign.

The reporting horizon is the two verified archive checks, a claim-to-evidence
matrix, an Arc4 paper draft with reusable figures, and one concrete capstone
protocol ready for scientific review. Goal054 and all earlier results/failures
remain frozen. No commit, push, publication or legacy-repository access is
authorized.

## Two checks and controls

**Supplied background level.** Use all 1,000 archived Goal054 evaluation blocks
in E0_h1, E0_h3, E06_h1 and E06_h3. Their true map mean background hazard is
.002/day. Refit with that supplied mean fixed at **.0016** and **.0025** per
day, respectively .8 and 1.25 times truth. Both fitted background models receive
the same erroneous supplied value. Retain the full h=1..10 and beta=−2..2
rectangle, each by .05. The map normalization uses the supplied mean and the
unchanged deterministic exposure proxy A. Correct-level results for the same
blocks come from the verified Goal054 statistic table and form paired controls.
Qualification must reconstruct selected correct-level scores before reuse.

**Prey-detection heterogeneity.** Use all 1,000 archived Goal051 blocks for
D20_h1 and D20_h3, fitting with the original supplied p=.65 and mu=.002.
The true detection field is site-specific, fixed over visits, drawn from the
registered Beta distribution with mean .65 and SD .20. Score the same archived
blocks' B_h1 and B_h3 cells as matched baseline controls. These are additional
control fits of existing histories, not new generator conditions. Paired
D20-minus-B contrasts distinguish the departure from a difference between
Goal051's and Goal054's random evaluation panels. Do not condition on which
histories were misleading or flagged in Goal051.

The requested conditions require **10,000** new fits: 8,000 wrong-level fits
and 2,000 D20 fits. The paired Goal051 baselines add **2,000 control fits**.
The four correct-level Goal054 columns are reused. Thus the synthesis has
16 analysis columns, each with 1,000 histories, of which 12 columns require
new scoring. Fable's estimate of roughly6,000 fits undercounted the stated
four-truth, two-level comparison. This corrects costing without dropping any
approved condition or changing replication.

These are retrospectively selected archive checks. Original history generation
predates this registration and D20 was selected because Goal051 found it
harmful. They provide sensitivity evidence for the current decision, not a
new independent confirmation of the original Goal051 nomination.

## Fixed analysis and frozen decisions

Keep the current landscape, source configuration, conductance assumptions,
160 sites, 120/40 training/holdout split, six occasions and two visits, supplied
spread/resistance/detection, K131072 arrival bank and alpha1. The only fitting
change in the first check is the supplied mean background hazard. The second
changes the input archive, leaving the observation model unchanged. Reuse
existing integration APIs with an explicit mean hazard; do not modify previously
bound source or caches. New mean hazards require separately identified
integrations. No oracle fit, unknown-parameter fitting, interpolation, grid or
bank enlargement is included.

Apply the **frozen Goal054 reference table** with exactly its plus-one tails,
conservative 1e-12 tolerance, .05 nominal level and all81 beta nodes. The primary
rule is full-supremum adjusted h=1 rejection; the constant beta0 comparator is
primary for paired benefit/cost interpretation. Retain Berger–Boos gamma=.01
and fixed2.71/3.84 as descriptive secondary diagnostics, without selecting a
new preferred rule. Use training scores only for decisions and fitting;
holdout scores are diagnostic prediction summaries.

The reference table is intentionally **not recalibrated** for wrong mu or
heterogeneous detection. Its exact-model rank guarantee does not transfer to
these departures. This is a test of robustness of a frozen decision procedure,
not a demonstration of valid nuisance estimation or an external-information
interval test. Even good performance at two supplied values would not establish
uniform validity between them or account for a random external estimate.

## Outcomes, uncertainty and predictions

Report all per-condition null declaration and h3 sensitivity rates for the
primary and constant rules, paired wrong-minus-correct-level contrasts within
the Goal054 blocks, and D20-minus-B contrasts within the Goal051 blocks. Retain
secondary-rule rates, h/beta boundary contacts, beta shifts, point bias/MAE in
log h, at-least-1.5-fold point-error rates, and direct adjusted-minus-constant
held-out prediction. Do not call an effect declaration accurate magnitude
recovery. Use the matching estimator for any rule-conditioned summary and
retain its denominator/undefined values.

Use exactly **2,000 paired bootstrap draws**, seed **2026100105**, with three
independent resamples per draw: 999 Goal054 reference blocks, 1,000 Goal054
evaluation blocks, and 1,000 Goal051 blocks. Pair the reference blocks across
all81 nodes, Goal054 indices across its12 analysis columns, and Goal051 indices
across its4 columns. Report frozen-table and calibration-aware95% percentile
intervals. Reference resampling measures sensitivity to the original table;
it does not generate or adopt a new calibration. Do not treat histories from
different archives as paired, resample sites independently or pool unlike
rules as a common endpoint. No additional draws or histories are triggered by
an unresolved interval.

Register Fable's forecasts separately from correctness gates:

- At mu=.0016, E0_h1 constant-rule false declarations will be roughly8–10%.
  E06 already has substantial constant-rule false declarations at correct mu,
  so the numerical range is interpreted for the E0 baseline only.
- Adjusted-rule behaviour under wrong mu is explicitly uncertain. Whether
  fitted beta absorbs some error is a hypothesis, assessed from fitted beta
  and operating rates, not an assumed mechanism.
- D20_h1 adjusted declarations will be at least12%.

Report pointwise forecast outcomes and interval support separately. All valid
outcomes, including failure of these forecasts, complete the checks.

## How the checks guide the capstone design

The decision target is whether a rough supplied level is a defensible next
design candidate, not whether two stress points grant a new validity theorem.
If any wrong-level h1 primary rate has its calibration-aware95% interval wholly
above5%, record clear failure of nominal-level robustness. Recommend the
pre-invasion-monitoring branch for capstone development, with its required
unknown-level fit/qualification made explicit. Do not launch that development
within this tranche.

If all wrong-level h1 primary intervals have upper limits at most5%, recommend
a bounded external-information branch, with the external information and
required nuisance-aware calibration specified before use. Remaining cases are
inconclusive: report them as such and recommend the better-supported design
without treating non-rejection as robustness. For heterogeneous detection,
report two distinct flags: (a) the D20_h1 primary rate has a calibration-aware
95% lower limit above .05; and (b) the paired D20_h1 minus B_h1 primary-rate
contrast has a calibration-aware 95% lower limit above zero. **Either flag**
makes an observation-model or survey repair a capstone prerequisite. This
conservative union avoids passing a procedure with an absolute excess or a
resolved deterioration hidden by a conservative baseline. Report which flag
triggered; a paired increase alone is not an absolute nominal-level failure.
This tranche identifies and costs that prerequisite rather than implementing it.

Any external-estimate branch must specify the measurement model for the
estimate, its precision and bias assumptions, and the required nuisance-aware
calibration before it can be used. Two fixed misspecified inputs cannot
validate that procedure. Fable's `1/E_pre + 1/E_post` calculation is an ideal
complete-data information benchmark, with E denoting expected event counts;
it is neither observed-data field precision nor a qualified survey forecast.

No result here licenses giving the analyst a wrong value and still calling
the decision calibrated, silently supplying a true nuisance, or switching
to a favourable secondary cutoff. Any protocol recommendation must respect
all consequential failures found by both checks, not choose one successful
cell.

## Qualification and execution

Authenticate original Goal051 observation identities and Goal054 observations,
statistics, reference tables and source/input hashes. Select exact cells and
all replicate indices without drawing new histories. Goal051's retained archive
contains frozen seeds, opaque identities and score profiles rather than raw
observation counts. Reconstruct those same histories with its unchanged
generator, authenticate every selected identity, and require full constant-model
training/held-out profile replay for every reused history. This deterministic
reconstruction is archive recovery, not an additional simulation replicate.
Verify the frozen-source byte
identities and every reused integration. New outputs live under a separate
Goal055 root and cannot overwrite earlier evidence.

Meaningful controls are: exact archive-to-analyst conversion; selected
correct-level full-bank score replay across the beta rectangle; beta0 recovery
of the original constant likelihood; h1 consistency; deterministic tie handling
and an independently checked evaluation-only reducer; decision equivalence to
Goal054 at its saved statistics; and bootstrap pairing by archive. Validate
the new mean-hazard calculation against direct site-hazard evaluation.

Use a measured timing panel covering all fitted coefficients and both new mean
hazards before production. Its projection must include integration construction,
all archived scoring, serialization and synthesis. Scientific replication is
fixed; resources and timeout are operational choices delegated to Astra.
Source changes invalidate qualification. Preserve attempts/receipts and do not
duplicate a running or completed phase. Failure leads to diagnosis from saved
evidence, not outcome-driven retuning.

Close with authenticated outputs, inspected figures/tables, one independent
result/claim review and the complete Arc4 synthesis/capstone-design package.
Fable is the approved future truth-holder. The design may define a sealed
generator/analyst handoff, but no sealed truths are drawn or disclosed and no
capstone observations are generated in this tranche.
