# Goal 060: refine the fixed-map certificate and complete public preparation

4 October 2026, Hobart. **Approved; implementation and qualification pending.**

Barry approved the finer certificate on the same map after Fable's review in
thread 53, message 932. This implements the concrete
[Goal 059 recovery proposal](../059-capstone-preparation/next-stage-proposal.md)
and includes Fable's requested sealing script for later review and execution.
It advances Charter Pillar 5 and the same conditional Pillar 4 declaration
procedure. The scientific design remains the
[Goal 059 registration](../059-capstone-preparation/registration-2026-10-04.md).

The endpoint is a qualified public package, including a tested but unexecuted
sealing script, handed to Fable after independent review. A further public
qualification failure instead closes this attempt with its evidence preserved.
This scope does not draw private roots or sealed histories, read a private
identity, alter the approved truth law, run confirmatory reference campaigns,
commit, push or publish.

## Single numerical amendment

Change only the continuous hazard certificate's beta partition from 80 to
**1,024 equal intervals over [-2,2]**. Use the existing construction: upper-bound
each site numerator by its two endpoint values, lower-bound each whole-map
denominator term by its endpoint minimum, then take the maximum ratio over
intervals and sites. Retain the existing factor (1+1e-12) and outward `nextafter`
margin. Keep the domain **x<=5**, degree-48 compression, h [1,10], mu
[.0005,.006]/day and detection SD [0,.4]. The fixed partition is not increased
adaptively in response to its result.

The post-Goal059 diagnostic results are already known: the 80-interval bound
was 5.350148709; 1,024 intervals gave 4.928543928. Independent continuous-beta
maximization gave 4.894118952. Other examined counts and their outcomes are
disclosed in the recovery proposal. This is an approved amendment informed by
a deterministic public-map result. It is not an entirely unseen registration.
No observation, fit, public bank or confirmatory reference from this map was
available when the amendment was chosen.

Goal 059 remains a closed negative qualification. Its original registration,
source archive, failed public-input metadata, map audit, receipts and development
preview disclosure remain unchanged. The limit is an operational domain guard;
failure of its sufficient enclosure did not demonstrate an inaccurate
likelihood. The analytic series-truncation bound is distinct from finite-bank,
floating-point, optimizer and statistical error, none of which this amendment
alone establishes.

## Same map and unchanged random addresses

Retain candidate 0, public root 2026100403, namespace 59, map seed
2286118029579671682 and sampling seed 12049465925351981407. Copy the original
map/design and exposure artifacts byte-for-byte into a separate recovery output;
reconstruct them only to verify identity. Do not invoke a map-search loop.

- Map/design NPZ SHA-256:
  `f5c590d1b600c74a686a77215488844e78e19e30fdc59fe34ab44f39acebdfc2`.
- Exposure NPZ SHA-256:
  `b74004fc9ecf03499cfdc9ecca4919b0e17987eba405709f4e3f95f9bc9c0831`.
- Original independent map audit SHA-256:
  `06ad70058ac680c5c3d8fc2d282307cf3643033e9104cf6cc00b07c58d1feb7a`.
- Original source-manifest SHA-256:
  `e63af340a6c2180914db6c779e4b3316ef9db99e3f27b169156ef6168e289867`.

The recovery output preserves the original negative `public_inputs.json` under
a separate name and writes a new metadata/qualification receipt with the
1,024-interval certificate, original file bindings and this amendment. Original
accepted-candidate, seed-ledger, failed-attempt, map and exposure files are copied
unchanged. Downstream input schema, canonical site order and all 160 physical
sites remain identical. A failed recovery certificate stops this attempt.

Preserve Goal 059 public bank and eight-fixture addresses exactly: root
2026100403, namespace 59, bank domain 3 and fixture domain 4. Preserve the
confirmatory rule at root 2026100404, namespace 59, screening domain 5 and
effect domain 6, including all node/stage/reference indices. Its 765 nodes,
99 screen references/node, 999 effect references/node and complete four-case
union are unchanged. A new receipt binds this same rule to the amended source
and runtime before any public bank or fixture draw.

## Qualification and public execution

Before registered bank/history generation, freeze the amended source, original
inputs, registration, independent auditor, sealing script and locked runtime.
Use the same Python 3.14.5 / NumPy 2.5.1 / SciPy 1.18.0 / PCG64 Linux runtime.
Mechanical tests use root 987654321 exclusively. Independently verify interval
coverage and endpoints, the numerator and positive denominator bounds, the
outward margin and a deliberately failing mechanical example. Reproduce the
certificate and original-map identity on the locked target.

Then execute the unchanged K=131,072 bank, eight fixed public fixtures,
four-model fits, three profiles, 1,350-point lattice, both K=65,536 half-bank
comparisons, training/holdout isolation and every original numerical/stability
gate. Persist main fits before diagnostics. Independently replay public
generation, score all stored main/profile/lattice points using the direct bank,
and reconstruct all predicates and coarse-grid arithmetic. No gate, reference
count, seed, sample, optimizer or bank size may change after an outcome.

Use a new isolated directory on deep-server under `/data/codex/scratch/`, with
at most 32 bank workers, 16 fitting workers, one numerical-library thread per
process, 64 GiB aggregate RSS and four hours for public construction plus audit.
Target qualification has a separate 30-minute bound. Preserve partial evidence
on numerical or resource failure. Named Nectar workflow/current-state reads
and target setup/verification are authorized; sibling repositories remain
unmodified. No registered random draw is repeated or replaced.

## Sealing script for Fable

Include a single explicit `seal` command that Fable can inspect and run only
after public readiness. It must verify the public readiness receipt, map,
qualified bank/audit bindings, source and runtime before obtaining private
entropy. Its default/help/preflight path must not draw a private root. Refuse
an existing output directory and require an explicit sealing subcommand.

The sealed generator draws four independent histories from the approved public
law with no forced composition or replacement. It uses the existing exact and
B100-A full correlated-spread generators; all 160 sites are generated. The only
public observations are the 120 training sites, with neutral case identifiers.
Private roots, stage seeds, realised truth, fields, latent quantities and 40-site
holdout observations must not enter the analyst package, filenames, logs,
exception messages or temporary plaintext files.

Obtain private entropy once from the operating system. Separately address each
case's truth-selection stream and its six generator streams using
SeedSequence/PCG64. Freeze this private-stream algorithm in the source; its actual
entropy and derived addresses belong only in the encrypted evaluator. Build
truth and holdout tar archives entirely in memory with separate 32-byte salts;
pipe each to `age -r` using the public recipient recorded in
[key custody](../../advisor/capstone-key-custody.md). Emit only the encrypted
archives, plaintext training package and neutral receipts. Receipts commit the
salted plaintext and ciphertext hashes; stdout contains only filenames, sizes
and hashes. Capture external-tool errors and prevent secret-bearing traceback,
warning or subprocess output. A failed sealing attempt must be preserved as a
generic failure, with no automatic new root or history replacement.

The frozen implementation obtains 96 bytes once: a 32-byte root and two
independent 32-byte salts. Interpret the root as a little-endian integer and
derive each seed as the first uint64 from `SeedSequence([root,60,case,stage])`,
with cases 0..3 and stages 0=truth, 1=spread, 2=prey loss, 3=predator visits,
4=site detection, 5=prey visits, 6=background field. Record every addressed
generator stream even when the exact branch does not use its field stream.
Pad each plaintext tar archive to a fixed, frozen size before encryption so
ciphertext length does not disclose the background branches or holdout counts.
The source documents those sizes and rejects overflow. These are implementation
safeguards, established before any private generation.

Test the law, random addressing, all split boundaries, salting, commitments,
encryption/decryption, overwrite refusal and error paths using public mechanical
fixtures and sacrificial test keys only. Do not execute the real sealing command
or use Barry's private identity. Fable retains the explicit final leak-review
and execution role; preparing/testing the script does not exercise that role.

## Acceptance and interpretation

Public readiness requires the amended certificate, all original public gates
and independent review to pass. Package hashes and a concise execution command
then allow Fable to review and run sealing. Any negative/incomplete gate keeps
`public_ready=false`. A pass establishes operational qualification on this map
and public panel; it does not establish likelihood convergence, effect recovery,
power, coverage, stress-case validity or four-case family-wise error control.
