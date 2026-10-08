# Goal 046: uniform K32768 escalation

At 10:49 UTC on 8 September, the first three full production ensemble reviews
were returned and independently recomputed locally. Barrier maps 2026090811
and 2026090812 fail the unchanged support-boundary classification criterion.
The third barrier map passes its ensemble review; half-grid checks are still
running. The current global K16384/32768 setting cannot be accepted.

For map 2026090811, the supplied-speed access onefold lower-boundary flag and
balanced fivefold upper-boundary flag change. For map 2026090812, the supplied-
speed access threefold lower-boundary flag and access fivefold upper-boundary
flag change. All other criterion families pass for these maps. The differences
are small numerically but exceed the declared requirement of unchanged boundary
classification. Their failed receipts and raw evidence are retained under
`artifacts/goal046_execution/production16384-v2/`; the first three local replay
receipts are indexed by `first-reference-return-check.json`.

Three further returned references were also reproduced locally. Connected
2026090813 changes the estimated-speed balanced onefold lower-boundary flag.
Corridor 2026090813 changes the supplied-speed access threefold lower-boundary
flag. Corridor 2026090811 changes the supplied-speed balanced threefold lower-
boundary flag and changes exclusion, including its paired sampling contrast,
by two histories; only one is permitted. Thus five of the first six completed
maps fail. The remaining original results continue to be recorded independently.

The final nine-map ensemble check has seven failures and two passes (connected
2026090811 and barrier 2026090813). Connected 2026090812 also changes coverage/
exclusion counts and paired contrasts by two histories. Corridor 2026090812
moves generating-rho LR by up to 0.797754, exceeding 0.5, as well as changing
a boundary flag. All nine comparisons are reproduced locally with exact
agreement in [the compact receipt](initial-production-ensemble-check.json).

## Approved continuation

Apply the already-approved ladder uniformly: K32768 selected and K65536
reference for all nine maps, with every scientific setting and numerical limit
unchanged. The next freeze is [production-freeze-k32768.json](production-freeze-k32768.json).
It differs from the original freeze only in the selected and reference bank
sizes. This is a candidate requiring production qualification, not an accepted
numerical setting. Original sacrificial qualification provenance is retained.

Reuse each completed original K32768 reference as the next selected input.
An independent methodological review supports this because it is the same
numerical calculation and the full history ensemble already exists. Do not
rewrite its original freeze, source provenance, role, summary or seed receipts.
A separate hash-bound adoption receipt must identify the old and new freezes,
source roots, original bundle files and the new selected role. Both numerical
checkers must explicitly validate adoption and retain its provenance in their
reports. Directly compare the actual K65536 bank prefix and history seeds to
K32768. Every selected K32768 map must still undergo full replay and separate
half-grid checks; K16384 half-grid results do not transfer.

The campaign source is a byte-identical copy of the original 82-file snapshot,
SHA256 `6ee147ed17b3324bc2c432b9a1ce7f686f527417f9abb9fa290cea05c53e4c87`.
Review-only adoption support is packaged separately, with its own hashes.
Source comparisons may strip verified absolute source-root prefixes, requiring
identical relative-source-path to hash mappings. They must not compare only
basenames or discard unrelated metadata differences.

The original per-map work finishes before that map starts its K65536 campaign,
so there are at most nine active map calculations across both batches. The new
watchdog must count both process groups while they overlap. Each retains a
10 GiB address-space cap and four workers with native library threads one.
The common deadline remains 2026-09-09 00:35:54 UTC. Reusing K32768 avoids
approximately 3.5–4 hours of repeated calculation; K65536 plus final K32768
half-grid checks is still a planning estimate, not a completion guarantee.
A resource ceiling or further unresolved numerical failure remains reportable
evidence and cannot justify relaxing thresholds or omitting maps.

## Dispatch and review

The successor was queued at 11:13:09 UTC under
`/data/codex/scratch/goal046-production-20260908-k32768/`, PID/group 38737,
with 48165 seconds remaining. Its nine queues and source verification passed;
at startup they were waiting for their respective original half-grid reviews.
The original group 30177 was confirmed immediately before launch.

Independent review of the concrete launcher, process gating, combined memory
monitor and adoption method found no material issue after a receipt-field
mismatch was repaired. The final 19-test Linux preflight passed in 93.56 seconds,
including real reduced campaigns passed through both adoption-aware checkers
with neither input bundle modified. Local tests, scoped Ruff and strict mypy
also passed. Review and dispatch source are bound by `REVIEW_SNAPSHOT.json`
SHA256 `52ee6a6b1976f7f4dbde257e47c533a0031e6baf2b3b9f87ade955dde0f176cc`.
These checks validate the implementation and provenance route; they do not
qualify the pending K32768/65536 scientific evidence.

By 12:48 UTC all original map reviews had finished and all nine successors
were active. The original half-grid checks pass 213 of 216 rows; the three
failures reproduce corridor 2026090812's generating-rho LR instability.
Every returned row, hash, saved/replayed surface and retained grid node was
independently verified. The [half-grid receipt](initial-production-halfgrid-check.json)
and original batch exit 1 retain that result. Final K32768/K65536 qualification
remains pending; these completed K16384 checks do not replace it.


## First production results at the escalated pair

At 18:55 UTC the three barrier K65536 campaigns were complete. Their returned
bundles, immutable adoption receipts, source manifests and all ensemble metrics
are verified, with exact local numerical replay. Barrier 2026090811 changes
the estimated-speed access fivefold upper-boundary and balanced threefold
lower-boundary classifications; it fails the frozen criteria. The other two
barrier maps pass their ensemble comparisons. All three selected-K32768
half-grid reviews and six other campaigns continue under the original timeout.

The global K32768/65536 setting is therefore rejected. No K131072 campaign is
launched because it cannot fit the remaining window. The independent reviewer
supports the [24-hour extension proposal](resource-extension-proposal.md).
The completion heartbeat is paused pending Barry's decision, with no change
to the existing jobs' deadline or to any scientific/numerical criterion.
