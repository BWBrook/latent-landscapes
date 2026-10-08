# Goal 049: pre-run registration and response to Fable

20 September 2026, before Goal 049 diagnostic execution or new histories.
Authority: Barry's instruction to proceed after receiving Fable's critique,
Correspondence thread 44, messages 276–280. The revised [plan](plan.md) is the
scientific contract; this record fixes its review amendments and predictions.
The [original proposal](plan-2026-09-19.md) remains available.

## Decisions fixed before execution

1. Use **known-nuisance, model-conditional discrete confidence sets**. “Operational”
   in the directory name does not imply readiness for unknown-nuisance field data.
2. Primary numerical comparison: K65536, alpha=0.5 versus nested K131072,
   alpha=1.0. The pseudocount fraction is matched. This is a sensitivity
   comparison, not an estimate of pure Monte Carlo variance or exact bias.
3. At fixed K131072, alpha=0.25, 0.5 and 1.0 form a descriptive regulariser
   sweep. Recalibrate every scoring variant separately. Four variants total.
4. Keep all 181 effect nodes, 999 calibration histories per node, rank 950,
   and 1,000 evaluation histories at each of h=1,2,3,4,5,10. Retain complete
   profile curves. Do not reduce replication or interpolate after seeing cost
   or outcomes; report a costed alternative if the ceiling cannot be met.
5. The primary figure is the candidate-cutoff curve, with pointwise LR-scale
   binomial/order-statistic quantile bands and zero-score fractions. The
   Beta(950,50) law describes probability content, not an LR-scale error band.
   The curve bands are not simultaneous bands. Chi-square references are
   heuristics, not an adopted asymptotic law for this composite statistic.
6. Add the archived speed-cutoff transport check separately from effect-set
   inversion. Both old banks have alpha=0.5; their comparison is confounded
   by relative regulariser weight and cannot pass the new matched-weight gate.
7. Keep the existing absolute endpoint tolerances. SE ratios, where SE>0,
   are descriptive. Zero SE leaves the absolute comparison intact and the
   ratio undefined. No new pass rule is attached to the regulariser sweep.

## Three predictions, not acceptance gates

These are historically informed predictions, specified before inspecting the
new diagnostic outputs. They are not independent prior hypotheses untouched
by earlier project results. Fable supplied the qualitative predictions;
Astra fixes the explicit summaries below so “approximately” is assessable.
Report each prediction and counterevidence even if it fails. They cannot change
the grid, calibration, numerical tolerance, or stopping rule.

**P1 — boundary effect.** For the primary K131072/alpha=1 table, predict
`c_1 < median(c_g : 2 <= g <= 8)` with a ratio at most 0.85. The heuristic
reference for c_1 is 2.7055 (chi-square(1) 90% quantile); no exact half-mixture
or atom size is assumed. Predict that applying c_1 as a flat cutoff gives
coverage below 0.95 at both h=3 and h=5, and that the oracle-flat null-exclusion
rate is below the candidate-wise rate at those truths. Report magnitudes and
uncertainty; do not turn small directional differences into resolved effects.
The three-anchor archive provides a retrospective precursor, not an
independent replication of this full-table prediction. Upper-boundary h=10
is separately described without prespecifying symmetric mixture behaviour.

**P2 — interior cutoff scale.** For the same primary table and the fixed
interior region 2<=g<=8, predict all point cutoffs lie within 30% of 3.84146
(2.68902 to 4.99390), and their maximum/minimum ratio is at most 1.5.
Show the uncertainty bands and fraction of interior nodes outside this band;
do not interpret 121 correlated nodes as independent tests. Cutoff proximity
does not imply set proximity: compare memberships and geometry with the
fixed 3.84146 comparator on the same histories. That comparator has no
asserted coverage guarantee here.

**P3 — speed transport.** In the archived profiled speed statistic, predict
the rho=1 cutoff exceeds the rho=0.5 cutoff at effects 1,3,5 in both banks.
Predict the smaller-source cutoff produces coverage below the archive's
239/251 reference at rho=1, and the larger-source cutoff produces coverage
above that reference at rho=0.5. Quantify severity as a deviation of at least
0.05 for one direction at each effect; report failures of this stronger
prediction too. Separate off-diagonal transport from diagonal pipeline checks.
Previously reported cutoffs near 45 and 20 motivate this prediction but are
not treated as measurements of a design effect.

## Randomness, controls and boundaries

Fresh root identifiers are 2026092001 (calibration), 2026092002 (evaluation)
and 2026092003 (bootstrap). Verify these differ from the archived bank roots
and use disjoint deterministic streams; record the construction in the run
receipt. Common random numbers across candidate truths within a phase are
allowed, while replicates at each candidate remain iid. Do not draw histories
from the fitting bank. A shared master label alone would not establish
dependence when streams are correctly spawned; the actual requirement is
independent bank/calibration/evaluation randomness and no reused RNG state.

The analyst receives observations, opaque IDs, known nuisance inputs and the
entire calibration table. It receives no generating effect, truth-role label,
arrival time or extirpation time. Freeze scores/set outputs before joining
the evaluator's truth sidecar. The matched oracle is evaluator-only.

Verify exact oracle/candidate-wise true-node identity, null-truth identity,
unchanged point estimation and prediction, full-grid maximizer inclusion,
inclusive ties, seed separation and alpha transformation. A fixed approximate
score can satisfy the rank argument while having distorted power/geometry;
integration error need not move power in only one direction. A beta-binomial
departure alone does not uniquely diagnose leakage: scoring/generator mismatch,
ties and conditional-versus-marginal reference mistakes also require checking.

The timing probe and h=1,3,10 canaries precede production. The ceiling remains
24 elapsed computation hours total, eight CPU workers and 32 GiB aggregate
memory, including four variants and the fixed 2,000-draw paired bootstrap.
No production launch occurs until measured timing and controls support that
budget. An unaffordable design is a valid bounded outcome. Preserve failures;
no larger bank, extra calibration, new maps or favourable redraw is authorised.

## Interpretation amendments

Apply the reviewed cross-arc amendments with historical results alongside the
retrospective interpretation. Arc 2B's old 3/10/19 counts remain historical;
the coverage-free classification is explicitly 4/9/19, with S08 the only
changed condition. Arc 2C separates 22 substantive contrasts and eight
calibration checks. Arc 2A's fixed-cutoff bootstrap omits calibration-table
variation. Arc 1 retains its original nontransportability and other failures.
Each surviving recovery criterion must identify its measured estimand.

Fable's critique is incorporated, not treated as empirical validation. The
four Arc 3 numerical failures and all earlier non-adoption decisions remain.
