# Goal 056 execution record

3 October 2026 (Hobart). **Complete: numerical feasibility, independent replay and descriptive synthesis passed.**

Barry's approval and the study boundary are recorded in the
[registration](registration-2026-10-03.md). This is the open feasibility study,
with no sealed histories, private keys or large calibration references.

The original qualified run root is
`deep-server-ts:/data/codex/scratch/goal056-observed-nuisance-20261003-v2`.
The original path without `-v2` preserves the first preflight.
The host was idle at preflight, with 125,761 MiB available memory and 4.3 TiB
free under `/data`. The existing verified Goal 045 bank is read in place.
No earlier experiment or run directory is modified.

The first [source manifest](../../../artifacts/goal056_execution/preflight-v1/source-manifest.json)
binds 98 source, test and normative-input files. Its SHA-256 is
`1e8f15a1be5ccb06d4dbdb2aa1a46e6fa7d4ba2e8687d8d75150ef418f004b43`.
All 97 Goal 055 source bindings were independently rehashed unchanged before
this freeze. Navigation documents can advance without altering those bindings.

Local verification: **173 focused tests passed**, including frozen adjusted
likelihood comparisons; scoped Ruff and mypy checks passed. An independent
native methodological reviewer checked the generator, continuous hazard bound,
rank proof, observation isolation, numerical failure handling and the revised
runner. The review accepted code-level readiness, conditional on the Linux
full-bank qualification.

The first Linux preflight passed 172 tests but found one over-strict exact-equality
assertion in the holdout-isolation test: training sums differed by 1.4e-14.
This is well below the unchanged registered 1e-8 numerical tolerance. The test
was repaired to reconstruct observations before preparing cached emissions
and compare at 1e-12 absolute tolerance. The failed preflight source and logs
are preserved under `artifacts/goal056_execution/preflight-v1/` and the original
remote root. No qualification or panel history was generated in that attempt.
The v2 [manifest](../../../artifacts/goal056_execution/source-manifest.json),
SHA-256 `174d7849837e05224e7b04e6d7a14bd2c78fab01b97998eed50d6434d69844ed`,
differs only in that test file. The scientific source is identical. Linux now
passes all **173 tests**, Ruff and mypy across all eleven scoped source/test
files. Full-bank qualification ran from this frozen snapshot.

Qualification uses four fixed mechanical count patterns, 17 parameter points
covering the domain edges and an interior point, and repeated four-model fits.
It must pass the registered 1e-8 log-likelihood agreement and repeatability
checks before any panel history is generated. Its runtime ceiling is 30 min.

The first panel has 16 workers, one BLAS thread each, a four-hour wall ceiling
and a conservative 48 GiB summed process-group RSS ceiling. The wrapper samples
RSS each second, retains a launch/exit receipt and terminates the whole process
group if either ceiling is exceeded. Shared resident pages may be counted more
than once. The wrapper refuses a second attempt under the same phase name.
Numerical failures remain outputs, never a reason to redraw the panel.

Full-bank qualification exited zero at **07:34:34 UTC** after **132.55 receipt
seconds**, with peak summed RSS **589,434,880 bytes**. All 17 parameter points
passed; maximum site/training/holdout absolute log-score differences were
9.17e-13 / 2.28e-12 / 9.10e-13. All 32 mechanical model fits converged and
repeat differences were exactly zero. The continuous-beta certificate gives
x<=4.17763332<5. Bank load/compression took 30.54 s; scalar joint and pre-only
scores averaged 2.448 ms and 0.856 ms on the target host.

The [qualification verification](../../../artifacts/goal056_execution/qualification-verification.json)
reconciles exit status, all source bindings, compressed-bank identity and raw
comparison values. Qualification JSON SHA-256:
`d35e85d92e89adf76a68dcffd6c403483bbfb0ed4eb886691d43b3d45d2a7b2d`.

The single panel was launched at **07:37:59 UTC**, wrapper PID **78650**, after
that verification. It exited 1 at **07:40:28 UTC**, after **149.150845 s**, with
peak summed RSS **5,761,949,696 bytes**. All sixteen histories and all 64
converged main fits were saved; twelve cells completed all diagnostics. Four
cells (1, 9, 11, 15) failed profile-seed validation because decoding log(10)
gave 10.000000000000002. No resource ceiling was reached. The
[recovery amendment](profile-recovery-amendment.md) records the bounded repair;
the original partial panel and its failure receipt remain untouched.

An AST comparison confirms that only the profile seed helper changes in the
scientific module. The recovery preserves all sixteen main files and twelve
complete cell files byte-for-byte, and completes only the missing diagnostics,
fixed-fit heldout scores and the not-yet-run coarse lattice. The exact
generation timer was not flushed; 1.674007159 s from remote file timestamps is
retained explicitly as a planning proxy. Final measured costs include the
failed phase and the recovery phase, including repeated incomplete work.


## Completed recovery and independent audit

Recovery used a new root,
`deep-server-ts:/data/codex/scratch/goal056-observed-nuisance-20261003-profile-recovery`,
with four workers, one BLAS thread each, 48 GiB RSS and a 14,250-second ceiling
within the remaining original allowance. The source archive contains the 98
current core bindings and two additional bindings for the recovery script and
amendment. Its manifest separately binds the AST check, source patch, wrapper,
original resource context, original source manifest and two auxiliary build/test
files. Recovery-manifest SHA-256:
`19ec94e5cd934b5c21a5922ffd7f5de9873d8654081e0467542acd1cfcc93a3f`.
Only the profile helper and its regression test differ among the 98 original
bindings. The original qualification applies to the unchanged likelihood,
generator and main-fitting code; this is an explicit amended diagnostic run,
not an assertion that every output came from one unchanged source snapshot.

An initial recovery environment setup omitted the build-required README. The
setup failed before tests or scientific execution; the log is retained as
`environment-missing-readme.log`. Adding the exact original-v2 README and frozen
adjusted-likelihood test as auxiliary files resolved packaging. Linux then
passed **174 tests**, scoped Ruff and mypy in eleven files. No numerical source
or observation was changed by this packaging correction.

Recovery started **08:03:26 UTC** and exited zero **08:05:14 UTC**, after
**108.306913 s**, with peak summed RSS **1,420,005,376 bytes**. It completed cells
1, 9, 11 and 15 and the first coarse-grid audit. All 40 completed-file hashes
were verified. The 31 preserved observation/manifest/main/completed-cell files
are byte-identical to the original attempt, and the original failure receipt
is copied under `original-failed.json`. All 64 numerical rows passed; 7,088
profile nodes converged. Panel completed-receipt SHA-256:
`c5e6167b0402d6ca6bd29204db3ff62f6397617ab4976f72890af936c4002171`.

The independent auditor directly traversed the original empirical bank and
reimplemented shared-Beta emissions. It replayed all 64 training/held-out fit
points and both effect statistics. The first audit took **17.611460 s** and
exited 1 only because its expected numerical rows omitted the recovery's
`profile_source_id` metadata; all direct scores and source/preservation checks
passed. The auditor added that field, demonstrated that a wrong identity is
detected, and reran once to `independent-audit-v2`. The original audit script,
outputs and failed receipt remain preserved.

The second audit exited zero **08:10:49 UTC**, after **18.414194 s**, with peak
child RSS **535,716 KiB**. Maximum differences are 6.82e-13 training nats,
1.14e-13 total held-out conditional-prey nats, 2.66e-14 site nats and 1.36e-12
for the effect statistic. Predator marginal and category-mass errors are zero.
The independent grid/profile reconstruction and every provenance check passed.
Final independent-audit SHA-256:
`90ab4ef25b01d4c369551878e9abd00c5291e76d719f97ba07d9f38a6ab71445`.
The auditor source SHA is
`50aaaccfe16aa37e09bfb98ce5aa426c81cf38ea015da467469891d680a2193f`.

The descriptive synthesis produces 64 model rows, 16 pre-only rows, 48 profile
rows and two PNG/PDF figure pairs. Source and output hashes are recorded in
`artifacts/goal056_execution/synthesis/manifest.json`. A layout-only correction
moved figure legends outside the panels; earlier figures/manifest remain under
`figure-layout-before/`. Tables and the report were unchanged. The report's
`scientific_status` retains the immutable runner's historical
`panel_recovered_pending_scientific_audit` value; the passing v2 audit and final
completion check supply the subsequent audit state. Never rewrite the runner
receipt to make that historical field appear current.

## Cost accounting and closeout

| Recorded phase | Wall seconds | Outcome |
| --- | ---: | --- |
| Full-bank qualification | 132.548342 | Passed |
| Original sixteen-worker panel | 149.150845 | Saved all main fits; profile-seed failure |
| Four-worker diagnostic recovery and lattice | 108.306913 | Passed |
| Independent direct replay, first audit | 17.611460 | Scores pass; audit-schema mismatch |
| Independent direct replay, repaired audit | 18.414194 | All checks pass |

The panel phases total **257.457758 s**. Qualification plus panel phases totals
390.006100 s; including both independent audits gives 426.031754 s of recorded
execution-phase wall time. This is not elapsed development time or CPU time.
Environment setup, local/Linux tests, transfers and plotting were not included
in this sum. Bank load/compression is already inside qualification and must not
be counted twice. The 1.674007159-second generation proxy is inside the original
panel time and must not be added to the phase total.

The [synthesis](synthesis.md), [independent review](final-review.md),
[figures](figure-captions.md) and [calibration proposal](calibration-proposal.md)
complete the registered deliverables. The final
[completion check](../../../artifacts/goal056_execution/completed-check.json)
records local output rehashes, independent-audit status and all 97 preserved
Goal 055 bindings. No scientific process remains active, and no completed
phase should be restarted. Large reference calibration, sealed generation and
publication remain separate decisions. No private key, sealed draw, commit,
push or publication was produced.


Astra posted the verified closeout and next proposal to Correspondence thread
53 as message **852**, replying to 846, at **18:22 AEST on 3 October**. Fresh
catch-up through 852 found no intervening reply; the global retrieval checkpoint
and actual acknowledgement are both 852. Fable is next to critique, then Barry
makes the next scientific decision. The previously requested user-run key and
staged-release instructions remain for Fable; no key material was generated.
