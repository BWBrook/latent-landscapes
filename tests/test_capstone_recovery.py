from __future__ import annotations

import json
import platform
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from latent_landscapes import capstone_public as public
from latent_landscapes import capstone_recovery as recovery

REPO = Path(__file__).resolve().parents[1]
ORIGINAL = REPO / "artifacts/goal059_execution/public_inputs"
PREDECESSOR = REPO / "artifacts/goal059_execution"
REGISTRATION = REPO / "docs/goals/060-capstone-certificate-recovery/registration-2026-10-04.md"


def run_recovery(output: Path, *, original: Path = ORIGINAL) -> dict[str, Any]:
    return recovery.recover_public_inputs(
        original,
        output,
        predecessor_audit=PREDECESSOR / "map-audit/audit.json",
        predecessor_source=PREDECESSOR / "source-manifest.json",
        predecessor_registration=(
            REPO / "docs/goals/059-capstone-preparation/registration-2026-10-04.md"
        ),
        registration=REGISTRATION,
    )


@pytest.mark.skipif(platform.system() != "Linux", reason="exact frozen Linux exposure replay")
def test_recovery_preserves_original_arrays_and_negative_metadata(tmp_path: Path) -> None:
    before = {name: public._sha(ORIGINAL / name) for name in recovery.ORIGINAL_HASHES}
    output = tmp_path / "recovered"
    result = run_recovery(output)
    assert result["state"] == "qualified"
    assert result["certificate"]["interval_count"] == 1024
    assert result["certificate"]["transform_x_upper"] == pytest.approx(4.928543928, abs=1e-9)
    assert before == {name: public._sha(ORIGINAL / name) for name in before}
    for name, expected in before.items():
        destination = "original-public-inputs.json" if name == "public_inputs.json" else name
        assert public._sha(output / destination) == expected
    assert json.loads((output / "original-public-inputs.json").read_text())["state"] == (
        "qualification_failed"
    )
    loaded = public.load_public_inputs(output)
    assert loaded.metadata["attempt"] == 0
    assert loaded.metadata["qualification_goal"] == 60
    assert len(loaded.setup.site_ids) == 160
    with pytest.raises(FileExistsError):
        run_recovery(output)


def test_changed_original_is_rejected_before_output_creation(tmp_path: Path) -> None:
    original = tmp_path / "original"
    shutil.copytree(ORIGINAL, original)
    with (original / "public_inputs.json").open("a") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="identity mismatch"):
        run_recovery(tmp_path / "output", original=original)
    assert not (tmp_path / "output").exists()


def test_fixed_certificate_can_fail_and_retains_domain() -> None:
    certificate = recovery.fixed_hazard_certificate(np.zeros((4, 4)), np.array([4.0]))
    assert certificate["interval_count"] == 1024
    assert certificate["beta_interval"] == [-2.0, 2.0]
    assert certificate["required_transform_domain_upper"] == 5.0
    assert certificate["passes"] is False


@pytest.mark.skipif(platform.system() != "Linux", reason="exact frozen Linux exposure replay")
def test_failed_recovery_leaves_bound_negative_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Inject a certificate failure, without choosing any map or random history.
    certificate = recovery.fixed_hazard_certificate(np.zeros((4, 4)), np.array([4.0]))
    monkeypatch.setattr(recovery, "fixed_hazard_certificate", lambda *_: certificate)
    output = tmp_path / "failed"
    with pytest.raises(RuntimeError, match="failed amended hazard"):
        run_recovery(output)
    receipt = json.loads((output / "recovery.json").read_text())
    assert receipt["state"] == "qualification_failed"
    assert receipt["certificate"]["passes"] is False
    assert public._sha(output / "public_inputs.npz") == (
        recovery.ORIGINAL_HASHES["public_inputs.npz"]
    )
    with pytest.raises(ValueError, match="qualification did not pass"):
        public.load_public_inputs(output)
