"""Verify pathwise early decisions for a capped plus-one rank test.

This verifies computation, not fitted-nuisance bootstrap validity. No model
fits, biological simulation, or historical campaign changes occur here.
"""
from fractions import Fraction
from itertools import product
import hashlib
import json
from pathlib import Path

from scipy.stats import binom


def stopped(bits, alpha):
    cap = len(bits)
    exceedances = 0
    for used, bit in enumerate(bits, 1):
        exceedances += bit
        lower = Fraction(1 + exceedances, cap + 1)
        upper = Fraction(1 + exceedances + cap - used, cap + 1)
        if lower > alpha:
            return False, used, lower, upper
        if upper <= alpha:
            return True, used, lower, upper
    raise AssertionError("a complete valid sequence must resolve")


def expected_work(q, cap=999, alpha=Fraction(1, 20)):
    """Sum exact binomial continuation probabilities, without random draws."""
    largest_rejecting_count = (alpha * (cap + 1)).numerator // (alpha * (cap + 1)).denominator - 1
    terms = []
    for used in range(cap):
        low = max(0, largest_rejecting_count - cap + used + 1)
        high = min(used, largest_rejecting_count)
        terms.append(0.0 if high < low else float(binom.cdf(high, used, q) - binom.cdf(low - 1, used, q)))
    return float(sum(terms))


checked = 0
for cap in range(1, 14):
    for alpha in (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)):
        for bits in product((0, 1), repeat=cap):
            fixed_p = Fraction(1 + sum(bits), cap + 1)
            decision, used, low, high = stopped(bits, alpha)
            assert decision == (fixed_p <= alpha)
            assert low <= fixed_p <= high
            checked += 1

# Independent finite-cap computation for a continuous simple null: its
# conditional exceedance probability is Uniform(0,1), so S_t is uniform 0..t.
ideal_null_expected = sum(
    max(0, min(t, 49) - max(0, t - 949) + 1) / (t + 1)
    for t in range(999)
)
receipt = {
    "meaning": "exact binary equivalence to fixed B=999 rank decision; not an exact plug-in bootstrap inference",
    "rank_convention": "p=(1+count(T_star>=T_observed))/(B+1); reject p<=.05",
    "cap": 999,
    "nonrejection_boundary": "50 exceedances",
    "rejection_boundary": "950 non-exceedances",
    "exhaustive_small_cap_sequences_checked": checked,
    "fixed_cap_test": {
        "all_exceedances": list(stopped([1] * 999, Fraction(1, 20))[:2]),
        "no_exceedances": list(stopped([0] * 999, Fraction(1, 20))[:2]),
    },
    "expected_replicates_given_exceedance_probability": {
        str(q): expected_work(q) for q in (0., .01, .025, .05, .1, .2, .5, .9, 1.)
    },
    "ideal_continuous_simple_null_expected_replicates": ideal_null_expected,
    "limitations": [
        "Uniform-q result does not apply automatically to a fitted-nuisance bootstrap.",
        "Early stopping gives a p-value interval and decision, not the uncomputed numerical fixed-cap p-value.",
        "Failed fits are not non-exceedances; repair or mark an unresolved comparator.",
        "Actual wall time also depends on statistic-dependent refit cost, batching and failures."
    ],
    "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
target = Path(__file__).with_suffix('.json')
target.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
