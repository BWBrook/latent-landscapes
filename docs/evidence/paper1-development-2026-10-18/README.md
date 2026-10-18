# Paper 1 development evidence, 18 October 2026

This is the compact source-and-receipt archive for the
[development report](../../paper1-numerical-development-2026-10-18.md) and
[protocol](../../paper1-integrated-tranche-protocol-2026-10-18.md).
These diagnostics use archived Goal 060/062 inputs. They are not new
validation data, a production package or a calibration result.

`manifest.json` maps each snapshot to its original repository-relative path
and SHA-256. Larger per-history tables and optimizer receipts remain in
`artifacts/paper1_planning_20261018/`; the manifest records their hashes.
The archive preserves the first failed GP implementation and its independent
audit, as well as the repaired version. Historical results are not relabelled
as successful qualification.

For reproduction, use a separate checkout with the recorded Goal 060/062
input archives available. Restore snapshots to the original paths listed in
the manifest. Scripts derive paths from their execution directory depth and
write outputs beside themselves; the preserved GP source versions must be
placed at `artifacts/paper1_planning_20261018/gp-prototype/run_gp_prototype.py`
when executing them, rather than run inside a snapshot subdirectory.
Run with the repository's locked
Python environment, e.g. `.venv/bin/python <restored-script>`. Do not execute
the source copies directly from this evidence folder. Numerical integration
and optimization use NumPy/SciPy; exact runtimes and source/input hashes are
recorded. Elapsed times are hardware- and load-dependent.

The final GP result combines three preserved fits and one targeted repair.
The pre-tight-polish source and complete receipts are archived under
`gp/pre-tight-polish/`. To replay the repair, restore those receipts to their
original snapshot directory and run the final source with
`--repair-from artifacts/paper1_planning_20261018/gp-prototype/intermediate-pre-tight-polish`.
To repeat the earlier full search, execute the pre-tight-polish source at the
execution path above in a separate checkout. Per-endpoint provenance in the
final manifest distinguishes those executions. The parent endpoint check
reevaluates all selected fits with the final criterion.

The frailty check reads hidden complete-data times deliberately. The GP
prototype reads the observation packages, public covariates and arrival bank;
both examples have the full pre/post calendar. The sequential check enumerates
binary rank sequences and evaluates binomial probabilities, with no ecological
simulation. The normaliser and original oracle checks preserve earlier
Claude–Codex mechanism work.

Codex (GPT-6) integrated the work and independently reconstructed the frailty
arithmetic and Gamma integral. The bounded implementation delegates used
GPT-5.6-luna; the independent GP numerical reviewer used GPT-5.6-sol.
After identifying optimizer failures, that reviewer also implemented the
targeted numerical repair; the parent checked the repaired endpoints separately.
Claude's originating analyses and scientific proposals are attributed in
Correspondence thread 87. This record supplements that exchange; it does
not treat agreement between models as numerical verification.
