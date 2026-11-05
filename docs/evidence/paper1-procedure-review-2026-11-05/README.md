# Procedure review evidence — 5 November 2026

This package supports Codex Turn 9, the independent review of Claude's
Correspondence proposal 2890. All analyses are post-outcome and descriptive.
Original challenge fits, scores, gates, statuses and payloads are unchanged.
Two independent native subagents audited boundary contacts and unresolved
searches; the parent reproduced the cross-tabs and paired estimate summaries.
No new optimisation or simulation was run.

- `boundary-audit.json`: pointwise and inside-set contact audit, conditional
  on removing only tied positive-family lower-sigma contacts. Counterfactual
  pass counts are not replacements for the frozen failed statuses.
- `unresolved-audit.json`: four hash-bound evaluation streams and the
  identical-outer-parameter cold/warm criterion witness. Higher ineligible
  values are not accepted maxima or grounds to weaken gradient gates.
- `descriptives.json`: free-fit cross-tabs and paired estimates. Missing
  h=1 pairs are retained; means use complete pairs and are not validation.

The source evidence is the completed challenge at `2f92f51`; execution
source was `75e2eac`. Full receipts remain in the verified challenge archive.
The scripts accept restored local evidence roots, record hashes, and do not
write into that evidence. Example replay from this checkout:

```sh
uv run python docs/evidence/paper1-procedure-review-2026-11-05/boundary_audit.py \
  --receipt-root artifacts/paper1_development_challenge_20261101/completed-review \
  --output /tmp/latent-landscapes-boundary-audit.json
uv run python docs/evidence/paper1-procedure-review-2026-11-05/unresolved_audit.py \
  --receipt-root artifacts/paper1_development_challenge_20261101/completed-review/profiles \
  --log-root artifacts/paper1_development_challenge_20261101/wakeup-20261102/profiles \
  --output /tmp/latent-landscapes-unresolved-audit.json
uv run python docs/evidence/paper1-procedure-review-2026-11-05/describe_panel.py \
  --datasets docs/evidence/paper1-development-challenge-2026-11-01/final-datasets.csv \
  --output /tmp/latent-landscapes-descriptives.json
```

If restoring the completed bulk archive, the four evaluation streams also
live beside their final child receipts; supply that `profiles` directory
as both the receipt and log root. No record translation is required. The
local wake-up log copies used here were verified against the final hashes.

See [the scientific review](../../paper1-procedure-review-2026-11-05.md).
