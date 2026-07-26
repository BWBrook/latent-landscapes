# Goal 005 Log

## 2026-07-26: Goal Authorized

Barry approved a cross-rate stress test of the accepted stochastic one-rate
benchmark before any second spread parameter is introduced.

The generating rates are frozen at `0.5`, `1`, and `2`. The Goal 004
landscape, process, sampling design, calendar, detection model, likelihood,
candidate grid, integration-bank size, replicate counts, neutral comparator,
and decision thresholds remain fixed.

Goal 005 distinguishes locally calibrated recoverability from transport of
the `rho = 1` cutoff. Sparse or saturated flank data and cutoff
nontransportability are valid outcomes. No Goal 005 production run, fitting,
generated artifact, commit, push, or Goal 006 work had started when this
contract was frozen.

## 2026-07-26: Implementation And Production Result

The cross-rate orchestration was implemented without modifying Goal 004. The
shared integration bank is reconstructed from the frozen Goal 004 seed tree;
flank calibration and validation streams use disjoint phase roots from
`SeedSequence(20260729)`. Candidate rates use the exact frozen grid, so the
same bank represents `T(rho) = T(1) / rho` through candidate-rate scaling.

Focused Goal 005 tests passed (`6` tests). The canonical production command
completed in `280.09` seconds and the deterministic repeat completed in
`281.78` seconds. Both wrote exactly 15 files and `diff -rq` reported no
differences. The verification payload reports all invariants true; generated
artifacts and build outputs remain ignored and unstaged.

The completed outcome is `one_rate_recovery_robust_cutoff_nontransportable`.
Local full-bank coverage was 0.964 at `rho = 0.5`, 0.936 at `rho = 1`, and
0.954 at `rho = 2`; all three local full-bank support topologies were 500/500
interior. Local paired Brier intervals were wholly below zero at every truth.
Applying the `rho = 1` full-bank cutoff to the flanks produced coverage 0.978
at `rho = 0.5` and 0.980 at `rho = 2`, with Wilson intervals entirely above
0.95, so transport is conservatively over-covering and not operationally
portable.

Observation signal summaries are aggregated by truth rate and survey time
with central 90% intervals. Representative profiles use actual local
cutoffs. The fitted object remains a site-history simulated composite
likelihood, not a full joint spatial likelihood; between-site process
dependence is omitted. The result is conditional on the frozen landscape,
calendar, detection model, and one-rate parameterization.

The final focused audit repair made three contract corrections: local
validation rows now identify their own truth-rate cutoff source; transported
rows are labelled diagnostic rather than as local calibration classes;
detection fractions use all 320 visit records per survey time while occupied
fractions use one value per site. Frozen Goal 004 reconciliation now gates
cutoff, coverage, topology, boundary contacts, paired-Brier interval, and
bank-class/overall-class agreement. The canonical and repeat packs above are
the post-repair pair.

Final validation after the repair passed:

- `git diff --check`;
- focused Goal 005 tests: 6 passed;
- Ruff formatting and lint checks;
- mypy across `src` and `tests`: 44 source files;
- full pytest suite: 110 passed;
- source distribution and wheel build; and
- independent final scientific/code/artifact review: `ACCEPT`.

Canonical artifact SHA-256 values:

```text
559ebe42d35d671f26066ef8cec5121b02585fc737a5bca46de189c3ef4ccc9b  calibration_results.csv
8de27348f47c8222a8f6589e8e37d5fa5e3cf7bdfdff94d167fe99b7d61af19c  config.json
f01c0724d25c2e06aa5c8df29691d927a739d3b5694973d6e85ba184d1b55b48  observation_signal_summary.csv
351f6a128531e6040077e1b83d0daa6c3360fe3a342155aab608ae8a818843c6  predictive_summary.csv
9bd1f5cfbe101b4a0a58000b60a56c1798c120865027fecd537549b2f3b4fa7a  rate_summary.csv
0b02fe6fc1bbca24ffe48c9c323766e138a4bfb122cb9e62dfed532aed88f484  representative_profile.csv
2fcfdd4e73142bac8d88fa3b6761fbf432beca4d251b8f869ec52cfb711a7a83  review.md
8f383c64357c5e628931550e1774b5d9d8a4abace6f959fdaebe10c044607a3a  seed_manifest.csv
c41b7a12724ab1b5828501d73dab1b40deac3db18339e8957851d8d699055e12  summary.json
62b7792bca21a0aa7881109040de2d83c6dc7232ccf69c3e2d44b719be7103b2  transported_cutoff_summary.csv
af5b30aafe5d29f644c6a7179bee1d81d07536e5c1833ad44e9cc0ddc8cee9a4  validation_results.csv
99ddf1f86b3e05db8f9d6971bfb54baa7e1f9b1838c1fcdea2abffd8b248bdd3  verification.json
2cc89e354c9f701c1408c82dbfa25401a1c4e22dc3d595f853705ab8d92f988b  visuals/cutoff_transportability.svg
8140637c3c6c2eb70734ddea547d500a32ed5bdd1af8c012ae3bd4348cc133a2  visuals/local_recovery_across_rates.svg
28763a2255896a8ddafe4d201f6bfc9f498ab3bf52c18f5113c68533cec8304b  visuals/predictive_comparison.svg
```
