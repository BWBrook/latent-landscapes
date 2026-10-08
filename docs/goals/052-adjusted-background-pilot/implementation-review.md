# Goal 052 independent implementation review

24 September 2026. **GO for the registered full-bank pilot.**

An independent scientific reviewer verified the map-normalized hazard,
survival algebra, arrival-category boundary convention, alpha=1 empirical and
pseudo-arrival mixture, beta-zero nesting and h=1 factorization. Actual fits
consume observations, A and the independent bank. True arrivals enter only
the oracle lane and evaluator diagnostics. All models receive identical known
nuisances and fit the fixed training sites; held-out scores never select fits.

The exact category transform is an algebraic rearrangement of the existing
empirical likelihood, not a new approximation. Direct finite-mixture and
two-state oracle controls pass, including arrivals exactly at survey times.
Beta=0 agrees with the unchanged likelihood within tight roundoff tolerance
on the small-bank controls. Exact production-bank replay remains the first
mandatory control in the dispatched run.

## Repairs required and completed before launch

The review required authentication of the frozen Goal 051 run contract before
trusting its expected hashes; atomic receipt-last row writes; validation of
cached keys, dimensions, dtypes, finite values, row coordinates, source/input
identity and checksum; and preservation/recomputation of incomplete writes.
All are implemented and covered by meaningful failure-mode checks. Continuation
compares the complete recomputed contract, not only a stored fingerprint.

The review also found an incorrect synthesis subset pooling baseline and
aligned h=3 histories. It is corrected before any pilot evidence. Fitted-edge
flags are explicit for both lanes, the 0.10 sensitivity rule permits only
roundoff tolerance, prediction summaries retain descriptive blockwise evidence,
and synthesis hashes use explicit new outputs. Existing completed synthesis
cannot be silently overwritten. The contour layout now groups cells by row
and the six paired blocks by column.

The external wrapper supplies a nonblocking exclusive lock, completed-run
refusal, an initial 14,400-second timeout plus 30-second kill grace, eight
beta-row workers, numerical threads one and a 32-GiB virtual-address ceiling
for the single threaded scoring process. Its hash is bound and rechecked.
Barry's delegation permits documented operational changes if measured demand
requires them; it does not change the scientific design.

## Verification evidence

- Local combined likelihood, replay, row-cache, synthesis and relevant legacy
  tests: **90 passed**. New source/tests and entrypoints pass Ruff and strict
  MyPy. Shell syntax and Git whitespace checks pass.
- Independent reviewer checks: **49 passed** after the provenance repairs.
- Linux qualification: **89 passed** in the combined run; the only initial
  failure was the unstaged archived-data fixture. After linking the existing
  immutable archive into the test path, that remaining check passed (**1/1**).
  Both logs are retained; no numerical assertion failed.
- Remote preflight at 2026-09-24 03:38:57 UTC verified **83 frozen current
  source/test/design files**, **77 inherited source/input files**, the original
  production archive and the complete K131072 bank, including seeds/site order
  and prefix identity. No previous Goal 052 run or active wrapper existed.

Registration SHA256:
`dda6da90aefa8123ffe6e512cd50d03756c20667a8eccecf2383f66f277ea538`.
Wrapper SHA256:
`d895a14e9b956dd6f474fb2d89b53827046491954c4b1516b628cf49740bca10`.
The full source manifest and preflight receipt live under
`artifacts/goal052_execution/` and the named remote run root.

## Scientific limits retained

This is likelihood geometry on six previously examined blocks, one landscape,
known nuisances and a fixed finite bank/grid. The adjusted model omits G.
There is no exact nonzero-beta generating positive control in this panel;
therefore a ridge cannot uniquely diagnose survey information rather than
misspecification. h=1 contact under a null is expected but still yields
one-sided geometry. No old cutoff, coverage, power, structural-identifiability
or recovery claim is permitted. These limits do not block the approved pilot.
