# Goal 036: Prey-Effect And Background-Risk Reference Closure

## Programme role

This goal closes the prey-response component of Charter Pillar 1, the trusted
reference laboratory, and advances the Arc 1 exit gate in
`docs/paper1-adaptive-implementation-roadmap.md`. It does not begin the Arc 2
recoverability map.

## Scientific questions

1. At the accepted reference background hazard, does a fourfold predator
   effect sharpen the strict-recovery transition between the detected
   threefold and recovered fivefold benchmarks?
2. With the predator effect fixed at fivefold, is strict recovery retained
   when the counterfactual 60-day background extirpation risk is 5% or 20%,
   around the accepted reference value of 11.3%?

`Counterfactual 60-day background extirpation risk` means the absorbing
extirpation probability by day 60 if the predator never arrived. It is not an
annual turnover rate. The corresponding constant daily hazard is
`-log(1 - risk) / 60`.

## Frozen experiment

Retain the accepted Goal 026-028 landscape, 120/40 cluster-isolated
training/holdout design, known realised predator arrival, perfect prey-state
observations at days 10-60, absorbing extirpation, candidate grids, neutral
comparator, calibrated likelihood support, and strict recovery gates.

Run exactly three separately calibrated new conditions:

| Condition | Predator effect | Background specification | Master seed |
|---|---:|---:|---:|
| `fourfold_reference_risk` | 4x | daily hazard `0.002` | `202608290364` |
| `fivefold_low_background_risk` | 5x | 5% risk by day 60 | `20260811027` |
| `fivefold_high_background_risk` | 5x | 20% risk by day 60 | `20260811027` |

Each new cell uses 2,000 calibration histories, the 1901st ordered
likelihood-ratio statistic, and 1,000 validation histories. The low and high
fivefold cells deliberately share the accepted Goal 027 master seed so their
process and latent prey-threshold streams are matched. The fourfold cell is
independent.

Load and exactly reconcile, without rerunning:

- the accepted Goal 028 threefold/reference-risk result as the lower effect
  anchor; and
- the accepted Goal 027 fivefold/reference-risk result as both the upper
  effect anchor and middle background-risk condition.

## Prespecified decisions

A cell is `fully_recovered` only when every Goal 028 gate passes. It is
`detected_but_not_fully_recovered` when at least 950/1000 supports exclude a
hazard ratio of 1 and the lower 95% bound on held-out predictive advantage is
positive, but another full-recovery gate fails. Otherwise it is
`not_reliably_detected`; invalid computation is `implementation_blocked`.

If the fourfold cell fully recovers, bracket strict recovery between threefold
and fourfold. If it is detected but not fully recovered, retain the bracket
between fourfold and fivefold. A detection failure relative to the accepted
threefold anchor is nonmonotonic and requires human review; do not rerun it.

Call fivefold recovery robust over the 5%-20% background-risk bracket only if
both new extremes fully recover. Otherwise identify which extreme is
conditional and which recovery gates failed.

Any scientifically valid positive or negative result completes the goal. Do
not add another effect multiplier, background risk, seed, replication,
threshold, or retuning step after seeing production evidence.

## Review surface

Write exactly six ignored outputs:

- `calibration_statistics.csv`;
- `validation_results.csv`;
- `condition_decision_summary.csv`;
- `summary.json`;
- `review.md`; and
- `prey_reference_closure.svg`.

Report each condition using the 60-day background risk, daily background and
post-arrival hazards, hypothetical immediate-arrival 60-day extirpation risk,
and the accepted recovery metrics. New-cell validation rows must also expose
truth-assisted event-information diagnostics: total/training/holdout events,
censoring, pre- versus post-arrival observed events, arrival by day 60, and
post-arrival at-risk exposure. These diagnostics explain information yield; they are
not extra likelihood inputs.

## Interpretation boundary

Holding the hazard ratio fixed while changing background risk also changes the
absolute post-arrival hazard, pre-arrival loss, event yield, and censoring.
Therefore this goal estimates conditional recoverability across baseline-risk
regimes, not a causal background-hazard effect. Background hazard is known in
both generator and likelihood; joint estimation is out of scope.

## Validation and stopping rule

- use the existing Goal 026 engine through one thin Goal 036 module and CLI;
- add only a small in-loop diagnostic record rather than resimulating data;
- use four focused tests covering risk conversion, decisions, anchor
  reconciliation, and the reduced bundle/event accounting;
- run one reduced smoke and the three production cells;
- inspect the table, memo, and figure once;
- run focused tests, the full suite once, Ruff, strict MyPy, package build, and
  `git diff --check`;
- permit at most one material repair pass.

Generated artifacts and build outputs remain ignored. Stop at Barry's
scientific review. Do not update the README or roadmap with an Arc 1 closure
claim, commit, push, begin Arc 2, introduce imperfect observations, estimate
background hazard, or perform unrelated cleanup.

Barry approved this experiment on 29 August 2026.

## Outcome

The production experiment returned `arc1_prey_reference_closure_complete`.

At the accepted 11.3% counterfactual 60-day background risk, the fourfold
effect was fully recovered. Its calibrated support contained truth in
`949/1000` validation datasets, every support excluded no effect and was
connected and interior, median absolute log-effect error was `0.118`, median
log support width was `0.719`, and the lower 95% bound on held-out predictive
advantage was `0.0449`. Together with the accepted threefold result, which was
detected but slightly too broad and conservatively calibrated, this brackets
the strict recovery transition between threefold and fourfold.

Fivefold recovery depended on the baseline event-information regime. The
accepted 11.3% reference and new 20% background-risk cells both fully
recovered. At 5% background risk, the predator effect was nevertheless clearly
detected: `996/1000` supports excluded no effect and held-out prediction beat
neutral with a lower 95% advantage of `0.0290`. It did not pass strict full
recovery because only `924/1000` supports were connected and interior and the
median log support width was `0.954`, above the `0.800` precision gate.

The event audit is consistent with reduced event information in the low-risk
condition, without changing the model.
Median observed extirpations were `22` at 5% background risk, `47` in the
accepted 11.3% reference, and `74` at 20%. The low-risk cell therefore retained
a reliable nonzero signal but supplied too few events for the prespecified
precision standard. This is a conditional recoverability result, not a causal
effect of background hazard and not evidence about jointly estimating that
hazard.

## Validation

The reduced smoke wrote the exact six-file bundle and reconciled all event
partitions. The final production run evaluated only the three frozen new cells and
completed locally in 14 minutes 56 seconds. Accepted Goal 027 and Goal 028 anchors
were loaded and reconciled without rerunning them. One material review repair
clarified that post-arrival exposure stops at extirpation; deterministic
production regeneration changed only this diagnostic, not the recovery
outcomes. The table, review memo, SVG, JSON, event diagnostics, and
ignored-output status were inspected once. Final
checks comprised the focused Goal 026-028 and Goal 036 tests, the full suite,
Ruff formatting and lint, strict MyPy, package build, and `git diff --check`.
Generated artifacts and build outputs remained ignored and unstaged. No extra
effect multiplier, background risk, seed, replication, retuning, Arc 2 work,
commit, or push was performed.
