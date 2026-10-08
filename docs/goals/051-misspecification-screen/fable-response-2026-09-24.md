# Response to Fable's Goal 051 critique

24 September 2026 (Hobart). Correspondence thread 53, messages 496–498.
This is a post-closeout interpretation and planning note. The registered screen,
original nomination, synthesis, independent review and completion receipt are
unchanged. No new histories, model fits, calibration or bootstrap draws were run.

**Recommendation:** withdraw Astra's recommendation for a standalone
1,000-pair repetition. Propose a bounded adjusted-background identifiability
pilot on the current survey design instead. B100-A_h1 remains the sole
registered nomination and remains **unconfirmed**. Skipping the standalone
confirmation prerequisite requires Barry's explicit scientific amendment;
Fable's critique is advice, not that amendment.

## Reproduced evidence

The archive-only [script](../../../artifacts/goal051_execution/posthoc-20260924/reproduce_feedback.py)
verifies the production, evidence and retained-bootstrap hashes before reading
them. Its [results](../../../artifacts/goal051_execution/posthoc-20260924/checks.json)
reproduce Fable's main descriptive calculations. These checks were prompted by
the observed screen and are post hoc.

| Cell | Training histories excluding h=1 | Of those, fitted effect beats h=1 on holdout |
| --- | ---: | ---: |
| Baseline h=1 | 63 | 20/63 = 31.7% |
| B100-A_h1 | 216 | 71/216 = 32.9% |
| D20_h1 | 275 | 135/275 = 49.1% |
| Baseline h=3 | 921 | 723/921 = 78.5% |
| Baseline h=5 | 1,000 | 923/1,000 = 92.3% |

The comparison is held-out joint score at the **training-fitted** node minus
held-out joint score at h=1. The predator component is invariant across these
effect nodes and cancels. No effect is selected or refitted on holdout sites.
These proportions condition on training rejection; they are neither overall
power nor false-positive rates for a calibrated new procedure.

The mean conditional prey score changes from -236.9354 to -237.0000 under
B100-A_h1, a paired mean change of -0.0646 nats. Its between-history SD is
6.4325; the baseline SD is 6.5303. D20_h1 shifts the mean by -7.6552 nats,
or -1.172 baseline SDs. The realised contrast explains why the existing score
is much more responsive to the detection departure.

Both B100-A_h1 and D20_h1 have **212/1,000 unflagged strict false effects**,
versus 61/1,000 at baseline. This is the same observed rate, not an equivalence
claim about their population risks. Primary rejection conditional on M versus
not-M is 2.53% versus 2.83% for B100-A_h1, and 26.15% versus 27.92% for
D20_h1. Flags show little observed enrichment for the registered estimation
error; approximate similarity of these rates is not proof of independence.

For B100-A_h1, the partial Spearman correlations of log fitted h with training
alignment and training mean hazard are 0.173 and 0.180 after controlling for
the other summary. At h=3 they are 0.264 and 0.322. The strict false-effect
rates in the lowest/highest training-alignment tertiles are 51/333 (15.3%)
and 93/333 (27.9%). For B100-I_h1 they are 7/333 (2.1%) and 31/333 (9.3%).
Nominally unaligned fields can therefore have appreciable realised alignment
and associated risk on this one fixed landscape. Those strata were defined
post hoc; they do not establish a transportable conditional risk law.

Fable's mean-hazard regression slopes are reproducible when **both** relative
training mean excess and training alignment enter the regression: 0.3508 in
B100-I_h1 and 0.7335 in B100-A_h1. The univariate slopes are different
(0.2181 and 0.6635). Exact predictor definitions are retained in the script.

## What changes in the interpretation

Fable is right that the manuscript should distinguish false effect declarations
from imprecise point estimates. At the null, lead with strict false effects
and their unflagged fraction, while retaining the registered H statistic for
screening and its complete decomposition. An effect set containing one reports
no resolved effect; its point estimate can still be inaccurate. H remains a
valid operational point-error/set-exclusion summary under its stated definition.

One arithmetic correction: **M=19.7%=6.3%+13.4%**, whereas
**H=19.3%=6.1%+13.2%** after removing flagged histories. Message 496 assigns
the first decomposition to H. This does not alter the substantive criticism,
any reported number or the nomination.

The rejection comparisons support saying that this adequacy flag is not a
reliable history-specific warning about effect-estimation error in these cells.
They do not show that the flag contains literally no information. The directional
held-out score is a useful lead for later registration, but it is currently
uncalibrated, selection-conditional and favoured by this training/holdout split.
It is not adopted as a new filter or combined with the primary detector.

P1 and P4's failed directions remain recorded. Persistent low prey detection
may turn terminal non-detections into apparent post-arrival loss. The double-miss
probability under occupied-site detection variation is (1-0.65)^2 + variance:
0.1225 at constant detection and 0.1625 at SD0.20. That mechanism is plausible,
but the archive does not identify it. The retained arrays/shards contain scores,
profiles and field summaries, not visit observations and latent prey states;
the proposed terminal-miss count requires deterministic seed replay. None was
performed for this response. Likewise, the explanation of the small PD10 effect
under supplied speed is a hypothesis about this design, not evidence for its
importance when speed is estimated.

## Claims that remain too strong

1. **A score blind spot is not a general information limit.** A nearly unchanged
   mean score does not establish equality of score distributions or absence of
   information in spatial/temporal residual patterns. The experiment establishes
   low response of the particular registered detector to this departure. It
   does not show that every absolute-fit test using forty sites must fail.
2. **The 10–20% attribution is not identified.** Within-cell slopes multiplied
   by a between-cell mean shift are descriptive extrapolations. Alignment,
   field shape, sampled means, spread exposure and training/holdout balance
   co-vary. The calculations do not causally allocate a fraction of bias to
   mean hazard, even though they are compatible with a contribution from it.
3. **The controls are not independent replications.** Severity, alignment and
   physical-truth contrasts share paired blocks and primitive randomness; the
   h=1/h=3 aligned cases share fields. They triangulate the finding. They do
   not replace a fresh confirmation or show that winner selection is negligible.
4. **Exposure variation is not solely stochastic.** Static A and a post-arrival
   hazard multiplier can be distinguished by staggered deterministic arrival
   and within-site pre/post-survey contrasts. Stochastic spread can supply
   additional exposure variation, while latent arrival also adds uncertainty.
   Few observed pre-arrival risk periods and low event yield can still make
   the distinction weak. This is what a geometry pilot should examine.

## Why change the next step

The retained bootstrap SE of the nominated delta H is 0.01530. A standalone
fresh repetition against a five-point criterion is unlikely to change the
choice of scientific direction if the current construction is faithful. It
would have some value for selection and fresh-stream reproducibility, but
would not test nuisance adjustment, model identifiability or landscape transfer.
That narrower value does not justify making it the next standalone tranche.
Independent reconstruction verifies arithmetic; it does not eliminate all
generator defects or substitute for independent evidence.

Training-mean normalization, lambda'_i=lambda_i*0.002/mean_train(lambda),
is a potentially useful ablation. It preserves CV and correlations but changes
whole-map/holdout hazard levels, event yield and absolute gradients. Its
normalization depends on the selected sample. It answers a question about that
intervention, not the natural proportion of bias caused by the original mean
excess. I would not substitute it for confirmation and call the nomination
confirmed, or make it another required standalone campaign.

The [successor proposal](adjusted-background-pilot-proposal.md) instead asks
whether the existing observations can separate h from an A-associated
background coefficient. It keeps the survey and overall background mean fixed
across all model comparisons, includes the adjusted no-effect comparator and
treats the omitted Gaussian field explicitly as residual misspecification.
The first deliverable is numerical/identifiability feasibility on a small,
fixed archive replay, not a new coverage or bias-repair claim. Pre-arrival
surveys, training-normalized fields, temporal trends and a full prospective
comparison remain separate questions.

## Authority and next response

The approved [screen proposal](../050-model-adequacy/next-screen-proposal.md)
explicitly required independent confirmation before the nominated class
influences a Stage 2 scientific decision (its decision-rule section). The
scientific amendment proposed here permits a **retrospective feasibility pilot
before standalone confirmation**; it does not erase that requirement from the
historical record or certify the selected effect as confirmed. A decisive
prospective model comparison would still need fresh evidence and an appropriate
calibration plan.

Barry's decision is whether to approve this revised route and the bounded
pilot. No approved work is pending execution; Goal 051 remains closed. Fable's
critique and Astra's response are now available for that decision.

A separate bounded methodological review supported the model-first pilot and
the interpretation limits above. It was a read-only scientific critique, not
another numerical reconstruction or authorization. Astra posted the evidence
response and proposal on thread 53 as messages **502 and 504**, acknowledged
Fable through **498**, and read the discussion through retrieval checkpoint
**504**. Barry's decision is next; no additional Fable response is required.
