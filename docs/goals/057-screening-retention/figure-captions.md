# Goal 057 figures

4 October 2026. Accepted figures are in `artifacts/goal057_execution/synthesis-v3`.
Earlier figure attempts are retained for provenance and should not be used.

## Screening retention

[PDF](../../../artifacts/goal057_execution/synthesis-v3/retention_and_union_ecdf.pdf)
and [PNG](../../../artifacts/goal057_execution/synthesis-v3/retention_and_union_ecdf.png).
Left: numbers of nuisance nodes retained by the registered q>.01 screen for
the sixteen fixed Goal 056 fixtures. The full grid contains 3,645 nodes and
each node has 99 public pre-only references. Right: empirical distribution of
the 1,820 unions of four distinct fixture sets, ranging from 577 to 1,901 nodes
with median 1,266. These overlapping combinations describe this panel and are
not independent calibration replicates. All known true nodes are retained;
this is not an estimate of coverage.

## Nuisance mean-error diagnostic

[PDF](../../../artifacts/goal057_execution/synthesis-v3/diagnostic_mean_errors.pdf)
and [PNG](../../../artifacts/goal057_execution/synthesis-v3/diagnostic_mean_errors.png).
Mean log(mu-hat/mu), beta-hat-beta and detection-SD error for 99 reused pre-only
references at each of eight registered nuisance nodes. Error bars are
approximate pointwise 95% Monte Carlo intervals for mean errors, using t(98)
quantiles and the empirical within-node variance. They are not intervals for
ecological parameters. All 792 returned estimates are finite and converged;
none is excluded. Node identities and nuisance values are in the synthesis
table. Zero-SD boundary nodes are labelled explicitly. The positive SD means
at those nodes coexist with approximately half the estimates at zero.

## Retained nodes on the global likelihood surface

[Sixteen-page PDF](../../../artifacts/goal057_execution/synthesis-v3/global_surfaces.pdf),
with [case 0](../../../artifacts/goal057_execution/synthesis-v3/global_surface_case_00.png)
and [case 7](../../../artifacts/goal057_execution/synthesis-v3/global_surface_case_07.png)
PNG previews. Each page shows one fixture and five detection-SD slices.
Colours show R=2(max_grid ell_pre-ell_pre), using a common linear scale across
all sixteen surfaces. The mesh preserves the irregular mu spacing. Open
circles mark the original retained grid nodes, the red star the known true
point, and the dashed contour R=10. Contours interpolate grid values for
display only. The R=10 marker is descriptive, with no chi-square, p-value or
confidence-region interpretation. It was not used to modify the retained
sets. Retention well outside that marker motivates investigation of another
screening statistic but does not by itself establish identifiability or the
compression achievable by a valid alternative.
