# Goal 057: public nuisance-screen retention

4 October 2026 (Hobart). **Approved; implementation and qualification.**

Barry approved the revised one-hour pilot: “Yes, approved. Proceed with full
authority through this new tranche.” This implements the
[reviewed proposal](../056-observed-nuisance-feasibility/calibration-proposal.md)
and advances Charter Pillar 4 calibration and Pillar 5 capstone preparation.
The scientific question is whether the registered inexpensive nuisance screen
compresses the reference grid enough to make a later effect campaign practical.
Close with the measured retention, both agreed diagnostics, actual resource
use, independent checks and a costed recommendation, or a preserved and
diagnosed numerical/resource failure. A large retained set is a valid result.

## Frozen experiment

Use the existing 72-by-84 laboratory map, its whole-map standardized exposure,
160-site design and 120 training / 40 holdout split. Use only the training
observations for screening and nuisance fitting. The sixteen Goal 056 histories
remain unchanged. Their known truths are descriptive evaluation labels.
Do not access or generate sealed histories or modify any earlier result.

Retain the Goal 056 grid in its existing beta-major order: 81 beta nodes in
[-2,2], mu=(.0005,.001,.0016,.002,.0025,.0032,.004,.005,.006), and prey-detection
SD=(0,.1,.2,.3,.4), giving 3,645 nuisance nodes. At each node, generate exactly
99 independent pre-only histories. A cohort starts present at day -60; visits
are at -60,-50,-40,-30,-20,-10,0, twice per occasion. Background hazard is
mu exp(beta A_i)/mean_map exp(beta A). One Beta-distributed detection probability
per site has mean .65 and the node's SD and is shared across all its visits;
SD=0 is fixed .65. Independent exponential loss thresholds implement the
absorbing prey-loss process. This pre-only law needs no predator spread or
arrival-bank traversal. Generate all 160 sites; score the 120 training sites.

The local statistic, inclusive ranks and conservative tie tolerance are frozen
in `preinvasion_calibration.py`: D=2(maximum over the node and its immediate
axis neighbours minus the node log likelihood), at most seven point scores.
q=(1+number of the 99 reference D values at least observed D)/100, retaining
q>.01. Use TIE_ATOL=1e-10 and TIE_RTOL=1e-12 as implemented. No global support
statistic may alter this retained set. Batch evaluation over independent
histories is permitted only after equality with individual point evaluation
passes on deterministic mechanical observations.

Freeze all streams before reference generation or fixture scoring. Use NumPy
PCG64 with SeedSequence([2026100401,57,node_index,reference_index,stage]), where
node_index is 0..3644, reference_index is 0..98 and stage is 1 (loss), 2
(site detection), or 3 (visits). The complete node/reference/stage seed ledger
and public inputs are hashed before launch. Worker order must not affect
streams. Mechanical qualification uses separate fixed inputs and no registered
reference stream. Never replace seeds, augment reference counts or retry failed
fits under another seed. Exact replay for audit is permitted and labelled.

## Retention and global-surface diagnostic

Cache a complete pre-only likelihood surface for each of the sixteen fixtures;
derive its local contrasts without further scores. Report all sixteen set
sizes, each known true node's q and retention, and all C(16,4)=1,820 four-fixture
union sizes. These unions are an exhaustive description of this fixed panel,
not independent replicates or a guarantee for future cases. Do not estimate
screen coverage, false-declaration rates or power from this panel.

For each surface compute R(nu)=2(max_grid ell_pre-ell_pre(nu)). Report retained
R median, 90th/95th percentiles and maximum; retained count and fraction with
R>10; and the whole-grid count with R<=10. Plot retained nodes on the global
surface. Ten is a descriptive marker with no confidence or chi-square meaning.
High-R retained nodes suggest scope to investigate a global statistic later;
near-peak retention does not prove that no valid alternative can compress more.

## Reused-reference nuisance diagnostic

Fit the unchanged five-start `fit_pre_only_nuisance` to the same 99 references
at each of the eight nodes mu={.0016,.0025}, beta={0,.6}, SD={0,.2}: 792 fits
without additional histories. The likelihood and fitter remain unchanged.
Persist these 792 small pre-only count arrays to support independent checking;
other references need only scalar statistics, stream identities and receipts.

Compare production and independently implemented analytic pre-only likelihoods
at each true and fitted point, requiring absolute whole-history difference
<=1e-8. The independent scorer must implement normalized hazards, cohort
survival and shared-Beta count emissions without calling production scoring,
normalization or emission routines. A fitted objective more than 1e-6 below
the true-point objective is a numerical failure, never a prompt for refitting.

Report nodewise mean and median log(mu-hat/mu), beta and SD errors, mean-error
Monte Carlo SEs and approximate 95% Monte Carlo intervals, boundary frequencies,
optimizer failures and the 3-by-3 parameter-error covariance. Show SD=0 nodes
separately. The equally weighted pooled summary is a balanced eight-node
mixture, not a common-bias estimate. Include all finite returned estimates in
the descriptive error accounting, identify failed optimizations explicitly and
give success-only summaries only as labelled sensitivity results if needed.
Missing/nonfinite estimates retain their counts and have no imputed value.
Monte Carlo intervals describe simulation uncertainty in estimated mean errors,
not confidence intervals for ecological parameters.

Optimizer nonconvergence in this ancillary diagnostic is recorded rather than
discarded or replaced: the screen itself requires no optimization. A nonfinite
screen score/statistic, independent-score mismatch or truth-dominance failure
stops new dispatch and preserves the attempt. Such a stopped attempt cannot be
reported as a complete successful experiment. Partial results may diagnose it.

## Decision arithmetic and resource envelope

Before generating any future effect table, enforce one cap on the union of
the cases' required nodes. An over-cap union must request no effect references
and return p=1/abstention. Propagate convergence flags from both observed and
reference null/free fits: finite clamped statistics do not rescue failed fits.
Implement and test these rules now using mechanical inputs only. This pilot
does not choose the final cap or generate any effect reference.

Use a new isolated directory on deep-server, at most eight workers, one
numerical-library thread per worker, 16 GiB aggregate process-group RSS and
3,600 seconds for the complete reference/fixture/diagnostic run. A bounded
mechanical qualification precedes it; analysis and plotting consume no new
simulation budget. Record source/input/seed hashes before launch, exclusive
attempt and completion receipts, actual generation/preparation/scoring/fitting/
checking/serialization times, wall time, peak RSS and output bytes. Preserve
partial results on a cap or numerical stop; do not restart the campaign
automatically. Record any qualified technical repair before a further attempt.

Translate retained union sizes into later effect costs using 999 references
per node and the Goal 056 measured pair/generation workloads, preserving the
worst-grid scenario and labelling ideal parallel projections. A large campaign
requires target-host throughput measurements, including Kunanyi when its scale
is useful. This one-map pilot neither validates a new map nor sets its resource
cap. Full effect-reference micro-pilot, operating-rate study, screen redesign,
new capstone map, sealed generation, commit, push and publication are outside
this tranche.

## Prelaunch technical deviation, recorded before the complete run

Development checks inadvertently used registered streams before the final
source/seed-file freeze. The executor reports four repeated generations of
node 0's 99 references during chunk/diagnostic checks, additional repeated
generations of node 0 references 0 and 1 in five early test-suite invocations,
and the first eight uniform variates from node 17/reference 23/loss stage in
five seed-address test invocations. Thus 99 unique reference histories at node
0 were previewed, along with a prefix of one other stream. Development output
logs were not retained; these invocation counts are the executor's account.
No other registered node/reference history was reported generated.

This violated the intended separation of mechanical and registered streams.
All test draws now use mechanical root 987654321. The complete pilot retains
root 2026100401 and every original address; no seed, reference count, screen,
likelihood, fitter or scientific threshold was changed in response. The previewed
references remain in their assigned positions rather than being replaced. The
full grid experiment is still a public diagnostic, and must not be described
as wholly frozen before any reference preview. This disclosure and the final
corrected source are bound before the complete campaign launches.

The pooled mean-error Monte Carlo interval uses the eight fixed strata's
within-node variance estimates and Welch–Satterthwaite degrees of freedom;
it does not treat the eight chosen nuisance nodes as a random sample.
