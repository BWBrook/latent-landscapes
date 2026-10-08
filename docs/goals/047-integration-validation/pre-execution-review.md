# Goal 047 pre-execution scientific review

**Review date:** 11 September 2026, before any Stage A study output.

## Decision

The registered design is scientifically coherent and appropriately bounded,
and the final Stage A decision checker implements its declared comparison and
classification rules. The checker is ready for use after the numerical runner
passes its separate real-helper smoke and produces the bound technical replay
receipt. This review does not constitute a Stage A result or accept any Goal
046 evidence.

The design targets two decision-relevant numerical functionals: the calibrated
known-rho null effect width and the effect-profiled rho core/tail. It separates
pseudocount weight within a fixed empirical bank from bank realization at equal
K, keeps the post-selected failures distinct from prospective controls, and
limits any positive conclusion to operational repeatability. The conditional
early stop avoids generating six new banks if the existing integrator is
already materially alpha-sensitive. Three fresh K65536 replicates can proceed
only after that gate; they do not form a pooled higher-K reference. This is a
leaner and more discriminating design than another bank-doubling ladder.

## Checker reconstruction

For the connected width functional, `width_summary` correctly:

- takes the 239th one-based order statistic as zero-based sorted index 238;
- applies each design/bank/alpha's own cutoff with an inclusive LR mask;
- counts connected support components from false-to-true transitions;
- derives lower and upper H181 endpoints and their log-ratio width;
- evaluates null coverage at effect-grid index zero; and
- forms balanced-minus-access width and coverage/exclusion contrasts.

`compare_width` applies the registered 0.5-LR cutoff, zero topology and boundary
changes, one-cell endpoint, one-history count, one-of-250 contrast and 0.01 mean
log-width limits. Opposing access and balanced count changes cannot cancel
because both design-specific and paired-contrast movements are checked.

For the corridor functional, `tail_summary` profiles the raw joint surface over
effect and rho separately, centres each truth/bank/alpha profile at its own
maximum, and retains rho=1 as the first candidate for the direct tail check.
`compare_tail` constructs the pairwise union of nodes where either centred
profile has LR<=10, then applies the registered effect-MLE, rho-MLE, core-LR and
generating-rho LR tolerances. Raw rho-profile movement and maximum shifts are
reported diagnostically without creating a new gate. The window rule now marks
the isolated rho=1 node and either edge of the seven-node window as
inconclusive whenever any of them attains the maximum, including a tie that
`argmax` alone could miss.

All three pairwise alpha comparisons are made within each half or combined
bank. Equal-K half comparisons and the two matched-relative-weight comparison
families are reported but do not enter the Stage A alpha-sensitivity decision.
This matches their diagnostic, correlated status. A fixed-window inconclusive
case takes conservative precedence over an independent width or alpha failure;
the output therefore stops without mislabelling incomplete tail scope as a
pseudocount effect.

## Repairs made before this review

The initial checker omitted the registered technical replay gate, detected only
the `argmax` rho node at the window boundary, and discarded raw likelihood
diagnostics. Before this final review it was strengthened to:

- require a runner report with completion status and exactly four connected/
  corridor, half0/combined replay errors no larger than 1e-9;
- verify that the report binds the supplied NPZ by SHA256 and exact array
  inventory;
- detect any forbidden rho node tied at the maximum; and
- retain non-gating raw profile and maximum movements for interpretation.

These changes repair decision validity without expanding the registered
criteria.

## Verification and remaining limits

Nineteen focused tests covering the checker and pseudocount reweighting pass.
The decision tests directly exercise rank-239 calibration, disconnected support
topology, opposing design-count changes, independent profile centring,
generating-rho movement outside the LR core, tied edge maxima, failed replay and
unbound arrays. Ruff and formatting checks pass for the checker and its decision
tests.

The checker assumes that the bound runner report has already validated map,
history, bank, alpha and source provenance; it independently enforces the replay
errors and array binding before classification. The study still cannot measure
systematic integration bias because it has no qualified exact reference. A
Stage A pass supports only continuation to the registered independent-bank
stage, while an alpha failure or fixed-window inconclusive result is a complete
stop under the frozen branch rule. The two Goal 046 barrier failures remain
outside this study and binding.

Proceed with Stage A only after the runner's real-helper smoke, provenance
receipt and independent output check pass. No further criterion, seed, window
or control adjustment is scientifically justified before execution.
