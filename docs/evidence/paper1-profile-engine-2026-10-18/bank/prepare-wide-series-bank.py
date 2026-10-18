"""Prepare a separately identified high-order bank for the h<=30 prototype."""
from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np

from latent_landscapes import preinvasion_likelihood as likelihood

root = Path(__file__).resolve().parents[2]
source = root / "artifacts/goal060_execution/audit-repair/arrival_bank/arrivals.npy"
old_path = root / "artifacts/goal060_execution/audit-repair/mechanical/compressed-bank.npz"
destination = Path(__file__).with_name("arrival-bank-order192.npz")
receipt_path = destination.with_suffix(".json")
if destination.exists():
    raise FileExistsError(destination)
if receipt_path.exists():
    raise FileExistsError(receipt_path)
order, max_x = 192, 40.0
# Positive-term exponential-series tail, bounded without subtractive cancellation.
first_omitted = math.exp((order + 1) * math.log(max_x) - math.lgamma(order + 2))
geometric_bound = first_omitted / (1.0 - max_x / (order + 2))
assert geometric_bound < 1e-12
with np.load(old_path, allow_pickle=False) as old:
    ids = tuple(str(x) for x in old["site_ids"])
    old_moments = old["power_moments"].copy()
    old_counts = old["category_counts"].copy()
    old_mass = old["category_mass"].copy()
    old_checksum = str(old["bank_checksum"])
started = time.perf_counter()
bank = likelihood.compress_bank(np.load(source, mmap_mode="r"), ids, series_order=order)
elapsed = time.perf_counter() - started
assert bank.bank_checksum == old_checksum
assert np.array_equal(bank.category_counts, old_counts)
assert np.array_equal(bank.category_mass, old_mass)

# The reduction and power kernels may choose a different SIMD path when the
# same site column sits in a differently aligned full matrix.  The old 49
# moments are therefore checked quantitatively, rather than requiring a false
# bitwise invariant.  The raw array identity, counts and masses remain exact.
recomputed_old = bank.power_moments[:, :, : old_moments.shape[-1]]
difference = np.abs(recomputed_old - old_moments)
relative = difference / np.maximum(np.abs(old_moments), np.finfo(np.float64).tiny)
ulp = np.abs(
    recomputed_old.view(np.uint64).astype(object) - old_moments.view(np.uint64).astype(object)
)
old_moment_check = {
    "element_count": int(old_moments.size),
    "bitwise_equal": bool(np.array_equal(recomputed_old, old_moments)),
    "unequal_count": int(np.count_nonzero(recomputed_old != old_moments)),
    "affected_site_count": len(np.unique(np.argwhere(recomputed_old != old_moments)[:, 0])),
    "max_abs_difference": float(np.max(difference)),
    "max_relative_difference": float(np.max(relative)),
    "max_ulp_difference": int(np.max(ulp)),
}
if (
    old_moment_check["max_abs_difference"] > 1e-15
    or old_moment_check["max_relative_difference"] > 5e-15
    or old_moment_check["max_ulp_difference"] > 2
):
    raise AssertionError(f"material lower-order moment difference: {old_moment_check}")

np.savez_compressed(
    destination,
    site_ids=np.asarray(bank.site_ids),
    bank_size=bank.bank_size,
    category_counts=bank.category_counts,
    category_mass=bank.category_mass,
    power_moments=bank.power_moments,
    bank_checksum=bank.bank_checksum,
    series_order=order,
    max_x=max_x,
)

with np.load(destination, allow_pickle=False) as saved:
    assert tuple(str(value) for value in saved["site_ids"]) == bank.site_ids
    assert int(saved["bank_size"]) == bank.bank_size
    assert str(saved["bank_checksum"]) == bank.bank_checksum
    assert int(saved["series_order"]) == order
    assert float(saved["max_x"]) == max_x
    assert np.array_equal(saved["category_counts"], bank.category_counts)
    assert np.array_equal(saved["category_mass"], bank.category_mass)
    assert np.array_equal(saved["power_moments"], bank.power_moments)

selected_indices = np.asarray([0, 79, 159])
selected = likelihood.CompressedBank(
    tuple(bank.site_ids[index] for index in selected_indices),
    bank.bank_size,
    np.ascontiguousarray(bank.category_counts[selected_indices]),
    np.ascontiguousarray(bank.category_mass[selected_indices]),
    np.ascontiguousarray(bank.power_moments[selected_indices]),
    np.ascontiguousarray(bank.bank_arrivals[:, selected_indices]),
    hashlib.sha256(
        np.ascontiguousarray(bank.bank_arrivals[:, selected_indices]).view(np.uint8)
    ).hexdigest(),
    order,
    max_x,
)
direct_checks = []
for x in (5.0, 20.0, 40.0):
    hazards = np.full(len(selected_indices), x / (10.0 * (30.0 - 1.0)))
    compressed = likelihood.build_integration(
        selected, [30.0], hazards, exact=False, enforce_domain=True
    )
    direct = likelihood.build_integration(selected, [30.0], hazards, exact=True)
    check_difference = np.abs(compressed.survival_moments - direct.survival_moments)
    direct_checks.append(
        {
            "x": x,
            "max_abs_difference": float(np.max(check_difference)),
            "max_relative_difference": float(
                np.max(
                    check_difference
                    / np.maximum(np.abs(direct.survival_moments), np.finfo(float).tiny)
                )
            ),
            "series_remainder_bound": float(compressed.series_bound),
        }
    )
assert max(row["max_abs_difference"] for row in direct_checks) < 1e-14

receipt = {
    "order": order,
    "max_x": max_x,
    "lower_order_moment_check": old_moment_check,
    "lower_order_roundoff_accepted": True,
    "category_counts_bitwise_preserved": True,
    "category_mass_bitwise_preserved": True,
    "selected_site_indices": selected_indices.tolist(),
    "compressed_vs_direct_checks": direct_checks,
    "exponential_series_tail_bound": geometric_bound,
    "scipy_remainder_bound": likelihood.series_remainder_bound(max_x, order=order),
    "grid_max_x_at_h30": 10 * math.exp(-2) * 29,
    "preparation_seconds": elapsed,
    "raw_arrival_array_sha256": bank.bank_checksum,
    "raw_arrival_file_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "prior_compressed_file_sha256": hashlib.sha256(old_path.read_bytes()).hexdigest(),
    "output_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "runtime": {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
    },
}
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps(receipt, indent=2))
