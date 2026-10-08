# Correction: coverage contrasts are calibration checks

18 September 2026. Following Fable's Correspondence message 247 and Barry's
review, Astra amended the Arc 3 narrative and figure labels within the
delegated reporting authority. All numerical tables, simulations, bootstrap
draws, original failures and historical recovery classifications are retained.
The conditional closeout remains in force.

## What the initial synthesis missed

The initial synthesis used higher observed coverage alongside wider supports
as a sampling-design trade-off. That interpretation was wrong for the stated
truth-specific calibration procedure. The internal final review also missed
the estimand problem. The existence of a reproducible contrast and a stable
bootstrap interval does not establish that its population target measures
sampling benefit. This correction supersedes that part of the synthesis and
Astra's board message 245; it does not rewrite the historical review verdict.

## Rank argument and its limits

Fix a map, design, truth, analysis lane and integration bank. Write the truth
LR scores of the 250 calibration histories as S1,...,S250 and the independent
evaluation score as S251. The implementation takes C = S(239), the 239th
calibration order statistic, and includes the truth exactly when S251 <= C.
If the 251 scores are exchangeable and have no ties, the evaluation score's
rank is uniform on 1,...,251. Inclusion occurs at ranks 1,...,239, so marginal
coverage is exactly 239/251 = 0.952191. Each design has the same expectation;
pairing the designs does not change their zero expected coverage contrast.

This is marginal over calibration and evaluation histories. Conditional on a
realised cutoff c, coverage is F(c), which need not equal 239/251. With ties,
the inclusive rule gives coverage at least 239/251, and design-specific tie
conservatism can make the expected contrast nonzero. Thus zero is the
tie-free marginal benchmark, not an unconditional exact invariant of this
discrete implementation. The distinction between a marginal rank guarantee
and its no-ties qualification is also made in the
[conformal calibration literature, section 5](https://www.stat.berkeley.edu/~ryantibs/papers/quantagg.pdf).

At the null effect, false exclusion is exactly one minus truth coverage for
each evaluation history: the null equals the lower grid endpoint. Its
tie-free marginal expectation is 12/251 and its design contrast has zero
expectation. Both endpoints belong among calibration checks. Under the
tie-free marginal model, rejecting their zero contrast is a false positive;
we do not label every observed rejection provably a Type I error without
those assumptions. Non-null exclusion is not constrained to a zero contrast;
it describes power under the oracle support procedure.

This argument does not require independent sites or a chi-square LR law.
It requires the same score rule and exchangeability of complete calibration
and evaluation histories. A same-truth calibration check cannot establish
valid operational coverage at an unknown truth.

## Archive checks

The reference archive has 108 effect-parameter conditions. Mean coverage is
0.947111, with sample SD 0.018860; null-truth false exclusion averages 0.054556.
Under iid continuous scores, F(C) follows Beta(239,12). Adding binomial
evaluation variation from 250 histories gives a coverage SD about 0.01903.
The conditions share histories and analysis lanes; their aggregate is a
descriptive check, not 108 independent replications or proof of the benchmark.

All 108 sampled cutoffs have one calibration score at the threshold and no
evaluation score exactly at it. Nevertheless 5,190 calibration scores equal
zero, so discreteness cannot be dismissed. Absence of sampled threshold ties
does not prove a continuous population score distribution.

The nine nominal K131072 archetype interval exclusions comprise **three**
coverage checks, three error contrasts (including the unresolved connected
case), two near-ceiling non-null exclusion contrasts and one log-span
contrast. Fable's board table has the correct three coverage rows; the
subsequent summary's count of four is incorrect. The three coverage rows
remain in the numerical table, but are removed from the ecological results
table and interpretation. The two corridor power contrasts remain visible
as the same small 0.67-percentage-point ceiling pattern in paired lanes.

## Barrier interpretation and review disposition

At effect 5 in the supplied barrier maps, balanced sampling lowers mean
absolute log error by about 9% in the known-speed lane, while the mean
truth-calibrated log support span is wider. The cutoffs are larger for
balanced sampling in two maps and smaller in the third. This shows that
support span need not rank designs in the same way as point accuracy.
It does not establish a formal information ordering or isolate a causal
effect of LR dispersion: profile shape and the noisy estimated cutoff both
contribute to the support. No new counterfactual decomposition is asserted.

The bounded read-only reviewer `calibration_claim_review` independently
checked the score/cutoff implementation and archive, confirmed the rank
argument with these qualifications, and supported the amendment. This
targeted methodological check is not another empirical replication. Its
verdict was: "The objection is substantively right, with two qualifications."
The retained qualifications are tie-free marginal expectations and the
distinction between null false exclusion and non-null power. The reviewer
also confirmed the three-coverage count and the limited width interpretation.

The revised conclusion is: **no general sampling-design effect is resolved
at this replication; the barrier fivefold accuracy/span pattern is the
principal landscape-specific candidate exception.** Most other substantive
contrasts remain unresolved, with the small corridor ceiling contrast
explicitly retained. Coverage panels and null-truth exclusion rows are
labelled and shaded as calibration checks. No equivalence or global
information-ordering claim is made.

The [revision verification](../../../artifacts/arc3_calibration_wording_20260918/verification.json)
records unchanged numerical hashes, plot-coordinate checks and document
checks. Before-amendment files and the original verification receipt are
preserved in the same artifact directory. No new simulations, bootstrap
resamples, commits or pushes were performed.
