from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


def _module():
    path = Path(__file__).parents[1] / "scripts" / "diagnose_calibration_transport.py"
    spec = importlib.util.spec_from_file_location("goal049_archive_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_support_geometry_retains_exact_components_and_empty_supports() -> None:
    module = _module()
    mask = np.array(
        [
            [False, True, True, False, False],
            [True, False, True, False, False],
            [False, False, False, False, False],
        ]
    )
    result = module.support_geometry(mask, np.array([1.0, 2.0, 3.0, 4.0, 5.0]), 1)
    assert result["truth_membership"].tolist() == [True, False, False]
    assert result["cardinality"].tolist() == [2.0, 2.0, 0.0]
    assert result["components"].tolist() == [1.0, 2.0, 0.0]
    assert result["empty"].tolist() == [False, False, True]
    assert np.isnan(result["log_hull_span"][2])


def test_order_statistic_cutoff_uses_archive_rank() -> None:
    module = _module()
    values = np.arange(250.0)
    assert module.cutoff(values) == 238.0
