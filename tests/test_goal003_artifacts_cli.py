from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from latent_landscapes.goal003.artifacts import ROOT_FILES, VISUAL_FILES, write_review_bundle
from latent_landscapes.goal003.benchmark import build_ensemble


def test_review_bundle_has_exact_13_files_and_reconciles(tmp_path: Path) -> None:
    result = build_ensemble()
    paths = write_review_bundle(result, tmp_path / "bundle")
    assert len(paths) == 13
    observed = {path.relative_to(tmp_path / "bundle").as_posix() for path in paths}
    assert observed == {*ROOT_FILES, *(f"visuals/{name}" for name in VISUAL_FILES)}


def test_cli_writes_completed_negative_result(tmp_path: Path) -> None:
    output = tmp_path / "cli"
    completed = subprocess.run(
        [sys.executable, "scripts/run_goal003.py", "--output-dir", str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "time_scale_review_required" in completed.stdout
    assert len(list(output.rglob("*"))) == 14  # directory plus 13 files
