# Latent Landscapes: current handover

31 October 2026 (Hobart), direct likelihood and completed numerical meshes.

The [direct-profile record](docs/paper1-direct-profile-development-2026-10-31.md)
reports stable differentiable scoring of the unchanged empirical-plus-seven-
pseudo arrival law, with no hazard cap or smoothing. Independent review and
167 focused tests support the kernel and guarded Newton-first mode solver.
Both B_H3 and H3 now resolve all 35 mesh nodes in both variance families,
with interior free optima h=4.19518 and 2.34622. All retained positive-profile
points agree with the original solver under the recorded numerical gates.

The traversals took 25.86 and 15.91 minutes on single-thread Mac mini processes.
This clears the previous finite-mesh arithmetic/support failure; it does not
qualify continuous confidence sets, independent-bank precision, global modes,
Laplace accuracy, 260-site behaviour or campaign throughput. The evidence
preserves an unsuccessful intermediate acceleration and an explicitly reviewed
engineering call-target miss. A pre-existing free-h30 rounding defect remains
recorded for a targeted fix before boundary-case qualification; fixed-h30
nodes and these interior free optima are unaffected. Goal 062 stays closed.

Next: repair that endpoint transform, qualify independent-bank sensitivity
and continuous profiles, then assess higher-accuracy integration and the
broader challenge suite. Further runtime work remains necessary.

Barry selected **broader first**: landscape generality and common competing
background models belong in one substantial Paper 1. The
[reviewed protocol](docs/paper1-integrated-tranche-protocol-2026-10-18.md)
combines six backgrounds, three paired monitoring arms and common fitted
models. Claude–Codex review has settled the map-stratum mean error target,
precision rule, six-point effect truth grid, fitted h domain [1,30], and the
bootstrap declaration/truth-inclusion comparison. R3 is dropped. The protocol
is a development specification, **not a registered production experiment**.

The [numerical development record](docs/paper1-numerical-development-2026-10-18.md)
reports the corrected complete-data frailty check on 4,000 archived histories,
the first observed-data spatial prototype, and a verified stopping rule for
fixed-cap bootstrap decisions. The frailty result is selective: cluster
frailty helps in the high-hazard heterogeneous cell, while independent Gamma
frailty inflates effects. A survivor-selected pilot cannot establish the
baseline-monitoring comparison. All four spatial endpoints now pass independent
gradient, direct-likelihood and grid-refinement checks. The repaired local fit
pairs took 313 and 440 seconds; full-profile accuracy, Laplace approximation
and campaign efficiency still need qualification.

The new [profile-engine development record](docs/paper1-profile-engine-development-2026-10-18.md)
adds analytic Laplace derivatives, a bidirectional profile search, explicit
predator-visit missingness and a nested monitoring-panel sampler. Independent
review found and prompted repairs to training-site selection, calendar checks,
near-stationary mode convergence and profile reporting. The first 35-node
spatial mesh traversal took 190.73 seconds on one Mac mini thread and recovered
the earlier optimum, but positive variance resolved at only 18 nodes because
the interpolation support was too narrow. It is not a qualified full profile
or evidence that the six-model 20-second target is achievable.
Wider-grid canaries then exposed probability underflow, reproduced by direct
integration. The single reviewed intermediate grid also failed: h=30 could
not retain the required support margin, and h=6.05348 missed the gradient
threshold. **This historical stopping point is superseded by the 31 October direct-profile
record above.** Stable scoring and two full mesh traversals are now complete;
the 600-case qualification suite remains unrun. The exact
failures, source snapshots and independent review are archived with the record.

The amended two-cell access buffer and joint 300-site master-panel selection
passed all 30 prespecified map-capacity checks. The seeded selector also passed
on all three pilot archetypes; biological histories have not yet been generated
on those new panels. The 600-case plan is now a finite challenge suite with
separate numerical and integration-sensitivity checks, not a population-level
99% subgroup-agreement guarantee.

The immediate work is to qualify the spatial criterion and whole effect
profiles across difficult cases and both site counts, then freeze the
executable design before rule training and untouched validation. The 90-map
scenario is a minimum-count
illustration; precision, rather than an arbitrary resource ceiling, sets the
final allocation. The [initial plan](docs/paper1-integrated-tranche-planning-2026-10-18.md)
and [iteration-2 review](docs/paper1-design-model-review-2026-10-18.md) preserve
the earlier recommendations and authority state.

Current repository guidance routes scientific gates through independent AI
review and permits coherent commits/pushes to the existing private remote.
Barry's standing two-way-door instructions support this reversible numerical
work. Publication and other one-way doors retain explicit human review.
Goal 062 and the original blinded capstone remain complete and closed.
The following closure and operational records are preserved history.

## Preserved Goal 062 closure

16 October 2026 (Hobart), Goal 062 complete, independently reviewed and returned.

**The ten-cell final-procedure campaign is complete:** 5,000 histories,
20,000 main fits, 5,000 audited declarations, 5,000 audited held-out scores,
and all 50 prespecified diagnostics. The [report](docs/goals/062-final-procedure-evaluation/report.md)
records all cells and uncertainty; the [independent closure review](docs/goals/062-final-procedure-evaluation/final-review.md)
records the arithmetic and interpretation checks. Exact-family h=3 declaration
rates are 44.4% and 90.8% at mu=.001 and .004/day, with within-1.5-fold recovery
55.0% and 83.2%. B100-A h=3 declaration rates are 45.6% and 77.6%, alongside
matched null rates 2.6% and 0.6%. These are conditional, fixed-design results.
No abstentions, unavailable h estimates or registered main-fit warnings occurred.

The approved repair continuation finished at **16:37:31 AEDT on 15 October**,
exit zero with no resource stop or remaining workers. It used 40 workers,
45 minutes 33 seconds and peak aggregate RSS 25.05 GiB. The original production
attempt had already completed the 466 missing reference tables and 5,000 main
bundles; its failed rank-audit receipt is preserved. The complete 765-table
cache and all seed addresses are unchanged. The continuation root is
`/data/codex/scratch/goal062-final-procedure-20261015-rank-repair1`.
Do not relaunch completed work.

All **76,283 returned files** passed checksum verification on the Mac mini;
all 466 new raw reference databases were rechecked and remain on Deep.
Local raw return: `artifacts/goal062_execution/completed-20261015/snapshot/`.
[Closure provenance](docs/goals/062-final-procedure-evaluation/results/closure-provenance.json)
links source, runtime, approval, qualification, archive and result hashes.
Independent reconstruction reproduced all 2,150 summary comparisons and
20,000 bootstrap streams, with no discrepancies; the parent separately
reconstructed headline counts and Wilson intervals.

Deep rebooted safely and was verified at **07:06 AEDT on 16 October**, now on
kernel **6.8.0-147**. SSH/Tailscale, `/data`, campaign hashes and essential
services recovered; both idle development containers were restored. Reboot
markers are clear. The 15-hour heartbeat is **paused**. The
[reboot receipt](docs/goals/062-final-procedure-evaluation/results/reboot-receipt.json)
and [execution record](docs/goals/062-final-procedure-evaluation/execution.md)
preserve the checks.
Barry's [15 October authority](docs/decisions/2026-10-15-goal062-source-amendment-approval.md)
continues to cover proportionate operational fixes and sensible compute
choices. Material science, scope and external commitments retain review.

**Next scientific boundary:** this closes the registered fixed-design
operating-performance experiment, not the full Paper 1 charter. Landscape
generality, a common competing-process candidate set, and effect-magnitude
interval coverage remain separate decisions in the
[roadmap](docs/paper1-adaptive-implementation-roadmap.md). No new experiment is
launched by this handover.

The following launch and 14 October progress record is preserved history;
its original running status is superseded by the completed campaign above.

Barry selected **amend, independently review, then launch without returning**
in [Decision Inbox](docs/decisions/1c886620-8524-4d69-8585-3b5ef960bea3.md)
and confirmed the approval in chat. The [amendment](docs/goals/062-final-procedure-evaluation/amendment-2026-10-11.md)
adds B100-A h=1/3 at both mu levels: **ten cells, 500 independent histories
per cell, 5,000 total**. No h=2 cells are authorized. The
[independent amendment review](docs/goals/062-final-procedure-evaluation/amendment-review-2026-10-11.md)
conditionally supports the design with no outstanding document correction.
The original registration, estimate and review are preserved unchanged.

The [amended compute estimate](docs/goals/062-final-procedure-evaluation/compute-estimate-amended-2026-10-11.md)
is **46–57 hours**, including the unchanged 465,534 new effect-reference
histories, at up to 51 deep-server workers. The 64 GiB RSS, 50 GiB free scratch
and **72-hour ceiling** remain binding. Implementation, qualification, the
bounded run and audit are one approved tranche; scientific changes or envelope
increases return for a decision. B100-A rates remain descriptive outside the
nominal guarantee; beta error and true-node retention are not applicable.

Implementation and the independent audit adapter have passed
[source review](docs/goals/062-final-procedure-evaluation/implementation-review-2026-10-11.md).
[Qualification 2](docs/goals/062-final-procedure-evaluation/execution.md)
passed on Deep in 25 minutes: 65 focused Linux tests, inherited-reference and
public-fixture comparisons, all ten mechanical cells, diagnostics, the workload
projection and the 51-worker memory probe. Qualification 1 was stopped and
preserved as superseded evidence. [Independent receipt review](docs/goals/062-final-procedure-evaluation/qualification-review-2026-10-11.md)
supports acceptance with no required repair or repeat qualification. Barry
[approved the exact runtime and launch](docs/decisions/2026-10-13-goal062-runtime-approval.md)
in this chat on 13 October: “Approved, proceed.” That direct approval is
authoritative; the unsubmitted Decision Inbox form is not a remaining gate.
The kernel remains 6.8.0-146, and the complete runtime, source, qualification
and inherited custody were reverified unchanged before launch.

Production started at **22:51 AEDT on 13 October** (11:51 UTC), with 51 workers
on Deep under the qualified process-group supervisor. Its persistent deadline
is **22:51 AEDT on 16 October**. The 27,000 evaluation-stage and 20,000 bootstrap
addresses are frozen and all 47,000 seeds are unique. At **14:27 AEDT on
14 October**, 441,510 of 465,534 new reference histories were checkpointed
(94.8%); 415 of 466 new tables were complete and the final 51 were underway.
Reference audits and evaluation had not started. All 51 workers were active,
using 21.13 GiB aggregate RSS. Evaluation histories wait until all 765 reference
tables are complete and independently audited. No operating-rate result is available.

The remote root is
`/data/codex/scratch/goal062-final-procedure-20261011-qualification2`,
production attempt `001`. Initial supervisor PID is `280990`, process group
`280991`; verify current identities before acting. The thread heartbeat runs every 15 hours;
`goal-062-campaign-follow-through` continues monitoring, audit and reporting
within the approved envelope, with notifications only for meaningful changes
or required action. Do not launch a duplicate campaign or reset its deadline.
The measured workload gate is 40.579 hours and the whole-qualification RSS
peak is 28.78 GiB. Retain the approved 46–57-hour planning allowance and the
unchanged 72-hour ceiling. Implementation is committed and pushed as `2d4a04b`.
Current execution and approval details are in the linked records and
`artifacts/goal062_execution/`.

Barry authorised a **post-run Deep reboot** in chat on 14 October. Complete
the campaign and remote audits, return and checksum the required outputs,
and confirm no other active work would be interrupted before rebooting.
Preserve the original runtime evidence and verify access, `/data`, the running
kernel, reboot-marker state and essential services afterward. The pending
update is kernel 6.8.0-147; the campaign still runs under qualified 6.8.0-146.
This authorises a reboot, not broader package maintenance or interruption of
unrelated work. The existing 15-hour heartbeat carries this follow-through.

For future Kunanyi work, notify Barry before Jumpbox access so he can sign
into the TPAC console in Chrome; he then permits control of Jumpbox access.
The current campaign remains on Deep.

## Preserved handover after the initial Goal 062 proposal

11 October 2026 (Hobart), after preparation of Goal 062.

**The [six-cell prospective design](docs/goals/062-final-procedure-evaluation/registration-2026-10-11.md)
and [compute estimate](docs/goals/062-final-procedure-evaluation/compute-estimate.md)
are prepared for a launch decision.** Barry requested design/cost preparation
and independent review before launch. No new histories, reference tables,
benchmarks or production source changes have been made.

The panel has 500 independent histories in each of h={1,3,5} crossed with
mu={.001,.004}/day, holding beta=.50 and detection SD=.20 fixed. It measures
conditional declaration, abstention, point recovery and prediction on the
unchanged capstone map/bank and one realised reference panel. The proposed
design completes the 466 missing effect-reference tables first: 465,534 new
references, with the existing screen and 299 effect tables reused after
verification. Planning allowance is 42–50 hours at up to 51 deep-server
workers, 64 GiB RSS, 50 GiB free scratch and a 72-hour checkpointing ceiling.
These are proposed resources; current capacity and new-adapter throughput
have not been measured.

The [independent design review](docs/goals/062-final-procedure-evaluation/design-review-2026-10-11.md)
conditionally supports this design and cost envelope. Its bootstrap and
full-grid clarifications are incorporated, including fixed secondary error
quantiles. Implementation must qualify a new panel adapter around the unchanged
scientific kernels before production;
the existing four-case runner cannot be used unchanged. The all-null capstone
remains intact, and this panel does not resolve the separate landscape,
competing-model or magnitude-interval questions.

**Next boundary:** Barry's launch decision on this concrete proposal. Approval
can cover implementation, mechanical qualification, the bounded run and audit
as one tranche; scientific changes or resource increases return for review.

## Preserved handover after the Paper 1 evidence synthesis

11 October 2026 (Hobart), after the Paper 1 evidence synthesis.

**The [charter-level evidence synthesis](docs/paper1-evidence-synthesis-2026-10-11.md)
is complete. Further experiments are recommended selectively; none has been
authorized or launched by this assessment.** The controlled recovery maps and
earlier known-nuisance power results remain substantial evidence. The final
observed-nuisance procedure has no replicated positive-effect evaluation or
calibrated magnitude interval. Its all-null capstone remains a valid blinded
demonstration and is not to be redrawn.

The principal recommendation, if the final procedure is presented as a
practical positive-effect method, is a prospectively registered evaluation
with independent null and positive-effect histories. Narrow claims about
exact-grid null control, feasibility and the blinded demonstration do not
strictly require another simulation. Reference completion and fixed-table
versus repeated-table uncertainty need explicit costing and definition.
The unchanged charter also leaves numerical
qualification of landscape generality and a common competing-process-model
comparison unresolved. These need bounded further work or an explicitly
reviewed claim boundary. A new power panel alone would not complete the charter.

The [independent review](docs/paper1-evidence-synthesis-review-2026-10-11.md)
records its assessment. The roadmap now reports both historical Arc 2B
classes (3/10/19) and the previously accepted coverage-free interpretation
(4/9/19); only S08 changes. Historical outputs and the charter are unchanged.
No simulations, refits or code cleanup were performed.

**Next scientific decision:** review the synthesis recommendations and the
intended Paper 1 claim boundary before registering further work.

## Preserved handover after truth release

9 October 2026 (Hobart), after the authorized truth reveal.

**The capstone truth assessment is complete: all four generating effects are
null (h=1).** Claude accepted the complete-report lock in thread-53 message
1278; Barry then released the truth. The archive matches commitment
`f4145408b52e24e459e751f9fa646a3365fb9d596f8a3da8476853e48c56af8d`.
All 3,793 files in the accepted pretruth closure were reverified unchanged.

The [truth report](docs/goals/061-blinded-capstone-training/truth-report.md)
records every committed forecast under its original rule. All four null-class
forecasts are correct. The continuous adjusted estimate in case-02 remains
1.28762361924 (absolute log-h error 0.2527983638884294); the other three are 1.
Exact-family branch forecasts hit cases 00 and 03 and miss cases 01 and 02,
which are B100-A. Conditional beta errors are 0 and 0.25 in the two exact
cases; beta is unscored in the other two. Mu forecasts hit three cases, missing
case-03 by 0.0006/day. All four SD points and all four broad SD sets hit.

The p_BB values remain 1, 1, 0.422 and 1, with four valid non-declarations and
no realized false declaration. This all-null panel supplies no positive-effect
power or recovery evidence; the B100-A cases do not extend the exact-family
on-grid guarantee. The holdout forecast outcome remains one pair hit and
three misses. No fit, calibration, model or prediction was changed.

The original reports and locks remain immutable. The separate
[truth review](docs/goals/061-blinded-capstone-training/truth-independent-review.md)
accepts the assessment without repair; all 40 independently calculated
forecast outcomes/errors match, as do all four h estimates and p_BB values.
The ten-file final inventory is
`artifacts/goal061_truth/truth-assessment-manifest.json`, SHA-256
`0220d0ad3db75326f995a7c92972893d6d6e3e64c24d27f6b9bd02e9420ce94c`.
It binds the released archive and new assessment, review, source, tests and
results, with the accepted pretruth lock retained as inherited evidence.
Three new arithmetic/commitment tests pass, with Ruff checks green.
No new simulations, generator replay or private encryption-identity access
were needed.

**Next useful tranche:** synthesize the capstone with earlier controlled
experiments against the Paper 1 charter, separating supported claims from
remaining evidence gaps. Any new positive-effect experiment needs its own
prospective design; this capstone must not be redrawn to improve its story.

## Preserved handover before truth release

The following records the complete-report lock before Claude's acceptance
and Barry's truth release above. Its pending-release statements are historical.

8 October 2026 (Hobart), after the complete report lock.

**The training-plus-holdout analysis is complete; the independently reviewed
combined report is locked for Claude's review.** Barry explicitly
released the holdout on 8 October. Its archive matches the prior commitment,
and all 3,734 training-lock files remain unchanged. Truth remains sealed.

The [combined report](docs/goals/061-blinded-capstone-training/complete-report.md)
records one leading-pair forecast hit (case-00) and three misses. Case-01's
10.51-nat adjusted training gain reverses to a 1.85-nat held-out disadvantage.
Cases 01 and 03 have tiny differences between their two constant fits; their
exact winner labels do not imply substantive separation. No fit or declaration
changed. The four p_BB values remain 1, 1, 0.422 and 1.

All 16 scores, 640 site contributions, 128 cluster contributions and 24
pairwise differences passed the independent direct-bank audit. Maximum score
and contrast discrepancies were 5.69e-14 and 1.14e-13 nats. All exact winner
sets and forecast outcomes agree. Seven targeted tests passed in the original
Linux runtime. The [holdout execution record](docs/goals/061-blinded-capstone-training/holdout-analysis-2026-10-08.md)
preserves the released input, immutable training bindings, original and final
audit sources, resource receipts and checksummed evidence return.

The [complete-report lock](docs/goals/061-blinded-capstone-training/complete-report-lock.md)
binds 23 direct files, the 36 returned run files and the unchanged 3,734-file
training closure: **3,793 unique files / 6,376,862,557 bytes**. Exhaustive
verification passed, as did comparison of all 258 previously qualified current
source/script/test files. The root is
`artifacts/goal061_holdout/complete-report-lock.json`, SHA-256
`baa0ec8660321d698e4cb5b2d3ef9f41ef41fec9b3a7e751fe18a00813e835af`.
Its separate receipt is
`artifacts/goal061_holdout/complete-lock-verification.json`.

**Next boundary:** Claude reviews the locked complete report; Barry then
separately releases truth. This review is pending. The truth forecasts and
their scoring rules remain unchanged. Decision Inbox guidance has been read and is available when
a substantive decision needs Barry's input; no questionnaire is needed now.

## Preserved handover before holdout release

The following records the training-lock and Git checkpoint state before
Barry's subsequent holdout release above.

8 October 2026 (Hobart), after the training-lock review and repository checks.

**Goal 061 is complete: the blinded training report is locked and accepted by
Claude (historically Fable).** Barry's approved endpoint has been reached.
The acceptance is thread-53 message **1054**, posted at **11:32:54 AEDT on
6 October**, after Claude's independent verification of all 3,734 files.
Barry's separate holdout and truth releases remain pending.
No holdout or truth plaintext, private key or private generating identity has
been accessed by Codex.

## Repository checkpoint and standing Git authority

On 8 October Barry confirmed that Codex and Claude have authority to commit
and push as they see fit, with bundled commits preferred over atomic commits.
This supersedes historical no-commit/no-push restrictions in completed goal
records. It does not release protected data or change scientific review gates.
The existing GitHub repository is private; the last pushed checkpoint before
this update was `bcc2c85` (Goal 045, 8 September). This checkpoint combines the
completed Goals 046–061 with their source, tests and research records.
Bulk generated artifacts remain outside Git under the existing ignore policy.
The Goal 046 result CSVs retain their original line endings through a scoped
Git attribute, so the checkpoint preserves their exact generated bytes.

Local verification on 8 October passed **763 tests (3 skipped)**, Ruff lint and
the offline source/wheel build. The root training-lock checksum and all 52
direct file hashes passed; all 258 current source/script/test files match the
qualified 334-file production snapshot. The locked scientific evidence and
commitments were not edited. Repository-wide hygiene checks remain non-green:
45 files fail Ruff's formatting check; strict mypy reports 130 errors in 20
files across source and tests, including 20 errors in two source modules
(`conditional_reference.py` and `gamma_conditioning.py`). These include missing
SciPy stubs and annotation/type errors. They are recorded for a separate
maintenance tranche, without changing qualified code during this checkpoint.

## Locked training result

The [completed training report](docs/goals/061-blinded-capstone-training/training-report.md)
records four valid non-declarations, with **p_BB = 1, 1, 0.422 and 1** for
cases 00--03. There are no abstentions or diagnostic holds. These results do
not establish absence of an effect, generating-family identity, parameter
recovery, power or coverage. The report retains the conditional casewise
exact-family on-grid scope and the numerical/generator limitations.

All 16 main fits, 1,772 profile points and 5,400 lattice points passed their
independent numerical checks. All **75,735 screening references** and all
**298,701 effect references** at the unchanged 299-node union passed; the final
rank chain was independently reconstructed from saved audit arrays. Candidate
counts remain 33, 43, 107 and 128. Case-02's nodewise values range from 0.173
to 0.412. The other three p_BB values equal 1 algebraically for their near-zero
observed statistics and valid tables, as Fable noted in message 1024.

The original production attempt finished at **04:51:03 AEDT on 6 October**,
exit 0, after 15 hours 30 minutes 50 seconds, with 23.21 GiB sampled aggregate
peak RSS. A 05:16:33 AEDT process check found no original supervisor or group
members. Do not restart completed work. The remote evidence remains at
`deep-server-ts:/data/codex/scratch/goal061-capstone-training-20261005-qualification-repair3`;
the complete local mirror is `artifacts/goal061_execution/qualification-repair3/`.

The [training-lock note](docs/goals/061-blinded-capstone-training/training-lock.md)
explains the bound evidence and release sequence. The root manifest is
`artifacts/goal061_execution/training-lock.json`, SHA256
`2265d62e3e953792b2892a4d7b34c784d5800b2f7ba078db99ed753e13bd1861`.
Its 52 direct files and five explicitly based child inventories cover **3,734
unique files / 6,375,566,653 bytes**. Exhaustive local custody verification and
the separate independent lock check both passed. Their receipts are
`artifacts/goal061_execution/return-verification.json` and
`artifacts/goal061_execution/training-lock-verification.json`.

The [final claims review](docs/goals/061-blinded-capstone-training/final-review.md)
found no scientific correction needed. Its remaining mechanical lock condition
was satisfied by the independent checksum attestation. The reviewed report is
`5810719117dfc01b0221560ec368be6539cc7b95fe0e06d7fe1140b7d660eb2f`.
The 334-file production source manifest remains
`5879fbdaf7b3880151358319a7b7c7c0837463b06ba06f1a34fb80a3fbc2e36a`;
all original 321 qualified source files and all five inputs remain unchanged.
All 26 qualification evidence files and 97 qualified-public-package files
passed. A missing local historical-registration copy was restored from exact
frozen-source bytes before the full return check. That custody event and all
three earlier mechanical qualification failures remain recorded.

The original [predictive specification](docs/goals/061-blinded-capstone-training/predictive-specification.md)
remains `88ba503b84a4827d342d590fa0c70e4945e27babb7c8f2f26085e0fa08ba1b1d`.
The [prereveal forecasts](docs/goals/061-blinded-capstone-training/prereveal-predictions.md)
committed in message 1029 remain
`ea017c2300214b834ddb28fae577d9c5f9e43ba9f43337a185d448bd7bab1895`.
They were made after training inspection and before either release. The locked
figures and full-precision tables are in
`artifacts/goal061_execution/training-figures/`.

Astra sent the exact lock to Fable on correspondence thread 53 in message
**1052 at 05:30:25 AEDT**. The local posting receipt is
`artifacts/goal061_execution/correspondence-training-lock.json`. Claude accepted
that exact lock in message **1054**. The task retrieval cursor is **1165**;
the actual acknowledged thread-53 message is **1054**.
The `complete-blinded-capstone-training` follow-up was deleted after this
handoff. It must not continue polling or launch another analysis.

**Next boundary:** await Barry's explicit release of the committed holdout
before any held-out scoring. Claude's lock review is complete. Then follow the unchanged
predictive specification without refitting or selecting models. Lock the
complete report before the separate truth release. Do not interpret either
model acceptance or a numerical `release_blocked=false` flag as human release
authority. The [execution record](docs/goals/061-blinded-capstone-training/execution.md)
preserves the full staged history.

## Preserved Goal 060 closeout

**Goal 060 is complete: the public package is qualified.** Barry approved
Fable's message 932 and the fixed 1,024-interval certificate on the same map.
The certificate passed at `4.928543927785195 < 5`. All 306 Linux tests,
mechanical qualification, the 131,072-history bank and the entire eight-fixture
panel passed. The repaired full independent audit and unchanged sealer's public
preflight then passed. The original failed manifest-interface audit, negative
readiness and all outputs remain immutable; all 658 original return hashes passed.

The [bounded interface repair](docs/goals/060-capstone-certificate-recovery/audit-interface-repair-2026-10-04.md)
adds an independently reviewed adapter without changing the original 303 source
files, any numerical gate, generated history or fitted result. It passed all
14 relevant Linux tests, Ruff and mypy. The new 321-file freeze is
`9ee6aad80f0cf132a54a59e7b030c58459008d517ecb31b54d0f3200f9dbd0de`;
603 copied input/evidence files are bound to the preserved run. The audit-only
attempt finished at 00:09:24 AEDT on 5 October at
`/data/codex/scratch/goal060-capstone-recovery-20261004-audit-repair` on
`deep-server-ts`, with no resource stop or remaining workers. Readiness is
positive. Final checks verified all 637 returned repair files, 603 copied
inputs, 321 archive members and 87 preserved Goal 059 files. Combined public
execution and audit took 76.89 minutes, within the original four-hour bound.

The [synthesis](docs/goals/060-capstone-certificate-recovery/synthesis.md) and
[execution record](docs/goals/060-capstone-certificate-recovery/execution.md)
record the current state. The original diagnosis preserves a reviewer's
recommendation for further approval; the parent treated the exact interface
correction as routine implementation work within the approved preparation.
Correspondence thread 53 messages 939–940 disclose qualification, the excluded
development test-root exploration and the audit repair. Message **944**, posted
at **00:21:00 AEDT on 5 October**, hands the qualified package to Fable.
The [final independent review](docs/goals/060-capstone-certificate-recovery/final-review.md)
accepts readiness for Fable's leak review; the
[posting receipt](artifacts/goal060_execution/correspondence-closeout.json)
records the handoff. Current task cursor and acknowledged message are 944.
No real private root, sealed history,
confirmatory reference campaign, commit or push is authorized in this tranche.
Fable's final leak review and the
[single-command sealing handoff](docs/goals/060-capstone-certificate-recovery/sealing-handoff.md)
are next. No private root or sealed history has been generated here.

## Preserved Goal 059 closeout

This historical closeout is retained as written. Barry's subsequent Goal 060
approval above supersedes its pending certificate-refinement decision.

**Goal 059 closed with a terminal negative map qualification.** The first
structurally valid registered map (candidate 0) required a conservative
transform bound of **5.350148708913006**, above the fixed domain **5.0**.
The independent map-only auditor reconstructed and reproduced the failure.
Post-stop diagnosis gives an actual continuous-box maximum of **4.89412 < 5**:
the sufficient interval enclosure was conservative. This does not amend the
registered gate or authorize continuation; a narrow certificate-refinement
decision can retain the same map, parameter box and numerical domain. The
[proposal](docs/goals/059-capstone-preparation/next-stage-proposal.md) fixes
1,024 equal beta intervals in the existing enclosure, giving a known diagnostic
bound of 4.92854. It is not authorized or executed.
The registered run and audit ended at **21:12:20 AEDT** on 4 October; no process
remains active. **The public capstone package is not ready for Fable's sealed
generation.** No registered bank, public panel or sealed history was drawn.

The [synthesis](docs/goals/059-capstone-preparation/synthesis.md),
[execution record](docs/goals/059-capstone-preparation/execution.md) and
[independent review](docs/goals/059-capstone-preparation/independent-review.md)
describe the negative qualification. Linux qualification passed 278 tests,
Ruff, mypy and mechanical numerical checks before the registered attempt.
The 273-file final source manifest is
`e63af340a6c2180914db6c779e4b3316ef9db99e3f27b169156ef6168e289867`.
All 51 returned-file hashes and 12,157 predecessor source/evidence checks pass.
The superseded packages and first missing-fixture test failure remain preserved.
The [completion check](artifacts/goal059_execution/completed-check.json) passes.
The negative result and concrete recovery proposal were sent to Fable on
thread 53 as **message 928 at 21:25:23 AEDT**. Task cursor/read marker is 928;
Fable's review and Barry's next decision remain pending.

Barry's approved decisions remain the
[registration](docs/goals/059-capstone-preparation/registration-2026-10-04.md):
skip the old-map pilot, retain the full 765-node union, use the approved public
truth law and the new map. The map, sites, analysis bounds and random addresses
remain fixed. Do not replace the map, enlarge the numerical domain, relax the
gate or generate a bank/panel without the next recorded decision.

The earlier production-root development preview is disclosed in the frozen
registration and [methods review](docs/goals/059-capstone-preparation/methods-review.md).
Its candidate 5 used incorrect sampling and numerical selection and is excluded
from adoption. Messages 925–926 correct message 924's initial no-map-draw claim
and report recovery of the preview artifact. The registered candidate 0 comes
from the corrected structural rule specified before the preview.

## Preserved Goal 058 closeout

This historical section records the state at Goal 058 closure. The accepted
Goal 059 registration and negative qualification above supersede its proposed
next step and still-pending truth-law choice.

**Goal 058 is complete: all four full effect-reference tables are usable.**
Barry approved beta spacing .25 (765 nodes), deferred the global-screen change
and authorized the fixed four-node micro-pilot. The single registered attempt
retained all 3,996 histories; every returned null/free pair and independent
true/null/free direct-bank check passed. It finished at **18:11:34 AEDT** in
**29.64 minutes**, with **7.461 GiB** sampled peak process-group RSS. Production
used sixteen workers and audit four, within the approved 48 GiB/two-hour cap.
No Goal 058 process remains active and no completed phase should be rerun.

The [synthesis](docs/goals/058-effect-reference-micro-pilot/synthesis.md),
[independent review](docs/goals/058-effect-reference-micro-pilot/independent-review.md),
[execution record](docs/goals/058-effect-reference-micro-pilot/execution.md) and
[completion check](artifacts/goal058_execution/completed-check.json) close the
tranche. All four nodes have 999 valid references. Maximum independent
likelihood/T differences are 1.137e-12/2.728e-12; all 19,980 seeds, 3,996 unique
addresses, tables and 8,003 payload hashes pass. Twelve generator replays match
bitwise. Linux passed 209 tests, Ruff and mypy; target qualification verified
the original full bank and pair/four-model equivalence before registered draws.
The complete raw production return is 8,004 files / 66,866,422 bytes. All source
snapshots and Goal 056/057 evidence remain intact.

This qualifies a pipeline at four null settings. The low-rate corner put
73/999 fitted null-history effects at h=10; reliable effect recovery is not
established. Zero observed failures does not imply reliable complete tables
at all 765 nodes. False-declaration rates, power, coverage and the full-data
threefold question remain unmeasured.

The [next proposal](docs/goals/058-effect-reference-micro-pilot/next-stage-proposal.md)
recommends a bounded 765 x 99 recalibration of the existing local screen, using
fresh references and the old open panel for descriptive retention. It remains
unapproved. The old 268-node coarse-mask proxy gives 33.1 hours under the
measured 16-fit/4-audit allocation, or 9.59 hours under hypothetical 64-worker
scaling in both stages with a 1.5 margin. These are cost scenarios, not observed
coarse-screen unions or runtime guarantees. The global-screen idea stays deferred.

The final sealed truth distribution must reconcile beta=.6 with the new grid
and separately label the B100-A residual-field stress branch. No replacement
truth or weights have been chosen. The recommended primary confirmatory banks
use fresh streams after the complete final design is frozen; Goal 058 banks
remain open design evidence. Four histories and key custody stay as agreed.
No large calibration, new map, sealed history, commit, push or publication
has occurred in this tranche.

Fable's messages **902–903** were read and acknowledged; the saved-data
calculations and their limits are in
[Astra's response](docs/goals/058-effect-reference-micro-pilot/fable-response-2026-10-04.md).
Astra relayed Barry's decisions as **message 906** at **17:14:05 AEDT**.
The verified completion and costed next proposal were posted to thread 53 as
**message 911** at **18:23:05 AEDT**. The latest catch-up cursor and actual
acknowledgement are both **911**. **Fable's review, then Barry's scientific
decision, are next.** Do not infer that Fable has read the post.

## Preserved Goal 057 closeout

**Goal 057 is complete: the local screen is cheap, but leaves large effect-reference
unions.** The [synthesis](docs/goals/057-screening-retention/synthesis.md),
[independent review](docs/goals/057-screening-retention/independent-review.md),
[execution record](docs/goals/057-screening-retention/execution.md),
[figures](docs/goals/057-screening-retention/figure-captions.md) and
[completion check](artifacts/goal057_execution/completed-check.json) close the
approved tranche. All 360,855 references and 792 diagnostic fits finished on
eight deep-server workers at **15:05:41 AEDT**, in 397.28 s with .986 GiB sampled
peak aggregate RSS. All fits converged. Independent reconstruction passes all
58,320 public scores, ranks/candidate sets, 1,820 unions, 792 diagnostic
contrasts and true/fitted scores, 21 generator replays and the full seed ledger.
Linux 158 focused tests, Ruff, mypy and mechanical qualification passed before
the run. No scientific process remains active and no completed phase should
be rerun.

Retained sets contain 420–990 nodes. Four-case unions range 577–1,901, median
1,266, projecting to 32–39 hours at 64 workers for later effect references
under the stated workload/margin assumptions. All sixteen known true nodes
are retained; this fixed-panel result does not estimate coverage or power.
The registered balanced mean log-background error is -.01594 (MC interval
[-.03982,.00793]); a labelled post-run arithmetic supplement gives +3.95%
([+1.64%,+6.26%]), not a general 20% inflation. These do not establish zero bias
at every node or full-data effect bias. Many retained nodes have large global
R, motivating the [next proposal](docs/goals/057-screening-retention/next-stage-proposal.md):
review one fixed coarser global screen before large calibration.

The source archive and all Goal 056 evidence remain intact. A pre-freeze
development preview of 99 node-0 histories and one other stream prefix is
disclosed; production seeds, reference counts and methods were not changed.
Postprocessing repaired a 99-versus-999 cost multiplier and a transposed
heatmap. Original attempts are preserved; accepted figures/report are in
`artifacts/goal057_execution/synthesis-v3/`. The final audit receipt is
`independent-audit/result-v3/report.json`. Current reporting source differs
from the frozen source only in the synthesis script and README; production
modules, tests and registration remain unchanged.

Astra posted the verified results and proposal to thread 53 as **message 896**
at **15:30:44 AEDT** on 4 October. The task retrieval checkpoint and actual
acknowledged message are both **896** at this handoff. **Fable's review is next,
then Barry's scientific decision.** Do not infer that Fable has read the post.
The proposed 225-anchor comparison remains prospective: old-panel results
would stay descriptive because that panel motivated the new statistic.
The full effect micro-pilot, operating-rate study, new map and sealed generation
have not run. No commit, push, publication or new automation was performed.
The historical Goal 056 request below was superseded by Barry's approval of
Goal 057; its completed numerical results remain frozen.

## Preserved Goal 056 closeout

**Goal 056 is complete: observed-nuisance likelihood feasibility passes;
calibration cost depends on unmeasured screening retention.** The
[synthesis](docs/goals/056-observed-nuisance-feasibility/synthesis.md),
[independent review](docs/goals/056-observed-nuisance-feasibility/final-review.md),
[execution record](docs/goals/056-observed-nuisance-feasibility/execution.md),
[figures](docs/goals/056-observed-nuisance-feasibility/figure-captions.md) and
[calibration proposal](docs/goals/056-observed-nuisance-feasibility/calibration-proposal.md)
complete the approved study. The
[completion check](artifacts/goal056_execution/completed-check.json) verifies
40 panel outputs, 28 synthesis outputs, the 64/16/48-row tables, both source
snapshots and all 97 preserved Goal 055 bindings.

All 64 main fits, 16 pre-only fits and 7,088 profile nodes converged. Linux 174
tests, Ruff and mypy passed. Independent raw-bank replay agrees within
6.82e-13 training nats, 1.14e-13 held-out total nats and 1.36e-12 in effect
statistics. The sixteen histories were generated once. A profile-only
boundary-rounding repair recovered four missing diagnostic cells while
preserving all observations, main fits and twelve completed cells byte-for-byte.
The original failure and both audit attempts remain preserved; no completed
phase should be rerun. No scientific process remains active.

Adjusted h estimates in the eight true-threefold cases range 1.717–4.020,
median 2.005; one null history estimates h=3.355 with a shallow profile. The
local log-h curvature scale lies inside the .40–.60 forecast in 3/8 threefold
cases, and is not a sampling SE or confidence interval. Detection-SD error
is within .03 in 7/8 heterogeneous cases. Held-out gains are mixed. These are
numerical feasibility and descriptive fixtures, not recovery or calibrated
operating-rate evidence.

The original panel and recovery used 149.15+108.31=257.46 seconds; qualification
used another 132.55 seconds. Full effect-reference cost projects to 10.25–12.42h
for 100 union nodes or 15.6–18.9 days for all 3,645 at 16 workers with a 1.5 margin.
Retention is unknown. The concrete next proposal is a public screen-retention
pilot, with four-case union-cap and failed-fit rules, followed by a separately
reviewed small effect-reference pilot. These are new scientific decisions;
neither has run. A new map needs its own numerical/resource qualification.

**Next owner: Barry**, to approve or decline the revised public screening
pilot. Fable's critique and key instructions arrived in thread 53 messages
**875–876**; Astra read both and replied with **message 880** on 4 October
at 12:28 AEDT. The task retrieval checkpoint and actual acknowledged message
are both **880**. The [response](docs/goals/056-observed-nuisance-feasibility/fable-response-2026-10-04.md)
verifies Fable's error calculations while qualifying the near-ideal-information
and settled-bias interpretations. An independent methodological review agrees.
The [revised proposal](docs/goals/056-observed-nuisance-feasibility/calibration-proposal.md)
adds 792 pre-only fits reusing eight nodes' screening references, independent
pre-only likelihood checks, and a descriptive retained-set/global-surface
overlay. It retains the proposed one-hour envelope and separately costs later
64-worker or Kunanyi production. No pilot was approved or launched in this
review; no source, fitting rule or frozen result changed.

Barry reported creating his key and supplied the public recipient on 4 October.
It matches the recipient in [Fable's custody instructions](docs/advisor/capstone-key-custody.md),
and age v1.3.2 accepts it for encryption. Astra accessed no private identity,
passphrase, password manager or private folder; decryption and backup custody
remain Barry's checks. The public recipient is
`age194jmw2rywjfazsc6w8hqht3lnlxldkcp9dwl49xm54r6hk8y4vtslny0yr`.
Four future histories and simple accidental-exposure protection remain
approved in principle. No sealed history, large calibration, commit, push or
publication has occurred. There is no active Goal 056 heartbeat.

Frozen original remote root:
`deep-server-ts:/data/codex/scratch/goal056-observed-nuisance-20261003-v2`.
Recovery/audit root:
`deep-server-ts:/data/codex/scratch/goal056-observed-nuisance-20261003-profile-recovery`.
All compact evidence, observations, evaluator truth and synthesis are local
under `artifacts/goal056_execution/`; the original full empirical bank remains
at its verified Goal 045 remote location.

**Goal 055 is complete: the two nuisance checks expose limits of the frozen
procedure.** Supplying 80% of the true map mean raises adjusted null declarations
to 7.8% [5.3, 9.5] in E0 and 10.8% [7.1, 12.8] in E06. Both registered
wrong-mean lower-limit predicates exceed 5%. Persistent prey-detection SD .20
raises adjusted null declarations to 19.8% [15.2, 22.1], versus 3.8% in its
paired Goal 051 baseline: +16.0 points [12.1, 17.8]. Both absolute and paired
detection flags trigger. These pointwise, retrospective archive checks do not
confer nuisance-robust calibration.

The [synthesis](docs/goals/055-arc4-synthesis/synthesis.md),
[claim audit](docs/goals/055-arc4-synthesis/claims-audit.md),
[paper draft](docs/goals/055-arc4-synthesis/arc4-draft.md), three
[figures and captions](docs/goals/055-arc4-synthesis/figure-captions.md) and
[independent review](docs/goals/055-arc4-synthesis/final-review.md) are complete.
Goals 049–054, the selected-but-unconfirmed Goal 051 nominee, and earlier
numerical failures remain frozen. Declaration, magnitude recovery and model
discrimination remain distinct; Pillar 4 and Pillar 5 are not complete.

The [proposed capstone](docs/goals/055-arc4-synthesis/capstone-protocol.md)
selects 60 days of pre-invasion monitoring and a model for shared site-level
prey-detection heterogeneity. The smallest next proposal is observed-data
likelihood feasibility and one 16-history timing panel, before a separately
registered calibration and any sealed truth draw. It specifies an explicit
E0/E06/B100-A background mixture, public map/sampling streams and Fable-held
private truth, training/holdout/report locks, and Astra's blinding. This is a
historical design whose approved likelihood-feasibility prerequisite is now
complete under Goal 056 above. Large calibration and sealed generation still
require separate decisions. No capstone truth, generator seed or observations
have been drawn.

Production exited zero **2026-10-01 20:57:14 UTC**, after **6 h 22 min 05 s**,
within its 9 h 55 min timeout. It scored 12,000 condition fits of 8,000 unique
archived histories; four correct-mean columns were reused. The single fixed
2,000-draw synthesis exited zero **21:04:14 UTC**, after 33 receipt seconds.
All 169 production outputs and 10 synthesis outputs passed verification. Raw
rectangles reproduced all 10 statistics exactly; independent bootstrap and
all-seven-rule checks passed. All 97 source bindings and 89 predecessor source
identities remain unchanged. No scientific process remains active.

The [execution record](docs/goals/055-arc4-synthesis/execution.md) and
[completion receipt](artifacts/goal055_execution/completed-check.json) index
local compact evidence. Authenticated bulk rows remain at
`deep-server-ts:/data/codex/scratch/goal055-nuisance-checks-20261002-v2`.
Never restart timing, production, synthesis or their completed audits. The
failed first wrapper attempt remains preserved. No commit, push, publication,
new calibration or unknown-nuisance implementation occurred.

**Historical Goal 055 handoff, superseded above:** Barry was to decide the proposal in
[Astra's response to Fable](docs/goals/055-arc4-synthesis/fable-response-2026-10-03.md).
Fable's critique is thread 53 **messages 811–813**, posted 2 October at 10:34
AEST; Astra read and acknowledged all three on 3 October. The previous closing
message used an obsolete snapshot ending at 809 and incorrectly named Fable
as next responder. The response recommends a scalable calibration method as
a feasibility deliverable, four sealed histories and genuinely private key/draw
custody, all subject to Barry's decision. No new study has started.
Astra's response is **message 842**, posted 3 October at 15:43 AEST. The task
retrieval checkpoint and actual acknowledged message are now both **842**.
The **latent-landscapes-goal-055-completion heartbeat is deleted**.

For future closing messages about this exchange, refresh thread 53 first,
record the actual acknowledged message separately from the global retrieval
checkpoint, and state the next owner. End the user-facing closing text with
the current date and time in Hobart, as Barry requested; interim updates are
exempt.

**Goal 054 is complete: useful conditional effect decisions, with a real
sensitivity cost.** The [synthesis](docs/goals/054-null-effect-calibration/synthesis.md)
and [independent review](docs/goals/054-null-effect-calibration/final-review.md)
close the approved calibration and nonlinear-aligned pair. The primary adjusted
rule declares at 4.2% and 3.2% in the exact beta0/.60 null evaluations, with
76.1% and 93.0% threefold sensitivity. In the two residual-field nulls its rates
are 2.5% and 2.8%, versus 15.7% and 14.7% for the constant rule. At constant
background it loses 9.2 percentage points of threefold sensitivity and retains
substantial magnitude error. Validity is finite-grid and averaged over reference
and evaluation generation; this table has no guaranteed conditional 5% size.

The cutoff is 3.46649 at interior beta=.55. Berger–Boos recovers no sensitivity.
The nonlinear-minus-linear h1 contrast is +0.3 points [−0.9, 1.3], so the new
pair did not locate a failure boundary. The constant B100-A null forecast of
at least 18% misses pointwise at 15.7%; its interval remains unresolved.
Textbook comparisons are descriptive. Known-nuisance, fixed-bank, finite-grid,
one-landscape limits remain, and effect declaration is separate from magnitude
recovery or confidence coverage. Goal 049–053 and earlier failures are frozen;
the original Goal 051 nomination remains unconfirmed.

All 88,919 histories, 81 rows, frozen replays and 168 production outputs passed
verification. Production exited zero **2026-09-29 16:14:55 UTC**, after
**3 h 5 min 39 s**. The single fixed 2,000-draw synthesis exited zero
**16:43:17 UTC**, after **42 seconds**; all 11 outputs passed verification.
Independent raw-score reconstruction and a separate rule/selected-bootstrap
audit matched exactly. No job remains active; never rerun these completed
phases. The [execution record](docs/goals/054-null-effect-calibration/execution.md)
and [completed check](artifacts/goal054_execution/completed-check.json) index
the evidence. All reduced evidence and observations are local; the 81
authenticated bulk score files remain at
`deep-server-ts:/data/codex/scratch/goal054-null-effect-calibration-20260929`.

The [next proposal](docs/goals/054-null-effect-calibration/next-tranche-proposal.md)
has now received Fable's critique and Barry's approval, with the two additional
archive checks recorded in Goal 055 above. Astra posted results and proposal on Correspondence thread 53 as
**messages 784–785**. The **goal-054-calibration-completion** heartbeat has
been **deleted**. Correspondence was caught up contiguously through message785;
the task-local retrieval checkpoint and acknowledged message are both **785**.

**Goal 053 is complete: conditional benefit with a substantial flexibility cost.**
The [synthesis](docs/goals/053-prospective-background/synthesis.md) and
[independent review](docs/goals/053-prospective-background/final-review.md)
close the approved six-cell, 1,000-block prospective comparison. Adjustment
reduces aligned-null mean absolute log error from 0.3395 to 0.1872 and aligned
threefold error from 0.2911 to 0.2445, reversing the pilot's adverse threefold
direction. It worsens error under constant background: 0.1505 to 0.3092 at
the null and 0.2281 to 0.3254 at h3. Exact nonzero-beta controls benefit, but
their direct predictive gains are smaller than forecast. Oracle arrivals
change matched averages little. All main precision targets pass; finite-grid,
fixed-bank, known-nuisance and one-landscape limits remain. No confidence or
calibrated effect-declaration claim follows, and Goal 051 remains unconfirmed.

The [execution record](docs/goals/053-prospective-background/execution.md)
verifies 81 rows, all 6,000 actual and 1,000 oracle histories, frozen replays,
170 production files and 13 synthesis outputs. Production exited zero at
**2026-09-27 08:19:52 UTC** (3 h 16 min 37 s); the single fixed 2,000-draw
synthesis exited zero at **08:26:00 UTC** (15 receipt seconds). No job remains
running. Never rerun these completed phases. Remote root:
`deep-server-ts:/data/codex/scratch/goal053-prospective-background-20260927`.
Observations, metadata, row receipts, summaries and synthesis are local;
authenticated bulk score arrays remain remote, indexed by
`artifacts/goal053_execution/retrieval-manifest.json`. Direct raw-score
extraction reproduces all 7,000 metric rows exactly.

The [next proposal](docs/goals/053-prospective-background/null-effect-calibration-proposal.md)
recommends a finite-grid adjusted h=1 decision, with 999 reference histories
at each of 81 beta nodes, 1,000 new six-cell evaluation blocks and explicit
reference-table uncertainty. Full confidence calibration and survey changes
remain deferred. Fable's critique was received and Barry approved Goal 054 above.
Routine compute resources and timing remain delegated. The earlier task-local
correspondence checkpoint was **579**;
the verified result and next proposal are **messages 580 and 581** on thread 53.
The **goal-053-prospective-background-completion** heartbeat has been **deleted**.
Verification is indexed by `artifacts/goal053_execution/completed-check.json`.

**Goal 052 is complete: feasible adjustment, no demonstrated repair.** The
[synthesis](docs/goals/052-adjusted-background-pilot/synthesis.md) and
[independent review](docs/goals/052-adjusted-background-pilot/final-review.md)
close the approved 24-history retrospective pilot. Adjustment lowers aligned-null
mean h from 1.225 to 1.083, but in aligned threefold histories the move from
3.633 to 2.750 worsens mean absolute log error (0.310 to 0.402) and provides
no consistent direct held-out advantage. Broad h–beta trade-offs persist;
oracle arrivals narrow profiles in only 12/24 histories. The failed expectation,
paired beta-edge contacts and coarse/fine flags remain visible. No confidence
calibration, population recovery claim or confirmation of Goal 051 follows.

All 81 rows, 24 exact replays, source/input/output hashes and the one fixed
deterministic synthesis are verified. Production exited zero at **2026-09-24
03:52:17 UTC**, after 12 min 22 s on eight workers, peak RSS 2.25 GiB.
Synthesis exited zero at 04:00:26 UTC after 2.95 s. No computation remains
running; never rerun these completed phases. Remote evidence remains at
`deep-server-ts:/data/codex/scratch/goal052-adjusted-background-20260924`.
See the [execution record](docs/goals/052-adjusted-background-pilot/execution.md).

The [costed next proposal](docs/goals/052-adjusted-background-pilot/prospective-comparison-proposal.md)
uses 1,000 fresh paired blocks in six cells, including exact beta=0/+0.60
controls, known-beta diagnostics and the original aligned-background cases.
It prioritizes paired multiplicative estimation error and direct predictive
comparison, limits full oracle diagnostics and defers confidence calibration.
Fable's critique and Barry's approval now authorize Goal 053 above. Resource
and timing choices remain explicitly delegated to Astra. Additional calibration,
survey changes, unknown nuisances, commits, pushes and publication remain
outside scope.

Astra posted the verified findings and next proposal on Correspondence thread
53 as **messages 511–512**. The completed
`goal-052-adjusted-background-completion` heartbeat has been **deleted**.
The historical retrieval checkpoint at Goal 052 closeout was 510; Goal 053
above records the current correspondence and execution state.

**Goal 051 is complete.** Aligned background variation remains the sole, unconfirmed
nomination. Barry's approved 17-cell/17,000-history screen
and fixed 1,000-draw synthesis completed under the
[registration](docs/goals/051-misspecification-screen/registration-2026-09-23.md).
The [synthesis](docs/goals/051-misspecification-screen/synthesis.md) reports
primary hidden failures of **42.3% versus 19.3%** under aligned background
variation at a physical null: **+23.0 percentage points [19.9,25.9]**.
Only 2.7% of histories trigger the primary adequacy detector. Strict false
effects are a separate endpoint: 21.6%, of which 21.2 percentage points remain
unflagged, versus 6.1% unflagged at baseline. These findings are conditional on one landscape, fixed tables/bank
and known nuisances; they do not complete Charter Pillar 4.

Five cells meet the screen rule, but only **B100-A_h1** is nominated globally.
Prey-detection SD0.20 also causes errors and is more often detected;
predator-detection SD0.10 has little measured effect here. Nine scalar
predictions are contradicted, five supported and five unresolved; both
forecasts of non-resolution are met. Failed predictions remain visible.
The [independent final review](docs/goals/051-misspecification-screen/final-review.md)
reconstructed all endpoint arrays, all saved bootstrap means/deltas and all
578 field-diagnostic rows exactly. All 82 source/input/helper hashes and nine
synthesis output hashes pass; see the
[completed check](artifacts/goal051_execution/completed-check.json).

Production exited zero at **2026-09-23 13:05:58 UTC**, after 21 min 41 s;
synthesis exited zero at **13:09:57 UTC**, after about 8 s. Including the full
preparation and verification allowances, the charge is **77 minutes within
four hours**. No scientific compute remains running. The
[execution record](docs/goals/051-misspecification-screen/execution.md) holds
the receipts and administrative closeout. Do not restart any phase. All Goal
049/050 evidence and earlier numerical failures remain frozen.

Astra posted the verified findings and original proposal on Correspondence
thread 53 as **messages 491–492**. Fable accepted closeout and critiqued the
next step in **496–498**. Astra's [response](docs/goals/051-misspecification-screen/fable-response-2026-09-24.md)
and [archive-only checks](artifacts/goal051_execution/posthoc-20260924/checks.json)
reproduce the post hoc score, held-out comparison and field-association
diagnostics. They do not establish a general information limit, causal bias
decomposition or a calibrated new detector. No new histories, fits or draws
were used. Frozen scientific documents still match the completion receipt.

**Decision resolved by Goal 052 approval above:** Astra withdrew the recommendation for the standalone
[confirmation](docs/goals/051-misspecification-screen/confirmation-proposal.md)
and instead proposes an [adjusted-background identifiability pilot](docs/goals/051-misspecification-screen/adjusted-background-pilot-proposal.md):
24 fixed archive replays, the current survey, a fitted spatial background
coefficient and adjusted no-effect comparator, within four computation hours,
eight workers and 32 GiB. This is a proposed amendment to the approved
confirmation-first sequence. Barry has now approved that change and the pilot;
the nominee is not thereby confirmed. Full prospective Stage 2, additional
surveys and a larger comparison remain separate scientific decisions.

Astra posted the evidence response and revised recommendation as **502 and
504** on thread 53 and acknowledged Fable through **498**. This task's latest
retrieval checkpoint is **510** (a global cursor, not a read-marker ID).
The subsequent approval authorizes Astra's pilot continuation above. The completed
`goal-051-screen-completion` heartbeat was deleted at 2026-09-23 13:24 UTC
and remains deleted. Commits, pushes and publication remain outside scope.

**Goal 050 is complete: a conservative assumed-model adequacy baseline.**
The [synthesis](docs/goals/050-model-adequacy/synthesis.md) reports 19/1,000
rejections in the fresh null block (1.9%; calibration-aware 95% interval
1.1–3.2%) and 0.4–2.4% across six retrospective truths. These are false-rejection
rates under the assumed model; Goal 050 did not test alternative generators.
Goal 051 above supplies the first registered robustness screen.
Fresh C99 truth inclusion is 99.2%. The full-grid detector, known nuisances and
independent empirical integration bank remain fixed.

The crossed null counts are **74,57;69,48** per 1,000 for original/fresh
calibration cutoffs crossed with original/fresh evaluation. All five paired
contrast intervals include zero. The original 7.4% effect-set exclusion flag
remains unexplained and the original calibration table is retained. The
[final independent review](docs/goals/050-model-adequacy/final-review.md) and
[completion receipt](artifacts/goal050_execution/completed-check.json) support
closure under this limited scope.

Production and synthesis exited zero; all original profiles, joint holdout
scores, fitted nodes and opaque IDs replayed exactly. All source/input/output
hashes passed. Production took 2 h 41 min 46 s and synthesis 42 s; the conservative
charge including the full analysis/review reserve is 4.28 h within the 12-hour
cap. No compute remains running; the completed Goal 050 heartbeat was deleted. See the [execution record](docs/goals/050-model-adequacy/execution.md).

**The revised robustness-screen package was approved as Goal 051 above.**
Fable reviewed the completed result and proposed screen on Correspondence
thread 53 (messages 468, 469, 471). Astra's [response](docs/goals/050-model-adequacy/fable-screen-response-2026-09-23.md)
accepts the added diagnostic and four generator cells as proposed work, while
retaining the disagreement that low assumed-model size establishes low power.

The [revised proposal](docs/goals/050-model-adequacy/next-screen-proposal.md)
contains 17 paired cells/17,000 histories: the original 13 plus predator-only
detection SD0.10 at h=1,3,5 and aligned background confounding at h=3. It keeps
Berger–Boos as primary, adds the fitted-node plug-in p-value as secondary with
fresh baseline checks, preserves primary H nomination, and records Fable's
predictions without making them acceptance gates. Projected charge is 2.83 h;
the proposed four-hour/eight-worker/32-GiB ceiling required full-cell timing.
That proposal-stage gate has now passed under Goal 051 as recorded above;
its earlier 2.83-hour estimate is superseded by the measured bound budget.

Astra posted the review response and revised recommendation on thread 53 as
messages 475–476. This task read and acknowledged Fable through message 471
(task-local retrieval checkpoint 471; later own replies are 475–476).
No further Fable response is required to execute the approved package.
The alternative-generator campaign and its scientific choices are authorized
by Barry's approval above. Stage 2 competing
fits and the neutral comparator remain a separate scope decision. Goal 050,
its original table and all earlier numerical failures remain frozen.

**Goal 049 is complete: a known-nuisance finite-grid calibration reference.**
The [synthesis](docs/goals/049-operational-calibration/synthesis.md),
[figure](artifacts/goal049_execution/review/calibration_resolution.png),
[independent review](docs/goals/049-operational-calibration/final-review.md) and
[verified completion receipt](artifacts/goal049_execution/completed-check.json)
record the outcome. Candidate-wise calibration removes the need for the
unknown prey-effect truth when selecting cutoffs. All 36 registered matched-bank
endpoint tolerances pass. Interior cutoffs are 3.73–4.34, with lower cutoffs at
the two boundaries. Detection improves over the evaluator-only oracle-flat
comparison at h=3; the tiny h=5 ceiling difference is unresolved. Sets remain
broad, and neither point estimates nor predictions change with set construction.

The realised primary table excludes the null in **7.4%** of null histories
(calibration-aware 95% interval **5.6–9.7%**). This is a retained calibration
quality-control flag, not a conditionally 95% table. Mechanistic review found
no generator/scorer mismatch or seed leakage; no redraw or retuning was made.
The archived speed-transport failure remains severe. The archived strict h=5
power-increase prediction failed at the ceiling and remains recorded.

Production finished at 07:33:28 UTC in 6 h 11 min 55 s; the fixed 2,000-draw
synthesis finished at 07:44:39 UTC in 4 min 7 s. All source, bank, seed and
frozen output checks pass locally/remotely. Both exit receipts are zero and
no scoring process remains. Computation including timing and the conservative
prior-work allowance is about 7.40 h, within the 24-hour budget. Full profiles
and original receipts are retained; see the [execution record](docs/goals/049-operational-calibration/execution.md).
The completed Goal 049 heartbeat has been removed; Goals 045–048 remain paused.

**Goal 049's handoff to Arc 4:** retain the assumed-model calibration and
matched-generator baselines under the same realised table. Goals 050 and 051
subsequently implemented the approved detector and alternative-generator
screen above. Unknown nuisances, candidate-wise speed calibration and field
use remain separate extensions.
Barry's instruction to proceed authorized this completed tranche, including
Fable's thread 44 critique and the cross-arc interpretation amendments.
Fable supports closure in messages 366–368. Astra responded as message 374,
rejecting the proposed fitted-node LR goodness-of-fit test (identically zero)
and qualifying several new claims; see the [review response](docs/goals/049-operational-calibration/fable-closeout-response-2026-09-20.md).
Fable withdrew the earlier claims and proposed a corrected detector in
messages 378–379. Astra accepted the repaired construction and replied as
message 389. The [Arc 4 design brief](docs/arc4-design-brief.md) specifies a
99% auxiliary set, full-grid Berger–Boos adjustment, conditional-score recovery,
one primary discrepancy and a bounded crossed null-block diagnostic.
An independent mathematical check supports the finite-grid marginal guarantee;
conditional realised-table validity is not claimed.

The former detector and screen scope decisions were resolved by Barry's
approvals of Goals 050 and 051 above. Both are now complete; the proposed
model-first pilot and amendment to the confirmation sequence were approved
on 24 September and are now being implemented as Goal 052.

Communication preference from Barry, 20 September: end every closing Codex
message to him with a date-time stamp in Hobart time; interim updates need
no stamp. State whose response is next when reporting Fable–Astra exchanges.

**Arc 3's bounded sampling comparison is closed as a conditional synthesis.**
The [result](docs/goals/046-landscape-sampling-generality/synthesis.md) resolves
no general sampling-design effect at this replication. The principal candidate
exception is lower point error with wider truth-calibrated supports in the
barrier fivefold condition. Coverage and null-truth false-exclusion contrasts
are calibration checks, not evidence of sampling benefit. Fable's review
identified their incorrect use in the initial narrative; the
[correction](docs/goals/046-landscape-sampling-generality/calibration-interpretation-correction-2026-09-18.md)
records that failure of the synthesis and internal review. This is not an
equivalence claim or a blanket ecological null.

Barry delegated the completion choice following Fable's replies 227–228.
The [reporting amendment](docs/goals/046-landscape-sampling-generality/endpoint-amendment-2026-09-18.md)
and [independent review](docs/goals/046-landscape-sampling-generality/endpoint-final-review-2026-09-18.md)
record the boundary. The original four numerical failures remain failures;
exact integration accuracy and replacement-method qualification remain
unresolved. Nested-bank endpoint stability supports only the stated
conditional interpretation, not general method acceptance.

The archive audit and a single 10,000-resample bootstrap refinement are
complete. Nine of 90 archetype intervals nominally exclude zero; seven retain
exclusion under the finite-bootstrap rank check and two remain unresolved.
Those counts include three nominal coverage-check exclusions; they are not
counts of ecological effects or independent discoveries.
Calibration accounts for about 98% of width-contrast variance but only about
50–55% of coverage-contrast variance. No new process/calibration histories,
maps or banks were generated; no larger campaign or new scheduler was launched.
Current changes remain uncommitted; no commit, push or publication authority
is inferred. No Arc 3 computation remains running.

Goal 049 closes under its registered known-nuisance scope. Any stronger
numerical-accuracy or landscape-generalization claim
requires its own bounded qualification. Preserve the conditional Arc 3 result
and its original failures when planning that work.

## Historical numerical closeout (12 September)

The records below retain the pre-amendment stopping decisions. Their former
prohibition on synthesis was superseded by the 18 September delegated
reporting amendment above; their numerical failures and non-adoption remain.

**Goal 048 is complete with a finite-budget numerical failure.** The
infection-order conditional integrator passes exact controls and full-map
arithmetic spot checks. All three independent K1024 connected-width comparisons
pass, but all corridor comparisons fail: generating-rho LR movement reaches
7.7774 against 0.5. The method is not adopted. See the
[results](docs/goals/048-integration-redesign/results.md),
[verification](artifacts/goal048_execution/completed-check.json) and
[independent review](docs/goals/048-integration-redesign/final-review.md).

Both simulations finished at **2026-09-12 04:54:01 UTC** after 47.56 minutes,
using at most 1.850 GiB aggregate RSS. All source/input/output hashes and 78
compact-curve likelihood replays pass. No simulation is running; the Goal 048
completion heartbeat is paused. The next proposed tranche replays existing
corridor order seeds with per-order or batch contributions at six influential
sites to guide variance reduction or a defensible larger budget. It has not
launched. The generating model and composite estimand remain fixed, and no
production requalification or ecological synthesis is authorized.

**Goal 047 is complete with a registered negative numerical-method result.**
Stage A identifies pseudocount sensitivity in the connected-map calibrated
width functional. Within fixed empirical banks, changing alpha over 0.25, 0.5
and 1 moves the balanced-minus-access mean log-width contrast by
0.011805–0.020275, exceeding the 0.01 limit; a support-boundary classification
also changes. Six of nine within-bank alpha comparisons fail. Stage B is
unrun under the prospective stopping rule, and the completion heartbeat is paused.

The corridor profiles pass all within-bank alpha gates (maximum generating-rho
LR movement 0.06291 versus 0.5), but equal-sized bank halves still differ by
about 1.84–1.86 LR at generating speed. This distinguishes conditional
pseudocount sensitivity of calibrated widths from bank-realization sensitivity
of the tail. It does not establish exact integration bias or accept ecological
inference. Read [Goal 047 results](docs/goals/047-integration-validation/results.md),
the [verification receipt](docs/goals/047-integration-validation/completed-check.json)
and [independent review](docs/goals/047-integration-validation/final-review.md).

Stage A ran in 26.58 minutes with peak RSS 3.101 GiB. All source, input and
output checks pass locally and remotely; every reported comparison metric
reconstructs exactly, and saved replay error is at most 1.819e-12. All study
processes have stopped. Current source and evidence are uncommitted.

Goal 046 / Arc 3 remains numerically unresolved: its final K65536/131072
comparison has five ensemble passes and four failures. All nine bundles and
all 216 replay/half-grid rows are verified; every separate grid-refinement gain
passes. The prior [bank-half diagnostic](docs/goals/046-landscape-sampling-generality/split-bank-diagnostic-results.md)
and [numerical diagnosis](docs/goals/046-landscape-sampling-generality/final-bank-diagnosis.md)
remain preserved. Goal 047 does not alter any of those four failures.

Goal 048 completed its integration redesign prototype and bounded retrospective
pilot. Replacement-method adoption and prospective validation remain scientific
review decisions. No changed acceptance rule, map omission,
production restart, ecological synthesis, commit, push or publication is
authorized. The frozen
[registration](docs/goals/047-integration-validation/registration.json) and
[execution record](docs/goals/047-integration-validation/execution-state.md)
retain the study's complete evidence and stopping boundary.

Goal 045 / Arc 2C is scientifically complete after numerical acceptance and
independent final review. Its completion heartbeat remains paused. The result
and evidence below describe that completed arc.

## Scientific result

Across the six frozen synthetic conditions, estimating predator spread speed
produced no detected systematic deterioration in prey-effect recovery relative
to supplying its true value. All 30 paired 95% bootstrap intervals include zero;
this is not an equivalence claim. Both analyses remain weak in the threefold
cases and the slow fivefold case. Usual-speed fivefold effect coverage is 91.6%
in both analyses, despite informative accuracy, width and exclusion.

Rho supports are now numerically accepted on the discrete G201 grid. Coverage
is 96.4% at usual speed and 92.4% at half speed. All are connected and avoid
boundaries. Truth-specific calibration, known detection/background/resistance,
one landscape and fixed observation design remain substantive limits.

Start with [the synthesis](docs/goals/045-spread-prey-oracle-bridge/synthesis.md),
then [Goal 045](docs/goals/045-spread-prey-oracle-bridge/Goal.md) and the
[numerical decision](docs/goals/045-spread-prey-oracle-bridge/numerical-decision.md)
if the execution history is relevant. The [independent review](docs/goals/045-spread-prey-oracle-bridge/final-review.md)
records the acceptance verdict. README and the adaptive roadmap identify
the broader scientific boundary. Earlier handovers remain in Git history;
they describe superseded operational states.

## Evidence and source

- Frozen campaign source: `e8c08f10f7b67118a85ee37770d8ee48ee2c213a`.
- Accepted profiles: `artifacts/goal045_execution/reference65536/output/`;
  131072 numerical reference: `artifacts/goal045_execution/reference131072/output/`.
- Remote roots on `deep-server-ts`:
  `/data/codex/scratch/goal045-full-bank-reference64-20260906-e8c08f1/` and
  `/data/codex/scratch/goal045-full-bank-reference128-20260907-e8c08f1/`.
- The last reference finished successfully at 2026-09-07 16:57 UTC, taking
  14.565 campaign hours plus approximately 13 minutes to extend the bank.
- Both runs contain 250 calibration and 250 evaluation histories per case.
  Their original `timing`/nonproduction receipts are retained. The explicit
  bank amendment accepts the completed 65536 reference as scientific evidence;
  current source changes only the bank-size default.
- Durable tables, figures, numerical comparisons and provenance are under
  `docs/goals/045-spread-prey-oracle-bridge/`; banks/raw arrays remain outside Git.
- Active code: `arc2c_{design,likelihood,campaign,synthesis}.py`, with run,
  numerical-check and synthesis entry points. The path already reuses the
  accepted Arc 2B likelihood kernel and needs no additional framework.

## Prior closeout and current boundary

The final independent audit passed without a material repair. Exact reviewed
paths are published to main under Goal 045's authority; the completion check is
paused. The focused 24-test suite, scoped formatting/Ruff/strict mypy, build,
raw-profile checksum checks and figure inspection passed.

Goal 046 supersedes the earlier instruction to stop after Goal 045 and
authorizes its declared landscape and sampling changes. Paper 1 remains
synthetic-only; unknown detection/background, real data and unrelated
sibling-repository work remain outside scope. Goal 045's exceptional compute
and publication permissions do not silently transfer to the new goal.
Preserve original failed numerical comparisons; they are part of the methods
record, not stale files to erase. The earlier primary-only closeout proposal
was never approved and is superseded by completion of the original criteria.
