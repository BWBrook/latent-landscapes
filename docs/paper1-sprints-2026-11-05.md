# Two dependent sprints: revised execution envelope

5 November 2026. Codex review of Claude's proposal 2897, following Barry's
request for greater autonomy and subsequent direction toward multi-node PBS
execution on kunanyi. This is the revised plan for Claude's Sprint 1 and
Codex's Sprint 2; neither sprint was launched in this review turn.

The sequence is right: Claude develops the candidate and executable design;
Codex independently reviews, qualifies and trains it; both cross-review and
reconcile before validation is opened. Keep that division rather than moving
the solver back to its previous author. Independent subagents can resolve
scientific reviews inside each sprint without sending routine choices to Barry.

The successful joint endpoint is a **reviewed validation packet ready to
freeze**, including measured costs, trained rules and their development evidence.
A failed qualification or a scientifically inadequate training result is a
valid alternative endpoint, with the failed evidence and a concrete next design.
Readiness cannot be promised regardless of the results.

## Working system

Use this document, the existing handover and evidence directories. Each owner
works through the entire sprint to its exit, committing coherent milestones,
using bounded delegates and reporting consequential findings. No new workflow
framework, standing monitor or per-stage permission exchange is needed.

Handover supplies the exact candidate commit, packet, receipts, unresolved
issues and next executable command. A board post is a handover record, not a
mechanism that automatically wakes another agent. Once active, the receiving
agent proceeds within this envelope without another routine approval request.

Independent review precedes the outcomes it protects. Review the numerical
method, qualification design **and experiment/training design** before their
respective first outcomes. Codex can repair objections in Sprint 2; a
substantive repair by Codex receives independent subagent review before use.
Late cross-review supplements these checks, rather than retroactively replacing
them. Any later method change invalidates affected qualification/training
outputs and requires the corresponding replay before validation can open.

Preserve registered histories and failures. Revisions after qualification
outcomes are recorded deviations even if training has not begun. Engineering
repairs, resource allocation and implementation details stay with the agents.
Changes to central scientific scope or the primary model receive independent
scientific review; unresolved priority/taste disagreements go to Barry with a
recommendation. Mere expense does not justify quietly weakening the science.

## Sprint 1 — Claude: candidate procedure and executable experiment

**Mode diagnosis and repair.** Start with the four frozen outer vectors and
the identical-parameter witness. Historical latent vectors were not retained:
there is no serialized old warm vector to reconstruct. Predeclare and serialize
new start vectors/recipes. Allow overlapping diagnoses and an unresolved class;
multimodality is a hypothesis, not an established explanation of the large
gradients. Inner convergence and Hessian conditioning remain live alternatives.

Define the full score as a function of h, alpha, beta, sigma, detection SD,
data, arrival bank, evaluator settings and deterministic start/branch policy.
Define the failure result too. Warm caches must not silently change either.
A materially superior extra warm candidate needs deterministic verification
or an unresolved outcome under the frozen rule, not a successful result with
an advisory flag. Test reordered evaluations, warm/cold calls and cache reuse.

The current branch selector maximises the joint objective; the Hessian term
then changes the Laplace contribution. Specify which quantity selects a branch.
A multimode sum changes the criterion and needs an independently reviewed rule
for duplicate/overlapping modes, stationarity, positive-definite Hessians and
derivatives near mode changes. Do not add it automatically as a solver fix.
Prefer the simplest specified procedure the diagnosis supports.

Implement the narrow pointwise tie-contact rule from Turn 9, keeping the raw
envelope score. The h=30 rounding defect is already fixed: retain its
regressions, do not reopen it without a new failing witness. Fourteen live
endpoint/outside-domain checks passed in this review.

**Diagnostic replay and consolidation.** Replay the two unresolved profiles
after any solver repair. A contact-only change can re-evaluate existing receipts;
it does not require refitting all twelve search and six bank failures. If the
score/solver changes, invalidate and replay affected numerical evidence. These
old cases remain diagnostics, never fresh qualification.

Build one analysis entry point returning the six free/null fits, failure class,
spatial score/profile evidence and **cutoff-indexed set construction**. Final
intervals depend on the subsequently selected C_I cutoff. Existing development
PanelSearch uses only c=3.84, so qualification must cover the prospective grid
or a justified whole-profile guarantee. Bracketed root finding does not discover
missing components: retain adaptive peak, switch and topology discovery,
domain contacts and tighter replay. R1 is a fixed benchmark, not a trained rule.

**Experiment packet.** Freeze the T construction and amplitude using permitted
geometry/planning evidence; temporal stress; distributions and admissibility;
30 development maps total (ten per archetype); seed namespaces; observation
masks and pairing; cutoff grids/ties; history-allocation rule; failure taxonomy;
forecast inputs; and claim denominators. Validation seed commitments remain
unopened and validation maps/outcomes ungenerated through reconciliation.

Qualification, training and validation have distinct identities. Maps inspected
for qualification are not untouched rule-training/validation evidence. Any
qualification reuse must be explicitly labelled development use and reviewed;
prefer separate qualification maps. Retain infeasible map seeds and distinguish
geometry failure from conditional fit failure.

Freeze the fresh qualification panel, base/random and enriched denominators,
site counts, archetypes, relevant backgrounds and effect support through the
fitted boundary. Define the failure-rate gate's unit, threshold, uncertainty
and clustering. Correlated arms/fits are not independent replications. Freeze
any permissible stratum-specific continuation and its claim scope beforehand;
otherwise failure triggers repair, not retrospective removal of difficult strata.

Retain all six truths h={1,2,3,4,5,10} for magnitude inference. A predeclared h=1/3
pipeline/cost batch can precede the remaining truths, but cannot become final
interval training or validation sizing for the six-truth claim.

Specify whether simpler-family calibration covers declaration only or also
magnitude intervals; the latter needs additional profiles. Fix a measured-cost
rule for any proposed bootstrap redesign before main outcomes, with independent
review of changed comparison meaning. Keep the existing matched bootstrap
comparison until such an amendment is accepted.

**Compute and manuscript.** Make the PBS target pilot and production driver
part of Sprint 1, alongside the pitch, six-figure alternative-outcome captions,
claims ledger, two-page brief outline and reusable agent-guide outline. Measure
the complete entry point at 120/260 sites on compute nodes, not merely a
single fixed-h solve or a Mac timing. Record wall/CPU time, memory, bank/data
I/O and numerical equality with the reference. Prepare portable locked source,
PBS resource requests, failure/resume logic and a measured campaign estimate.

**Exit:** versioned candidate code, reviewed experiment and sampling rules,
measured execution plan, frozen fresh qualification manifest and manuscript
scaffold. No rule-training or validation outcomes inform that packet.

## Sprint 2 — Codex: qualify, train and assemble validation packet

The entry review covers the solver/contact semantics, full cutoff-grid topology,
fresh qualification and the experiment/training packet, not only sections 1.2
and 1.7 of Claude's draft. Fix within the sprint and obtain independent review
of changed scientific choices before outcomes; no routine round trip to Barry.

Run qualification on PBS. Reconcile scheduler exits with complete case receipts
and scientific gates. If it fails, diagnose, record the deviation, review one
bounded repair and test on a new frozen panel. If that fails, close with an
informative negative result and revised proposal. A different primary family
is a scientific redesign, not an automatic fallback hidden in execution.

After qualification, run the frozen training design and allocation rules.
Evaluate R1; select R2 and C_I using the agreed objectives and equal-map
weighting. Preserve numerical failures as failures/noncoverage. Hold out whole
maps for cross-validation and repeat cutoff selection and forecast fitting
inside each training fold. Do not evaluate an all-map-trained rule as if it
were held out. Complete all six truths and the declared comparator scope.

Estimate map/within-map variability and apply the existing frozen precision
rule for validation counts. One hundred histories is a costing illustration:
at a Bernoulli rate .05 its per-map MCSE is about .0218; .005 requires about
1,900 independent histories (10,000 near rate .5). Actual planning retains
paired covariance and map variation; more histories cannot replace maps.

Close with learned rules, forecasts, evidence, counts, seed commitments and a
draft validation packet. Cross-review each other's sprint and repair affected
products. Only reconciliation of the final immutable method and packet permits
opening validation; selection changes after that require fresh validation.

## PBS plan and cost evidence

Barry's explicit direction in this chat makes kunanyi the primary route for
large qualification and training work. Use independent task batches across
PBS nodes; distributing each small latent solve across nodes is unnecessary.
Group work by map/bank where useful, pack independent workers within measured
node memory, fix numerical-library threads, and avoid millions of tiny jobs.
Keep immutable task/seed identities, per-case results and failed attempts;
resume only reconciled missing/failed execution work, never silently replace
scientific failures. Stage/cache large shared inputs to avoid an I/O bottleneck.

Scale a representative compute-node pilot to several nodes and then request
hundreds/thousands of CPUs within verified queue/account policy. Measure
scaling efficiency and queued versus running time. Source and environments,
file sizes/hashes, runtime exits and case receipts must verify before promotion.
Operational access details and quotas belong in the private control plane.

Claude's hypothetical arithmetic is correct: 30 maps × six backgrounds ×
two mu values × six truths × 100 histories gives 216,000 biological histories,
648,000 paired-arm datasets and 3,888,000 free/null fit outputs. At eight
minutes per spatial profile alone this is 86,400 CPU-hours:

| Concurrent CPUs | Ideal profile-only days |
|---:|---:|
| 40 | 90 |
| 1,000 | 3.6 |
| 2,000 | 1.8 |

These are scenarios, not forecasts or reserved capacity. They exclude other
profiles, qualification, retries, cross-validation refits, bootstrap, I/O and
queue delay. Current shared-host lean-search medians are 62.20 minutes for
120-site cases and 255.03 minutes for 260-site cases, before post-search work.
Those measurements are not cluster forecasts either; they show why eight
minutes cannot be treated as an achieved benchmark.

The read-only access attempt in this review did not establish an authenticated
cluster session; no live queue/quota query or PBS submission was made. Sprint 1
must resolve access and inspect current limits before its compute-node pilot.
This setup work can run alongside the numerical/design work.

Evidence: [cost arithmetic and observed times](evidence/paper1-sprints-2026-11-05/cost-scenarios.json),
[reproduction script](evidence/paper1-sprints-2026-11-05/cost_scenarios.py),
[Turn 9 diagnostic evidence](paper1-procedure-review-2026-11-05.md) and the
[governing protocol](paper1-integrated-tranche-protocol-2026-10-18.md).
