# Goal 050 synthesis: a conservative adequacy baseline

21 September 2026 (Hobart). **The registered detector/null-check tranche is
complete and passed final independent review.** No alternative
generator was tested. This advances the preparation for Charter Pillar 4 and
Arc 4; it does not complete model discrimination.

## Scientific result

The frozen held-out conditional prey-score detector rejected the assumed model
in **19 of 1,000 fresh null histories (1.9%)**, with conditional Wilson 95%
interval **1.22–2.95%** and calibration-aware bootstrap interval **1.1–3.2%**.
Across the six retrospective assumed-model truths, rejection ranged from
**0.4% to 2.4%**. These are conservative realised baseline rates for this table,
bank, grid and known-nuisance simulator. They establish neither sensitivity to
misspecification nor safety against misleading ecological estimates.

| Generating h | Detector rejection | Calibration-aware 95% interval | C99 truth inclusion |
| --- | ---: | ---: | ---: |
| 1, retrospective | 22/1000 (2.2%) | 1.30–3.60% | 98.8% |
| 2, retrospective | 23/1000 (2.3%) | 1.40–3.80% | 99.7% |
| 3, retrospective | 24/1000 (2.4%) | 1.40–3.60% | 99.3% |
| 4, retrospective | 24/1000 (2.4%) | 1.50–3.60% | 99.4% |
| 5, retrospective | 16/1000 (1.6%) | 0.80–2.50% | 99.1% |
| 10, retrospective | 4/1000 (0.4%) | 0.00–0.90% | 99.3% |
| 1, fresh prospective | 19/1000 (1.9%) | 1.10–3.20% | 99.2% |

The six retrospective rows share paired replicate streams; they are not six
independent studies. All generating h values in this table belong to the
assumed model. Thus even the h=10 row measures false rejection of model
adequacy, not detector power against an alternative model. Fresh C99 inclusion
has conditional Wilson interval 98.43–99.59% and calibration-aware interval
97.7–99.8%. The finite-grid marginal guarantee and the realised-table operating
characteristics remain distinct.

## The crossed null check

The fresh rank-950 null cutoff is **2.490251**, compared with **2.279370** in the
unchanged original table. Crossing both with the two independent evaluation
blocks gives:

| Rank-950 calibration cutoff | Original null evaluation | Fresh null evaluation |
| --- | ---: | ---: |
| Original | 74/1000 (7.4%; 5.6–9.60%) | 57/1000 (5.7%; 4.1–7.7%) |
| Fresh | 69/1000 (6.9%; 4.5–8.6%) | 48/1000 (4.8%; 3.4–6.8%) |

Parentheses contain the rate and its calibration-aware 95% interval. The cells
share cutoffs and/or evaluation histories, so their differences require paired
uncertainty. The registered contrasts are:

| Change | Percentage points | Calibration-aware 95% interval, percentage points |
| --- | ---: | ---: |
| Fresh minus original cutoff, original evaluation | -0.5 | -3.0 to +0.8 |
| Fresh minus original cutoff, fresh evaluation | -0.9 | -2.7 to +0.90 |
| Fresh minus original evaluation, original cutoff | -1.7 | -3.9 to +0.5 |
| Fresh minus original evaluation, fresh cutoff | -2.1 | -3.9 to +0.4 |
| Cutoff-by-evaluation interaction | -0.4 | -1.2 to +1.1 |

Every contrast interval includes zero. Descriptively the evaluation-block
change is larger than the cutoff change, but this small crossed experiment
cannot assign a unique cause to the original 7.4% flag. A fresh evaluation
under the original table gives 5.7%, and changing both blocks gives 4.8%; neither
outcome erases or repairs the original table's realised error. Its 7.4% result
and Goal 049 uncertainty remain as originally reported. The Goal 050 1,000-draw
interval is a separate registered uncertainty calculation, not a replacement
for Goal 049's 2,000-draw result.

Model-adequacy rejection and effect-set null exclusion answer different
questions. The detector's 1.9% fresh false-rejection rate does not calibrate the
effect set's 5.7% fresh false-effect rate, and a failure to reject adequacy does
not certify an effect estimate.

## Preserved predictions and limitations

The registered prediction that confidence-set maximization may be conservative
is supported descriptively by these realised rates. The prediction that the
crossed blocks might localise sensitivity remains unresolved: all five paired
contrasts include zero. Neither prediction was an acceptance gate, and no
statistic, cutoff, replication count or bootstrap precision was changed after
seeing the results. Earlier withdrawn claims and failed predictions in Goal 049,
and all four original Arc 3 numerical failures, remain unchanged.

The secondary training predator score is exactly invariant across h within each
paired replicate (maximum difference zero). Its distributions are reported
separately and make no omnibus rejection claim. This invariance is an internal
control, not evidence that every nuisance is correctly specified.

Validity is restricted to the supplied nuisances, independent fixed empirical
integration bank and finite 181-node effect grid. Existing evaluation histories
are retrospective because they informed detector design; only the new null
block is prospective. No off-grid, unknown-nuisance, alternative-generator or
field-data validation follows. The 1,000-draw empirical bootstrap preserves
four-block dependence but is not an exact finite-sample theorem. A percentile
interval can collapse at a ceiling while rare bootstrap draws still give a
positive SE: the h=5 effect-null-exclusion row has this behaviour; h=10 has
exactly zero SE. Neither is a population-certainty claim.

## Verification and evidence

All 180,819 original calibration histories and 6,000 original evaluation
histories replayed with zero LR-profile difference and identical fitted nodes
and opaque IDs; all original evaluation held-out joint scores also matched
exactly. Both fresh blocks completed at their registered counts. Source,
registration, seed, input and whole-file output identities verified locally and
remotely. The registered synthesis used exactly 1,000 draws from root 2026092006;
the bootstrap itself took 35.67 s, and the complete synthesis wrapper took 42 s.
No source change, redraw or restart was needed after timing qualification.

Production took 9,706 s (2 h 41 min 46 s), timing 299 s, and peak production RSS
was 1.79 GiB. Including the 1,800-s preparation allowance and actual synthesis,
computation used 11,847 s (3.29 h), before the bounded result-review overhead;
even charging the full 3,600-s synthesis/verification reserve gives 15,405 s
(4.28 h), below the 12-hour ceiling. Both production and synthesis exit receipts
are zero.

- [Registered design](registration-2026-09-20.md), [execution](execution.md),
  [implementation review](implementation-review.md), [final review](final-review.md).
- [Endpoint table](../../../artifacts/goal050_execution/synthesis/endpoint_results.csv),
  [crossed cells](../../../artifacts/goal050_execution/synthesis/crossed_null_cells.csv),
  [paired contrasts](../../../artifacts/goal050_execution/synthesis/crossed_null_contrasts.csv).
- [Standalone figure](../../../artifacts/goal050_execution/synthesis/model_adequacy.png)
  and [PDF](../../../artifacts/goal050_execution/synthesis/model_adequacy.pdf).
  Plotted intervals condition on the realised tables; calibration-aware intervals
  are in the tables above and accompanying CSVs.
- Full evidence remains under `artifacts/goal050_execution/` locally and
  `/data/codex/scratch/goal050-model-adequacy-20260920` on deep-server-ts.

## Next scientific decision

Freeze this implementation and reference table, then test whether ecological
misspecification can produce misleading estimates without triggering the
detector. The [costed next-screen proposal](next-screen-proposal.md) prioritises
heterogeneous detection and background confounding. Its ecological choices,
severities and authority need Barry's review, with Fable invited to challenge
the proposal before implementation. No alternative-generator campaign,
competing-model fit, commit, push or publication was launched here.
