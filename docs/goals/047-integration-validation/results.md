# Goal 047 result: the current integrator is pseudocount-sensitive

12 September 2026 (Hobart). Stage A completed at 2026-09-11 11:48:28 UTC.

The study ends at its registered Stage A rejection. Holding empirical arrivals
and observation histories fixed, changing the category pseudocount changes the
connected-map calibrated width contrast beyond the prespecified tolerance.
Every bank representation has at least one failing alpha comparison. Stage B
is therefore **unrun by design**, and no fresh arrival banks were generated.
Goal 046's four numerical failures remain binding; ecological synthesis remains
unqualified.

## Decisive result

The table gives the maximum movement over alpha=0.25, 0.5 and 1 within each
fixed empirical bank. The primary pseudocount remains 0.5; the sensitivity
levels are not competing methods from which to select a favourable result.
The width functional is the balanced-minus-access mean log support width,
using each design/bank/alpha's own rank-239 cutoff.

| Connected bank | Width-contrast movement | Registered limit | Boundary classifications changed |
|---|---:|---:|---:|
| First K65536 half | 0.011805446 | 0.01 | 1 |
| Second K65536 half | 0.012639014 | 0.01 | 1 |
| Combined K131072 | 0.020274711 | 0.01 | 1 |

The boundary criterion permits no changes. Six of nine pairwise within-bank
alpha comparisons fail both that criterion and the mean-width criterion.
No support-component changes occur. Cutoff movement stays below 0.5 LR,
endpoints move by at most one H181 cell, and coverage/exclusion counts and their
paired contrasts move by at most one of 250 histories. Those passing criteria
cannot compensate for the registered failures.

For the primary combined bank, changing alpha from 0.5 to 1 changes the width
contrast from 0.076563427 to 0.064292859, a movement of 0.012270568. Thus the
negative decision does not depend only on comparing the two extreme sensitivity
levels.

## Separating the two numerical sensitivities

All 27 within-bank corridor alpha case comparisons pass. The largest direct
LR movement at generating rho=1 is 0.062910306, below the 0.5 limit. Both MLEs
remain fixed, core-profile movements pass, and every maximum stays inside the
fixed seven-node window. The result is not a window-inconclusive stop.

The contextual comparisons distinguish this from bank-realization variation:

- At alpha=0.5, the two equal-sized halves have connected width contrasts
  differing by only 0.000254175, but corridor generating-rho LRs differ by
  1.8378–1.8597 across the three effect truths.
- Matching the relative pseudocount fraction across a half and the combined
  bank reduces width-contrast movement to at most 0.000334754; all four matched
  width comparisons pass. Their corridor tail movements still reach about
  0.987 LR and exceed 0.5.

Within a fixed bank, alpha is the sole changed numerical factor, so the width
movement identifies pseudocount sensitivity conditional on these stress cases.
The matched-weight comparisons support that interpretation. They remain
correlated comparisons and do not establish exact integration bias, a unique
cause for the original bank-doubling failure, or prospective generality. The
corridor result separately retains sensitivity to bank realization. Neither a
new pseudocount nor a bank-size change is selected or accepted by this study.

## Verification and evidence

The run and automatic decision check both exited successfully. Runtime was
1594.921 seconds (26.58 minutes), with peak aggregate RSS 3.101 GiB, within
the two-hour and memory limits. All associated processes have stopped.

The parent independently checked all 76 preflight files, 22 immutable inputs
and both 82-file Goal 046 source snapshots locally and on the remote host.
The registered design and seed ledger remain unchanged. All connected LR and
support-drop arrays reconstruct exactly from the retained raw training
likelihoods. All reported metrics in the 16 comparison records (nine alpha,
three equal-K half and four matched-weight comparisons) reconstruct exactly.
First-half replay of the original saved results is exact; combined replay
differs by at most 1.819e-12, below the registered 1e-9 tolerance.

The [verification receipt](completed-check.json) binds the raw arrays, report,
decision, exit and preflight receipts. The [independent terminal review](final-review.md)
confirms the rejection and its claim boundary. The frozen design remains in
[design-proposal.md](design-proposal.md) and [registration.json](registration.json).
Full reduced arrays, raw training surfaces, source snapshots and logs are
retained under `artifacts/goal047_execution/`; the remote source and reference
bundles remain immutable. No commit, push or publication occurred.

## Next scientific decision

Goal 047 is complete with a negative method result. The completion heartbeat
is paused. Further work requires a reviewed integration or regularization
redesign, including how numerical accuracy will be assessed before a new
qualification study. This result does not authorize implementing such a
redesign, resuming production, relaxing the original criteria or omitting
failed maps.
