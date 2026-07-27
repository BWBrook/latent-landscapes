# Goal 009 Log

## 2026-07-27: Authorized And Frozen

Barry approved a bounded recovery of Goal 008 under the programme's 80/20
delivery policy.

The first Goal 008 remote campaign completed its nine worker computations but
returned `implementation_blocked` after 50 minutes 44 seconds and wrote no
scientific pack. Source and inherited fixed-input invariants were subsequently
confirmed true. Because the aggregate and cell diagnostics were discarded,
the exact failed invariant is not observed.

Independent reviews ranked cross-platform bit-exact central projection hashes
as the leading explanation. The accepted Goal 007 reference was generated on
the Apple Silicon Mac, whereas Goal 008 ran with Python 3.14.5 and NumPy 2.5.1
on x86-64 Linux. This remains an inference; a genuine cell invariant failure
cannot be excluded.

Goal 009 freezes every Goal 008 scientific choice. It changes only the central
implementation-continuity comparison and the persistence of evidence after a
completed blocked campaign. Structural fields remain exact. Finite floating
fields use independently reviewed nine-decimal canonical projection hashes,
while raw hashes remain audit evidence.

Any completed hard block must write a strict three-file quarantine diagnostic
bundle containing campaign, cell, central, class-surface, telemetry, and
non-finite evidence. One unchanged `deep-server` production campaign is
authorized after local and independent review. It will not be rerun within
this goal.

## 2026-07-27: Implementation And Reference Audit

Development was test-first. The focused red gate collected 17 tests: eight
failed on the intentionally absent Goal 009 surfaces and nine inherited tests
passed. Missing surfaces were projection canonicalization, retained per-cell
invariants, the blocked diagnostic writer, and pre-campaign trust and CLI
routing.

The accepted Goal 007 `calibration_results.csv`, `validation_results.csv`,
`bank_summary.csv`, `predictive_summary.csv`, and `seed_manifest.csv` were
parsed in an independent one-time standard-library audit without importing the
Goal 008 implementation. The bank and predictive tables were joined by
`bank_variant`, accepted row order was retained, and typed payloads reproduced
the three historical raw hashes exactly:

```text
calibration 60b541649ad8fffa7bef0810c5246358c50dacf01027c2a6fa5bf6cbb5523f24
validation  ac559b76981b9962db4e537f725dd8c87b8348866e4c28000c7316348bb08439
bank        76168e5525ddf86f50c702c88ffff04206875de19acba12801c0d548dd788e3d
```

The reviewed canonical rule recursively rejects non-finite values, rounds each
finite float with `round(value, 9)`, normalizes either signed zero to `0.0`,
then hashes compact sorted-key strict JSON. An independent audit resolved the
otherwise ambiguous string-versus-number representation in favour of rounded
JSON numbers. The hard-coded canonical hashes are:

```text
calibration 4dc4feac4a37a40cbb61052451b324420a2b356fab88c1b0438998c9007ce021
validation  007d763117d4417c0192034bd99a126d2c103ba5afe2d76fd660d94213ed76e5
bank        5c5c97e2b3ab273f7976a0fda1285cb56c94d25a3a06803a2b835eb87c7cb5ce
```

Exact structural hashes are
`6bd91745eab72ba27e989ca6ff26aaccf0f7a2746a92cc96a7d6dd5937627687`,
`235530e3acb0d8b12d784ae01b94c108f95f7d2a9e01ea02682d40a95b73b905`,
and `ef9510ad0bab11c6bc1f2b6281be485499343b66aac3ae7b98d4525d95af8971`.
The accepted seed-manifest identity is
`2b57f1eb90db41201d5a1311db168c7012953e4f6683bd5c37845ac7a0113aae`.
Runtime code has no dependency on the ignored Goal 007 artifacts.

Goal 008 now retains all nine cell invariant maps. A completed blocked campaign
writes exactly `diagnostics.json`, `compute_provenance.json`, and
`verification.json` after the same trusted provenance gate; pre-campaign
trust failures and worker exceptions write neither diagnostics nor a
scientific pack. Non-finite values use explicit tagged strings plus paths while
all JSON remains strict. The first focused green gate passed all 17 tests.

## 2026-07-27: Local Acceptance

The single focused self-review found no scientific or reconciliation defect.
It added direct assertions that a completed scientific result writes no
quarantine and that failed pre-campaign trust prevents campaign execution and
diagnostic claims. It also clarified the post-campaign pack-failure message.
No further repair loop was started.

Final local validation:

```text
focused Goal 008 tests                 17 passed
git diff --check                       passed
Ruff format check                      73 files already formatted
Ruff check                             passed
mypy                                   65 source files passed
full pytest                            154 passed, 3 inherited Goal 006 warnings
uv build                               sdist and wheel built
```

No production-sized campaign was run. No files were staged, committed, or
pushed, and generated build and artifact outputs remain ignored.

## 2026-07-27: Phase-Identity Continuity Repair

An authorized review found that the calibration and validation central
projection payloads omitted the exact structural field `phase`. Development
again started red: the focused benchmark suite reported two failures and nine
passes. The reviewed constants disagreed with the phase-blind references, and
changing an actual central calibration row from `phase="calibration"` to
`phase="validation"` incorrectly left the real production reconciliation gate
matched.

The accepted Goal 007 calibration and validation tables were re-parsed with a
standalone standard-library derivation. Their separate table identities
unambiguously supplied `phase`; before adding it, the derivation reproduced
both historical raw hashes exactly. An independent reviewer obtained the same
replacement hashes. Only the affected calibration and validation references
changed:

```text
calibration structural
  old 6bd91745eab72ba27e989ca6ff26aaccf0f7a2746a92cc96a7d6dd5937627687
  new 2da6de6fd746892c72e4ba7b2eff5174c494f33912f4b097c2d7ed3c64d916d7
validation structural
  old 235530e3acb0d8b12d784ae01b94c108f95f7d2a9e01ea02682d40a95b73b905
  new 9edab67ef228a0e8ec634caae235e9f858f1fd461e5886dc0e113d5aa0acb173
calibration canonical
  old 4dc4feac4a37a40cbb61052451b324420a2b356fab88c1b0438998c9007ce021
  new b2d157ce2ab0c2303f6a9cc9455c9c64f89275581eb9805ba745b0f03f9955b9
validation canonical
  old 007d763117d4417c0192034bd99a126d2c103ba5afe2d76fd660d94213ed76e5
  new bce714706ccf2ecdb9377d213ed54f17d37c3b0c30bb4b9ae11fada0351452f4
```

The historical raw hashes remain unchanged audit evidence, and all bank
constants remain unchanged. For additional non-gating audit evidence, the
phase-inclusive raw hashes are
`5b318ea7fa4938a55b5883dd2a6f1ac20862e68b28abcb62a36e206255fa972c`
for calibration and
`c5f8d365945cc459726b4308290e082493168eed42efc029812ff89e2390d133`
for validation.

After adding `phase` to both central payloads, the focused benchmark suite
passed all 11 tests. The regression now proves through `_central_projection`
that the exact payload passes while a phase-only mutation fails the actual
production continuity gate. No scientific configuration changed, and no
production campaign was run.

Final bounded repair validation:

```text
focused Goal 008/009 tests             18 passed
Ruff format check                      2 files already formatted
Ruff check                             passed
targeted mypy                          2 source files passed
git diff --check (three owned paths)   passed
```
