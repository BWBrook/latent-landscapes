# Independent methods review: Goal 060 certificate recovery

4 October 2026, Hobart. **The amendment is scientifically defensible but
readiness remains conditional on implementation, frozen-target and public-panel
qualification.** Goal 060 changes one sufficient numerical certificate after a
known false-negative enclosure. It does not change the map, estimand,
observation process, numerical domain or inferential rule, and it must not be
described as overturning Goal 059's valid negative result.

## Target, estimand and scope of inference

The immediate target is operational: certify that every exact-family fitted
hazard over `beta in [-2,2]`, `mu <= .006` and `h <= 10` remains inside the
degree-48 compressed transform domain `x <= 5` on the already fixed map and 160
sites. Goal 060 replaces 80 equal beta intervals with 1,024 while retaining the
same numerator-upper/whole-map-denominator-lower construction and outward
rounding. The registered post-Goal059 diagnostics already show a passing bound;
this is a disclosed, outcome-informed amendment.

The eventual scientific estimand remains the casewise evidence for a
post-invasion hazard multiplier `h` under the exact-family model, conditional
on this fixed synthetic map, access-constrained sampling design, arrival bank,
numerical statistic and complete nuisance-reference procedure. The primary
prediction target remains held-out conditional prey log score on eight reserved
clusters. Neither the certificate nor a successful public qualification would
establish ecological generality, unbiased magnitude recovery, power, coverage,
stress-family validity, likelihood convergence or four-case family-wise error
control.

## Generating, observation and computational pipeline

The fixed design has 120 training and 40 held-out sites in separate five-site
clusters over four strata. Future public fixtures and sealed histories retain
the Goal 059 correlated spread, exact/B100-A background branches, persistent
site detection, shared occasion states, two visits per occasion, no false
positives or recolonization, and prey loss carried through day 0. Only training
sites enter fitting and calibration. The confirmatory screen remains 99
references at each of 765 nuisance nodes; the effect test remains 999 references
at every required retained node, with the same conservative Berger--Boos rule.

The computational order must remain:

1. copy candidate 0 map/design, seed ledger and exposure artifacts byte for
   byte into a new recovery package while retaining the original negative
   metadata;
2. independently reproduce the 1,024-interval certificate and all predecessor
   bindings under a new source/runtime freeze;
3. run the unchanged mechanical qualification;
4. only then generate the fixed `K=131,072` bank and eight public fixtures;
5. fit the four models, three profiles and 1,350-point lattice under full and
   two disjoint half banks;
6. independently replay fixtures, score every stored point with the direct
   bank and reconstruct every stability predicate; and
7. expose readiness for later sealing only if every gate passes.

No step may select a new root, candidate, domain, partition, bank, optimizer,
reference count or tolerance after observing a result. A resource interruption
leaves work pending at the same addresses. A numerical failure is preserved and
ends this recovery.

## Certificate validity and the informed amendment

For a beta interval `[l,u]`, `exp(beta A)` is monotone in beta for each fixed
cell. Therefore

`max(exp(l A_site), exp(u A_site))`

is a valid numerator upper bound, while the whole-map mean of

`min(exp(l A_cell), exp(u A_cell))`

is a positive denominator lower bound. Their ratio bounds every beta in the
interval without an optimizer. Taking the maximum over all sites and all 1,024
contiguous intervals covers the complete registered beta range. Multiplication
by `mu=.006`, the transform factor `10*(h-1)=90`, the existing `(1+1e-12)`
factor and outward `nextafter` gives the final sufficient bound.

The known map gives `x<=4.9285439278` with 1,024 intervals, a margin of
`0.0714560722` below 5. Independent continuous maximization gives
`4.8941189519`; the residual enclosure slack is expected and harmless. The
partition is fixed rather than increased until a pass. This is a materially
cleaner recovery than changing the transform domain, rerolling the map or
adding an optimizer to the production gate.

The favorable result is already known, so the amendment supplies no fresh
evidence about landscape generality. Its legitimacy rests on the scientific
criterion being the actual fixed-map domain property and on retaining every
other choice. The new registration correctly discloses this. Goal 059 must
remain closed as a valid failure of its frozen 80-interval certificate.

## What the degree-48 series bound does and does not prove

For category coordinate `u in [0,1]`, the compressed transform uses

`exp(-x) * sum_(k=0)^48 (x u)^k/k!`

for `exp(-x) exp(xu)`. Positivity gives a worst-case unscaled Taylor remainder

`B(x) = exp(x) Pr[Poisson(x) > 48]`.

This is the quantity returned by `series_remainder_bound`. At `x=5`, independent
evaluation gives `B=3.2439836051e-29`, agreeing with Fable's value. At the old
80-interval bound `x=5.3501487089`, it is `9.0126160041e-28`; at `x=10`, it is
`2.0525054910e-14`. After the leading `exp(-x)` factor, the per-unit-weight
absolute remainder is bounded by the Poisson tail itself
(`2.1857789597e-31` at x=5). The same `B(x)` is also a conservative relative
bound because `exp(xu)>=1`; a tighter pointwise relative bound is the Poisson
tail at `xu`.

These analytic statements concern truncation of the positive exponential
series only. They do not bound:

- finite arrival-bank Monte Carlo error or alpha=1 pseudo-arrival influence;
- float64 construction, summation or cancellation when survival moments are
  differenced into event probabilities;
- log-likelihood error when probabilities are very small;
- optimizer convergence, multimodality, boundary estimates or profile error;
- misspecification, calibration transport, recovery, power or coverage.

Direct empirical-versus-compressed score comparisons address the combined
implemented numerical path at tested points. They remain necessary even though
the analytic series remainder is negligible. Calling `B(x)` a bound on total
likelihood, bank or optimizer accuracy would be incorrect.

## Independent-audit design

The new auditor should contain only the Goal 060 layer: byte identity to the
original map package, preservation of the negative metadata, predecessor audit
and source/registration hashes, exact interval support, denominator positivity,
outward guard, certificate reproduction and a deterministic failing fixture.
It should not import the production recovery module.

After that layer passes, the auditor can compose the frozen Goal 059 audit
functions for structural reconstruction, bank ledger/chunks, mechanical
receipts, public fixture replay, direct main/profile/lattice scores, full/half
stability and the 765-node calibration fixture. Reusing those independently
reviewed functions avoids a divergent copy while preserving the separation
from the production likelihood, normalizer, fitter and calibration code. The
full audit must bind the new source/runtime/registration freeze, independently
reconstruct the exact root-2026100404 confirmatory address contract, require
the registered Goal 059 calibration-fixture hashes, and retain the original
map-only audit; a new pass cannot overwrite or relabel it.

## Failure modes and residual risks

Map identity and selection are the principal provenance risks. Recovery must
copy the five unchanged accepted artifacts byte for byte, preserve the original
negative `public_inputs.json`, reconstruct candidate 0 independently and refuse
any other root, attempt or seed. A receipt that merely repeats producer hashes
without comparing original and recovered bytes is insufficient.

The 1,024-interval calculation is deterministic and cheap, but cross-platform
last-bit differences are possible in exponentiation and reduction. The fixed
outward margin and Linux reproduction address this; the independent audit
should report the raw maximum, guarded maximum, winning interval and minimum
denominator rather than only a Boolean pass. A deliberately failing synthetic
map is required to show the gate can reject.

Identifiability and parameter trade-offs among `h`, `beta`, `mu` and detection
remain serious. Spatial dependence, a single map, bank approximation,
nonregular `h=1` profiles, boundary solutions and B100-A misspecification can
all affect fit stability and interpretation. The unchanged public full/half
bank, nesting, profile-core, generating-coordinate and held-out contrast gates
are necessary diagnostics, but none proves global identification or operating
characteristics. Any failed history remains a failed public qualification;
averaging cannot rescue it.

The sealing script is a separate confidentiality surface. Its help, preflight
and test paths must be demonstrably entropy-free; tests must use sacrificial
keys; and a later explicit leak review must inspect filenames, logs, exception
paths, temporary storage and subprocess capture. Passing public numerical
qualification does not qualify sealing.

During that review I exceeded the registered test-root envelope: I inspected
truth selections for integer roots 1--294 and generated 64 full in-memory test
histories on the root-987654321 mechanical map, selecting the first root for
each of the 16 exact/B100-A branch patterns. No file, bank, fit, qualification,
registered public draw, private entropy or private key was produced, and none
of those draws is admissible evidence. The exact command and aggregate output
are preserved in `artifacts/goal060_execution/development-review/`; individual
selected roots were not printed or persisted and were not replayed after the
error was identified. Further capacity review uses the registered mechanical
root and fixed-shape arithmetic only. At the worst four-B100-A composition,
the truth archive's raw arrays total at most 416,064 bytes before NPZ/TAR
overhead, versus the frozen 2,099,200-byte target; the holdout raw arrays and
identifiers total under 9 KiB versus 266,240 bytes. These margins make archive
overflow implausible without a schema change, which the source freeze forbids.

## Final pre-freeze sealing review

The final sealing path is acceptable for source freeze and public
qualification. This is a code and threat-model judgement, not evidence that
public qualification or private sealing has occurred. The reviewed module,
CLI and sealing test hashes are, respectively,
`73eeed484d20056d4dd79f0496e623f9a4ad66e8df3c3bbb3e60e8938ff07e53`,
`cd90c5393da8dafaea5877247ee8f17de9058a0248bd7c9ef8a7bff7855918f7`
and `2b9fe3f1aebc298251c08600a21f768f0da9cca71cca131f0b36cecf540b4f21`.

Before reading the private root, the sealer validates every receipt-listed
file hash, the required package inventory, the source and runtime freezes, the
recovered map, the bank file and array hashes, and the completed Goal 060
independent audit. The audit must report a passed root-2026100404 confirmatory
contract whose hash equals the separately validated contract file. The public
`age` recipient probe also precedes the private draw. These checks close the
material risks of accepting the old Goal 059 audit, an incomplete Goal 060
audit, a changed additional receipt binding or an unverified confirmatory
address contract.

Within the private section the code fails closed if core-dump or output
suppression cannot be established, obtains one 96-byte entropy value, and
splits it into a 32-byte root and two 32-byte salts. The root is interpreted
little-endian; truth addresses use namespace 60 and stage 0, while the six
history streams use their fixed stages 1--6. Four full 160-site histories are
generated before the 120 training sites are released. Truth and the 40 held-out
sites are serialized only in memory, padded to fixed archive sizes, encrypted
through `age`, and published while stdout and stderr remain suppressed. All
private-section exceptions trigger best-effort removal of the staging
directory and expose only a generic failure receipt. No plaintext is ever
written there; filenames, manifests and CLI output contain only public
identifiers, dimensions, byte counts and hashes.

The combined local sealing and recovery checks passed 25 tests, with three
Linux-only exact-replay tests skipped on macOS; Ruff and mypy passed for the
module, CLI and sealing tests. The tests include sacrificial-key round trips,
fixed ciphertext-size checks, pre-entropy failures, warning/descriptor and
`BaseException` suppression, partial-encryption failure, audit-schema rejection,
additional-binding tampering and confirmatory passed/root/hash tampering. No
production seal, registered private draw or Barry identity was used.

Residual confidentiality limits are explicit. Python objects are not
zeroized, the operating system may retain process memory, and runtime or power
side channels are outside this accidental-disclosure threat model. The real
recipient probe establishes only that the public recipient is syntactically
usable; it does not establish private-key custody or recoverability. Exact map
replay and the actual source/runtime/package bindings remain Linux gates, and
the sealing command must remain unexecuted until `public-ready.json` is
positive and the later named reviewer accepts the frozen package.

## Recommendation

Proceed to frozen mechanical and map-only qualification. The producer,
independent auditor, sealer and tests now agree on the registered receipt
schemas and predecessor bindings. A map-only pass authorizes the unchanged
public bank/panel qualification, not sealed generation. Public readiness still
requires the complete direct-score/stability audit, and the qualified frozen
package still requires the separate named sealing review before any private
draw.

Independent scientific review materially changes confidence here because the
amendment follows a known certificate outcome and because an apparently tiny
numerical change controls access to all later random generation. Once byte
identity, fixed partition, rejection fixture, source freeze and complete public
gates pass, no additional methodological change is justified within Goal 060.
A second independent review would materially increase confidence in the
eventual scientific qualification and confidentiality handoff, but would not
change the present decision to freeze and run the registered public gates.
