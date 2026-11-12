from __future__ import annotations

import importlib
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest


@pytest.fixture
def diagnostic(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("diagnose_loss_derivatives")


def test_decimal_reference_derivative_signs_and_closed_identity(diagnostic: Any) -> None:
    for z in (0.01, 0.5, 1.0, 3.0, 10.0):
        value, first, second, third = diagnostic.decimal_reference(z)
        a = z / math.expm1(z)
        assert value == pytest.approx(math.log(-math.expm1(-z)), abs=2e-15)
        assert first == pytest.approx(a, rel=2e-15)
        assert second == pytest.approx(a * (1 - z - a), rel=2e-13)
        assert third == pytest.approx(
            a * (1 - 3 * z + z * z) - 3 * a * a * (1 - z) + 2 * a**3,
            abs=2e-15,
        )
        assert value < 0 < first
        assert second < 0


def test_decimal_reference_finite_differences_in_log_z(diagnostic: Any) -> None:
    delta = 1e-4
    for z in (0.01, 0.5, 3.0, 10.0):
        centre = diagnostic.decimal_reference(z)
        plus = diagnostic.decimal_reference(z * math.exp(delta))
        minus = diagnostic.decimal_reference(z * math.exp(-delta))
        for order in range(3):
            assert (plus[order] - minus[order]) / (2 * delta) == pytest.approx(
                centre[order + 1], rel=1e-6, abs=5e-9
            )


def test_threshold_nextafter_and_array_shape(diagnostic: Any) -> None:
    z = np.asarray([[np.nextafter(1e-3, 0), 1e-3], [np.nextafter(1e-3, math.inf), 0.1]])
    actual = diagnostic.rearranged_algebra(z)
    assert all(row.shape == z.shape for row in actual)
    expected = np.asarray([diagnostic.decimal_reference(float(x)) for x in z.reshape(-1)])
    np.testing.assert_allclose(np.asarray(actual).reshape(4, -1).T, expected, atol=2e-15)


def test_safe_algebra_keeps_representable_tail_and_avoids_overflow(diagnostic: Any) -> None:
    z = np.asarray([40.0, 710.0, 746.0, 750.0, 755.0, 760.0, 1000.0, 1e103, 1e308])
    actual = np.asarray(diagnostic.rearranged_algebra(z)).T
    expected = np.asarray([diagnostic.decimal_reference(float(x)) for x in z])
    assert np.isfinite(actual).all()
    np.testing.assert_allclose(actual, expected, rtol=3e-13, atol=np.nextafter(0.0, 1.0) * 2)
    assert actual[0, 0] < 0
    assert actual[2, 1] > 0
    assert actual[4, 2] < 0
    assert actual[5, 3] > 0
    assert np.all(actual[6:] == 0)


def test_small_z_reference_resolves_cancellation(diagnostic: Any) -> None:
    minimum = float(np.nextafter(0.0, 1.0))
    assert diagnostic.decimal_reference(minimum)[2:] == (0.0, 0.0)
    for z in (1e-300, 1e-100, 1e-20):
        value, first, second, third = diagnostic.decimal_reference(z)
        assert value == pytest.approx(math.log(z), abs=2e-13)
        assert first == 1.0
        assert second == pytest.approx(-z / 2, rel=1e-14, abs=0)
        assert third == pytest.approx(-z / 2, rel=1e-14, abs=0)


def test_diagnose_preserves_warning_nonfinite_and_premature_zero(diagnostic: Any) -> None:
    report = diagnostic.diagnose((40.0, 710.0, 1e103))
    assert report["summary"]["nonfinite_frozen_points"] == [1e103]
    assert report["summary"]["warning_points"] == [1e103]
    assert report["rows"][2]["frozen_finite"] == [True, True, True, False]
    assert report["rows"][2]["frozen"][3] == "nan"
    assert report["rows"][0]["frozen_zero_reference_nonzero"][0]
    assert report["rows"][1]["frozen_zero_reference_nonzero"][1]


@pytest.mark.parametrize("z", [0.0, -1.0, math.inf, math.nan])
def test_reference_rejects_invalid_domain(diagnostic: Any, z: float) -> None:
    with pytest.raises(ValueError, match="finite and positive"):
        diagnostic.decimal_reference(z)
    with pytest.raises(ValueError, match="finite and positive"):
        diagnostic.rearranged_algebra(np.asarray([z]))
