# Proposed adjusted-background identifiability pilot

**Approval update, 24 September:** Barry approved this scientific route and
delegated compute resources and timing. The controlling execution design is
[Goal 052's registration](../052-adjusted-background-pilot/registration-2026-09-24.md).
The text below preserves the proposal as it stood before approval; its
four-hour resource limit is superseded as a human approval boundary.

24 September 2026. **Proposed; no implementation, replay or fit authorized.**
This recommendation supersedes Astra's recommendation to run the separate
[two-cell confirmation](confirmation-proposal.md), whose original record stays
unchanged. It requests an explicit amendment to the approved confirmation-first
route. The Goal 051 nomination remains unconfirmed.

## Scientific question and scope

Can the existing survey distinguish the physical post-arrival multiplier h
from a spatial background hazard associated with the known invasion geometry?
The deliverable is a bounded assessment of likelihood geometry and computational
feasibility that informs the prospective Stage 2 design. It advances Charter
Pillar 4 / Roadmap Arc 4, without claiming that the ecological effect has already
been recovered after adjustment.

Keep the current landscape, source, sites, train/holdout split, survey schedule,
known detection/spread/resistance assumptions and independent K131072 alpha=1
bank. Supply the same whole-map mean background hazard mu=0.002 to every model.
Estimate the additional spatial coefficient only in models that include it.
Unknown overall background mean and additional surveys are deferred, so model
flexibility is the only new scientific factor in this pilot.

## Model family and information symmetry

Let A be the same deterministic, map-derived normal-score resistance-distance
proxy defined in Goal 051. It uses source and conductance information available
to the analyst, not realised arrivals, background fields, prey states or the
integration bank. Define

`lambda_i(beta) = 0.002 * exp(beta*A_i) / mean_all_map_cells(exp(beta*A))`.

Before arrival a_i the hazard is lambda_i; afterwards it is h*lambda_i.
Compare these nested fitted models on the same training observations:

| Model | Parameters fitted | Purpose |
| --- | --- | --- |
| Constant background | h; beta fixed at 0 | Current analysis control |
| A-adjusted background | h and beta | Separate spatial background pattern from post-arrival effect |
| A-adjusted no-effect comparator | beta; h fixed at 1 | Test predictive contribution of predator effect after spatial adjustment |

All models retain the same known mu and other supplied nuisances. The neutral
comparator is fitted to the same training data. Holdout data are used only for
reported predictive comparisons, never fitting or choosing parameter bounds.
The adjusted model is given the same proxy used to construct the aligned
generator, so this is deliberately favourable adjustment information.
It omits the correlated Gaussian field G and therefore is not the full B100-A
generating model. A beta coefficient must not be represented as a measured
causal effect of distance or as recovery of G.

## Bounded development evidence

Use exactly the first six archived production replicate indices, 0–5, in each
of B_h1, B_h3, B100-A_h1 and B100-A_h3: **24 history replays**, paired in six
blocks. Freeze these indices before inspecting adjusted fits. They are chosen
by archive order, not by error, detector flag, field alignment or apparent
fit quality. No new random histories or confirmation block are included.

The archive retains scores and summaries rather than observation histories.
Replay the original streams and first reproduce the corresponding original
profiles, joint holdout scores and fitted nodes under the constant model.
Treat every replay as development evidence from an already examined screen.
It supplies no fresh validation and is too small for a population bias or
detector-power claim.

Required controls and outputs:

- Check beta=0 against the unchanged constant-background likelihood, whole-map
  hazard normalization and direct small-state likelihood calculations.
- Examine the joint beta/h surface first with replayed true arrivals supplied
  as an explicitly oracle diagnostic, then with the actual latent-arrival
  integration and predator observations. Oracle results never substitute for
  the analyst fit.
- Freeze numerical search bounds, grid/refinement rules and solver checks
  before new fits. Inspect joint/profile likelihood shape, competing maxima,
  weak directions and boundary contact. The physical h=1 boundary is expected
  under a null; boundary contact by itself is not an implementation failure.
  Do not add penalties or shrink bounds after observing a ridge to manufacture
  identification.
- Report training/holdout overlap in A and arrival-time support, the amount of
  observed pre-arrival risk time, fitted locations and held-out scores against
  the fitted adjusted no-effect comparator. Distinguish interpolative prediction
  from extrapolation across this split.
- Retain raw likelihood-ratio surfaces. **Do not apply Goal 049/050 cutoffs or
  label new profile ranges 95% intervals.** Nuisance profiling changes the
  statistic and its calibration. The pilot must propose a defensible,
  computationally costed calibration and prospective evaluation route before
  any such claims.

A weak ridge or inability to separate h and beta is a valid result. It would
motivate a deliberate observation-design discussion. A stable numerical fit
is only evidence that the proposed next comparison is feasible, not proof
of recoverability or adequacy under the omitted G field. A larger prospective
design must include exact adjusted-model positive controls and independent
histories before evaluating bias, calibration, discrimination or power.

## Resource and stopping proposal

Request a **four-hour total computation cap**, eight workers, one numerical
thread per worker and 32 GiB aggregate address-space limit on deep-server-ts.
This is a new maximum envelope, not expenditure authorized by unused Goal 051
time and not a claim that the new likelihood has already been timed.

Charge 1,200 s for preparation/controls or actual computation if greater;
reserve at least 1,800 s for synthesis/verification and 30 s for termination
grace. Allow at most 900 s for a source-bound timing qualification. The maximum
remaining pilot allowance is therefore 10,470 s when those allowances are
fully used. Use measured actual timing in the launch receipt and apply a 1.5
factor to the complete projected workload, counting one-time construction once.
The timing must include the new background likelihood and its prescribed
joint/profile search, not reuse Goal 051's per-history scoring rate.

Launch the remaining fixed replay panel only if all controls, identities and
the complete-workload budget pass. If qualification or the projection fails,
preserve the failure and report the computational limit. Do not enlarge the
bank/resources, shorten the panel or switch the scientific model to get a pass.
Source changes invalidate its numerical/timing qualification. No scheduler is
created until an approved run actually needs asynchronous continuation.

## Reporting horizon and decision requested

Authority would cover the pilot registration, implementation, controls,
independent implementation review, fixed archive replay, timing, joint/profile
diagnostics, synthesis and independent result review within that cap. Completion
is a verified feasibility/identifiability finding and a costed recommendation
for prospective Stage 2, or a preserved stopping outcome. A successful pilot
does not automatically launch a larger campaign.

It would explicitly permit retrospective model development before the prior
standalone confirmation prerequisite is fulfilled. It does not confirm the
screen nominee or relax the need for independent evidence in a subsequent
decisive comparison. New process histories, new calibration, unknown mean
background/detection/spread, additional surveys/landscapes, the field-normalizing
ablation, temporal confounding, commits, pushes and publication are excluded.

Recommend that Barry approve this model-first pilot on the current survey,
with that explicit change to the sequence. Pre-arrival augmentation is the
next design option if the pilot finds insufficient separation; it is not a
second factor silently bundled into the proposed work.
