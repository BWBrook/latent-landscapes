# Latent Landscapes: Successor Handover

## Current execution update: 6 September 2026 (Hobart)

The earlier failed-preflight snapshot below is historical. Bounded diagnosis
identified rho-grid resolution as the leading numerical issue. The repaired
201-point grid preserves the scientific design and is documented in Goal 045.
Source `ce368b36824b51b859e1136b60c95fe4b9d35a15` is frozen and pushed to main;
17 relevant tests, Ruff and strict mypy passed.

The repaired-grid workflow stopped at `preflight_gate` at 2026-09-05 16:23 UTC.
All four-history grid checks passed (maximum LL gain 0.0741); one shared
calibration predator history failed the bank spread-profile LR tolerance
(1.012 versus 0.5). Production has not started. Its preserved evidence is at:

- Host: `deep-server-ts`; original tmux session `ll-goal045-rho201` has ended.
- Run root: `/data/codex/artifacts/goal045-rho201-20260906-ce368b3/`.
- Status: `workflow.status`, `workflow.stage`, `workflow.exit.status`.
- Evidence: `timing/`, `numerical_canary.json`, `numerical_canary.npz`,
  `preflight_gate.log`. Production `output/` is absent.

**Active diagnostic:** nested-bank predator-marginal screen, launched at
2026-09-05 16:43 UTC and verified `RUNNING` with seven 4096-draw chunks started.

- Host/session: `deep-server-ts`, tmux `ll-goal045-bank`.
- Root: `/data/codex/scratch/goal045-bank-convergence-20260906-ce368b3/`.
- Probe `status`, `exit.status` and `run.log` once while running, then end the wake.
- On success inspect `output/predator_bank_convergence.json`,
  `output/predator_profiles.npz` and `output/bank_provenance.json`; preserve and
  reuse `output/base_arrivals_32768.npy`. These are diagnostic predator-only
  profiles over all 201 rho values and all four paired timing histories.
- Next: assess 16384 versus 32768, then certify with the full joint likelihood,
  all 181 effect values and all six paired cases in the fixed union of relevant
  LR<=10 windows plus neighbouring cells. Keep the numerical limits, including
  MLE/truth-LR stability and support topology/endpoints. Document a supported
  numerical bank amendment before production. The screen alone is insufficient.
- Quiet two-hour heartbeat: `goal-045-completion-check`, attached to the current
  successor task and updated to follow this diagnostic. Diagnose failure
  before rerunning. After production retrieve evidence, check eventual calibrated
  cutoffs against the canary LR<=10 range, synthesize with 1000 paired
  whole-dataset bootstraps, inspect figures, obtain independent final scientific
  review, and publish the exact accepted paths. Pause the heartbeat at completion
  or a required human decision. No new approval is needed for these stages.

Four frozen timing histories (two calibration, two evaluation) now support the
bank/grid canary, with all six cases kept paired. Original failed-run evidence
is preserved. Goal 045 is still scientifically unfinished.

## Historical handover snapshot

Prepared 5 September 2026 for a fresh task started directly in
`/Users/bwbrook/papers/latent-landscapes`. Remote state was verified at
approximately 08:35 UTC; the Git/automation notes include Barry's subsequent
branch-cleanup request.

**Immediate state: Goal 045 is approved but unfinished. Its numerical
preflight stopped before production. Diagnose that bounded issue next;
do not restart the programme or launch an unchanged campaign.**

## Start Here

Read the current global `~/.codex/AGENTS.md`, then these repo files in order:

1. [AGENTS.md](AGENTS.md): scope and authority.
2. [README.md](README.md): present scientific system and accepted findings.
3. [Paper 1 charter](docs/paper1-experimental-design-charter.md): the North Star
   and paper-level definition of done.
4. [Adaptive roadmap](docs/paper1-adaptive-implementation-roadmap.md): the arcs;
   its last Arc 2C design gate has now been resolved by approval of Goal 045.
5. [Goal 045](docs/goals/045-spread-prey-oracle-bridge/Goal.md): current contract
   and execution record. This handover supplies the latest operational snapshot.

Do not read the entire old conversation, every historical goal, or the legacy
repo for orientation. Consult history when a specific question needs it.
Current code and evidence outrank this dated snapshot.

## Scientific Direction

Our question is: **under what landscape, process and observation conditions
are spatial predator-prey parameters identifiable and recoverable from
imperfect data, and is their reported uncertainty calibrated?**

The agreed publication sequence is synthetic methodology first, British
mink-water vole application second, and Australian murid responses to invasive
cats and potentially foxes third. Barry's collaborators are Natalie Briscoe,
Damien Fordham and Ryo Ogawa. Their contributions may now appear in the private
repo; preserve others' work and inspect Git state before editing.

Early real-data work and an overly simple synthetic system motivated this
controlled rebuild. The old `/Users/bwbrook/papers/spatext` is a read-only
laboratory notebook/parts catalogue, not a dependency or architecture to retain.
Its goal numbers are unrelated to this repo's. The old `mink` action task is
retired. Chief of Staff is not the technical control surface for this project.

The current reference landscape is a reproducible 72 x 84 grid with water
barriers, matrix, patches, corridors and three western sources. Sampling uses
160 access-constrained sites and spatially separated training/holdout clusters.
The model combines stochastic predator spread, habitat resistance, imperfect
repeated detection and absorbing prey extirpation. `rho` controls spread speed;
`eta` controls resistance contrast; the prey-effect multiplier increases loss
hazard after predator arrival. Hazard multipliers are not loss probabilities.

Accepted milestones, conditional on this landscape/model/design:

- **Arc 1 is frozen:** understood recovery controls for spread, resistance,
  detection and prey effect. Weak signals can remain unidentifiable. Locally
  calibrated, parameter-specific intervals were more useful than the tested
  broad simultaneous envelope. See the linked README and Arc 1 synthesis.
- **Arc 2A is closed:** 16 predator-process truths informed simple performance
  maps, then 16 untouched truths tested them prospectively. Useful predictive
  relationships emerged; boundary-contact topology did not generalise as a
  smooth surface.
- **Arc 2B is closed:** the equivalent 16+16 prey-effect experiment varied effect,
  background loss and known detection. All five performance maps beat their
  frozen mean comparator prospectively, but biological recovery remained
  selective: 3/32 truths fully recovered, 10 detected without meeting every
  strict gate, 19 not reliably detected. Successful prediction of recoverability
  is not successful recovery everywhere.

Later arcs test landscape/sampling generality, a small alternative-model set,
and a synthetic-realistic capstone, followed by synthesis and consolidation.
We have not completed those or established universal recovery thresholds.
Do not expand the present bridge into that whole programme.

## How To Collaborate With Barry

Use these skills selectively:

- [Twilight Laboratory](/Users/bwbrook/.codex/skills/twilight-laboratory/SKILL.md):
  align on the consequential endpoint and authority, then execute internal
  stages autonomously. Return at the gold stamp, a genuine scientific decision,
  or a real blocker; not for another routine `proceed`.
- [Kill Your Darlings](/Users/bwbrook/.codex/skills/kill-your-darlings/SKILL.md):
  consolidate the active path at meaningful boundaries. Retain code/tests for
  current consumers and distinct consequential risks, not historical comfort.

The rule is **rigour at the scientific decision boundary; proportional
engineering everywhere else**. Complete the useful end-to-end tranche, perform
one serious review/material repair pass, and stop optional polishing. Negative
results are results. Do not retune truths or remove inconvenient gates to obtain
a favourable result. Match comparators' information and nuisance assumptions.

Use native subagents for genuinely independent implementation or review, under
current global policy. Do not revive old model-routing tables, named persistent
executors, thread-tool dependencies, or elaborate approval ladders. Verify key
claims directly. Explain results in ecological language with defined quantities
and self-contained figures; Barry has repeatedly corrected opaque technical
summaries that hid the actual scientific question.

## The Approved Bridge: Goal 045 / Arc 2C

Question: **how much harder is prey-effect estimation when predator spread
speed must also be estimated rather than supplied correctly?** Compare both
analyses on identical simulated observations.

- Six cases: usual/half speed (`rho=1/0.5`) crossed with prey effects `1/3/5`.
  The 1x cases are no-effect controls.
- Keep resistance fixed at 1, both detection probabilities known at 0.65, and
  background hazard known at 0.002/day (11.3% loss risk over 60 days without
  predators). Six survey times, two visits each, zero false positives.
- All fitting uses 120 training sites; 40 holdout sites score prediction only.
  Older all-160-site recovery summaries are context, not exact replay targets.
- Realised predator arrival remains latent in both analyses. Integrate the
  same candidate arrival jointly across both species within a site. Across
  sites use the established marginal composite likelihood.
- Production plan: 4096-draw integration bank; 250 calibration and 250 independent
  evaluation datasets per case; paired random streams; parameter-specific
  calibrated intervals; 1000 whole-dataset paired bootstrap resamples of both
  calibration and evaluation. Calibration still knows the generating condition.
- Primary prediction is held-out prey prediction conditional on predator
  observations, against an information-matched no-effect model. The no-effect
  model's conditional prey score is independent of speed. This avoids the
  comparator asymmetry found and transparently amended during Arc 2B.

Gold stamp: an interpretable six-case paired comparison with uncertainty,
numerical checks, clear tables/figures, independent final review, bounded
consolidation and authorised publication. Weak/negative recovery can satisfy it.
Unknown background/detection, new landscapes/truths, extra surfaces and Goal 046
are outside scope. Material scientific changes or projected runs over 24 hours
need Barry. Routine numerical repair within the question is ours to resolve.

## Exact Handoff State

At Barry's explicit request, the handover checkout uses **`main` only**, with
the former goal branches consolidated and removed locally and from origin.
Their commit history is preserved. Goal 044 commit `4d6d23b` remains the last
scientifically accepted checkpoint; the unfinished Goal 045 source and handover
through `07737e7` are now included on `main` for continuity, not as an acceptance
claim. This branch cleanup does not close Goal 045 or relax its review gates.
Frozen run source is `b67e5e6cf0f7d297883c265dd5c245ce1f90ea5e`; subsequent
handover/cleanup commits change documentation, not simulation code.

Active code is `src/latent_landscapes/arc2c_{design,likelihood,campaign,synthesis}.py`.
It reuses the accepted Arc 2B likelihood kernel. CLIs are
`scripts/run_arc2c_campaign.py`, `scripts/check_arc2c_numerics.py`, and
`scripts/synthesize_arc2c.py`. Pre-launch review and 28 focused tests, scoped
Ruff/mypy and build passed. Those checks do not establish scientific completion.

**Newly verified result:** timing succeeded in 566.7 seconds; the workflow then
stopped at `preflight_gate` with exit 1. Production output is absent and the
workflow tmux session is gone. It was not a crash during production.

For the first preselected evaluation history across the six cases, doubling
the bank to 8192 changed profile likelihood-ratio values by less than 0.038.
However, local half-grid refinement improved the joint maximum log likelihood
by about 1.19-1.25 in all three usual-speed cases, exceeding the 0.25 review
limit. Known-speed gains were negligible; slow-speed cases passed. This points
to spread-speed grid resolution near the peak, **an interpretation to diagnose**,
not evidence that the ecological model failed. No repair or rerun was started
during this handover.

Remote locations on `deep-server-ts`:

- Timing, base bank and first-history profiles:
  `/data/codex/scratch/goal045-timing-20260905-b67e5e6/`.
- Workflow, canary and reserved production directory:
  `/data/codex/artifacts/goal045-production-20260905-b67e5e6/`.
- Read `workflow.status`, `workflow.stage`, `workflow.log`, and
  `numerical_canary.json`; timing inputs are under `output/`.
- Compact local copies: `artifacts/goal045_execution/numerical_canary.json`
  and `timing_run_summary.json`. These and raw outputs remain ignored.

The old task's two-hourly heartbeat, `goal-045-completion-check`, was paused and
then **deleted** during the authorised cleanup. Its Chief of Staff worktree was
also removed. The project checkout and scientific evidence remain intact.
After taking ownership, arrange a quiet scheduled continuation in the new task
if needed. The old task's Codex goal remains unfinished; it was not falsely
closed for handover. Execution ownership passes to the successor.

## First Useful Actions

1. Verify current Git/run state and inspect the existing canary evidence.
2. Diagnose the grid-resolution issue using the saved timing bank/histories.
   Prefer the smallest numerical repair that answers the approved question;
   do not blindly enlarge every grid or rerun unchanged checks. Preserve the
   original evidence and record any justified amendment before production.
3. After numerical acceptance, freeze source and run the same six-case campaign.
   Use `uv run --frozen`; check remote-compute guidance in
   `/Users/bwbrook/work/nectar` before dispatch. Mac mini is the control host;
   `deep-server` is the CPU-work default. Never infer completion from a stale
   status file alone or restart merely because monitoring timed out.
4. Retrieve/verify evidence, synthesize, inspect findings and figures, obtain
   independent final review, then publish exact accepted paths under Goal 045's
   existing authority. Keep raw profiles and bulky outputs out of Git. Update
   the README/roadmap at scientific closeout, not at every internal step.

Bring Barry a clear result and recommendation. The purpose of the fresh task
is better judgment with less historical burden, not another architectural reset.
