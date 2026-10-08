# Goal 048 execution state

12 September 2026 (Hobart). **Complete: the registered finite-budget pilot
fails its corridor criteria.** The results are returned, verified and
independently reviewed. No replacement method or ecological result has been
adopted. See [results](results.md) and [terminal review](final-review.md).

## Candidate and controls

The primary candidate conditions on the exponential-edge infection order and
integrates the holding times using positive uniformization. Compact linear
moments are averaged before likelihood logarithms. The accepted biological
model, observation model and composite estimand are unchanged. No pseudocount,
probability floor or clipping is used.

Independent small-graph infected-set CTMC and phase-type controls pass, including
an exhaustive mixture over infection orders. Source atoms and unequal-size
hierarchical averaging are covered. The focused reference, Gamma and jump-chain
checks pass locally and on deep-server: 24 focused target tests and the full
319-test local suite pass. The Gamma implementation is retained as
a diagnostic comparator; the reviewed primary recommendation is infection-order
conditioning. See [method options](method-options.md) and
[jump-chain feasibility](jump-chain-feasibility.md).

The registered first-order connected and corridor full-map refinement checks
pass: comparing mesh width 0.25/degree 6 with width 0.125/degree 8 changes masses
and survival moments by less than 3e-12 in absolute value. Maximum relative
change among positive entries above 1e-100 is below 2.3e-9. These checks quantify
conditional arithmetic only, not outer-bank Monte Carlo error. Some unused
extreme conditional tails underflow, but every observed-history likelihood is
finite in all twelve bank configurations.

## Frozen retrospective pilot

The [pilot registration](jump-chain-pilot-registration.md) is bound by
`artifacts/goal048_execution/jump-chain-registration.json`, frozen at
2026-09-12 03:55 UTC before pilot likelihood outcomes. The 6144 unique order
seeds are retained in `jump-chain-seeds.npz`. Each of the two old stress maps
has three independent K1024 banks with nested K256 prefixes. Connected uses all
250 calibration and 250 validation paired null histories, both designs and
known rho=1. Corridor uses the fixed old tail history, three truths and the
unchanged eight-rho window. All H181 candidates and old movement thresholds
are preserved.

Source and metadata are staged in the fresh directory
`/data/codex/scratch/goal048-jump-chain-pilot-20260912` on `deep-server-ts`.
All 60 production source files in the Goal 046 snapshot match exactly; new
prototype modules are separate. Staging contains no copied raw arrival banks.
The source/input manifest and supervisor are retained under
`artifacts/goal048_execution/staged/`.

Target spot timings projected about 30–55 minutes for the order calculations at
four workers per map. The hard envelope was two concurrent map jobs, four workers
each, one native thread per process, 10 GiB address space per process, 96 GiB
aggregate RSS and two hours wall time. No automatic bank enlargement is allowed.

The final source-domain guard and independent pre-execution review passed.
The full pilot launched at **2026-09-12 04:06:27 UTC** (14:06 Hobart).
Supervisor PID 8188 and timeout groups 8189/8190 were verified live after
dispatch. The launch receipt binds 83 staged files, with manifest SHA256
`667d2b76e7160065622dfa13f8b8a53663a0c045577384a0924ebd12081c88bc`.
Final jump-chain source SHA256 is
`97a7624ed132bd891dd1ecf8de59ef049ed60aa70c7ab68509d7386c1f1fbd7d`.
Target checks and launch receipts are returned under
`artifacts/goal048_execution/target-preflight/`.

## Verified completion

Both jobs exited zero; the supervisor finished at **2026-09-12 04:54:01 UTC**.
Elapsed time was 2853.68 seconds (47.56 minutes), and peak sampled aggregate RSS
was 1.850 GiB. The resource caps held, and both recorded process groups are
absent. Source, metadata, compact curves, raw likelihood arrays, reports, logs
and receipts are returned under `artifacts/goal048_execution/returned/`.

The [completion check](../../../artifacts/goal048_execution/completed-check.json)
verifies all 83 preflight files, 27 output/receipt hashes, the exact seed recipe,
all 60 accepted source modules, 64 current staged modules and three staged
scripts. All 78 representative compact-curve likelihood replays agree within
6.82e-13. The independent reviewer reconstructed every comparison scalar and
classification exactly from raw arrays.

All three K1024 connected bank comparisons pass. Across both sizes and prefixes,
connected passes 4/9 comparisons and corridor passes 0/9. There are no observed
support failures or corridor window-inconclusive cases. The largest K1024
corridor generating-rho LR movement is 7.7774 against 0.5, with influential
site probabilities sensitive to the sampled order bank. This is a terminal
finite-budget failure; it does not invalidate the conditioning identity.

The `goal-048-integration-redesign-check` heartbeat is now **paused** after
verified completion and terminal review. Previous Goal 045, 046 and 047
heartbeats remain paused. No simulations are running and no additional banks
have been launched. The next proposed work is a bounded replay of existing
corridor seeds with per-order/batch contributions at the influential sites,
to guide a reviewed variance-reduction or larger-budget choice. No adoption,
production requalification, ecological synthesis, commit, push or publication
is authorized.
