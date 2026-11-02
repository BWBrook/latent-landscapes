# Latent Landscapes

> **Status:** developed in the open as a working record. This is work in progress: contents may change, and nothing here is peer-reviewed unless stated.

Latent Landscapes is a synthetic research programme for understanding when the
parameters of spatially explicit predator-prey models can be learned from
imperfect ecological observations.

Its central question is:

> Under what landscape, process, and observation conditions are the parameters
> of spatially explicit predator-prey dynamics identifiable and recoverable
> from imperfect data, and how well is inferential uncertainty calibrated when
> the generating system is known?

The immediate scientific product is a synthetic methods paper. Because the
generating process and its parameters are known, failed recovery can be
diagnosed rather than confused with unknown field truth or model
misspecification. Real applications to British mink-water vole dynamics and,
later, Australian murid responses to cats and foxes are separate programme
stages.

## Why A Synthetic Laboratory?

The programme began with a real mink-water vole application, where weak
estimation could have arisen from the ecological model, observation error,
limited data, inference machinery, or some combination of them. An initial
known-truth synthetic example helped separate these causes but proved too small
and geometrically simple to expose the relevant spatial information limits.

Latent Landscapes therefore rebuilds the problem as a sequence of controlled
experiments. Each rung introduces one substantive complication only after the
preceding positive control is understood. Negative or weak-identifiability
results are scientific outcomes, not reasons for unrecorded retuning.

## Current Synthetic System

The present laboratory combines:

- a reproducible 72 by 84 cell landscape with impassable water, low-quality
  matrix, habitat patches, movement corridors, and three western invasion
  sources;
- a fixed access-constrained sampling design with 160 sites divided into
  spatial training and holdout clusters;
- deterministic and stochastic first-passage predator spread;
- a global spread-rate parameter, landscape-resistance contrast, repeated
  imperfect predator detection, and explicit survey windows;
- an absorbing prey-extirpation process parameterized by counterfactual 60-day
  background extirpation risk and a predator-effect multiplier;
- perfect and imperfect prey observation, including cases where predator
  arrival is latent; and
- fitted neutral comparators evaluated on held-out sites.

Inference uses exact or simulation-based likelihood profiles as appropriate.
Uncertainty is calibrated against independent synthetic datasets rather than
assumed to follow a convenient asymptotic reference distribution.

## What We Have Established

Under the current landscape and observation designs:

- global predator spread rate is recoverable across the tested slow, central,
  and fast waves when uncertainty is calibrated at the generating condition;
- resistance contrast is reliably distinguished from uniform movement at the
  moderate and strong tested contrasts, while the weakest contrast remains
  only partly identifiable;
- slow or late waves leave less temporal change inside the survey window,
  reducing precision for detection probability even when spread rate itself is
  recovered;
- a twofold prey effect remains weakly identified, a threefold effect is
  reliably detected but slightly imprecise, and strict recovery begins by a
  fourfold effect at the reference background risk;
- a fivefold prey effect is detected but imprecise at 5% counterfactual 60-day
  background extirpation risk and fully recovered at 11.3% and 20%;
- across 32 prespecified prey-process truths, simple maps learned from the
  first 16 predicted all five operating-performance outcomes in the untouched
  second 16 better than a first-block mean;
- prey-effect recovery remains selective: 3/32 truths met the historical
  full-recovery rule; the reviewed rule separating calibration checks from
  recovery gives 4/32, changing only S08. All 16 truths below a threefold
  effect remain not reliably detected;
- jointly fitted spread and prey-effect point estimates remain centred near
  truth, but one shared simultaneous uncertainty envelope is too blunt;
  parameter-specific calibration gives informative marginal intervals; and
- the process-based models outperform their fitted neutral baselines on held-out
  observations in the evaluated benchmarks.

The [Goal 049 interpretation amendment](docs/goals/049-operational-calibration/interpretation-amendments.md)
retains historical results alongside the revised classification. Same-truth
coverage and null-truth false exclusion are calibration checks. Historical
support widths and non-null exclusions remain conditional on truth-specific
calibration, and cannot be presented as an analyst-usable confidence procedure.
The [completed known-nuisance bridge](docs/goals/049-operational-calibration/synthesis.md)
supplies candidate-wise calibration on the fixed effect grid. All registered
matched-bank endpoint tolerances pass; interior cutoffs are near chi-square,
with lower boundary cutoffs. The realised table has 7.4% null false exclusion
(calibration-aware 95% interval 5.6–9.7%), retained as a quality-control flag.
The marginal rank guarantee is not conditional 95% coverage for this table.

These are conditional results, not universal thresholds. They describe one
landscape family, sampling design, survey schedule, process formulation, and
set of generating values.

## Current Scientific Boundary

Goal 062 is **complete and closed**. The ten-cell campaign finished on
15 October 2026 and passed [independent closure review](docs/goals/062-final-procedure-evaluation/final-review.md)
on 16 October. Its [completed report](docs/goals/062-final-procedure-evaluation/report.md)
contains 5,000 histories, with 500 per cell. Exact-family threefold-effect
declaration rates are 44.4% and 90.8% at the two background-hazard levels;
within-1.5-fold magnitude recovery is 55.0% and 83.2%. These are conditional
results for the registered fixed design and reference panel. The
[execution record](docs/goals/062-final-procedure-evaluation/execution.md)
preserves the launch, repair, completion and return history.

Barry selected **broader first** on 18 October: landscape generality and common
competing background models belong in one substantial Paper 1. The
[reviewed integrated protocol](docs/paper1-integrated-tranche-protocol-2026-10-18.md)
defines the next design. Current numerical development has completed two
[direct-likelihood profile meshes](docs/paper1-direct-profile-development-2026-10-31.md);
[independent-bank and continuous-profile qualification](docs/paper1-profile-bank-qualification-2026-11-01.md)
is complete on those two development histories: all eight profiles and all
five bank comparisons per history pass, with independent review. This is
bounded numerical qualification. Calibration, higher-accuracy integration,
260-site behaviour, the broader challenge suite and production throughput
remain to be qualified. See the
[current handover](HANDOVER.md) for execution status.

The [11 October evidence synthesis](docs/paper1-evidence-synthesis-2026-10-11.md)
records the earlier charter assessment; Goal 062 subsequently filled its
fixed-design operating-performance gap. The full Paper 1 charter remains
incomplete. The original all-null capstone and its forecast misses remain
preserved, and the broader protocol is still a development specification,
not a registered production experiment.

### Evidence progression

The first registered robustness screen is complete:
[Goal 051](docs/goals/051-misspecification-screen/synthesis.md) nominates aligned
background prey-loss variation at the null for independent confirmation.
Primary unflagged estimation failures rise from 19.3% to 42.3% on the accepted
landscape, while the adequacy detector rejects 2.7% of histories. This is a
fixed-table, fixed-bank, known-nuisance result; competing-model discrimination
and independent confirmation remain uncompleted. Strict false effects remain
unflagged in 21.2% of aligned-background histories versus 6.1% at baseline.
Following [Fable's critique and the archive checks](docs/goals/051-misspecification-screen/fable-response-2026-09-24.md),
Astra recommended an adjusted-background pilot instead of standalone
confirmation, and Barry approved that sequence change. The completed
[Goal 052 pilot](docs/goals/052-adjusted-background-pilot/synthesis.md) shows
that adjustment is feasible but does not establish a repair: broad parameter
trade-offs persist, and reduced mean inflation does not consistently improve
multiplicative estimation error or held-out prediction. The
[completed Goal 053 comparison](docs/goals/053-prospective-background/synthesis.md)
uses 1,000 fresh paired blocks under exact and incomplete background models,
with known-beta controls and direct held-out prediction. Adjustment improves
effect estimation under spatially varying background but worsens it under
constant background; predictive gains are smaller than forecast. A
[finite-grid null-effect calibration](docs/goals/054-null-effect-calibration/synthesis.md)
is now complete. The adjusted rule gives 4.2% and 3.2% exact-null declarations
at beta0/.60 and 76.1% and 93.0% threefold sensitivity. It sharply reduces
false declarations in the tested aligned fields, while costing sensitivity
and estimation accuracy under constant background. Its guarantee averages
over reference and evaluation generation at the registered beta nodes; it is
not conditional 5% control for the realised table. The nonlinear stress did
not locate a failure boundary, and Berger–Boos recovered no sensitivity.
[Goal 055 is complete](docs/goals/055-arc4-synthesis/synthesis.md). Its registered
archive checks locate two failures of the frozen procedure: a supplied mean
20% below truth raises adjusted null declarations to 7.8%/10.8%, and persistent
prey-detection SD .20 raises them to 19.8%, versus 3.8% in its paired baseline.
The Arc 4 claim audit, paper draft and three reusable figures are complete.
The [proposed capstone](docs/goals/055-arc4-synthesis/capstone-protocol.md)
therefore selects 60 pre-invasion days and requires shared site-detection
modelling, with observed-data feasibility and new calibration before any truth
draw. [Astra's response to Fable's review](docs/goals/055-arc4-synthesis/fable-response-2026-10-03.md)
recommends adding a scalable calibration route to that feasibility study,
four sealed histories and private key/draw custody outside both agents' access.
On 3 October Barry approved [Goal 056 feasibility](docs/goals/056-observed-nuisance-feasibility/registration-2026-10-03.md),
including scalable calibration as a deliverable, four future sealed histories,
simple protection against accidental exposure and password-manager custody
of his private key. [Goal 056 is complete](docs/goals/056-observed-nuisance-feasibility/synthesis.md):
all 64 main fits and 7,088 profile nodes converged, and independent raw-bank
replay agrees to about 1e-12. A profile-only boundary-rounding repair preserved
all histories and main fits. Effect magnitudes remain variable; this is
numerical feasibility, not recovery or calibrated error-rate evidence.
Goal 056 generated no sealed truth or private key. On 4 October Barry supplied
the public recipient. The [revised pilot proposal](docs/goals/056-observed-nuisance-feasibility/calibration-proposal.md)
includes Fable's two diagnostics. Barry approved the one-hour tranche on
4 October; [Goal 057 is complete](docs/goals/057-screening-retention/synthesis.md).
Its 360,855 pre-only references and 792 diagnostic fits took 6 min 37 s on eight
workers, with independent reconstruction passing. The screen retains 420–990
nodes per public fixture; four-fixture unions contain 577–1,901 nodes, median
1,266. All sixteen known true nodes are retained, a descriptive result rather
than a coverage estimate. The median union projects to 32–39 hours at 64
workers for a later 999-reference effect table. The
[next proposal](docs/goals/057-screening-retention/next-stage-proposal.md)
recommends reviewing one fixed coarser global screen before large calibration.
The early registered-stream preview and postprocessing repairs are disclosed.
Barry subsequently approved [Goal 058](docs/goals/058-effect-reference-micro-pilot/registration-2026-10-04.md):
use beta spacing .25 (765 reference nodes), defer the global-screen change,
and test the complete effect-reference path at four fixed nodes with 999
histories each. [Goal 058 is complete](docs/goals/058-effect-reference-micro-pilot/synthesis.md):
all 3,996 pairs and independent direct-bank checks passed, making all four
tables usable. Production and audit took 29.64 minutes with 7.461 GiB sampled
peak RSS. Linux 209 tests and the independent final review pass. The lower-rate
corner still put 73/999 null effect estimates at the h=10 boundary; numerical
success does not establish effect recovery or calibrated error rates.
Continuous fitting remains unchanged. The
[next proposal](docs/goals/058-effect-reference-micro-pilot/next-stage-proposal.md)
is a bounded 765-node recalibration of the existing local screen; its actual
retention remains unmeasured. Large confirmatory work, the final sealed truth
law and a new map remained separate decisions at that closeout.
Barry subsequently approved [Goal 059 public preparation](docs/goals/059-capstone-preparation/registration-2026-10-04.md):
skip the old-map pilot, allow the complete 765-node union, adopt Fable's public
truth law and prepare a new connected map. The eight-fixture numerical check
and independent review precede Fable's sealed generation.
[Goal 059 closed with a negative map qualification](docs/goals/059-capstone-preparation/synthesis.md):
the first structurally valid candidate's conservative certificate gave 5.350,
above the fixed 5.0 domain. Independent reconstruction reproduced the failure;
no registered bank, public fixture or sealed history was generated. The map and
approved design remain fixed. Post-stop diagnosis places the actual maximum at
4.894, inside the domain. Barry approved
[Goal 060](docs/goals/060-capstone-certificate-recovery/registration-2026-10-04.md)
to refine the certificate to 1,024 intervals on that same map, complete the
unchanged public qualification and prepare a tested sealing script for Fable.
[Goal 060 completed public qualification](docs/goals/060-capstone-certificate-recovery/synthesis.md)
on 5 October: the refined bound is 4.92854, and the 131,072-history bank and
eight-fixture panel passed the complete independent numerical audit. A narrow
audit-interface repair preserved the original failed audit, all generated
outputs and every scientific gate. The tested sealing script's public
preflight passed, enabling Fable's final leak review and sealed generation.
Earlier development deviations remain disclosed and excluded from qualification.
The original nominee remains unconfirmed; earlier numerical failures and
calibration flags remain.

Fable completed the leak review and sealed four histories once on 5 October.
Barry then authorized [Goal 061's blinded training analysis](docs/goals/061-blinded-capstone-training/analysis-plan-2026-10-05.md).
The training adapters and independent audit passed locked-runtime mechanical
qualification on 5 October, including 59 tests, all direct score audits and
checkpoint resumption. Blinded production launched at 13:20 AEDT with 51
workers and finished at 04:51 AEDT on 6 October. All four training audits,
75,735 screening references and 298,701 effect references at 299 nodes passed
their independent numerical audits. The
[completed training report](docs/goals/061-blinded-capstone-training/training-report.md)
records four valid non-declarations, with p_BB values 1, 1, 0.422 and 1, and
no abstentions. This does not establish absence of an effect or generating-value
recovery. The [training lock](docs/goals/061-blinded-capstone-training/training-lock.md)
binds the returned evidence, independent claims review, figures and unchanged
prereveal commitments. Claude (historically Fable) accepted the exact lock in
thread-53 message 1054 on 6 October after independently verifying all 3,734
bound files. Three mechanical
interface failures are preserved in the
[execution record](docs/goals/061-blinded-capstone-training/execution.md).
The blinded training endpoint is complete. Barry released the committed
holdout on 8 October. The [combined report](docs/goals/061-blinded-capstone-training/complete-report.md)
scores all 16 frozen fits without refitting: one of the four leading-pair
forecasts matches, while the other three miss. Case-01's 10.51-nat adjusted
training gain reverses to about a 1.85-nat held-out disadvantage. The independent
direct-bank audit reproduces every winner set and forecast outcome. These
four descriptive comparisons do not establish generating-model identity or
operating rates. The independently reviewed complete report was
[locked before truth release](docs/goals/061-blinded-capstone-training/complete-report-lock.md).
Claude accepted it in thread-53 message 1278 on 9 October, after which Barry
released truth. The [truth assessment](docs/goals/061-blinded-capstone-training/truth-report.md)
finds all four h values equal to 1; cases 00 and 03 are exact-family, while
cases 01 and 02 are B100-A. All four null-class forecasts match, but two branch
forecasts miss. Three mu forecasts and all four detection-SD forecasts match
their truth-law grid values. The unchanged procedure made no false declaration
in this panel. These four null realizations provide no positive-effect power
or recovery evidence, and the B100-A outcomes do not extend the exact-family
guarantee. Original reports, forecasts and locks remain unchanged.

The single-landscape reference laboratory and its Arc 1 synthesis are frozen
and accepted. They supply understood positive controls, reference-case
transition brackets, calibrated marginal uncertainty, an explicit negative
joint-uncertainty result, and held-out neutral comparisons. These findings are
conditional evidence rather than universal thresholds.

Arc 2A has now evaluated 32 prespecified predator-only truths spanning spread
rate, resistance contrast, and detection probability. The first 16 truths were
used to learn transparent low-order relationships; predictions were frozen
before the second 16 were generated. Detection precision, resistance
precision, resistance exclusion, and predictive advantage all predicted that
new block better than a first-block mean comparator.

Across all 32 truths, point estimates met the accepted error limits and every
process model outpredicted its fitted time-only neutral baseline. Two truths
had broad resistance intervals, but the second occurrence was predicted before
it was observed. One truth retained an isolated calibrated-coverage flag.
Boundary-contact probability did not generalize as a smooth surface and is
therefore reported only as an observed support-topology diagnostic. Arc 2A is
scientifically closed and its active code has been consolidated into design,
campaign, and synthesis components. Further local interpolation is not
recommended.

Arc 2B has likewise evaluated 32 prespecified prey-effect truths spanning a
1.5- to 6-fold predator effect, 5-20% counterfactual 60-day background prey
loss, and 0.35-0.85 known prey detection. Five transparent surfaces learned
from `S01-S16` all generalized prospectively to the frozen `S17-S32` block.
Effect strength was the dominant transition, while greater event yield and
better prey detection improved accuracy, precision, topology, and predictive
separation. These are maps of where recovery succeeds or fails, not evidence
that recovery is universal: 3/32 truths were fully recovered, 10/32 detected
the effect without meeting every strict gate, and 19/32 were not reliably
detected.

The Arc 2B null comparison was amended transparently after the pilot but before
prospective simulation. The primary comparator now uses the same known
background hazard as the fitted process model; a separately fitted neutral is
retained descriptively. Exact replay confirmed that no simulated history,
calibration statistic, cutoff, or non-score result changed. Arc 2B is now
scientifically closed and consolidated.

Arc 2C is scientifically closed after independent review of its six-case
comparison. Estimating spread speed produced no detected systematic deterioration
in prey-effect recovery: all 30 paired bootstrap intervals include zero. This
is not equivalence. Both analyses remain weak in the threefold cases and the
slow fivefold case, and usual-speed fivefold effect coverage is 91.6% in both.
The result conditions on known detection/background and one landscape/design.
The 65536-draw integration bank passes the unchanged criteria against 131072;
earlier numerical failures and the grid/bank amendments remain documented.
See the [scientific synthesis](docs/goals/045-spread-prey-oracle-bridge/synthesis.md)
for the six-case table, figures, uncertainty, numerical evidence and limits.

Arc 3's bounded comparison is complete as a
[conditional scientific synthesis](docs/goals/046-landscape-sampling-generality/synthesis.md)
under [Goal 046](docs/goals/046-landscape-sampling-generality/Goal.md).
Across nine maps in three seed-matched archetype triplets, balanced versus
access-constrained sampling shows no general effect resolved at this
replication. The barrier fivefold condition is the principal candidate
exception: lower point error but wider truth-calibrated supports. Coverage and
null-truth false exclusion are calibration checks, not sampling-benefit
endpoints; see the [interpretation correction](docs/goals/046-landscape-sampling-generality/calibration-interpretation-correction-2026-09-18.md).
This is not an equivalence claim or a blanket ecological null.
The bootstrap intervals condition on the supplied maps and truth-specific
calibration; they do not establish generality to a landscape population.

The [18 September amendment](docs/goals/046-landscape-sampling-generality/endpoint-amendment-2026-09-18.md)
and [independent review](docs/goals/046-landscape-sampling-generality/endpoint-final-review-2026-09-18.md)
permit this conditional archival reporting. The original K65536/131072
numerical qualification still fails four maps, despite small endpoint
movements relative to bootstrap SE and passing sampled local grid checks.
Exact integration accuracy remains unresolved. The
[original diagnosis](docs/goals/046-landscape-sampling-generality/final-bank-diagnosis.md),
[Goal 047 regulariser sensitivity](docs/goals/047-integration-validation/results.md)
and [Goal 048 failed corridor qualification](docs/goals/048-integration-redesign/results.md)
remain visible. No replacement integrator is adopted and no expanded campaign
is launched by this closeout.

Later paper stages include alternative generating models and one
synthetic-realistic capstone.

No result in this repository is yet a claim about real mink, water voles,
Australian murids, cats, or foxes.

## Programme Trajectory

1. **Synthetic methods:** establish identifiability, recovery, calibration, and
   model-discrimination limits while truth is known.
2. **British mink-water vole application:** apply the accepted workflow to a
   comparatively constrained real system.
3. **Australian predator-prey application:** extend the approach to sparse,
   heterogeneous evidence on murids, cats, and potentially foxes.

Study systems become more complex as our ability to model and infer from sparse
data improves.

## Start Here

- [Paper 1 experimental design charter](docs/paper1-experimental-design-charter.md):
  the governing scientific claim, scope, evidence pillars, and definition of
  done for the synthetic methods paper.
- [Paper 1 adaptive implementation roadmap](docs/paper1-adaptive-implementation-roadmap.md):
  the research arcs, decision gates, sensitivity-design strategy, and
  consolidation cadence.
- [Arc 1 reference synthesis](docs/arc1-reference-laboratory-synthesis.md): the
  frozen evidence, claims, boundaries, and standard evaluation surface.
- [Arc 2 recoverability design brief](docs/arc2-recoverability-design-brief.md):
  the ecological translation and staged design underlying the accepted
  predator-only experiment.
- [Team briefing](docs/presentations/2026-08-13-team-briefing/index.html):
  an 11-slide visual overview of the programme, main results, and trajectory.
- [Programme record](docs/programme.md): the detailed historical ladder and
  status of the experimental sequence.
- [Provenance](docs/provenance.md): how selected parts of the earlier SpatExt
  work were adapted without creating a runtime dependency.
- [Rebuild decision](docs/decisions/0001-rebuild-from-spatext.md): why this
  repository was started as a clean scientific rebuild.
- [Goal records](docs/goals/): prespecified questions, decisions, validation,
  and outcomes for individual experiments.

The presentation is an ordinary static web page. Open its `index.html` directly
or follow the launcher instructions in its local README.

## Installation And Checks

The project uses Python 3.12 or later and
[uv](https://docs.astral.sh/uv/):

```bash
uv sync --all-groups --frozen
uv run pytest
```

Focused quality checks are:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv build
```

Scientific workflows are exposed as scripts under `scripts/`. For example,
the foundational deterministic benchmark can be regenerated with:

```bash
uv run python scripts/run_goal001.py
```

The retained Arc 2A workflow is exposed through:

```bash
uv run python scripts/run_arc2a_campaign.py --help
uv run python scripts/synthesize_arc2a.py --help
```

The retained Arc 2B workflow is exposed through:

```bash
uv run python scripts/run_arc2b_campaign.py --help
uv run python scripts/synthesize_arc2b.py --help
```

The current Arc 2C workflow uses `scripts/run_arc2c_campaign.py`,
`scripts/check_arc2c_numerics.py`, and `scripts/synthesize_arc2c.py`.
Goal 045's accepted bank uses 65536 draws on the repaired 201-point rho grid.
Its saved full-ensemble profiles support replay without further simulation.

Later production experiments can be computationally expensive and may depend
on accepted evidence from earlier runs. Read the corresponding goal record and
script help before launching one.

## Repository Layout

```text
src/latent_landscapes/   Scientific models and inference code
scripts/                 Reproducible experiment entry points
tests/                   Focused scientific and implementation checks
docs/goals/              Prespecified experiment records and outcomes
docs/presentations/      Collaborator-facing briefing material
docs/decisions/          Durable programme decisions
artifacts/               Generated evidence packs, ignored by Git
```

Generated review packs and build outputs are intentionally not committed unless
a specific communication or provenance need requires them. A fresh clone
contains the code and durable scientific record, not every production
realisation.

The active Arc 2 workflows follow `design -> likelihood -> campaign -> synthesis`;
Arc 2B keeps its shared likelihood kernel in the campaign module. Arc 2A's
predator likelihood and support calculations live in `arc2a_likelihood.py`.
Older numbered modules remain where they supply live kernels or reference
benchmarks. Superseded Goal 012–013 and 018–025 runners are preserved in Git
history through `abcd080`; their goal records and generated evidence remain
available. Historical instructions in those records apply to their recorded
source versions.

## Collaboration

This is research code under active development. Interfaces may change when the
scientific design changes; backwards compatibility is not a programme goal.
Contributions should be narrow, state the scientific question they address,
distinguish observation from inference, and include validation proportional to
the claim being made.

## Licence

Code is released under the [MIT Licence](LICENSE). Text, figures and data created for this project are released under [CC BY-SA 4.0](LICENSE-CONTENT). Third-party material keeps its own terms where stated.
