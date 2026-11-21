# Boundary and resume repair passes the registered acceptance replay

21 November 2026. All 24 previously resolved comparison fits passed at all 12,460 registered locations. The candidate resolved 25 of the 27 previously failed fits. The two remaining failures are the dense and lean fits of the same corridor-1 window-low arm B dataset, the case specified in advance for retention if the envelope guard fired again. Every fit returned a terminal scientific result.

This completes the development acceptance test for source `432bb6e56e672f9e57f2f7bc369546023b07662e`. The data were selected partly for earlier failures. Estimating the failure rate requires a freshly drawn qualification panel. Reciprocal scientific review and panel sizing are next. [Registered deviation](../paper1-sprint2-boundary-resume-2026-11-16/acceptance-deviation.md) · [Original acceptance plan](../paper1-sprint2-repair-2026-11-12/acceptance-plan.md) · [15 November verdict](../paper1-sprint2-repair-2026-11-15/README.md)

| Registered check | Outcome |
| --- | --- |
| Comparison fits | 24 of 24 resolved, two per arm and search-role stratum |
| Required locations | All 12,460 evaluated at the exact archived coordinates |
| Largest absolute criterion shift | 1.53923 × 10⁻⁸ against a limit of 10⁻⁶ |
| Largest absolute profile likelihood-ratio shift | 3.07846 × 10⁻⁸ against a limit of 10⁻³ |
| Eligibility | Agreement on every required comparison |
| Development replay | 25 resolved and two stopped at the envelope guard |
| Two historical recoveries | Both resolved from their preserved searches under original repair source `a77e849` |
| Interrupted twin | Passed the exact comparison on its fit, search and evaluation records |

For spatial positive variance, the agreed comparison takes the larger of the raw positive and fitted zero-variance criteria on each side. When both endpoints qualify, this equals the spatial envelope. Three raw positive-criterion shifts in two tasks still exceed 10⁻⁶. The largest is 1.97843 × 10⁻⁵. Those raw values remain available for diagnostics and starts. The amended check measures accuracy of the quantity used for inference.

Both residual failures stopped before tight replay. At h = 22.2222 the dense fit exhausted the 80-iteration outer budget on a candidate 0.23053 criterion units above the best eligible positive-family endpoint. At h = 30 the lean fit had two such candidates, 0.23918 and 0.23996 above the endpoint. The guard threshold was 0.0001. The inner mode converged in eight iterations on each of the three evaluations. Across all 51 final receipts, all 1,535,504 recorded inner branch solves converged. They rejected 16,245 invalid trial steps. The median was four iterations, the 90th and 99th percentiles were eight and twelve, and the maximum was 37.

## Continuation and compute

PBS completion job 880988 finished successfully at 23:55 Hobart time on 20 November. Of the 51 main fits, 46 finished in one attempt and five needed a second. Four reached the 48-hour walltime and resolved in the second PBS array. A fifth, corridor-0 increased-heterogeneity C lean (index 34), resumed on another node under the original PBS job ID and resolved. The first process wrote 124 search events before it stopped. The surviving job history gives the final execution and leaves the interruption cause unknown. Two attempts were sufficient for every main fit.

Final PBS accounting records 924.50 one-core allocation hours across the main arrays. The first execution of index 34 adds at least 18.93 hours from its search log, putting the lower bound at 943.44 hours. Median walltime summed by fit was 11.92 hours. The longest fully accounted fit took 82.85 hours. The whole execution graph, including probes, historical recoveries and twin, accounted for at least 1,146.82 one-core hours by the same calculation.

The 46 uninterrupted fit processes supply comparable stage times. Of their 631.56 hours, the latent audit took 280.98 (44.5%). Intervals ending with a tight-tagged fixed or free fit accounted for 157.93 hours (25.0%). This interval attribution includes the work between successive events. Together the safeguards account for about 69.5% of these uninterrupted hours. The full sample intentionally overrepresents difficult cases, so panel sizing needs the distribution of ordinary qualification tasks as well as the long tail.

The real-data twin used the shortest of the 24 registered comparison tasks. PBS interrupted it during search after one durable operation and 20 evaluations in the next operation, then at call 71 of 142 in its audit loop. Every location in this selected task fell below the variance threshold for a numerical mode audit. Its resumed run reproduced the uninterrupted run's fit, search and evaluation stream exactly under the field exclusions frozen before launch. The audit interruption therefore exercises restart inside the real audit loop. [Interruption plan and scope](../paper1-sprint2-boundary-resume-2026-11-16/interrupted-twin-plan.md)

For each historical fit, the recovery restored 133 standard and 133 tight spatial points from its archived events. The resulting spatial report was reproduced from these rows. The two continuations performed 268 and 218 numerical audits and completed in 13.53 and 35.41 hours respectively, in addition to the searches saved from 15 November.

## Evidence

The terminal index, both reconciliations and the summary identify the frozen source. All twelve PBS job records and their array members reached a terminal state. The separate numerical, historical and interrupted-run checks used the underlying files. A target-side postflight rehashed all 387 distinct inputs named by the 51 fit and 24 probe plans (5,184,972,826 bytes), including the original runtime image and selected development banks. Every digest matched.

The audit matched 426 inventoried fit and probe outputs, 12,046 ordered search-operation payloads and 355 stage payloads to the terminal tasks and checkpoint identities. The independent comparison reconstructed the 24 selected tasks from the original pool of 417, matched the 27 original failures and their receipts, and verified each of the 12,460 probe checkpoints at its registered coordinate. A separate continuation review reproduced the uninterrupted and resumed twin’s three scientific payload digests and both historical spatial reports. For index 34, the restored first 123 operations and the intervening control event reproduce the first process’s 124-event scientific prefix.

The per-fit table records each terminal reason, walltime by PBS segment, invalid inner trials and histogram of converged inner iterations. The three private archives contain the original outputs, anchor checkpoints, independent checkers and their selected historical inputs. Each stored archive matches the separately verified SHA-256 in the bulk ledger. Board message 3613 records the scientific handoff. [Per-fit outcomes](fit-outcomes.json) · [Bulk ledger](../../bulk-receipts.sha256)

In a clean checkout with the three archives at their ledger paths, the following commands restore the evidence and reproduce the table from the repository root.

```sh
bundle=artifacts/sprint2/boundary-resume-20261121
mkdir -p "$bundle/raw"
tar -xzf "$bundle/evidence.tar.gz" -C "$bundle/raw"
tar -xzf "$bundle/anchor-checkpoints.tar.gz" -C "$bundle/raw"
tar -xzf "$bundle/audit-support.tar.gz"
python3 docs/evidence/paper1-sprint2-acceptance-2026-11-21/summarize-execution.py "$bundle"
```

Aggregate index SHA-256: `a4c5afa5daceb0fef5c959f98504bbb65975e08364d9e4d55d2e5cddc5220404`. Replay summary SHA-256: `bb195b4e6d29705168db904c503ff88741f1f7606f09e312856f893ee5ba71d5`. Twin comparison SHA-256: `1d72a3af472d5d4b57f305b801e188a9d80b23a449d72d8a5bb6487da9a37b42`.

Next: Claude — reconcile the acceptance result and size the fresh qualification panel.
