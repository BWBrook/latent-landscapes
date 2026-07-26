# Goal 006 Log

## 2026-07-26: Goal Authorized

Barry approved a process-only review of a second spread parameter before any
joint fitting. The parameter is landscape-resistance contrast

```text
c_e(eta) = g * (c_e / g) ** eta
```

at the prespecified grid `0, 0.5, 1, 1.5, 2`, with `rho = 1`.

The design preserves the exact Goal 003 edge fields as paired experimental
units and diagnoses away the best global time multiplier only in summaries.
No observation model, fitting, calibration, prey dynamics, real-data work,
remote compute, generated artifact, commit, push, or Goal 007 work had begun
when the contract was frozen.

## Implementation

The thin Goal 006 process, benchmark, artifact writer, CLI, and tests were
added without changing Goals 001-005. Production validation, canonical/repeat
bundle hashes, and the final decision class are recorded below after the
single focused repair pass.

## Completed 2026-07-26

Validation passed with `117` tests, `uv run ruff format --check .`, `uv run
ruff check .`, `uv run mypy src tests` (`51` source files), `uv build`, and
`git diff --check`. The canonical and repeat production runs each took about
13 seconds and emitted exactly 15 files. `diff -rq` reported no differences;
all generated artifacts and `dist/` remain ignored and unstaged.

The final outcome is `advance_to_joint_rho_eta_recovery`. The frozen Goal 003
eta-one constants reconcile exactly: cell-median `31.69888227914729`,
deterministic/stochastic-median correlation `0.9937734843350453`, temporal
scale ratio `0.4626972981816758`, t50 standard deviation
`1.6196762763006858`, and representative replicate `29` t50
`31.29398268570847`. The process has 5,225 passable cells, 823 water cells,
81 source cells, and 10,120 edges; all 100 paired shock streams replay, with
source-zero, water-infinite, and all-reachable invariants true.

Decision operands, computed at the replicate level, are:

| eta | median A | median J | median H | A/J consistency | expected-sign |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5 | 0.127747 | 0.140875 | 0.272237 | 100/100 | 100/100 |
| 1.5 | 0.136595 | 0.163093 | -0.294961 | 100/100 | 100/100 |

Both adjacent contrasts exceed the prespecified `0.05` A/J thresholds and
have the expected directional corridor-minus-matrix sign. The maximum
transformed edge-cost ratio is `23.349395408631782`, below the pathological
threshold of 100. The result supports a stable spatial process signature, not
joint parameter identifiability.

The focused review repair also made the two spatial diagnostics literal
representative-replicate map panels rather than aggregate line charts. The
aligned residual panels use a shared diverging scale and water masking; the
matched-front panels use raw 50% arrival fronts with explicit neither,
reference-only, eta-specific-only, overlap, and water-masked categories.
Matplotlib SVG IDs are normalized for byte-stable regeneration, and the
figure margins reserve separate legend/footer rows. The aggregate cell
summary now uses the actual frozen habitat classes
(`corridor`, `low_quality_matrix`, `high_quality_patch`, `medium_quality`).
Rendered SVG inspection found all five visuals nonblank and readable; the
canonical and repeat bundles are byte-identical. An independent table check
reconciled 5 edge rows, 500 unique replicate/eta rows, 5 spatial rows, 20
cell-summary rows, and 26,125 representative cell rows.

Canonical SHA-256 hashes (also identical in the repeat bundle):

```text
process_config.json 4635c6578b63c04d732e22ba0ae5c14da006b413064c12d19b17bf4c494bfe09
seed_manifest.csv 21bc26381c5f9e68943d7a2ba430716460577205333c3ab773050755b4f2a90f
edge_cost_summary.csv c25a3af5f7d49d5a239640a4d982cec286268e0546d00f22f5d570f88809e95f
replicate_summary.csv 94c197639280341e3fe44716311aa26386fbb9d5e13258272d3237136e45c3a7
spatial_effect_summary.csv 7ecbf7eec37c2f7b45e22efb0889d7590935af14b4bd89c594e719d270737623
cell_summary.csv b98daece55a6e40aebc611f1c3af64f724cc28d521c65ffa2d2e2533cba4000f
representative_realizations.csv 679b31b570cee9e4918f694401639f495e22952250ea27ca509e2a389406cf8d
summary.json 82332813a45e3d952910544283e4ba3e14beb819d9ebe68cba8aaaec939c63a0
verification.json 179dcac1fb5d52a4629527473e72d0ca1ebadbea2dd94caf616782da0775c15d
review.md bbb841440de56c08f7b925e31648641a2c89c5871fc8af3c127ba7110c235366
visuals/aligned_residual_maps.svg 7fdc3b53bb497a65fb3520e44b6ab903319c65a1b8ec9dc305399cb0a09d19ab
visuals/edge_cost_transformation.svg 60ef007477c02a24247b20056d0bf0d8ea6a755de9dd2587daa5bf8f55fae61b
visuals/habitat_contrast_curves.svg 15e0a46c25c0a5bc6ecb33d0717abed49f16119f9749042db8b6f8f0c9060c41
visuals/matched_occupancy_fronts.svg 32500985decf1489b5eb6c81b3319d97fd387328f71380e8acb827d8d9f4a9d0
visuals/source_reassignment.svg 3312f90ea0e3831d5ba0e8b491a7b612ff83e91ced6720bc550958d1b9a6e488
```

The remaining limitation is deliberate: this is a single accepted landscape
and process-only benchmark. It does not include observations, prey dynamics,
likelihood fitting, or a claim that `(rho, eta)` are jointly identifiable.
