# Goal 058: coarse calibration grid and four-node effect-reference micro-pilot

4 October 2026 (Hobart). **Approved; preparation and qualification.**
Barry accepted all three decisions following Fable's thread 53 messages
902–903: “agree with all, yes, skip, yes.” Adopt beta spacing .25 for the
calibration grid, defer the proposed global-screen redesign, and run the
previously proposed four-setting full effect-reference micro-pilot. This
advances Charter Pillar 4 calibration and Pillar 5 capstone preparation.

Close this tranche with the frozen grid, a complete 3,996-history end-to-end
reference attempt or preserved numerical/resource failure, measured costs and
failure frequencies, independently checked statistics and table/abstention
handling, and a costed next recommendation. Completion of the experiment does
not require every optimizer to succeed. A usable reference table does require
every required reference to meet the frozen validity checks.

## Scientific changes and retained boundaries

The new reference grid contains beta=-2,-1.75,...,1.75,2 (17 values), the same
nine whole-map means (.0005,.001,.0016,.002,.0025,.0032,.004,.005,.006), and the
same five detection SDs (0,.1,.2,.3,.4): **765 nodes** in beta-major, mu-middle,
SD-minor order. The whole-map hazard normalization and all continuous fitting
bounds, starts, tolerances and fallbacks remain unchanged. Grid coarsening
changes the reference support, not the likelihood or optimization resolution.

Retain the existing local-neighbour screening construction, inclusive ranks,
tie tolerance, 99 screening references/node and q>.01. Its beta neighbours
will be .25 apart on this grid. The Goal 057 table is not a recalibration of
that new statistic. A future screening table must use the coarse stencil
symmetrically for observations and references; this micro-pilot does not
generate that table. It generates full effect references at four fixed nodes
only. No 225-anchor/global-screen implementation or simulation is authorized.

The exact-family, on-grid validity argument can apply prospectively after the
method is fixed before the observations and references in question. It does
not establish off-grid or residual-field robustness. The existing beta=.6
development fixtures are off the new grid. Preserve them unchanged and do not
snap their truths or describe their retrospective ranks as calibrated.

Any future exact-family sealed truth must lie on the frozen 765-node support.
The old capstone proposal's E06=.6 branch and B100-A residual-field branch
cannot silently inherit that guarantee: its final truth-draw distribution
must be reconciled with the approved support before sealed generation.
This tranche fixes the support without drawing truth, choosing replacement
mixture weights or replacing a misspecification branch with an exact-family
case. The existing four-history and key-custody decisions remain in force.

## Fixed four-node experiment

Use the existing connected 72-by-84 laboratory landscape, its public exposure
covariate, the 160-site layout and 120 training / 40 holdout split. All sites
are generated; only training observations enter fits and effect statistics.
Use the unchanged full correlated predator-spread generator, not independent
site arrivals. The cohort starts present at -60, prey has thirteen two-visit
occasions from -60 to 60, predators six two-visit occasions from 10 to 60.
Keep supplied spread/resistance and predator/mean prey detection assumptions
from Goal 056. Site-level Beta prey detection is persistent across visits.

| Label | Coarse node | beta | Whole-map mu | Detection SD | h | References |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Interior | 382 | 0 | .0025 | .2 | 1 | 999 |
| Lower corner | 0 | -2 | .0005 | 0 | 1 | 999 |
| Upper corner | 764 | 2 | .006 | .4 | 1 | 999 |
| Opposite slope corner | 44 | -2 | .006 | .4 | 1 | 999 |

Generate exactly **3,996 independent full null histories**, preserving every
assigned address, observation, fitted result and failure. There are no new
alternative-effect histories or operating-rate evaluation samples. Do not
choose nodes from the realised screen, stop on favourable results, augment
reference counts, drop failures or redraw a replacement history.

Use the existing receipt-qualified K=131,072 empirical arrival bank with all
160 sites, alpha=1, at
`/data/codex/scratch/goal045-full-bank-reference128-20260907-e8c08f1/bank_cache/base_arrivals.npy`.
Verify its file/array checksums and configuration against Goal 056's
qualification receipt. This bank supplies the fitted integration; the full
generator independently simulates a correlated spread realization for every
reference. Store generated arrivals and other evaluator quantities separately
from the observed arrays, all openly labelled for this diagnostic pilot.

## Randomness and freeze

Use root **2026100402**, namespace **58**, coarse node index as above,
reference_index=0..998 and stage=1..5. Stages are spread, prey loss, predator
visits, site detection and prey visits, respectively. Each integer stage seed
is the first uint64 from
`SeedSequence([root,58,node_index,reference_index,stage]).generate_state(1,dtype=uint64)`.
Pass those seeds to the existing generator, whose `default_rng(integer_seed)`
uses PCG64. Record NumPy/runtime versions and all 19,980 stage seeds before
reference generation. Worker scheduling must not alter addresses.

Before launch, bind the registration, grid, seeds, source, qualification and
public inputs in an immutable run snapshot. Mechanical tests/qualification
must use root **987654321** or deterministic existing public inputs, never the
registered reference streams. This explicitly prevents the Goal 057 preview
error from recurring. Audit replays of fixed assigned addresses are permitted
after the run and must be labelled as replays, not new references.

## Frozen fitting and failure treatment

Reuse the exact Goal 056 adjusted pair: fit `adjusted_h1`, then
`adjusted_free_h`, passing the null's parameters and convergence status as the
extra candidate and its success flag. A thin wrapper may call the existing
fit primitive but must leave it unchanged and reproduce the adjusted pair
from the existing four-model call on fixed qualification inputs. Constant
models and profile grids are not required for this effect-reference pilot.

Store null and free convergence/status separately, all finite raw scores and
parameter estimates, starts, objective evaluations, boundary indicators,
timings and raw/clamped effect statistics. A finite clamped statistic never
overrides a failed fit. Record failed/nonfinite estimates explicitly without
imputation or success-only deletion. The screen and effect procedures keep
their existing union-cap and abstention rules.

Optimizer nonconvergence, a free score below null by more than 1e-6, or a null
fit below its true null-point score by more than 1e-6 makes that reference
invalid. Preserve it and continue other assigned histories. Do not improve
or restart the fit after seeing the gap. Any invalid one of a node's 999
references makes the node table unavailable; a case requiring it must return
p=1/abstention. No rank is computed from the remaining valid subset.

Independent scorer disagreement, a nonfinite kernel at a defined finite
parameter point, source/address/schema mismatch or a resource-cap breach is
a campaign-level numerical/resource failure. Stop new dispatch, retain partial
outputs and diagnose the original attempt. No automatic campaign restart.

## Verification and interpretation

Compare production with independent direct-bank likelihoods at the true,
null-fit and free-fit points for every history where those finite points are
available. Require absolute whole-history score agreement <=1e-8, effect
statistic agreement <=1e-6, and the nesting inequalities above. Independent
calculation must not call production emissions, hazard normalization or score
functions. Check all 3,996 unique addresses, seeds, statuses, counts and
serialized rows; replay at most references 0,499,998 at each node as a separate
determinism check. No independent audit refits are permitted.

Test inclusive rank arithmetic, missing/invalid table abstention, shared-table
loading and one cap on the complete case union before requesting any tables.
Mechanical case/node selections may exercise that path, but do not publish
them as screened ecological declarations. No final resource cap is chosen
from this four-node pilot. Report each node's usable/unusable status and all
failure frequencies alongside timings and memory/I/O.

This is a pipeline and resource qualification at four null settings. It cannot
estimate false-declaration rates, power, effect-magnitude recovery or coverage,
nor establish reliability across the other 761 nodes. The earlier R<=10 and
coarse-subset cost calculations remain descriptive proxies, not calibrated
screening sets, optimal-screen bounds or a promise of monotone compression.
The pre-only nuisance-error check does not establish that Goal 056's full-data
threefold errors were solely chance.

## Execution envelope

Use an isolated dated directory on deep-server, **at most sixteen workers**,
one numerical-library thread per worker, **48 GiB aggregate process-group RSS**
and a **two-hour campaign ceiling**. A bounded mechanical qualification on the
target precedes the registered draw; it must verify the actual bank and the
pair wrapper and expose material throughput/memory problems before launch.
Record complete-run and component wall times, sampled aggregate peak RSS,
file counts/bytes, output hashes and exclusive launch/completion receipts.
Keep independent raw checking within the same resource envelope where it is
part of the execution path; subsequent synthesis introduces no new histories.

Routine resource and implementation choices are delegated within this approved
scope. A frozen numerical/operational repair may be prepared after a failure,
but a second registered attempt needs an explicit scientific decision. Large
effect calibration, a new map, sealed generation, commit, push and publication
remain outside this tranche. All Goal 056/057 outputs remain preserved.
