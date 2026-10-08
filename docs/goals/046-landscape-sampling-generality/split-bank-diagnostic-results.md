# Goal 046: completed bank-half diagnosis

11 September 2026 (Hobart). The bounded diagnostic completed successfully;
its returned quantities and provenance are verified. The final production pair
remains rejected under the frozen all-nine-map rule. These selected diagnostic
cases explain numerical sensitivity; they do not support ecological inference.

## Execution and verification

The single run started at 23:28:34 UTC on 10 September and finished at
00:04:11 UTC on 11 September, with exit 0. Numerical runtime was 2135.51 seconds
(35.59 minutes), below the one-hour limit; peak sampled RSS was 3.0452 GiB.
It used the existing connected and corridor 2026090812 banks, two maps
serially, four workers and the unchanged numerical helper. No new bank,
history, rho candidate, acceptance rule or production run was introduced.

The [return check](split-bank-diagnostic-check.json) reconciles both 82-file
source snapshots, all 22 bound inputs, original remote adoption records,
prepared runner/launcher and completed output hashes. All 38 reduced arrays
are finite and have their expected shapes. Local and remote recomputation
agree exactly on every check and diagnostic quantity. The first half exactly
reproduces the saved K65536 quantities. The pseudocount-corrected combination
reproduces saved K131072 quantities within 1.365e-12, well below the fixed
1e-9 tolerance. Cutoffs, ranks, widths, raw/centred likelihoods and maxima were
also independently reconstructed from the reduced arrays.

Raw outputs and the reproducible check are under
`artifacts/goal046_execution/split-diagnostic/`. Original output is in
`full-output/diagnostic-report.json` and `diagnostic-arrays.npz`; the check is
`check_completed_diagnostic.py`, with local and remote JSON receipts. The
remote directory remains
`/data/codex/scratch/goal046-split-diagnostic-20260911/`.

## Connected map: halves agree, combined-bank cutoff changes

These are the known-speed, no-effect diagnostics for connected 2026090812.
Each bank uses its own access and balanced rank-239 cutoffs from the original
250 calibration histories and its original 250 evaluation histories.

| Quantity | First 65536 rows | Last 65536 rows | Combined 131072 rows |
|---|---:|---:|---:|
| Access cutoff, LR | 2.023022 | 2.023383 | 2.022629 |
| Balanced cutoff, LR | 2.299503 | 2.300107 | 2.394133 |
| Balanced-minus-access mean log width | 0.064523 | 0.064268 | 0.076563 |
| Balanced history 124: LR (rank) | 2.299503 (239) | 2.300107 (239) | 2.299812 (238) |
| Balanced history 131: LR (rank) | 2.288567 (238) | 2.292797 (238) | 2.394133 (239) |

The two equally sized halves differ by -0.0002542 in the paired mean log width.
The combined bank differs from the first half by +0.0120408 and from the
second by +0.0122950. History 131 remains below history 124 in both halves,
but overtakes it in the combined bank and sets the new balanced cutoff.
This sharpens the earlier diagnosis: the observed bank-doubling movement is
not mirrored by comparable between-half cutoff variation at fixed bank size.
It remains a material failure of the declared calibrated-width contrast.

This does not isolate its cause. Both halves use the same relative
pseudocount weight; the combined bank reduces that weight. Site probabilities
are also combined before logarithms and profiling, so a combined LR need not
lie between the two half-bank LRs. The present calculation does not separate
those mechanisms or measure exact integration bias. Similar halves alone
cannot establish convergence or rescue the combined production comparison.

## Corridor map: tail varies between halves, local maximum is stable

These are access evaluation history 0 at the original three effect truths.
The fixed diagnostic contains rho=1 and seven original G201 nodes around the
saved fitted speed. All three bank representations retain rho=1.101905 as the
maximum within that fixed window, for all three effect truths. No maximum
reaches a window edge or the isolated rho=1 node, so no widening is needed.
The second half was not searched outside the declared window.

| Effect truth | LR at rho=1, first half | LR at rho=1, last half | LR at rho=1, combined |
|---|---:|---:|---:|
| 1 | 38.484579 | 40.344273 | 39.372844 |
| 3 | 38.527699 | 40.385722 | 39.415007 |
| 5 | 39.773087 | 41.610880 | 40.652797 |

The half-to-half LR changes are 1.859694, 1.858023 and 1.837793. At the same
bank size and smoothing weight, the arrival draw realization therefore
changes this far-tail quantity substantially, while the checked fitted-speed
node is unchanged. The combined-minus-first-half movements reproduce the
three original failures: 0.888265, 0.887308 and 0.879710. These share the same
predator history and are not independent replications.

## Decision boundary

The diagnostic is technically complete. The four final ensemble failures
remain binding, including the connected calibrated-width instability. All
216 replay/half-grid rows were independently verified; the three failed rows
repeat the corridor tail issue, and every separate grid-refinement gain passes.
No numerical repair or ecological synthesis is licensed by this diagnosis.

The [independent review](split-bank-diagnostic-review.md) records the method
decision. A future integration or validation study needs a separate prospective
scientific design; keeping the present failed comparison is part of that
record. Closing Arc 3 as unresolved is also an available programme decision.
