# Independent closure review: Goal 060 registered run

4 October 2026, Hobart. **Goal 060 remains a negative public-readiness result,
but the observed failure is a deterministic audit-interface defect rather than
an observed statistical failure.** The generated bank, panel and fitted-result
files are preserved and hash-consistent. The independent audit stopped before
any stored fit, profile, lattice point, held-out score or stability result was
directly rescored, so none of those producer results is independently
qualified.

## Decision target and inferential boundary

This review asks whether the failed full audit detected a discrepancy in the
synthetic data, fits or registered scientific gates, or whether the auditor and
producer represented the same provenance object differently. It does not
reinterpret the estimand, observation process, nuisance grid, bank, fitted
models or producer gate thresholds. The scientific target remains the
casewise evidence for a post-invasion hazard multiplier under the registered
synthetic design, with held-out conditional prey log score as the prediction
target and the eight-history panel as the fixed scope of inference.

The preserved `public-ready.json` is correctly negative. Producer success is
not a substitute for the required direct-bank audit, and this review does not
promote the producer's pass to scientific qualification.

## Exact failure

The failed receipt has SHA-256
`21cfa9c56e29d95b40524c8e5e6afbeba8c2dceef264f3494b1ddf99c5836132`
and records `ValueError: panel completion provenance bindings are invalid`.
The exception arose in `audit_panel_results` before construction of the three
direct-bank representations and before the loop over any history or fitted
point.

The function evaluates eight `completed_checks` predicates. Read-only
reconstruction from the returned artifacts found seven true and one false:

| Predicate | Result | Evidence |
|---|---:|---|
| status | true | `completed.json` says `completed` |
| histories | true | 8 |
| representations | true | `full`, `first_half`, `second_half` |
| raw arrival array | true | independently recomputed array SHA-256 `ebea5bb220958376d1aed871a5994cbbcc5c262b292da5f2d23f853a93e78e80` |
| observations file | true | SHA-256 `a65ebeeac8ff8f7e80229f0c5f2e2cc26b685afce03a1951c7fb33e0058f1110` |
| evaluator file | true | SHA-256 `12a5df75430d3d046f65163b72552177ed7005ba9756e292c393e5bc0aed18e2` |
| panel manifest | true | SHA-256 `c40e757bb8d41b8ed2a34125d7527bd86f3a54a2e5786aec89b2161c95a50dd9` |
| bank manifest object | **false** | producer object has one additional derived field |

The producer validates the on-disk arrival-bank manifest, copies its JSON
object, and adds

```text
manifest_sha256 = 38a20576dde419bc13363670a236b64cd72d66de06103a6bbd5b276e3f37b768
```

to the in-memory copy. It embeds that augmented object in
`panel-results/completed.json`. The value is exactly the SHA-256 of the
unaltered on-disk `arrival_bank/manifest.json`. The Goal 060 audit wrapper
instead reads the on-disk JSON directly and passes that unaugmented object to
`audit_panel_results`, which requires exact dictionary equality. Removing only
the derived `manifest_sha256` key from the embedded copy makes the two objects
exactly equal. No other key or value differs.

The on-disk object cannot directly carry a hash of its own final bytes without
a circular definition. The producer's augmented representation is therefore
intentional and internally valid; the wrapper supplied the wrong form to the
existing exact comparison. This defect was not exercised by the pre-freeze
tests: there is no test of `audit_panel_results` against a completion receipt
created through the production bank-validation path.

## Preserved evidence and limits

The registered producer stages completed with exit code zero. Its completion
receipt reports all task-status, all coarse-grid/main-fit and all eight
nested-bank stability gates as passed. All 53 expected panel-result files are
present: 24 task reports, 24 main-fit reports, three 1,350-point coarse grids,
the stability report and the completion receipt. The expected task identities
are complete. The return manifest binds the failed audit, panel completion,
observations, evaluator, panel manifest, arrival-bank manifest and arrival
array to the local copies. Closure verification matched all 658 returned
artifact hashes, all 303 frozen source-archive members and all 87 preserved
Goal 059 files. The return-manifest SHA-256 is
`13b4beeedf417b9953827477bc43e9ce7fd469d04fba8f50087ec41dafc14bc0`.

Control flow shows that the independent source/recovery checks, confirmatory
address check, registered calibration-fixture check, arrival-bank audit,
mechanical-receipt audit, eight-history fixture replay and predraw bindings all
returned without error before this failure. Their detailed returned
diagnostics were not written because the audit catches the later exception and
writes a minimal failed receipt. They should be reproduced by any prospective
audit recovery rather than inferred as final passes from this control-flow
fact alone.

The following registered checks were not reached and have no independent
result:

- direct scoring of all main fits and stored profile points;
- direct reconstruction of the three coarse lattice surfaces;
- held-out site and cluster score comparisons;
- independent nesting, profile-core and generating-coordinate gates; and
- independent reconstruction of full/half-bank stability.

Accordingly, the evidence supports byte preservation and a producer-reported
pass, not an independently verified statistical pass. It neither reveals a
failed fit nor establishes that every stored numerical result is correct.

## Recommendation

Preserve this run, the negative readiness receipt and the original failed audit
unchanged. Do not regenerate the bank or histories, refit models, edit the bank
manifest, rewrite `completed.json`, replace the failed receipt or relax any
scientific gate.

The narrow prospective remedy is a registered audit-recovery amendment that
changes only the Goal 060 wrapper's argument to `audit_panel_results`. It should
pass the raw manifest augmented with the independently computed
`bank_result["manifest_sha256"]`, reproducing the producer's validated object
while retaining exact equality for every substantive field. A regression test
should construct a completion receipt through the production validator and
show that changes to either a manifest field or the derived file hash still
fail closed. Changing the shared scoring or gate logic is unnecessary.

Because this repair is outcome-informed and changes frozen audit source, Barry
should approve the bounded recovery before execution and Fable should review
the patch, test, new source freeze and immutable input hashes. The recovered
audit should use a new output path and preserve the failed audit alongside it.
Only the full corrected independent audit should be run against the existing
artifacts; no scientific generation or fitting needs repetition. Public
readiness must remain false unless that audit reaches and passes every direct
score and stability check and a separately registered readiness-recovery step
binds the new audit.

An independent review materially changes confidence here: it identifies a
single exact interface mismatch and supports reuse of the immutable generated
artifacts, while preventing the producer's favorable result from being treated
as qualification before the unreached checks run.
