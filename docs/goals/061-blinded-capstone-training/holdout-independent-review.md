# Independent review of released holdout scoring

8 October 2026, Hobart. This review covers the released Goal 061 holdout
comparison before generating-truth release. I reviewed the fixed prediction
specification, prereveal forecasts, scorer and independent-audit code, frozen
input and fit bindings, complete numerical outputs, figure, provenance, tests,
runtime receipts and the combined report. I did not access a truth plaintext,
private key or private generating identity.

## Decision

**Accept the held-out scores, forecast classifications and combined report for
locking.** The results answer the prespecified shared-map prediction question.
The only leading-pair forecast hit is case-00; cases 01--03 are misses under the
committed exact-maximum rule. No refit, score substitution, model omission or
post-release reinterpretation is warranted.

The numerical conclusion is unusually well verified. An independent direct
raw-bank reconstruction reproduces all sixteen production scores, all site and
cluster contributions, all pairwise differences, every exact maximizing set
and every pair-forecast outcome. The report also gives the necessary scientific
qualification: this is a comparison of four fixed predictors at reserved sites
on the same map, rather than a truth, recovery-rate, causal or new-map-transfer
result.

## Scientific target and evidence

For model \(m\) and case \(c\), the realized target is the registered score

\[
S_{mc}=\sum_{i\in H_c}\log p_m(Y^{\mathrm{prey}}_{ci}\mid
Y^{\mathrm{predator}}_{ci},\hat\theta_{mc},\text{public map},\text{fixed bank}),
\]

where \(H_c\) is the prospectively reserved set of 40 sites and
\(\hat\theta_{mc}\) is the exact frozen training-fit vector. Higher is better.
The score evaluates held-out prey histories conditional on their predator
observations, with whole-map normalization, the frozen observation model and
the qualified \(K=131{,}072\) arrival bank. It does not score predator
prediction, estimate an expected population-level score, or integrate over a
newly sampled spread law.

The data-generating and observation structure limits the scope. Training and
holdout sites share a case-level latent spatial process on one public synthetic
map. Each holdout comprises eight reserved five-site clusters. Prey and
predator counts are repeated observations of the latent ecological process,
with the fitted hazard, detection and background components carried forward
unchanged. The released archive is the committed archive, its 40 site
identifiers exactly complement the 120 training sites, and the audit merges
both sets by identifier into the canonical 160-site order. This avoids the
dormant risk of pairing cached predator emissions with a differently ordered
count array.

The complete score panel is:

| Case | Exact maximizing set | Forecast | Best predicted-pair gap (nats) | Best/runner-up margin (nats) |
| --- | --- | ---: | ---: | ---: |
| case-00 | adjusted free h; adjusted h=1 | Hit | 0 | 0, exact tie |
| case-01 | constant free h | Miss | 1.84885713243 | 0.00000114208 |
| case-02 | adjusted h=1 | Miss | 0.28423976204 | 0.12404179820 |
| case-03 | constant h=1 | Miss | 0.02273712651 | 0.00000076697 |

Case-00's two adjusted fits have identical parameter vectors, so their tie is
structural rather than a rounded display tie. In cases 01 and 03, the winning
member is numerically separated from the other member of the same family at
the fixed-bank audit tolerance, but the margins are only about
\(1.14\times10^{-6}\) and \(7.67\times10^{-7}\) nats. Those exact member ranks
have no defensible claim to practical separation. The forecast misses do not
depend on exaggerating these member ranks: the best named adjusted model is
1.8489 nats behind the constant family in case-01 and 0.02274 nats behind it in
case-03. Case-02 has the clearest realized winner margin, although its 0.2842
nat gap from the best named model is still a small descriptive difference over
40 sites.

## Verification and diagnostics

The final independent audit is
`artifacts/goal061_holdout/remote-return/outputs/independent-audit-final.json`
(SHA-256
`41b499344e02aba943291eca52d0651ad97b48b49747536d10afdc011b3a9769`).
It was produced by the final audit adapter with SHA-256
`545975daa5bfe1bf1dfc49afd53ac1050a830f68cfe5cbc5d9424c9c3cf1fad8`
in the qualified Linux runtime: Python 3.14.5, NumPy 2.5.1 and SciPy 1.18.0.
The final run passed and is semantically identical to the preserved first run
apart from runtime measurements. The earlier `independent-audit.json` remains
historical evidence and is not the receipt on which this acceptance is bound.

The final audit independently reconstructs the public design, reads the raw
arrival bank and directly evaluates empirical Laplace sums, hazards and
observation emissions. Production uses the qualified compressed-bank scoring
path. Their maximum absolute disagreement is
\(5.684\times10^{-14}\) nats for a total score,
\(1.599\times10^{-14}\) nats for a site contribution and
\(1.137\times10^{-13}\) nats for a pairwise contrast, all far below the
pre-existing \(10^{-8}\)-nat computational tolerance. Exact winner sets and
forecast arithmetic agree in all four cases.

The published CSVs are byte-identical to the scorer outputs. They contain 16
unique model totals, 640 unique site contributions, 128 unique cluster sums,
24 unique pairwise differences and four forecast records. Site and cluster
components reconstruct the totals to floating-point summation precision. The
rendered PNG and PDF agree with the full-precision table, retain the tiny
differences and state that panels use separate horizontal scales. Their
provenance binds the renderer and totals table. Four scorer tests and three
independent-audit tests passed; the latter specifically exercise canonical
identifier-based merging, exact ties and a sub-tolerance rank disagreement.

The archive commitment, accepted training-lock root, training observations,
public map and bank, all sixteen fit records, stored training diagnostics,
scientific sources, main scoring adapter and numerical runtime are hash-bound.
All main fits were converged and their diagnostic flags passed. The scoring
process used one process, with 28.19 seconds external wall time and 456.33 MiB
maximum resident memory. The final direct audit used 8.05 seconds external
wall time and 614,348 KiB maximum resident memory.

## Failure modes, alternatives and residual risk

The design prevents post-holdout fitting and ordinary train/holdout leakage:
the site split, models, fit vectors, integration bank, scoring rule and
leading-pair forecasts were fixed before release. It also preserves negative
results. The holdout does not remove weak information or parameter trade-offs
already visible in training. Near-coincident free-h and h=1 fits in several
cases remain evidence of weak separation, not additional null identification.
Conditioning on predator observations and comparing prey log scores cannot
identify the generating background branch or hazard class.

Spatial dependence is material. Forty sites and eight clusters are descriptive
score components, not independent replicates. A site bootstrap would be
pseudoreplicated, while a cluster bootstrap with eight clusters sharing the
same map would still not estimate new-map variation. No such interval should
be added. Completeness and count schemas were verified, and there is no observed
missingness, censoring or truncation to adjust, but the score comparison alone
does not test zero inflation, overdispersion, heteroscedasticity, nonlinear
misspecification or absolute observation-model adequacy. Those require targeted
predictive checks or new simulations under a separately approved question.

The independent implementation eliminates concern about the compressed-score
algebra and ordering, but both paths use the same finite arrival bank. It is
therefore not an independent-bank experiment and does not propagate Monte
Carlo uncertainty from the spread-law approximation. A bank-replicate
sensitivity would be the relevant diagnostic if the scientific question were
whether the micro-ranks persist under integration-bank resampling. It must not
replace the committed fixed-bank result or retrospectively change forecast
classification. The fixed-bank case-01 and case-03 within-family ranks should
simply remain qualified as practically non-separating.

Refitting after holdout, substituting profile optima, pooling the four cases,
or declaring tolerance-based co-winners would change the registered question.
The \(10^{-8}\) audit tolerance checks numerical agreement; it is not a
scientific equivalence margin. Evidence capable of supporting broader claims
would instead require replicated synthetic maps, prospective bank-replicate or
model-adequacy checks, and a validation design targeted at recovery, power,
coverage or transfer. The forthcoming truth release will answer the separately
committed truth-forecast questions, but it will not turn four holdout cases into
an operating-rate study.

I recommend locking the combined report and proceeding to the separately
authorized truth stage without rerunning or retuning this comparison.
Independent external review is unlikely to change confidence in the numerical
scores or their exact registered classifications because two implementations
agree at roundoff scale and the provenance is complete. It could materially
help only if the manuscript later seeks stronger claims about practical model
separation, integration-bank uncertainty, absolute adequacy or generalization
beyond this map; those claims are not made here.
