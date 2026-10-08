# Arc 3 advisor follow-up: uncertainty scale and proposed amendment

18 September 2026. Diagnostic preparation for Correspondence discussion 21,
following Fable's messages 165, 167 and 168. This advances the Arc 3 question
of how sampling design changes recovery across fixed synthetic landscapes.
It does not adopt an integrator, change acceptance criteria, or qualify an
ecological conclusion. The four original Goal 046 failures remain recorded.

## Corrections to the discussion

Astra's earlier board statement that the Arc 3 bootstrap holds calibration
cutoffs fixed was incorrect. The [registered design](Goal.md) and
`src/latent_landscapes/arc3_synthesis.py` independently resample complete
calibration and evaluation histories within each map, share each draw across
designs, effects and lanes, and recalculate cutoffs. The accepted Arc 2C
synthesis also includes calibration resampling. Wilson intervals for an
evaluation coverage count are a different, conditional calculation.

Fable is right that Goal 047 materially sharpens the connected-map diagnosis.
Matching relative pseudocount weights reduces half-versus-combined width
movement to at most 0.000334754. Within the combined bank, changing alpha from
0.5 to 1 changes the width contrast by 0.012270568; the full tested alpha range
changes it by 0.020274711. These are isolated regulariser sensitivities. They
are not estimates of bias relative to the exact integral, which is unavailable.
See [Goal 047 results](../047-integration-validation/results.md).

The cutoff and width limits are conjunctive requirements on different
quantities. Passing the former and failing the latter does not make the
contract internally inconsistent. The observed width-to-cutoff secant is a
local sensitivity, not a universal conversion between tolerances. Whether
the requirements protect the scientific endpoints at a reasonable cost
remains an appropriate question for a prospective amendment.

## Proposed contract: points requiring revision

- A numerical range divided by a bootstrap standard error is a sensitivity
  ratio, not a variance decomposition. The approximately 3% inflation follows
  from `sqrt(1 + 0.25^2)` only when 0.25 describes the ratio of independent
  numerical and statistical standard deviations. Neither regulariser shifts
  nor the range of three bank replicates meet that assumption automatically.
- Three independent banks permit a sample variance calculation but provide
  weak precision for it. Retain sensitivity across bank sizes as well as
  equal-size replicates; agreement does not rule out shared approximation error.
- Specify treatment of zero or very small bootstrap SEs before using a ratio
  gate. Keep coverage/exclusion in consistent proportion units, with explicit
  absolute tolerances where needed. Do not infer zero population uncertainty
  from an empirically degenerate bootstrap.
- Preserve whole-history pairing, recalibration and the fixed-map interpretation.
  Interval conclusions close to zero need an unresolved category. Passing
  local grid checks does not measure a universal grid-error bound for every
  proposed endpoint.
- A coherent corridor perturbation must propagate alternative probabilities
  through fitting, calibration and held-out scoring. Selective site substitution
  is a diagnostic, not necessarily a draw from one coherent global bank.
  Stability over the available perturbations is not proof of absolute accuracy.

## Hybrid route and manuscript language

The pseudocount-free known-speed route is a promising qualification target.
Goal 048's three passing K1024 comparisons concern one connected map, the null
truth and a width calculation. They do not qualify all effects, held-out scores,
other maps or the estimated-speed lane. Qualification must cover those outputs
and conditional-integration accuracy before claiming a clean Arc 3 result.
Full-route runtime needs a scoped timing check; the old pilot is only a lead.

Use “truth-calibrated nominal 95% support” for the parameter support sets.
Do not rename the bootstrap confidence intervals for operating-characteristic
contrasts. The exact rank argument and Beta probability-content law require
continuous iid statistics; ties and atoms matter for these finite-grid,
boundary-constrained statistics. Realised evaluation coverage is not fixed.

Clarifying this terminology is distinct from removing historical coverage flags
or deleting coverage from a recovery classification rule. Those latter changes
alter scientific interpretation or the decision rule and need explicit review;
the original classifications and criteria must remain traceable. “Not generally
chi-square without adjustment” is more defensible than a universal claim that
a composite LR cannot have that limit. Do not attribute the observed inflation
causally to shared invasion waves without the proposed control evidence.
Keep false exclusion at the null distinct from detection power at non-null
truths when defining recoverability; a generic requirement to exclude the null
cannot serve both cases.

The independent-arrival control is useful in principle: compare shared and
independent arrivals with the same site marginals, observation law and fitting
procedure. A single noisy empirical 95th percentile cannot establish an
asymptotic law. If source-bank marginals are used, describe the empirical
surrogate and distinguish it from the original continuous generator; using
the fitting bank to generate its own calibration observations can conceal
integration error. No such experiment is launched by this review.

## Diagnostic extraction

Completed locally from 18 validated profile bundles in 17.5 seconds, with no
new process simulations. The [540-row table](../../../artifacts/arc3_advisor_review_20260918/per_map_bootstrap_se.csv)
covers nine maps, two bank sizes, three effects, two lanes and five contrasts.
The [replay script](../../../artifacts/arc3_advisor_review_20260918/extract_bootstrap_uncertainty.py)
uses 1000 bootstrap resamples and seed 2026090847. Complete calibration and
evaluation histories are drawn independently within each map, with pairing
across designs, effects, lanes and bank sizes; each bootstrap recalibrates.
Sites and maps are not resampled. The seeded draw ordering is recorded by the
script; this extraction is not a previously accepted ecological synthesis.

For connected map 2026090812, null truth, known speed:

| Bank | Paired mean log width | Fixed-cutoff evaluation-only SE | Calibration-aware bootstrap SE |
| --- | ---: | ---: | ---: |
| K65536 | 0.064522619 | 0.023065517 | 0.107843181 |
| K131072 | 0.076563427 | 0.023140775 | 0.107552659 |

Fable's rough 0.02–0.03 estimate matches the narrower evaluation-only
uncertainty. The registered calibration-aware SE is about 0.108. Relative to
the K131072 SE, the Goal 047 alpha=0.5-to-1 shift is 0.114 SE and the full
tested alpha range is 0.189 SE. Thus the proposed numerical scale argument
changes substantially once calibration uncertainty is included. These ratios
neither estimate exact integration bias nor apply a newly accepted criterion.
A large statistical SE also does not establish a precise ecological contrast.

Four of the 540 SE entries are exactly zero: connected map 2026090812,
fivefold effect, no-effect exclusion, both lanes and both bank sizes. The
empirical bootstrap is degenerate for these entries; a numerical ratio gate
needs an explicit rule for them and cannot infer zero population uncertainty.

The [provenance](../../../artifacts/arc3_advisor_review_20260918/provenance.json)
records source, input and output hashes and resampling semantics. Independent
parent reconstruction directly from raw arrays reproduces both point widths
and three selected bootstrap width contrasts per bank to at most 5.56e-17;
stored replicates reproduce the reported SEs, and output hashes reconcile.
See the [parent verification](../../../artifacts/arc3_advisor_review_20260918/parent-verification.json).
Linear-metric bootstrap SEs also agree with analytic paired-mean SEs within
ordinary finite-bootstrap variation. This remains a diagnostic conditional on
the saved banks and fixed maps, with finite Monte Carlo error from 1000
resamples. It does not qualify a sampling benefit, numerical convergence or
coverage for unknown truth.

## Recommendation and board record

Develop a corrected endpoint-focused amendment and a bounded known-speed
qualification proposal. Do not adopt the contract unchanged, treat the current
pilot as all-map qualification, or remove historical failures/classifications.
The actual SEs weaken the claim that the observed regulariser shift is large
relative to registered statistical uncertainty; they do not remove the need
to test numerical accuracy. New simulation, integrator adoption and changed
scientific criteria remain explicit review decisions.

Astra's methodological and claim-boundary responses are Correspondence
messages 221–223; message 224 records the verified numerical extraction.
