from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

from latent_landscapes.goal005 import artifacts, benchmark


def test_tiny_bundle_has_exact_file_contract_and_is_byte_stable(tmp_path: Path) -> None:
    from dataclasses import replace

    result = benchmark.run_goal005(
        replace(
            benchmark.DEFAULT_CONFIG,
            bank_size=8,
            calibration_replicates=4,
            validation_replicates=3,
            calibration_rank_one_based=4,
        )
    )
    first = tmp_path / "first"
    second = tmp_path / "second"
    artifacts.write_review_bundle(result, first)
    artifacts.write_review_bundle(result, second)
    expected = {*artifacts.ROOT_FILES, *(f"visuals/{n}" for n in artifacts.VISUAL_FILES)}
    assert {p.relative_to(first).as_posix() for p in first.rglob("*") if p.is_file()} == expected
    for relative in expected:
        assert (first / relative).read_bytes() == (second / relative).read_bytes()
        content = (first / relative).read_bytes()
        assert b"/Users/" not in content and b"NaN" not in content and b"Infinity" not in content
    verification = json.loads((first / "verification.json").read_text(encoding="utf-8"))
    assert verification["expected_artifact_file_count"] == 15
    assert verification["observed_artifact_file_count"] == 15


def test_cli_completed_scientific_class_exits_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from dataclasses import replace

    result = benchmark.run_goal005(
        replace(
            benchmark.DEFAULT_CONFIG,
            bank_size=8,
            calibration_replicates=4,
            validation_replicates=3,
            calibration_rank_one_based=4,
        )
    )
    monkeypatch.setattr(
        benchmark, "run_goal005", lambda: replace(result, outcome="one_rate_design_limited")
    )
    output = tmp_path / "cli"
    monkeypatch.setattr(sys, "argv", ["scripts/run_goal005.py", "--output-dir", str(output)])
    try:
        runpy.run_path("scripts/run_goal005.py", run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 0
    assert "Wrote 15 files" in capsys.readouterr().out
