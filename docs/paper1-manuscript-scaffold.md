# Paper 1 scaffold: pitch, figures, claims ledger, brief and agent guide

5 November 2026. Claude (Opus 5.5), Sprint 1. This scaffold is written before
any rule-training or validation outcome exists. Every caption is stated for
each outcome that could occur, so the results choose the sentence; the
sentence is not written to fit the results. The claim IDs below form the one
ledger that the article, the brief and the agent guide all cite.

## Working title and pitch to the editor

**Working title:** *Measuring an invader's impact from imperfect surveys:
monitoring design and model choice decide what can be known.*

> Ecologists routinely ask how much an invading predator harms native prey,
> using counts from sites the predator reaches at different times. The answer
> depends on a quantity nobody observes: how prey would have fared anyway.
> Using landscapes where the truth is known, we test, across many independent
> maps, when standard monitoring designs and background models recover the
> true impact and when they fail. We report how reliably each recipe detects
> a real effect, how accurate its estimates are, and whether its stated
> uncertainty can be trusted. Three practical choices are at stake. Is it
> worth surveying before the invader arrives, or is the same effort better
> spent on more sites? Does a more flexible background model help, or does
> it soak up the very signal being measured? Can a project tell in advance,
> from planning information alone, whether its design will work? The results
> are a set of measured error rates, and the conditions under which they
> hold, that a manager can use before committing field effort.

The pitch must survive the results. If pre-invasion surveys turn out not to
help, or flexible models fail, those findings are the headline.

## The six figures

Each figure answers one question from the protocol. Denominators include
every registered dataset; failures are shown, not dropped.

**Fig. 1: Where the information comes from.** A schematic of one synthetic
landscape: invasion front, survey sites, arms A, B and C, the six
backgrounds, and the established recovery ladder (spread, detection,
impact). *Caption:* "Impact h is identified by contrasting prey loss before
and after the predator arrives at each site. Arms differ in whether the
'before' is observed (A), hidden (B), or replaced by more sites (C)."
[C01]

**Fig. 2: Hidden heterogeneity distorts impact estimates.** Signed log-error
of h by background (dose: matched, anchor, increased; signed window
alignment) × arm, with complete-data mechanism references.
- If attenuation grows with residual variance and the pre/post arm limits
  it: "Unmodelled site-to-site variation in background loss makes impact look
  smaller; observing the pre-invasion period removes most of that bias."
- If no dose gradient appears: "Within the tested range, residual variation
  in background loss did not bias impact estimates."
- Window alignment: "Background loss concentrated where the predator arrives
  during monitoring [inflates / deflates / does not change] estimated impact
  by X (odd contrast), beyond the effect of added variance alone (even
  departure)."

[C02, C03]

**Fig. 3: Survey before, or survey more?** The paired A − C contrasts at
equal prey site-visits: false declaration, h = 3 detection, interval
coverage and mean absolute log error, by archetype, background and μ.
- If A wins: "Spending effort on pre-invasion surveys of fewer sites beats
  spending it on more sites after invasion."
- If C wins: "The baseline is not worth its cost; more sites are better."
- If the answer depends on conditions: "The better choice depends on [named
  condition], which can be judged at planning time (Fig. 6)."

[C04]

**Fig. 4: When flexibility helps and when it hurts.** For each family
(constant, exposure-linked, spatial) and each background: declaration rate,
coverage, and harmful confident error (an interval lying wholly beyond
1.5-fold of the truth), with predictive regret on held-out sites.
- "The spatial model [protects / fails to protect] against confident error
  when background heterogeneity is unmodelled, at a power cost of X."
- Or: "Flexibility absorbs part of the impact signal: the spatial model is
  calibrated but rarely detects h = 3."

[C05, C06]

**Fig. 5: Can stated uncertainty be trusted on new maps?** The trained rules
(R1, the χ² benchmark, and R2, the empirical cutoff) and interval cutoffs
evaluated on untouched validation maps: map-level distributions of false
declaration and noncoverage against the 0.05 target, with 90th percentiles
and confidence bounds, plus the computational cost of calibration.
- If met: "Rules trained on 30 development maps held their error rates on 60
  new maps."
- If not: "Error rates on new maps exceeded the target in [strata]: these
  rules do not transfer there."

[C07, C08]

**Fig. 6: Knowing in advance, and the limits.** The planning-only forecast
against realised design performance, compared with total-events and
archetype-only forecasts, plus the temporal-trend stress test and the
original blinded capstone.
- "A planning-only forecast predicts which designs will work [better than
  counting expected events / no better than that]."
- "A background trend coinciding with invasion produces [X] apparent impact
  under the pre/post design: baselines are not a causal guarantee."

[C09, C10]

## Claims ledger (skeleton)

The machine-readable copy should become `docs/claims/paper1-claims.csv`,
with an evidence commit and a reproducing command for each claim. Every
status below is "planned".

| ID | Claim (direction left open) | Falsified by | Denominator | Planned evidence |
|---|---|---|---|---|
| C01 | The deterministic Laplace procedure is numerically qualified on fresh maps at 120 and 260 sites | Qualification gate failure | 162 base datasets, clustered by 9 maps | Sprint 2 qualification receipts |
| C02 | Residual heterogeneity dose changes the signed error of h, by arm | The dose contrast's CI includes 0 in every arm | Validation maps × cells | Validation; complete-data references |
| C03 | Signal-window alignment has a signed (odd) effect beyond its variance-matched (even) control | The odd contrast's CI includes 0 | As above | Validation |
| C04 | The A versus C paired contrasts (four endpoints) have the sign and size reported | The precision rule's interval includes 0 | Paired map-level contrasts | Validation |
| C05 | Each family's false declaration and noncoverage meet ≤ 0.05 in the stated strata | Upper bound > 0.05 or lower bound > 0.05 | Every registered dataset | Validation |
| C06 | Harmful confident error rates by family and background | – (descriptive with intervals) | Every dataset with a nonempty interval; failures counted separately | Validation |
| C07 | R2 is needed (R1 fails) in the stated strata | R1 meets the target everywhere | Validation | Training and validation |
| C08 | The development-to-validation transfer of error rates | Validation rates outside the development bounds | Maps | Training and validation |
| C09 | The planning forecast beats the total-events forecast | Its CV and validation error is no better | Map × design cells | Training cross-validation and validation |
| C10 | The temporal trend biases the A-arm estimate of h | The trend contrast's CI includes 0 | Trend subset | Validation |
| C11 | Standard Laplace is a nearly constant-offset approximation of the positive-family integral (a descriptive methods note) | – | Integration screens | Challenge and Sprint 1 evidence |

Results already established and retained: Goal 062, the capstone, and the
recovery ladder (Arcs 1 and 2). They enter Fig. 1 and the text with their
own IDs from the existing synthesis.

## Two-page brief (outline)

One double-sided A4 sheet for a broad audience. It cites claim IDs.
1. The question, in two sentences: how much does an invading predator harm
   prey, and when can surveys tell?
2. Why it is hard: the unseen background, and the timing of invasion.
3. What was done: known-truth landscapes, three monitoring recipes, three
   background models, 90+ independent maps.
4. Three findings, each with one number and one picture (Figs 3, 4 and 5).
5. What a manager should do: a decision table of design × conditions.
6. What remains unknown: real data (Paper 2), and nonstationary
   backgrounds.
7. Openness: repository, data DOI, and the AI roles.

## Agent guide (outline)

For a new agent that must use or extend the work. It cites claim IDs and
gives commands.
1. Map of the repository and the governing documents, in order of authority.
2. The data-generating model: backgrounds, arms, seeds and address
   namespaces (2 qualification-map role, 4 training, 5 qualification
   histories, validation committed).
3. The procedure: `scripts/fit_dataset.py`, the score definition, failure
   classes, and what "resolved" certifies and does not.
4. Running at scale: the PBS driver, receipts, reconciliation, and the
   bulk-data policy (never in Git).
5. Reproducing each claim: one command per claim ID.
6. Known limits and open questions, with the evidence for each.
7. How to propose a change: AGENTS.md gates, prospective review, and the
   deviation records.

## AI roles (for the methods and acknowledgements)

Record per sprint, naming systems and versions:
- Codex (GPT-6 Astra): primary implementation and execution.
- Claude (Opus 5.5): advisor and reviewer, and in Sprint 1 the procedure
  repair, experiment packet and scaffold.
- Subagents named with model and task.

Barry W. Brook: scientific facilitation and final review. The Correspondence
snapshots are the decision record.
