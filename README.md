# Latent Landscapes

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
- jointly fitted spread and prey-effect point estimates remain centred near
  truth, but one shared simultaneous uncertainty envelope is too blunt;
  parameter-specific calibration gives informative marginal intervals; and
- the process-based models outperform their fitted neutral baselines on held-out
  observations in the evaluated benchmarks.

These are conditional results, not universal thresholds. They describe one
landscape family, sampling design, survey schedule, process formulation, and
set of generating values.

## Current Scientific Boundary

The single-landscape reference laboratory is now frozen, pending acceptance of
its Arc 1 synthesis. It supplies understood positive controls, reference-case
transition brackets, calibrated marginal uncertainty, an explicit negative
joint-uncertainty result, and held-out neutral comparisons. These findings are
conditional evidence rather than universal thresholds.

The next proposed stage is human review of the completed Goal 038 predator-only
Arc 2A design pack. It translates landscape-resistance contrast into ecological
movement-cost ratios, supplies the exact 16-point Sobol pilot, and estimates
the production workload. No Arc 2 production campaign has been authorized.

Later paper stages must test generality across process and observation
conditions, landscape and sampling families, alternative generating models,
and one synthetic-realistic capstone.

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
  the provisional predator-only design and Goal 038 ecological translation
  awaiting collaborator decisions.
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

## Collaboration

This is research code under active development. Interfaces may change when the
scientific design changes; backwards compatibility is not a programme goal.
Contributions should be narrow, state the scientific question they address,
distinguish observation from inference, and include validation proportional to
the claim being made.
