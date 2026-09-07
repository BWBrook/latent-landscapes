# Goal 045: decision after the 65536-draw reference

Status as of 7 September: numerical acceptance remains unresolved. Barry has
authorized one final projected 25.34-hour doubling; the primary-only amendment
below remains an unapproved historical proposal. No bank has been promoted or
scientific closeout declared. The completed runs answer the same six-case question with
unchanged simulated observations, grids and calibration rule.

## Decision-relevant evidence

The primary question is the added cost of estimating predator spread speed
for recovery of prey effect. Across 16384, 32768 and 65536 integration draws,
all 30 paired 95% bootstrap intervals (six cases × five metrics) include zero. The observed paired mean
error and prediction differences are small and stable. This supports a
numerically stable result of **no detected added cost under the tested known-
detection, known-background, fixed-landscape setting**. It is not an equivalence
claim or proof of no cost under other conditions. The matched bank expansions
are numerical sensitivity checks, not independent scientific replications.

Between 32768 and 65536 draws, the largest change in a paired mean-error
contrast was 0.0003673 log units, mean log-width contrast 0.0007801, and
conditional prediction contrast 0.00001449 nats per holdout site. Coverage and
no-effect-exclusion point contrasts were unchanged. The complete three-bank
estimates and bootstrap intervals are in
[primary-bank-stability.csv](primary-bank-stability.csv).

The original four-history likelihood checks pass: maximum profiled-rho LR
change 0.23036, profiled-effect change 0.10906, known-speed effect change
0.01063, and direct truth-LR change 0.17017, all below 0.5. Effect MLE movement
and rho support topology/endpoints also pass. These checks cover four
preselected histories across six cases, not every campaign history. See
[the canary summary](bank32-64-canary-summary.json).

The wider-range calibration criterion still fails:

| Case | Speed cutoff, 32768 | Speed cutoff, 65536 | Change | Cutoff criterion |
| --- | ---: | ---: | ---: | --- |
| usual_1 | 44.53693 | 45.20778 | +0.67085 | Fail |
| usual_3 | 45.09474 | 45.82084 | +0.72610 | Fail |
| usual_5 | 45.19271 | 45.77916 | +0.58645 | Fail |
| slow_1 | 19.98955 | 20.15972 | +0.17017 | Pass |
| slow_3 | 19.94932 | 20.11821 | +0.16889 | Pass |
| slow_5 | 20.22087 | 20.26131 | +0.04044 | Pass |

Individual paired bootstrap cutoff changes reach 0.864 LR.

The recorded limit is 0.5 LR, so near-unchanged downstream intervals do not
turn these failures into passes. Individual endpoints move at most one G201
cell. Support components and boundary classifications are unchanged, mean
log-width changes are at most 0.001553, and median widths are unchanged.
Coverage changes by one of 250 datasets in usual_1 and is unchanged elsewhere.
Speed-cutoff bootstrap bounds move by up to 0.67246 LR; coverage bootstrap
bounds move by up to 0.004. These bootstrap diagnostics use the same index
resamples across banks. See [the full comparison](bank32-64-comparison.json).

At the largest bank, the most adverse 95% bounds across cases still allow an
increase of 0.00314 log-error units or 0.05376 log-width units, a 3.2 percentage-
point loss of coverage or non-null exclusion, a 2.4-point increase in null
false exclusion, and a 0.000223 nats/site loss of conditional prediction score.
These are bounds for distinct case/metric contrasts, not a simultaneous region.
They describe uncertainty conditional on the generating model and integration
bank; zero inclusion is not an equivalence test.

## Diagnosis and limits

Calibration history 198 sets the usual_1 and usual_3 cutoffs at all three
banks. Its predator-marginal truth LR increases from 43.96665 to 44.48538 to
45.15631 while its fitted speed remains 1.086735. History 221 sets the
usual_5 cutoff at the two larger banks; its predator-marginal fitted speed
moves one G201 cell, from 1.086735 to 1.101905. Those diagnostics fix prey effect
at one and are distinct from the full joint profile over effect.

The first bank comparison had a particularly influential rare observation at
training site cluster_20_site_0. Compatible arrival draws increase 52, 91, 179
across the three banks. Its history probability stabilises from 0.000127666
to 0.000111202 to 0.000109041. The latest cutoff change is more distributed
across sites; it cannot be attributed solely to that one site. The evidence
supports sensitivity of tail calibration histories to finite-bank integration,
while the four-history likelihood core and primary contrasts remain stable.
Duplicating the identical 32768-draw empirical bank while merely reducing
pseudo-count weight changed the two predator-marginal truth LRs by only
0.00807 and 0.00197, compared with 0.67093 and 0.63535 when adding fresh
draws. Changing the pseudo-count is therefore not supported as the repair.

Speed intervals are discrete G201 supports. Connectivity, widths and endpoints
are evaluated on that grid; continuous-profile endpoints have not been
validated. Neither these checks nor local calibration establishes performance
under unknown detection/background or a new landscape. The usual-speed 5x
case's effect coverage was 91.6% in both analyses at the production bank;
stable paired differences do not imply nominal absolute coverage everywhere.

## Compute and provenance

The reference completed at 2026-09-06 11:35 UTC after 30965.1 campaign seconds
(8.60 hours), plus about 6.4 minutes to extend the arrival bank. All source,
profile checksum, history seed, nested seed-prefix and event-diagnostic checks
passed. Direct remote array hashes also reconciled the 16384 and 32768
prefixes of the saved 65536 bank. Frozen campaign source is
`e8c08f10f7b67118a85ee37770d8ee48ee2c213a`; the 65536 profile SHA-256 is
`68cb9acc72e07589d6ab752841dba74313a1f1d9d4a297923f560d586f07d8ad`.
The run is retained at
`/data/codex/scratch/goal045-full-bank-reference64-20260906-e8c08f1/`.
Raw profiles, banks and diagnostic arrays remain outside Git.

Applying the same conservative projection to a 131072-draw replay gives
25.34 hours, exceeding Goal 045's 24-hour boundary. Another full doubling has
not been launched. It would also provide no advance guarantee of convergence.
The current numerical gate remains unresolved.

## Independent audit and proposed amendment, 6 September

An independent scientific auditor reconstructed all 30 point contrasts and
1000-bootstrap intervals directly from each of the three profile bundles.
The saved estimates agree to numerical precision. Individual analysis-lane
metrics are stable as well as their paired differences, so apparent agreement
is not merely cancellation. Effect calibration uses its own profiles and
cutoffs; the failed rho cutoff does not define effect intervals. Effect-cutoff
movement was at most 0.00387 LR across either doubling.

The auditor's verdict is **conditionally supported for the primary paired
claim; not supported for accepted rho-interval calibration**. The recommended
amendment for Barry's approval is:

1. Retain the original 16384-draw primary result, with the complete
   16384/32768/65536 numerical-sensitivity evidence. Do not promote a larger
   bank under the failed criterion.
2. Use the claim: "Across the six frozen synthetic conditions, estimating rho
   produced no detected systematic deterioration in prey-effect recovery
   relative to supplying the true rho." Preserve the uncertainty and scope
   qualifications above. No equivalence or general recoverability claim.
3. Mark secondary rho cutoffs, interval coverage and precision numerically
   unresolved; do not present them as an accepted speed-calibration result.
4. Close the bounded bridge only after Barry approves this amendment and the
   revised report, figures and roadmap receive the final focused review.
   No further full-bank replay is proposed.

If accepted rho-interval inference is later required, a separate numerical-
method tranche should investigate independent replicated banks and rare-event
variance reduction or more direct integration. That work would need its own
scientific design and validation on untouched calibration-tail histories.

The old `bridge_complete` value is an automatic synthesis classification, not
scientific acceptance. The report generator now states that distinction and
reports actual ensemble sizes rather than labelling full reference runs as
reduced checks. The original production synthesis has been regenerated with
this wording; numerical outputs are unchanged.

The two-hour heartbeat is paused at this human scientific gate. Goal 045 remains
open. This amendment is proposed, not approved: Goal 045 requires both numerical
criteria to pass under the current contract, and its authority section reserves
material scientific changes and projected runs over 24 hours for Barry.

## Reassessment after explicit compute approval, 7 September

Barry authorized the projected 25.34-hour doubling on idle deep-server if useful.
The independent auditor and parent now recommend **one final 65536/131072
reference**. The earlier recommendation weighed the original compute boundary;
the two observed, correlated nested differences do not prove persistent bias.
Another doubling can test the original secondary-rho objective under the same
criteria, though it cannot guarantee convergence or establish universal
Monte Carlo accuracy.

A pass of both the original four-history canary and the full-ensemble criteria
would support a documented 65536 bank amendment and final synthesis/review.
Any failure ends automatic bank doubling for this goal; no 262144 replay or
relaxed tolerance is authorized. The primary-only closeout proposal would then
return for Barry's scientific decision. Original failing evidence is preserved.

The wrapper appends eight 8192-draw chunks to the exact existing 65536 prefix,
then invokes the unchanged frozen campaign. The scientific design, seed streams,
grids, calibration rank and acceptance limits are unchanged. A cheap diagnostic
of the disjoint 32768 halves characterizes numerical variation and does not
select the launch or acceptance outcome.

Runner SHA-256:
`c5bfd9b5758ae56d1c252bdde2cb14f27ace85344c4bc05d4382e9e4022f0eb7`.
Wrapper SHA-256:
`18ed36bc6cdb7c8c860e41f510c0671b7936c93c2eb4429d45936c28d9558511`.
Syntax/Ruff checks and exact four-draw serial/spawn equivalence passed locally
and on deep-server before launch.

The [disjoint-half diagnostic](half-bank-predator-diagnostic.json) reproduced
all prior tail values exactly. The two 32768 halves differ by 1.37119 and
1.32924 LR at generating rho for histories 198 and 221, while near-peak profile
changes within union LR<=10 are only 0.33648 and 0.33273. The pooled 65536 values
lie between the halves. These are fixed-history numerical comparisons, not
independent biological replications, and they do not predict the next direction.

The final reference launched at 2026-09-07 02:10:12 UTC under
`/data/codex/scratch/goal045-full-bank-reference128-20260907-e8c08f1/`, with
frozen inputs verified and all eight extension workers running. The two-hour
heartbeat is active again. The original scientific question and review gates
remain in force; no larger bank has been promoted.
