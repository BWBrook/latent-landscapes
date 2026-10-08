# Complete report lock before truth release

8 October 2026, Hobart. The training-plus-holdout report and its independent
review are complete. This lock fixes their interpretation before Claude's
review and Barry's separate generating-truth release. It does not authorize
truth access.

The locked [complete report](complete-report.md) has SHA-256
`066abaff982d9d909a28a602d4c4fe93a0121ff8a6fd87c4854bf0c6b8d4dadb`.
The [independent review](holdout-independent-review.md), which accepts the
scores, forecast classifications and report for locking, has SHA-256
`e25d98fa9dd8e80ac24d97c1e1f7816c40a8f71f0a54cde2a260a9b4f831680f`.
Case-00 is the sole leading-pair forecast hit; cases 01--03 are misses.
The training results and all still-unevaluated truth forecasts remain fixed.

## Bound evidence

The root manifest is `artifacts/goal061_holdout/complete-report-lock.json`.
Its direct file mapping binds this note, the complete report, independent
review, execution record, full-precision result CSVs, PNG/PDF figure and its
provenance, three new stage scripts, two targeted test files, and release and
return-verification receipts. The returned-run inventory binds all 36 files
from the original Linux execution, including both independent-audit versions,
the final executed sources, test logs, commands and resource measurements.

The accepted training lock remains an explicitly inherited evidence closure:
its 52 direct files and five based inventories cover 3,734 unique files and
6,375,566,653 bytes. Its original root SHA-256 remains
`2265d62e3e953792b2892a4d7b34c784d5800b2f7ba078db99ed753e13bd1861`.
The original training lock and its release flags are historical and unchanged;
Barry's subsequent holdout authorization is recorded in the new release
receipt. The released archive commitment remains
`53903e56b0b86d8d713bf643d9c3062e8ce918fa8b84afa48f9b8ace6859fe6a`.

The final score JSON is
`a5c58a4a95f2deb6031f4b7297229e54c091f3c26e0efe33929025c54c5c43d2`.
The final independent-audit receipt is
`41b499344e02aba943291eca52d0651ad97b48b49747536d10afdc011b3a9769`.
All sixteen scores, their site and cluster components, pairwise differences,
exact maximizing sets and forecast outcomes agree between the qualified
compressed-bank path and the independent direct raw-bank reconstruction.
The latter uses the same fixed bank and does not assess bank-replicate
uncertainty or broader scientific generalization.

## Checksum and release boundary

The external `artifacts/goal061_holdout/complete-report-lock.sha256` commits
the root manifest without a self-referential hash cycle. The separate
`artifacts/goal061_holdout/complete-lock-verification.json` records the final
root checksum and exhaustive verification of its explicitly inherited and
newly bound files. Mutable status pages remain outside the lock. Paths merely
mentioned inside evidence files do not become additional recursive inputs.

The report is fixed for Claude's review. Barry must separately authorize the
truth release after that review; neither this lock nor a successful numerical
audit grants access. No truth plaintext, private key or private generating
identity was accessed during this stage. Later truth checks must retain the
committed forecasts and scoring rules, including incorrect forecasts.
