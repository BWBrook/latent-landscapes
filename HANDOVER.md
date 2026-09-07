# Latent Landscapes: current handover

8 September 2026 (Hobart).

Goal 045 / Arc 2C is scientifically complete after numerical acceptance and
independent final review. The accepted integration bank has 65536 draws. No
remote campaign is running and no further doubling is authorized. The completion
heartbeat is paused as part of closeout.

## Scientific result

Across the six frozen synthetic conditions, estimating predator spread speed
produced no detected systematic deterioration in prey-effect recovery relative
to supplying its true value. All 30 paired 95% bootstrap intervals include zero;
this is not an equivalence claim. Both analyses remain weak in the threefold
cases and the slow fivefold case. Usual-speed fivefold effect coverage is 91.6%
in both analyses, despite informative accuracy, width and exclusion.

Rho supports are now numerically accepted on the discrete G201 grid. Coverage
is 96.4% at usual speed and 92.4% at half speed. All are connected and avoid
boundaries. Truth-specific calibration, known detection/background/resistance,
one landscape and fixed observation design remain substantive limits.

Start with [the synthesis](docs/goals/045-spread-prey-oracle-bridge/synthesis.md),
then [Goal 045](docs/goals/045-spread-prey-oracle-bridge/Goal.md) and the
[numerical decision](docs/goals/045-spread-prey-oracle-bridge/numerical-decision.md)
if the execution history is relevant. The [independent review](docs/goals/045-spread-prey-oracle-bridge/final-review.md)
records the acceptance verdict. README and the adaptive roadmap identify
the broader scientific boundary. Earlier handovers remain in Git history;
they describe superseded operational states.

## Evidence and source

- Frozen campaign source: `e8c08f10f7b67118a85ee37770d8ee48ee2c213a`.
- Accepted profiles: `artifacts/goal045_execution/reference65536/output/`;
  131072 numerical reference: `artifacts/goal045_execution/reference131072/output/`.
- Remote roots on `deep-server-ts`:
  `/data/codex/scratch/goal045-full-bank-reference64-20260906-e8c08f1/` and
  `/data/codex/scratch/goal045-full-bank-reference128-20260907-e8c08f1/`.
- The last reference finished successfully at 2026-09-07 16:57 UTC, taking
  14.565 campaign hours plus approximately 13 minutes to extend the bank.
- Both runs contain 250 calibration and 250 evaluation histories per case.
  Their original `timing`/nonproduction receipts are retained. The explicit
  bank amendment accepts the completed 65536 reference as scientific evidence;
  current source changes only the bank-size default.
- Durable tables, figures, numerical comparisons and provenance are under
  `docs/goals/045-spread-prey-oracle-bridge/`; banks/raw arrays remain outside Git.
- Active code: `arc2c_{design,likelihood,campaign,synthesis}.py`, with run,
  numerical-check and synthesis entry points. The path already reuses the
  accepted Arc 2B likelihood kernel and needs no additional framework.

## Closeout boundary

The final independent audit passed without a material repair. Exact reviewed
paths are published to main under Goal 045's authority; the completion check is
paused. The focused 24-test suite, scoped formatting/Ruff/strict mypy, build,
raw-profile checksum checks and figure inspection passed. Do not start another
goal or remote run.

Later programme work needs an explicit bounded scientific decision. Paper 1
remains synthetic-only; no unknown detection/background, new landscape,
observation-design change, real data or sibling-repository work is authorized.
Preserve original failed numerical comparisons; they are part of the methods
record, not stale files to erase. The earlier primary-only closeout proposal
was never approved and is superseded by completion of the original criteria.
