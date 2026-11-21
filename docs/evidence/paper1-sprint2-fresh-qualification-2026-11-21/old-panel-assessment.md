# Old-panel evidence before fresh Sprint 2 qualification

21 November 2026. Development evidence for the Sprint 2 numerical qualification decision under Paper 1 charter pillars 3, 4 and 6. No new fits, likelihood evaluations, numerical audits, histories or draws were run.

**The frozen reducer has a common-anchor precondition that the planned audit cannot satisfy for most observed dense/lean pairs.** It checks for five exact nodes shared by the original fit profiles before it examines the audit sidecar. A sidecar with valid evaluations of the entire exact union cannot clear this precondition. Among the old original panel's 168 resolved dense/lean pairs, 159 miss the minimum in both spatial regimes. The same happens in 9 of 10 resolved dense/lean pairs from the source accepted on 21 November. This is a pre-draw issue in the evidence rule. With the current reducer, successful fits and audits can still leave the panel indeterminate. [Frozen rule](../../../scripts/summarise_sprint2_qualification.py) · [Audit producer](../../../scripts/audit_sprint2_pair.py)

The archived panel does not identify a check-level failure rate for source `432bb6e`. The original panel has 14 known failed cases and no fully assessed passing case. The selected `432bb6e` replay has one known failed case and nine cases with every required fit resolved. The single failure among the original 207 IDs quoted on Correspondence 3617 is the fit-only lower bound after filling the remaining roles with old-source results.

## Census by provenance

Each case table entry is **all required fits resolved / known fit failure / fit outcome unknown**, deduplicated over roles. A case with every required fit resolved still needs its check evidence.

| Old-panel evidence | Terminal roles (resolved / failed) | Missing / outside replay | Base (162) | Boundary (18) | Enriched (18) | Trend (9) | All (207) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original `99af520` | 417 / 27 | 42 / 0 | 131 / 10 / 21 | 15 / 0 / 3 | 15 / 2 / 1 | 7 / 2 / 0 | 168 / 14 / 25 |
| 15 November `a77e849` as originally adjudicated | 47 / 2 | 2 / 435 | 5 / 1 / 156 | 0 / 0 / 18 | 1 / 0 / 17 | 2 / 0 / 7 | 8 / 1 / 198 |
| 21 November `432bb6e` | 49 / 2 | 0 / 435 | 6 / 1 / 155 | 0 / 0 / 18 | 1 / 0 / 17 | 2 / 0 / 7 | 9 / 1 / 197 |
| Mixed overlay, replacing the 51 replayed roles with `432bb6e` | 442 / 2 | 42 / 0 | 140 / 1 / 21 | 15 / 0 / 3 | 17 / 0 / 1 | 9 / 0 / 0 | 181 / 1 / 25 |

The original 486 roles comprise 396 base and 90 non-base. Their resolved / failed / missing counts are 340 / 20 / 36 and 77 / 7 / 6, respectively. In the mixed overlay those counts are 358 / 2 / 36 and 84 / 0 / 6. The 42 original missing roles comprise 22 dense, 15 lean, two independent-bank and three exhaustive. All 42 have partial evaluation streams. Eighteen ended with a numerically resolved search receipt and no terminal fit. Twenty-four lack a terminal search receipt. The frozen fit plan and old reconciliation identify all 42 as missing. The preserved accounting records a mixture of walltime and node losses and does not assign a verified interruption cause to each role. All companions of the 14 original scientific failures have terminal fit receipts.

The replay selected 24 originally resolved comparison roles and all 27 originally failed roles, covering 35 case IDs. The 21 November source resolves 25 of the 27 previously failed roles. The residual dense and lean failures both concern corridor-1 window-low B and trip the envelope guard. Two separate 21 November continuations resolved the missing 15 November roles at `a77e849`. Those receipts do not revise the 15 November decision. In the mixed overlay 172 datasets use only original roles, ten use only candidate roles, and 25 require roles from both sources. Its 181 resolved dense/lean pairs include 14 cross-source pairs. Its 52 resolved bank pairs include eight cross-source pairs. The paired audit requires equal source identities. [Original rejection](../paper1-sprint2-failure-2026-11-12/README.md) · [15 November decision](../paper1-sprint2-repair-2026-11-15/README.md) · [21 November acceptance](../paper1-sprint2-acceptance-2026-11-21/README.md)

| Map | Original base (18) | Original non-base (5) | Candidate base (18) | Candidate non-base (5) | Mixed base (18) | Mixed non-base (5) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| barrier-0 | 12/0/6 | 3/0/2 | 0/0/18 | 0/0/5 | 12/0/6 | 3/0/2 |
| barrier-1 | 15/0/3 | 4/1/0 | 0/0/18 | 1/0/4 | 15/0/3 | 5/0/0 |
| barrier-2 | 11/0/7 | 5/0/0 | 0/0/18 | 0/0/5 | 11/0/7 | 5/0/0 |
| connected-0 | 17/0/1 | 5/0/0 | 0/0/18 | 0/0/5 | 17/0/1 | 5/0/0 |
| connected-1 | 18/0/0 | 4/1/0 | 0/0/18 | 1/0/4 | 18/0/0 | 5/0/0 |
| connected-2 | 13/4/1 | 2/1/2 | 3/0/15 | 1/0/4 | 17/0/1 | 3/0/2 |
| corridor-0 | 16/1/1 | 5/0/0 | 1/0/17 | 0/0/5 | 17/0/1 | 5/0/0 |
| corridor-1 | 15/3/0 | 4/1/0 | 2/1/15 | 0/0/5 | 17/1/0 | 5/0/0 |
| corridor-2 | 14/2/2 | 5/0/0 | 0/0/18 | 0/0/5 | 16/0/2 | 5/0/0 |

## What the saved checks establish

The live original target contained plans for banks, histories and fits. No common-anchor, gradient or integration phase plan or matching task paths were found. No archived gradient sidecar or integration screen was found for the repair sources. The 21 November anchor probes compare one old fit role to its replay at the specific archived locations selected for source non-regression. The Sprint 2 gate compares independently fitted roles at the pair's exact union under one source. Its gradient check needs the raw derivative at the selected free solution and an independently reoptimised stencil at two step sizes for each spatial regime and search. The selected optimiser endpoint, projected gradient norm and profile rows do not supply those stencil evaluations. Integration requires nine separately bound screen receipts. Eight original selected lean fits resolved and one failed scientifically. The archive contains zero screens, including zero explicit unavailable-scientific-fit receipts. [Frozen phase design](../../paper1-sprint2-entry-2026-11-06.md) · [Gradient and anchor producer](../../../scripts/audit_sprint2_pair.py) · [Integration screen](../../../scripts/screen_sprint2_importance.py)

| Prerequisite and archived result | Original | 21 November repair |
| --- | ---: | ---: |
| Dense/lean pair with both fits resolved | 168 | 10 |
| Of those, fewer than five exact original profile nodes shared in each spatial regime | 159 (124 base, 35 non-base) | 9 (7 base, 2 non-base) |
| Of those with both fits resolved, gate-ready full pair from fit records | 0/168 | 0/10 |
| Bank pairs with both fits resolved | 50 | 2 |
| Gate-ready full bank pair from fit records | 0/50 | 0/2 |
| Bank identity verification from saved manifests and payloads | 49/54 | Two same-source pairs use the verified old banks |
| Exhaustive role check, resolved and passing | 14/18 | 7/18 |
| Exhaustive role check, terminal scientific fit failure / missing / outside replay | 1 / 3 / 0 | 0 / 0 / 11 |
| Final fit evaluation streams passing the archive hash check | 444/486 | 51/486 |
| Gradient sidecars | 0/207 | 0/207 |
| Integration screen receipts | 0/9 | 0/9 |
| Complete cases under frozen `assess_case`, all scientifically failed | 14/207 | 1/207 |
| Complete passing cases | 0/207 | 0/207 |

Every resolved pair also lacks some cross-side locations in the original archived profile rows. The exposure and constant fits have no per-coordinate evaluation stream for those locations. The original dense/lean pair for `q-base-connected-0-constant-mu0.001-h1-B` provides a specific numerical discrepancy in exposure. Among its 35 exact shared exposure nodes, the greatest difference in own-free-normalised W is 0.15654424, above the 0.01 tolerance even allowing both original rows the sidecar's 1e-8 preservation tolerance. This is a failure witness under the original source. The frozen reducer returns `indeterminate` for the pair because the four views cannot meet their node requirements. The case is also in the mixed overlay, where it retains both original fits.

The spatial-shared-node issue begins with independently generated 35- and five-point meshes in log-h. Dense midpoint arithmetic can generate mathematically coincident nodes without producing the same binary64 values. For each spatial regime the original resolved pairs' exact-shared-node counts are 58 with two, 76 with three, 25 with four, seven with five and two with six. For `432bb6e` they are three, two, four, zero and one, respectively. All 50 original bank pairs share at least six original spatial coordinates because both use lean search, yet every one still needs cross-side checks.

| Map | Original base pairs below five / resolved | Original non-base pairs below five / resolved | Candidate base pairs below five / resolved | Candidate non-base pairs below five / resolved | Original bank identities verified / selected | Original exhaustive checks passed / selected | Original guard streams verified / required |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| barrier-0 | 11/12 | 3/3 | 0/0 | 0/0 | 2/3 | 2/2 | 39/51 |
| barrier-1 | 15/15 | 4/4 | 0/0 | 1/1 | 6/6 | 0/2 | 47/54 |
| barrier-2 | 11/11 | 5/5 | 0/0 | 0/0 | 5/6 | 1/2 | 42/54 |
| connected-0 | 15/17 | 4/5 | 0/0 | 0/0 | 0/0 | 2/2 | 47/48 |
| connected-1 | 18/18 | 4/4 | 0/0 | 1/1 | 9/9 | 2/2 | 57/57 |
| connected-2 | 13/13 | 1/2 | 3/3 | 0/1 | 9/9 | 2/2 | 52/57 |
| corridor-0 | 15/16 | 5/5 | 1/1 | 0/0 | 5/6 | 1/2 | 52/54 |
| corridor-1 | 14/15 | 4/4 | 2/2 | 0/0 | 5/6 | 2/2 | 54/54 |
| corridor-2 | 12/14 | 5/5 | 1/1 | 0/0 | 8/9 | 2/2 | 54/57 |

The target independently hash-verified all 444 surviving original terminal fit evaluation streams. They contain 18 unresolved-fit events, including 16 with no eligible endpoint in at least one variance family. Two high-sigma-anchor candidates and one other offending candidate come from the known corridor-1 window-low B failure. The 51 candidate streams show the same counts of offending candidates in that case. Bank identity is independently verifiable without fitting. The target verified 49 selected case bindings through the frozen bank verifier. For the remaining five, three scientific fit failures made dependent checks inapplicable and two cases lacked a required bank fit. The original reducer reports `incomplete` for both the numerical decision and packet, with all nine screens missing.

## Identifiable bounds and decision

The fit-only bound over original IDs is 14–39 failures out of 207, with 10–31/162 base and 4–8/45 non-base. The known original base failure mean is already 10/162 = 0.06173, above 0.05 before the dispersion term. Seven of 108 A/B base cases already fail. The original panel therefore cannot pass either route even if all missing checks succeed. The exposure discrepancy supplies one further original base failure witness under the registered tolerance.

For the 21 November source alone, the source-specific fit-only bounds over all old IDs are 1–198/207, with 1–156/162 base and 0–42/45 non-base. The mixed fit-only bounds narrow to 1–26/207, with 1–22/162 base and 0–4/45 non-base. The check-level upper bound on potential failures is the entire panel for each provenance because the archive establishes no complete passing case. The complete scientific failure rate conditional on complete assessed cases is uninformative: a terminal fit failure is what allows the reducer to skip absent dependent checks.

The frozen gate cannot be made ready by filling only the fit gaps. Review the implementation of the five-common-node rule against its intended scientific requirement before drawing. Counting at least five verified eligible exact common evaluations, including both endpoints, from a fully validated exact-union sidecar would preserve a common-node check without relying on incidental floating-point coincidences in the adaptive searches. That interpretation needs reciprocal review before adoption. The observed panels do not support replacing the assumed 60–80% fresh-pass range with an empirical probability.

## Reproduction

The panel SHA-256 is `51006aa0355ab4ce9f28e572a4272f09c0dc9fcdb52ae6ed0570aacbb1cf240d`, original fit plan SHA-256 is `09a42f38f1d579119afdd3b7b53bec0a968e269fc16fc48e426310e66e86a042`, and frozen reducer SHA-256 is `4f138512341825dbe348a227a4a9ac769707e38eb091e17ea14557f536563439`. The original, early repair and accepted candidate use the same reducer bytes.

The exact case and role census, per-view feasibility checks, failure witnesses and reducer decisions are in the ignored `old-panel/reconciliation.json` output. Run the reader from the repository root with the archived old fit/search receipts unpacked into `original-results` and the bulk 21 November packet unpacked at its existing ledger paths.

```sh
work=artifacts/sprint2/fresh-qualification-20261121
tar -xzf "$work/pre-draw-evidence.tar.gz" -C "$work"
tar -xzf "$work/pre-draw-inputs.tar.gz"
out=artifacts/sprint2/fresh-qualification-20261121/old-panel
mkdir -p "$out/original-results"
tar -xzf "$out/original-fit-receipts.tar.gz" -C "$out/original-results"
.venv/bin/python docs/evidence/paper1-sprint2-fresh-qualification-2026-11-21/old-panel-audit.py \
  "$out/reconciliation.json" --original-results "$out/original-results"
```

The independently verified private archives include the full local census, the target reducer output, the historical fit/search receipts, the supporting November 7 and 15 records and the selected replay's safeguard extraction. The target reader uses the original large evaluation streams and raw bank arrays at their preserved paths. [Bulk archive ledger](../../bulk-receipts.sha256) · [November 21 acceptance archive restoration](../paper1-sprint2-acceptance-2026-11-21/README.md)

The separate target reader `old-panel-target.py` takes the original results directory as its sole argument. Run from the original source checkout with the pinned runtime. It calls the complete frozen reducer at the real paths so that saved evaluation streams and bank payloads can be verified in place. It constructs the bank-reference bindings from the existing immutable task-output hashes. The resulting ignored `original-reducer-on-target.json` has SHA-256 `eeb1fa3a8ae5a639c4bce63e8b4a011b632c97418bb765059d2fe1bc10ef3cbc`. All 444 original fit receipt hashes and 207 case outcomes match the local reconstruction. The reader performs no anchor, gradient or screen evaluations.

Next: Claude — review the common-anchor requirement before a fresh draw.
