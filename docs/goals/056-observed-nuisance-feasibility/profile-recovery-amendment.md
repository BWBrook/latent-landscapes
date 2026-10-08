# Diagnostic profile recovery, 3 October 2026

The registered panel generated exactly its sixteen histories and saved all
64 main model fits and all sixteen pre-only fits. All 64 main fits report
convergence. Twelve cells completed all diagnostics. Cells 1, 9, 11 and 15
failed during beta-profile continuation when decoding the allowed upper bound
gave `exp(log(10)) = 10.000000000000002`; the next seed validator rejected it
as outside `[1,10]`. The failed run exited 1 after 149.150845 s. Its data,
source snapshot, logs and partial outputs remain at the original v2 root.

This is a profile-seed representation defect. The repair snaps seed values
within eight ULP of a declared physical bound to that bound, then performs the
existing validation. Genuine violations remain errors. Only `_profile_starts`
changes in the scientific source. An AST comparison verifies that every other
definition, including the main fitting algorithm, is unchanged; that helper
has only the two profile callers. The new regression exercises continuation
at the rounded upper bound and rejection of a genuine violation. Main-fit
starts, stopping tolerances, objectives, likelihoods, parameter ranges and all
acceptance tolerances remain exactly as registered.

Recover only the four incomplete cells' diagnostic profiles and fixed-fit
holdout scores. Reuse the saved main/pre-only fit values, copy all sixteen
main files byte-for-byte, and copy the twelve completed cell files byte-for-byte.
Do not generate any history, rerun a main fit or replace a main maximum with a
profile maximum. The original coarse lattice never ran; execute it once after
the four missing cells are recovered, then apply the original 1e-6 gap audit.
Retain any remaining numerical failure without changing the rule.

An independent native methodological reviewer accepted this bounded recovery
as a numerical repair, conditional on preserved input/main identities,
Linux regression checks and a separate recovery receipt. Freeze the amended
source and this record before recovery. Use four workers and one BLAS thread
each, with the original 48 GiB RSS cap and at most the original four-hour
compute allowance minus the 149.150845 s already spent. The original complete
cells retain their original source provenance; recovered diagnostics record
the amended provenance separately.

The failed run did not flush its in-memory generation timer. For cost planning,
the gap between `started.json` and the generator manifest's remote file mtimes
is **1.674007159 s**, or about .105 s/history. This is explicitly a filesystem
timestamp proxy, not the exact timer measurement. The original and recovery
wrapper receipts supply measured complete-phase times, including repeated
work lost from the four incomplete cells. Preserve those costs in the final
feasibility report.
