from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from latent_landscapes.goal016.artifacts import EXPECTED_FILES


def test_goal016_cli_runs_reduced_smoke(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "review-pack"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_goal016.py",
            "--reduced-smoke",
            "--output-dir",
            str(output_dir),
        ],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Outcome: reduced_smoke_complete" in completed.stdout
    assert "non-scientific" in completed.stdout
    observed = {
        path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*") if path.is_file()
    }
    assert observed == set(EXPECTED_FILES)
