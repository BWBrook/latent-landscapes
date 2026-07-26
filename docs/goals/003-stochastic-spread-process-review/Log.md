# Goal 003 Log

## 2026-07-26: Goal Authorized

Barry approved Goal 003 as a stochastic generating-process review gate before
any fitting. The approved formulation is a continuous-time,
conductance-weighted edge-transmission process with `rho` retained as the sole
future focal spread parameter.

## 2026-07-26: Pre-Packet Feasibility Evidence

Before freezing this packet, the orchestrator ran bounded, unretained local
probes of the proposed exponential-edge process to test feasibility and expose
obvious semantic problems. These were exploratory checks, not confirmatory
Goal 003 evidence.

The 100-replicate probe used the accepted 5,225-cell, 10,120-edge graph and
showed:

- exact local mean transit time `c_e / rho`;
- median stochastic time to 50% colonization about `31.1`, compared with
  deterministic median passable-cell arrival about `68.5`;
- all 100 stochastic realizations fully colonized by `t = 110`;
- correlation about `0.994` between deterministic arrival and the stochastic
  ensemble-median arrival surface; and
- non-zero replicate variation in spread timing.

An independent methodological review confirmed that the faster
landscape-scale wave is expected from competition among alternative random
paths. It is not an implementation error, but it breaks any assumption that
`rho = 1` preserves Goal 001's global arrival scale.

The production ensemble uses the separately frozen master seed `20260727`.

Accordingly, Goal 003 explicitly forbids post-hoc normalization or retuning.
The production pack must expose this temporal-scale issue and may validly
return `time_scale_review_required`.

No Goal 003 source code or generated review pack existed when this entry was
written. No observation model, inference, prey process, commit, or push was
started.

## 2026-07-26: Goal 003 Implementation And Validation

Implemented the frozen stochastic first-passage process on branch
`codex/latent-landscapes-goal003-stochastic-process-review`. Source identity
is the accepted Goal 001 landscape commit `53462d0365babf2c8070714a930f69b4071af276`,
landscape blob `f2f5fc24e64274e443f8eec8c314e212e2a6889f`, and spread blob
`cb15f2178ff9e2f359f06fdac34a9b551e163cd5`. No legacy repository was read at
runtime and no raw ensemble grid was written to artifacts.

The production command was `/usr/bin/time -p uv run python scripts/run_goal003.py`.
It completed in `2.13 s` wall time (`2.07 s` user, `0.05 s` system), wrote
exactly 13 files, and returned `time_scale_review_required`. The graph had
5,225 passable cells, 823 water cells, 81 source cells, and 10,120 undirected
passable rook edges. All 100 ordered `SeedSequence(20260727)` PCG64 children
were unique and replayable; all passable arrivals were finite, water arrivals
infinite, source arrivals exactly zero, and source provenance was populated.
A same-seed rho=2 check scaled every finite arrival exactly by one-half. The
deterministic/stochastic median cell association was `0.9937734843`;
deterministic median arrival was `68.50889859`, stochastic ensemble-median
median arrival `31.69888228`, and their temporal-scale ratio `0.4626972982`.
The old reference horizon was saturated in all replicates. Stochastic t50
sample SD was `1.61967628`.

Validation passed: focused Goal 001/003 tests `11 passed`; full pytest
`68 passed`; Ruff format/check clean; strict mypy clean; `git diff --check`
clean; and `uv build` source/wheel build successful. A second clean temporary
ignored bundle had an identical file set and bytes under `diff -rq`. The
canonical 13-file pack is
`artifacts/goal003_stochastic_spread_process/` and is ignored; no files were
staged, committed, merged, pushed, or published.

The temporal-scale mismatch is a completed process-review result. No
normalization, tuning, alternate distribution, observations, fitting, prey
process, or Goal 004 work was started. Human review is required before
transferring this generator to inference or choosing a calendar-scale
normalization. Artifact SHA-256 values are retained in the production handoff
record from this run; representative labels are deterministic t50 ranks
10/25/50/75/90.

All four SVGs were rasterized once with `rsvg-convert` and inspected as a
contact sheet; maps, selected realizations, trajectories, and the temporal
scale scatter were nonblank, labelled, and visually readable.

An independent final review reconstructed the frozen graph and all 100 seed
manifest rows, replayed replicate 0 and all five mechanically selected
replicates (52, 44, 29, 66, and 11), and reconciled their occupancy,
threshold-time, maximum-arrival, and source-contribution summaries exactly.
It found no material scientific, semantic, code, or provenance defect and
recommended acceptance. The only noted limitation was that the
machine-readable `seed_replay` invariant exercises child 0; the broader
selected-replicate replay is recorded here as independent review evidence.

SHA-256 values in declared file order (`process_config.json`, seed manifest,
replicate summary, cell quantiles, habitat summary, representatives, summary,
verification, review, and four SVGs):

```text
613f90e2c8f39fea175b34cc9f5465ef3d6c3d6a8fe72208bccd593b4f6183ca
639f4621ce1d43af50d58027b308706787861a7f47e303d0c1502b83b6e59efe
a0623c73a533e519644542e29c903c751d4ee3634fd2711c7663ed0bfa9b446c
6cda6c74162064c80e5f7af80cd65060255911a6a1fd96b37b93effcc994c52b
4f6176a96e1df916230cc7f414a44f20bc7a2b47fe751712639ccdd4feeb8ec4
bce866482c1c47430d0a0e82287dd43aa37455b956d6dc705550189dcc017a4d
6e23edb6c95f6df7ddb4535d42313145bc8ed786efced218c1abe34e7eda9739
38bb9e356af3d59ee4d09c1f37a1a935558911e8a3c1cc91b5ef076be95c4027
9ac5f14b764baaa2ccd9f7bea8820848ce81ab2d8336161bed54ca9e9af8df20
59aedc04718b1a4d541125685c93954010d59b6c13d695bbaf7c9aaed953c931
2e967877ab1a0b655815cbe7589ebcad5627ad2959b2ffd72c41e5cfb8210914
677bf606eca7ea0f5e5b30a6912a7eabcc3d609b36adbd5a0a3804dd0563ae05
4147b12a0bdec32e3fa6e584e1981632852760e444016b0724910e0f8640616e
```
