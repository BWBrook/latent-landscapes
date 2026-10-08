# Blinded capstone training report

6 October 2026. Completed blinded training analysis, prepared by Astra from
the four neutral cases. The [training lock](training-lock.md) identifies the
bound evidence and review. Held-out observations and generating truths remain
sealed.

The registered procedure does not declare an effect in any of the four cases. The
independently audited p_BB values are **1, 1, 0.422 and 1** for cases 00--03;
all four results are valid non-declarations, with no numerical abstention.
The adjusted training fit is at the lower bound h=1 in three cases; case-02
estimates h=1.288 with a likelihood-ratio statistic of only 0.09457 and broad
likelihood support. Here h is the predator-associated prey-loss hazard
multiplier. A non-declaration or boundary estimate does not establish absence
of an effect, identify the generating family, or demonstrate successful
recovery of the unknown generating value.

## Design and fitted comparisons

Each case supplies the same 120 training sites from a fixed 160-site design
on the public 6,048-cell map. Forty sites in eight clusters are reserved for
the later predictive comparison. All fits use the qualified K=131,072 arrival
bank, whole-map hazard normalization, the fixed observation model and the
unchanged continuous optimizer. The four candidates are constant or
exposure-adjusted background, each with free h or h fixed at 1. The primary
comparison is the adjusted free-h model against its adjusted h=1 null.

Here beta is the coefficient of the supplied exposure in the background-hazard
model; mu is its whole-map mean daily hazard; detection SD describes persistent
between-site variation in prey-detection probability. The fitting bounds are
h in [1,10], beta in [-2,2], mu in [0.0005,0.006] per day and detection SD in
[0,0.4]. Constant-background candidates fix beta=0.

| Case | Constant-model h | Adjusted-model h | Adjusted beta | Adjusted mu/day | Adjusted detection SD |
| --- | ---: | ---: | ---: | ---: | ---: |
| case-00 | 1.04235 | 1.00000 | 0.23736 | 0.00373573 | 0.28453 |
| case-01 | 1.00000 | 1.00000 | 1.00526 | 0.00399352 | 0.19966 |
| case-02 | 1.28346 | 1.28762 | -0.00503 | 0.00107970 | 0.30641 |
| case-03 | 1.00000 | 1.00000 | 0.15992 | 0.00107503 | 0.08337 |

All sixteen main fits are finite and converged. The table shows the free-h
fits; the [full-precision parameter table](../../../artifacts/goal061_execution/training-figures/training_main_parameters.csv)
retains all four models, raw log scores and numerical status. No diagnostic
profile or lattice point has replaced or seeded a main fit.

## Likelihood support and prerelease interpretation

![Audited likelihood support for the four neutral cases](../../../artifacts/goal061_execution/training-figures/training_likelihood_support.png)

The [vector figure](../../../artifacts/goal061_execution/training-figures/training_likelihood_support.pdf)
and [complete profile table](../../../artifacts/goal061_execution/training-figures/training_profile_grid.csv)
retain the constant h, adjusted h and adjusted beta profiles. Each curve shows
R=2 times the difference between its greatest finite grid log score and the
log score at that point. The displayed R axis stops at 10; the CSV retains
larger values. These are likelihood-support profiles, without confidence
coverage claims or confidence-interval thresholds. Grid maxima can differ
slightly from the continuous main optimum.

Case-02 has a much broader h profile than the other three cases. Its slight
interior optimum and broad support should be considered together: the point
estimate alone would conceal the weak discrimination among effect sizes.
Cases 00, 01 and 03 place their adjusted optima at the permitted lower bound;
the model does not allow h below 1.

Case-01 has the clearest fitted exposure gradient. Allowing beta to vary
raises the free-h training log score by about 10.51 nats relative to the
constant-background fit, while h remains 1. The adjusted model has additional
flexibility, and this comparison neither identifies a generating family nor
establishes superior held-out prediction. The other cases give smaller
training-score gains. All four candidates remain in the fixed predictive
comparison.

The generating identities, effect magnitudes and background mechanisms remain
unknown. These results cannot establish parameter recovery, empirical power,
coverage, model adequacy or a causal interpretation. Any negative calibrated
result must be reported separately from these descriptive fits and from a
numerical abstention.

The [explicit prereveal predictions](prereveal-predictions.md) record Astra's
effect-class, magnitude, background, detection and held-out performance
forecasts with their evidence and limitations. All four primary effect
forecasts are null, with case-02 the weakest; the background forecasts are
explicitly prior-modal rather than residual-field diagnoses. Their accuracy
will be checked separately from the registered declarations after the
appropriate releases. No posterior probabilities have been calculated.

## Registered calibration

All 765 nuisance-grid nodes have completed 99 pre-only screening references,
for 75,735 references in total. The observed and reference discrepancies use
the same immediate-axis comparison and conservative inclusive rank. Retain
nodes with q>0.01. Independent reconstruction agrees with every observed q,
the four candidate sets and their union.

| Case | Adjusted observed T | Retained nodes | p_BB | Declaration status |
| --- | ---: | ---: | ---: | --- |
| case-00 | 0 | 33 | 1.000 | Valid non-declaration |
| case-01 | 4.55e-13 | 43 | 1.000 | Valid non-declaration |
| case-02 | 0.0945666 | 107 | 0.422 | Valid non-declaration |
| case-03 | 4.55e-13 | 128 | 1.000 | Valid non-declaration |

T values are from the saved main fits; independent reconstruction differs by
at most 1.37e-12. The near-zero differences are below the registered rank tie
tolerance. For these three cases, T minus that tolerance is negative. Every
valid reference statistic is nonnegative, so all 999 references necessarily
count in each inclusive rank: p_nu=(1+999)/1000=1 and p_BB=1. Their completed
tables are valid, so these three results are non-declarations regardless of
the reference values. The campaign verifies numerical eligibility and
completes the registered procedure for these cases. Case-02's calibrated
p-value does depend on the reference distribution: its nodewise values range
from 0.173 to 0.412 across the 107 retained nodes, giving
p_BB=0.01+0.412=0.422. The largest nodewise value occurs at node 463.
This algebraic consequence, flagged by Fable in message 1024 and checked
against the frozen rank implementation, does not authorize skipping tables.

The union contains 299 distinct nodes. Every node completed all 999 full
correlated-spread h=1 references: **298,701 effect references in total**.
All tables passed the independent audit, retaining the original random
addresses and fitting rules. No partial rank was used. The registered rule is
p_nu=(1 + number of reference T values at least the observed T)/1000 and
p_BB=min(1,0.01+max over the case's retained nodes of p_nu). The fixed
conservative tie tolerance applies; declare only when p_BB<=0.05.

Under the registered rule, a completed invalid observed adjusted pair or
required reference table causes abstention for the affected case. None
occurred in this run. No failed reference was dropped, replaced or retried
with a new seed. These valid non-declarations mean that this procedure did
not declare an effect; they do not prove h=1.

The finite-grid error bound is casewise <=0.05 for an exact-family on-grid
null, conditional on the fixed map, design, numerical bank and algorithm. It
averages over observation and reference generation, rather than conditioning
on the realized reference tables. It is not four-case family-wise control and
does not cover off-grid nuisance values or the B100-A background mechanism.
This capstone is not a new empirical operating-rate experiment.

## Numerical evidence

Independent direct-bank reconstruction passed for all 16 main fits, 1,772
profile points and 5,400 coarse-lattice points. The largest absolute score
differences were 6.83e-13, 9.10e-13 and 5.01e-12, respectively. All four cases
passed convergence, nesting, profile and lattice diagnostics; no diagnostic
hold remains. All 75,735 screen references passed exhaustive generator and
score reconstruction. Every one of the 298,701 stored effect references
passed address, payload, status and direct truth/null/free score checks; the
largest effect-reference score difference was 2.05e-12 nats. All 299 tables
are usable. Independent reconstruction agrees with every observed screening
rank, retained set, nodewise effect rank and final declaration.

These checks verify the stored scores and the registered numerical procedure;
they do not prove global optimization or biological validity. Effect-generator
replay covered the prespecified first, middle and final references at each
node: 897 histories in total, all bitwise matched. There were no anomalous
rows requiring additional replay. This is sampled generator replay alongside
exhaustive stored-score and validity checking. An isolated internally
consistent substitution outside that replay sample is not independently
excluded by replay alone; provenance also depends on source custody, row
hashes and the checkpoint constraints. The generator audit shares the existing
spread kernel, and the fixed numerical bank does not establish rank invariance
under a different bank.

The original 51-worker production attempt finished at **04:51:03 AEDT on
6 October**, after 15 hours 30 minutes 50 seconds, with 23.21 GiB sampled
peak aggregate RSS and no resource stop or remaining process. The complete
computational evidence inventory binds 3,220 files totaling 6,095,664,578
bytes. The [training lock](training-lock.md) records the completed local
return verification, final claims review and all report/figure commitments.

The [execution record](execution.md) preserves all three failed mechanical
qualification attempts and their bounded interface repairs. The fourth
qualification passed before training inspection. All 321 previously qualified
source files remained byte-identical; the 334-file production manifest is
`5879fbdaf7b3880151358319a7b7c7c0837463b06ba06f1a34fb80a3fbc2e36a`.
The new orchestration was frozen after sealing but before training inspection.
The figure exporter was added after the production freeze and changes only
presentation; its [provenance record](../../../artifacts/goal061_execution/training-figures/figure_provenance.json)
binds audited inputs and generated outputs. The qualified scientific runtime
is Python 3.14.5, NumPy 2.5.1 and SciPy 1.18.0 on Linux.

## Predictive comparison and release sequence

The [predictive specification](predictive-specification.md) was hashed before
inspection of the actual training fits
(`88ba503b84a4827d342d590fa0c70e4945e27babb7c8f2f26085e0fa08ba1b1d`).
After Fable confirms the completed training lock and Barry releases the
committed holdout, score all four exact frozen training fits using the same
conditional-prey rule. Report total log scores, means per site, eight cluster
contributions and all pairwise differences. The sites and clusters share the
case-level spatial process; no site-IID or automatic cluster-IID confidence
interval is specified. No refitting or model selection is permitted.

The complete report including held-out results must then be frozen before the
separate truth release. This training report authorizes neither release. The
prereveal predictions and predictive specification retain their original
commitments; a reveal cannot retrospectively alter these declarations or
forecasts.
