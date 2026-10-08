# Goal 056 feasibility figures

## Figure 1. Training likelihood profiles for the open 16-history fixture

Each panel is one openly labelled development history, with the generating
effect shown by the dashed vertical line. Curves show the constant-background
and adjusted-background free-`h` training profiles, centred on each profile's
own maximum. The profiles are numerical support diagnostics from the fixed
181-point grid; they are not confidence intervals, calibrated thresholds or
operating characteristics. The panel is one history per registered cell and
does not support recovery, power or general identifiability claims.

For the adjusted-background profile, `SElogh` is retained as the local scale
`1/sqrt(-profile ell''(log h))` when the three-point curvature is negative.
It is an uncalibrated curvature diagnostic for a sitewise composite
likelihood under spatial spread, not a verified sampling standard error,
Godambe estimate or confidence interval.

## Figure 2. Fitted parameters and generating values

Points show fitted values from the constant free-`h` and adjusted free-`h`
models for the sixteen openly labelled development histories. Dashed lines
show the generating values for `h`, `beta`, mean hazard `mu` and shared-site
detection SD. These are descriptive estimates and errors from one open fixture;
they are not confidence intervals, calibration results or evidence of
operating rates. The future 3,645-node calibration grid was not run here.

Source rows are retained in `all64_model_rows.csv`, `preonly16.csv` and
`profile_diagnostics.csv`; input and output SHA-256 values are recorded in
the report manifest. The open fixture is explicitly one history per cell, not
a replicate panel for calibration or rate estimation.

The `SElogh` values shown in the report retain the same local-curvature
meaning described for Figure 1 and are not inferential standard errors or
confidence intervals.
