# Goal 046: numerical qualification and production compute

Initial approval, 8 September 2026: up to 24 elapsed hours on `deep-server-ts`, using
at most nine map processes with four threads each, native numerical-library
thread counts fixed at one, and a 96 GiB aggregate memory ceiling. This is a
new Goal 046 resource authorization. Goal 045's exceptional run permission was
specific to that completed goal.

## Evidence for the estimate

The Linux K2048 G201/H181 pilot takes 398.45 seconds with four integration
workers: 156.01 seconds generating the bank, 224.18 integrating it and 18.17
evaluating four paired histories. The bank is byte-identical to the Mac run;
MLEs agree exactly and all numeric profile differences are below 1.37e-12.
Unit and campaign tests also verify serial/parallel byte equality on Linux.
The completed Linux serial full-grid run takes 807.62 seconds for integration
and 988.05 overall; every saved profile array is exactly equal to the parallel
run. The measured integration speedup is 3.60-fold.

Linear planning extrapolation from that measurement gives about 3.4 hours of
bank generation plus integration per map at K65536, and 6.8 at K131072.
Conservatively retaining the observed two-history throughput adds about
0.6 hours per 500-history campaign. Nine maps can run concurrently on the
otherwise idle 64-logical-CPU, 128 GiB host. Smaller accepted banks would reduce
that cost. Allowing numerical pilots, refinement, synthesis and verification,
12--18 elapsed hours is a planning range, not a runtime guarantee. The
24-hour ceiling provides a bounded contingency; it is not permission to relax
a failing numerical criterion.

## Execution sequence

1. Retain the K128/256 and K2048/4096 failures. Start the next qualification
   trial at K16384/32768 on the three sacrificial pilot maps, with the first
   two calibration and evaluation histories, G201/H181 and both designs.
   Apply the unchanged bank and separate half-grid criteria. If necessary,
   increase the global candidate to K32768/65536, then K65536/131072, while
   retaining all failed evidence. Do not exceed the resource ceiling.
2. Freeze one qualified bank size for every map, the exact generator/source
   snapshot and the production settings before generating production recovery
   outcomes. Preserve the nine declared production map seeds and 250+250
   histories, with rank 239. Enable the production runner only against that
   freeze; the present pilot runner rejects reserved production map seeds.
3. Run each production map at the selected and doubled bank on identical
   histories. Apply the full-ensemble checker, including support topology,
   endpoints, cutoff and coverage/exclusion stability and the five paired
   sampling contrasts. Complete separate half-grid checks and any required
   extension to the reported effect LR range. A passing pilot does not waive
   the production-map numerical checks.
4. If production qualification requires a larger bank, preserve the failed
   comparison and reassess all maps at the same global setting, within the
   K65536 selected / K131072 reference ceiling and the elapsed-time budget.
   If those limits cannot resolve the numerical issue, return its evidence
   and a concrete decision to Barry. Do not reselect maps or adjust tolerances.
5. Return verified artifacts, synthesize the equally weighted map results and
   conditional fixed-map bootstrap intervals, inspect the figures, obtain one
   independent scientific review, and complete the approved research tranche.
   A null sampling benefit or weak biological recovery remains a valid result.

Runs use a fresh hashed source snapshot under `/data/codex/scratch/goal046-*`.
Keep local source authoritative, preserve input/output hashes and exit markers,
and return compact evidence to this repository. Monitor progress and failures
through completion; pause further launches if another workload needs the
reserved headroom. No cloud resize, system service, sibling-project change,
Git commit, push or external publication is included in this authorization.

## Authorized final continuation

Barry authorized deadline extension at agent discretion on 10 September
(Hobart). All predecessor calculations completed under the initial deadline.
The final uniform K65536/131072 comparison uses a fresh 30-hour window from
2026-09-09 23:00 UTC to 2026-09-11 05:00 UTC, with the same compute and numerical
limits. See [the final bank amendment](bank-escalation-k65536.md) for observed
runtime estimates and [compute-authority.json](compute-authority.json) for the
current deadline. Original evidence and the initial authority record are kept.
The completion heartbeat uses a four-hour cadence following Barry's preference.
