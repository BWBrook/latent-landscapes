# Stage costs of the completed A+B+C replay

16 November 2026. Read-only analysis of the 49 terminal fit receipts retained
from the 15 November repair assessment. This is development-resource evidence,
not a qualification result or authority to remove tight replay. Full precision,
per-fit stage wall/CPU times, input receipt hashes and event-stream hashes are
in [stage-times.json](stage-times.json). No model was rerun.

## Scope and time definitions

The 49 receipts comprise all 24 non-regression fits and 25 of the 27 formerly
failed development tasks: 23 now resolved and two retained scientific failures.
The two 48-hour kills lack final fit receipts and are excluded. Their partial
searches are not substitutes for complete task times. The two scientific
failures terminate before tight replay and have no latent-audit stage.

Times below come from `fit/receipt.json` (`cost.stages` and
`cost.total_wall_seconds`). They describe the fit process, excluding the task
wrapper startup/teardown counted in the previous assessment. Thus the pooled
695.019 fit-hours need not equal the earlier summed task-allocation hours.
Sums are over parallel tasks, not campaign elapsed time.

| Completed group | n | Median fit h | Maximum fit h | Summed fit h | Tight-attributed h | Tight/search pooled | Tight/full-fit pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Non-regression | 24 | 5.540 | 19.366 | 160.472 | 47.637 | 48.08% | 29.69% |
| Formerly failed development | 25 | 19.940 | 47.191 | 534.546 | 142.550 | 48.13% | 26.67% |
| All terminal | 49 | 11.460 | 47.191 | 695.019 | 190.188 | 48.12% | 27.36% |
| Resolved only | 47 | 11.775 | 47.191 | 693.932 | 190.188 | 48.18% | 27.41% |


## Native stage totals

| Stage | Receipts with stage | Median wall h | Maximum wall h | Summed wall h | Summed CPU h | Share of full wall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `input_hashes` | 49 | 0.000351 | 0.000510 | 0.017530 | 0.015813 | 0.00% |
| `load` | 49 | 0.000722 | 0.001136 | 0.035885 | 0.035669 | 0.01% |
| `search_setup` | 49 | 0.000001 | 0.000002 | 0.000051 | 0.000050 | 0.00% |
| `search` | 49 | 5.841768 | 28.667577 | 395.249827 | 394.880563 | 56.87% |
| `spatial_report` | 49 | 0.000002 | 0.000003 | 0.000082 | 0.000082 | 0.00% |
| `family_exposure` | 49 | 0.144094 | 0.454831 | 8.336213 | 8.333019 | 1.20% |
| `family_constant` | 49 | 0.229619 | 0.700794 | 14.795188 | 14.791006 | 2.13% |
| `latent_audit` | 47 | 5.116526 | 21.868372 | 276.579192 | 276.473784 | 39.79% |
| `envelope_guard_report` | 49 | 0.000016 | 0.000042 | 0.000778 | 0.000638 | 0.00% |

The stages sum to the complete fit time within 13.947 seconds pooled over
49 fits (median residual 0.093 seconds; maximum 5.065 seconds). Search consumes
56.87% of pooled fit wall time and the unchanged latent audit 39.79%; reduced
exposure and constant families together consume 3.33%. Among the 25 completed
development fits, latent audits total 226.646 hours across 23 audits, with a
median of 7.755 hours and maximum of 21.868 hours. The complete workflow,
including the audit, needs resumability.

## What the tight-replay number measures

`PanelSearch.started`, its event `elapsed_seconds`, and search
`cost.elapsed_seconds` use the same monotonic clock origin. Events are written
**after** fixed/free fits. For fixed fits the regime is `event.fit.tight`; for
free fits it is `event.tight`. Every event stream was checked for nondecreasing
timestamps and a final timestamp no greater than the recorded search elapsed
time.

The pre-existing `search.seconds_before_tight_phase` is the timestamp of the
first **completed** tight fit, not the start of tight replay. Subtracting it
from search time omits that first fit. The JSON retains both its preceding
event and first-completion timestamps, giving a bracket on the transition.
Moreover, standard and tight work are interleaved during final closure: a
single post-transition interval is not pure tight-replay time.

For each fixed/free event, this analysis attributes the elapsed wall interval
since the preceding event to that event’s regime. Untagged events and the final
unrecorded search tail remain separate. This yields 190.188 tight-attributed
hours: 48.12% of pooled search-clock time, or 27.36% of complete fit-process
wall time. It includes intervening bookkeeping and is **not** an exact pure
tight CPU stopwatch, a complete marginal cost estimate, or guaranteed savings
from removing tight replay. The per-fit median tight/search attribution is
47.95%; the pooled fraction weights longer searches more heavily.

The timing supports the claim that tight work is a substantial search cost.
It does not establish that tight replay should be removed: that would be a
separate prospective procedure decision, and its effects on closure, accuracy
and scientific outcomes are untested here. The large audit cost also prevents
treating tight removal alone as a solution to the complete-fit walltime issue.

## Per-fit breakdown

All times are hours, rounded here; the JSON retains full precision. `Tight*`
has the event-attribution meaning above. An em dash means the stage was absent,
not measured as zero. Full original task IDs are retained for unambiguous joins.

| Original task ID | Group | Class | Total | Search | Tight* | Exposure | Constant | Audit |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `fit-q-base-barrier-0-increased_heterogeneity-mu0.004-h1-A-exhaustive` | NR | resolved | 3.244 | 2.028 | 0.972 | 0.078 | 0.184 | 0.953 |
| `fit-q-base-barrier-1-increased_heterogeneity-mu0.001-h10-A-lean` | NR | resolved | 1.837 | 1.535 | 0.755 | 0.081 | 0.220 | 0.000 |
| `fit-q-base-barrier-1-window_high-mu0.004-h3-A-dense` | NR | resolved | 17.116 | 5.667 | 2.686 | 0.085 | 0.268 | 11.093 |
| `fit-q-base-barrier-1-window_low-mu0.004-h1-A-independent_bank` | NR | resolved | 2.268 | 1.980 | 0.996 | 0.078 | 0.208 | 0.000 |
| `fit-q-base-barrier-2-window_low-mu0.001-h10-A-independent_bank` | NR | resolved | 5.836 | 2.268 | 1.099 | 0.158 | 0.238 | 3.170 |
| `fit-q-base-connected-1-increased_heterogeneity-mu0.001-h10-C-lean` | NR | resolved | 11.775 | 6.770 | 3.307 | 0.444 | 0.610 | 3.950 |
| `fit-q-base-connected-1-matched_exposure-mu0.001-h1-A-exhaustive` | NR | resolved | 1.757 | 1.479 | 0.745 | 0.084 | 0.192 | 0.000 |
| `fit-q-base-connected-1-matched_exposure-mu0.001-h1-B-independent_bank` | NR | resolved | 1.804 | 1.527 | 0.764 | 0.080 | 0.196 | 0.000 |
| `fit-q-base-connected-1-window_low-mu0.004-h1-B-independent_bank` | NR | resolved | 15.620 | 4.856 | 2.417 | 0.144 | 0.203 | 10.417 |
| `fit-q-base-connected-2-constant-mu0.004-h3-B-exhaustive` | NR | resolved | 2.453 | 2.163 | 1.112 | 0.074 | 0.214 | 0.000 |
| `fit-q-base-connected-2-constant-mu0.004-h3-C-independent_bank` | NR | resolved | 9.564 | 8.678 | 4.481 | 0.184 | 0.701 | 0.000 |
| `fit-q-base-connected-2-window_high-mu0.004-h1-A-dense` | Dev | resolved | 47.191 | 28.668 | 13.498 | 0.091 | 0.182 | 18.249 |
| `fit-q-base-connected-2-window_high-mu0.004-h1-A-lean` | Dev | resolved | 23.621 | 10.016 | 4.951 | 0.144 | 0.166 | 13.294 |
| `fit-q-base-connected-2-window_low-mu0.001-h10-A-dense` | Dev | resolved | 21.613 | 13.442 | 6.137 | 0.110 | 0.207 | 7.853 |
| `fit-q-base-connected-2-window_low-mu0.001-h10-A-lean` | Dev | resolved | 12.517 | 7.397 | 3.526 | 0.151 | 0.203 | 4.765 |
| `fit-q-base-connected-2-window_low-mu0.001-h10-B-dense` | Dev | resolved | 16.914 | 9.092 | 4.150 | 0.098 | 0.227 | 7.496 |
| `fit-q-base-connected-2-window_low-mu0.001-h10-C-dense` | Dev | resolved | 33.187 | 16.106 | 7.367 | 0.339 | 0.523 | 16.218 |
| `fit-q-base-connected-2-window_low-mu0.001-h10-C-lean` | Dev | resolved | 26.209 | 11.790 | 5.843 | 0.455 | 0.512 | 13.451 |
| `fit-q-base-corridor-0-constant-mu0.004-h1-C-dense` | NR | resolved | 8.674 | 7.523 | 3.408 | 0.196 | 0.446 | 0.509 |
| `fit-q-base-corridor-0-constant-mu0.004-h1-C-independent_bank` | NR | resolved | 5.245 | 4.114 | 1.961 | 0.310 | 0.375 | 0.445 |
| `fit-q-base-corridor-0-increased_heterogeneity-mu0.001-h1-C-exhaustive` | Dev | resolved | 32.977 | 24.738 | 12.623 | 0.350 | 0.512 | 7.374 |
| `fit-q-base-corridor-0-increased_heterogeneity-mu0.001-h1-C-independent_bank` | Dev | resolved | 32.892 | 24.688 | 12.602 | 0.358 | 0.525 | 7.319 |
| `fit-q-base-corridor-0-increased_heterogeneity-mu0.001-h1-C-lean` | Dev | resolved | 32.138 | 24.356 | 12.396 | 0.344 | 0.504 | 6.932 |
| `fit-q-base-corridor-0-window_high-mu0.001-h10-C-exhaustive` | NR | resolved | 7.471 | 5.842 | 2.792 | 0.422 | 0.563 | 0.644 |
| `fit-q-base-corridor-0-window_low-mu0.001-h3-B-dense` | NR | resolved | 3.101 | 2.847 | 1.331 | 0.026 | 0.227 | 0.000 |
| `fit-q-base-corridor-1-b100_anchor-mu0.004-h3-A-dense` | Dev | resolved | 15.410 | 8.374 | 3.809 | 0.129 | 0.263 | 6.643 |
| `fit-q-base-corridor-1-b100_anchor-mu0.004-h3-A-independent_bank` | Dev | resolved | 9.027 | 3.324 | 1.561 | 0.175 | 0.253 | 5.274 |
| `fit-q-base-corridor-1-b100_anchor-mu0.004-h3-A-lean` | Dev | resolved | 8.871 | 3.307 | 1.564 | 0.188 | 0.258 | 5.117 |
| `fit-q-base-corridor-1-window_high-mu0.001-h3-B-dense` | Dev | resolved | 32.503 | 21.728 | 10.100 | 0.081 | 0.187 | 10.505 |
| `fit-q-base-corridor-1-window_high-mu0.001-h3-B-lean` | Dev | resolved | 18.913 | 12.939 | 6.333 | 0.141 | 0.182 | 5.650 |
| `fit-q-base-corridor-1-window_high-mu0.001-h3-C-dense` | NR | resolved | 19.366 | 10.759 | 4.871 | 0.259 | 0.583 | 7.763 |
| `fit-q-base-corridor-1-window_low-mu0.001-h1-B-dense` | Dev | search_unresolved | 0.668 | 0.371 | 0.000 | 0.169 | 0.127 | — |
| `fit-q-base-corridor-1-window_low-mu0.001-h1-B-lean` | Dev | search_unresolved | 0.419 | 0.118 | 0.000 | 0.170 | 0.130 | — |
| `fit-q-base-corridor-2-constant-mu0.001-h3-B-exhaustive` | NR | resolved | 2.105 | 1.797 | 0.889 | 0.086 | 0.220 | 0.000 |
| `fit-q-base-corridor-2-matched_exposure-mu0.001-h10-C-exhaustive` | NR | resolved | 5.875 | 5.131 | 2.543 | 0.202 | 0.541 | 0.000 |
| `fit-q-base-corridor-2-matched_exposure-mu0.001-h10-C-lean` | NR | resolved | 5.891 | 5.123 | 2.557 | 0.208 | 0.559 | 0.000 |
| `fit-q-base-corridor-2-window_high-mu0.001-h1-B-dense` | Dev | resolved | 21.183 | 13.186 | 5.794 | 0.053 | 0.188 | 7.755 |
| `fit-q-base-corridor-2-window_high-mu0.001-h1-B-lean` | NR | resolved | 10.625 | 6.181 | 2.796 | 0.110 | 0.164 | 4.170 |
| `fit-q-boundary-barrier-2-b100_anchor-mu0.004-h25-A-lean` | NR | resolved | 4.966 | 2.688 | 1.370 | 0.116 | 0.234 | 1.927 |
| `fit-q-boundary-corridor-0-b100_anchor-mu0.004-h25-A-dense` | NR | resolved | 7.378 | 3.073 | 1.390 | 0.077 | 0.168 | 4.058 |
| `fit-q-enriched-barrier-0-window_high-mu0.001-h1-B-lean` | NR | resolved | 1.891 | 1.604 | 0.809 | 0.092 | 0.195 | 0.000 |
| `fit-q-enriched-connected-0-increased_heterogeneity-mu0.001-h1-B-dense` | NR | resolved | 4.611 | 3.455 | 1.586 | 0.091 | 0.230 | 0.834 |
| `fit-q-enriched-connected-1-increased_heterogeneity-mu0.001-h1-B-dense` | Dev | resolved | 19.940 | 10.507 | 4.938 | 0.095 | 0.203 | 9.133 |
| `fit-q-enriched-connected-1-increased_heterogeneity-mu0.001-h1-B-lean` | Dev | resolved | 11.460 | 6.018 | 3.040 | 0.150 | 0.183 | 5.107 |
| `fit-q-enriched-corridor-1-window_high-mu0.001-h1-B-dense` | Dev | resolved | 17.161 | 11.153 | 5.348 | 0.114 | 0.256 | 5.637 |
| `fit-q-trend-barrier-1-temporal_trend-mu0.004-h3-A-dense` | Dev | resolved | 38.615 | 16.239 | 7.812 | 0.173 | 0.334 | 21.868 |
| `fit-q-trend-barrier-1-temporal_trend-mu0.004-h3-A-lean` | Dev | resolved | 27.906 | 10.497 | 5.333 | 0.222 | 0.313 | 16.873 |
| `fit-q-trend-connected-2-temporal_trend-mu0.004-h3-A-dense` | Dev | resolved | 19.557 | 4.954 | 2.292 | 0.161 | 0.329 | 14.112 |
| `fit-q-trend-connected-2-temporal_trend-mu0.004-h3-A-lean` | Dev | resolved | 13.656 | 3.155 | 1.533 | 0.189 | 0.287 | 10.023 |


## Reproduction and provenance

Selection SHA256: `099f28d9a45a8a4eb12b103ddaf23714ed3ced72120bb5c9184c9c75e514dfaf`.
Original replay-summary SHA256:
`7a9300b0db17c07d57d2c81a1be8b98d58aba8a71d31f0bb7fc133d290a3590b`.
All fit receipts name frozen source `a77e849ce0b0381b5c378b222bacfadce9beaf96`
and their original task IDs are in the fixed 24+27 selection. Each JSON row
records the hashes of the receipt and event stream used. No private address,
node identifier or access route is included.

The following read-only command reproduces the principal per-fit columns and
tight attribution directly from the retained payload:

```sh
.venv/bin/python - <<'PY'
import json
from pathlib import Path
base = Path('artifacts/sprint2/repair-20261112/final-20261115/fit-results')
print('task,total_h,search_h,tight_attributed_h,exposure_h,constant_h,audit_h')
for path in sorted(base.glob('*/attempt-0001/fit/receipt.json')):
    d = json.loads(path.read_text()); stages = d['cost']['stages']
    previous = tight = 0.0
    for line in (path.parent / 'search/evaluations.jsonl').read_text().splitlines():
        e = json.loads(line)
        regime = e.get('tight', e.get('fit', {}).get('tight'))
        if e['kind'] in ('fixed_fit', 'free_fit') and regime is True:
            tight += e['elapsed_seconds'] - previous
        assert e['elapsed_seconds'] >= previous
        previous = e['elapsed_seconds']
    h = lambda name: stages[name]['wall_seconds'] / 3600 if name in stages else None
    print(path.parent.parent.parent.name,
          d['cost']['total_wall_seconds'] / 3600, h('search'), tight / 3600,
          h('family_exposure'), h('family_constant'), h('latent_audit'), sep=',')
PY
```

Next: Claude — use full-stage costs when reviewing resumability and any later sizing decision.
