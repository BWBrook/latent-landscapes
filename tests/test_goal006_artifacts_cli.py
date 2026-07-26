from __future__ import annotations

import csv
import json
import runpy
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from latent_landscapes.goal006 import artifacts, benchmark


def test_tiny_bundle_contract_and_idempotence(tmp_path: Path) -> None:
    result = benchmark.run_goal006(replace(benchmark.DEFAULT_CONFIG, replicates=4))
    first, second = tmp_path / "first", tmp_path / "second"
    artifacts.write_review_bundle(result, first)
    artifacts.write_review_bundle(result, second)
    expected = {*artifacts.ROOT_FILES, *(f"visuals/{n}" for n in artifacts.VISUAL_FILES)}
    assert {p.relative_to(first).as_posix() for p in first.rglob("*") if p.is_file()} == expected
    for relative in expected:
        assert (first / relative).read_bytes() == (second / relative).read_bytes()
        content = (first / relative).read_bytes()
        assert b"/Users/" not in content
        assert b"NaN" not in content and b"Infinity" not in content
    verification = json.loads((first / "verification.json").read_text(encoding="utf-8"))
    assert verification["expected_artifact_file_count"] == 15
    residual_svg = (first / "visuals/aligned_residual_maps.svg").read_text(encoding="utf-8")
    fronts_svg = (first / "visuals/matched_occupancy_fronts.svg").read_text(encoding="utf-8")
    assert residual_svg.count("<path") >= 2
    assert "Diagnostic alignment only" in residual_svg
    assert "eta=0.5 versus eta=1 reference" in residual_svg
    assert fronts_svg.count("<path") >= 2
    assert "Raw 50% front: eta=0.5 vs eta=1" in fronts_svg
    assert "eta-specific only" in fronts_svg
    classes = {row["habitat_class"] for row in csv.DictReader((first / "cell_summary.csv").open())}
    assert classes == {"corridor", "low_quality_matrix", "high_quality_patch", "medium_quality"}


def test_cli_scientific_negative_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = benchmark.run_goal006(replace(benchmark.DEFAULT_CONFIG, replicates=4))
    monkeypatch.setattr(benchmark, "run_goal006", lambda: result)
    output = tmp_path / "cli"
    monkeypatch.setattr(sys, "argv", ["scripts/run_goal006.py", "--output-dir", str(output)])
    try:
        runpy.run_path("scripts/run_goal006.py", run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 0
    assert (output / "verification.json").exists()
