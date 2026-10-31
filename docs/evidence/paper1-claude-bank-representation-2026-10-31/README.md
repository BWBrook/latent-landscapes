# Claude check: arrival-bank representation at large hazard (31 October 2026)

Advisory diagnostic for Correspondence thread 87, responding to the
high-effect underflow reported in `docs/paper1-profile-engine-development-2026-10-18.md`.
Not registered evidence.

`binned_laplace_check.py` takes 16 randomly chosen sites (seed 0) from the
qualified Goal 060 arrival bank (`artifacts/goal060_execution/audit-repair/arrival_bank/arrivals.npy`,
131,072 x 160). For each 10-day arrival category it compares, over x in [0.01, 200]:

- the bank's own Monte Carlo precision of log E[exp(-x u)], from a random
  half-against-half split (reported as half the absolute difference);
- the error of a log-domain binned representation, in which each of 64 or 256
  equal bins carries its empirical mass and an exactly integrated uniform
  density, log[(exp(-x a) - exp(-x b)) / (x (b - a))], relative to the full bank.

Here u is the arrival position within its 10-day category (0 to 1), and x is
the excess cumulative hazard over that interval. Run from the repository root
with `.venv/bin/python`. The output is in `binned_laplace_check.txt`.
