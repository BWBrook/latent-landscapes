from __future__ import annotations

import csv
import hashlib
import json
import platform
import runpy
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from latent_landscapes.goal008 import artifacts as goal008_artifacts
from latent_landscapes.goal008 import benchmark as goal008
from latent_landscapes.goal010 import artifacts, benchmark


def _small_cells(rhos: tuple[float, ...], etas: tuple[float, ...]) -> tuple[goal008.TruthCell, ...]:
    return tuple(
        goal008.TruthCell(
            cell_id=f"cell-{eta_row * 3 + rho_column:02d}",
            rho=rho,
            eta=eta,
            rho_index=rhos.index(rho),
            eta_index=etas.index(eta),
        )
        for eta_row, eta in enumerate((0.5, 1.0, 1.5))
        for rho_column, rho in enumerate((0.5, 1.0, 2.0))
    )


def _write_small_goal009_pack(target: Path) -> Path:
    rhos = (0.5, 1.0, 2.0)
    etas = tuple(float(value) for value in goal008.FROZEN_ETA_GRID)
    config = goal008.Goal008Config(
        master_seed=goal008.MASTER_SEED,
        bank_size=2,
        calibration_blocks=2,
        validation_blocks=2,
        calibration_rank_one_based=2,
        rhos=rhos,
        etas=etas,
        truth_cells=_small_cells(rhos, etas),
    )
    result = replace(
        goal008.run_campaign(config, workers=1),
        outcome="joint_cross_truth_design_limited",
    )
    goal008_artifacts.write_review_bundle(
        result,
        target,
        {
            "provenance_mode": "test",
            "run_id": "goal009-small-artifact-test",
            "host_id": "local-test-host",
        },
    )
    return target


def _test_provenance() -> dict[str, object]:
    return {
        "provenance_mode": "test",
        "run_id": "goal010-small-test",
        "host_id": "local-test-host",
    }


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(csv.DictReader(handle))


@pytest.fixture(scope="module")
def small_result(tmp_path_factory: pytest.TempPathFactory) -> benchmark.Goal010Result:
    root = tmp_path_factory.mktemp("goal010-result")
    pack = benchmark.read_goal009_pack(
        _write_small_goal009_pack(root / "goal009"),
        require_published=False,
    )
    return benchmark.run_campaign(pack, config=benchmark.smoke_config(), workers=1)


def _expected_files() -> set[str]:
    return {
        "config.json",
        "compute_provenance.json",
        "baseline_boundary_anatomy.csv",
        "expanded_calibration_results.csv",
        "expanded_validation_results.csv",
        "expanded_truth_cell_summary.csv",
        "paired_boundary_transitions.csv",
        "domain_comparison.csv",
        "representative_profiles.csv",
        "decision.json",
        "verification.json",
        "review.md",
        "visuals/boundary_anatomy.svg",
        "visuals/domain_comparison.svg",
    }


def test_exact_deterministic_14_file_bundle_is_strict_and_self_verifying(
    tmp_path: Path,
    small_result: benchmark.Goal010Result,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    written = artifacts.write_review_bundle(small_result, first, _test_provenance())
    artifacts.write_review_bundle(small_result, second, _test_provenance())

    observed = {path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()}
    assert observed == _expected_files()
    assert len(written) == 14
    assert {path.relative_to(first).as_posix() for path in written} == observed
    assert artifacts.validate_review_bundle(first)["bundle_validated"] is True

    for relative in observed:
        assert (first / relative).read_bytes() == (second / relative).read_bytes()
        contents = (first / relative).read_bytes()
        assert b"NaN" not in contents
        assert b"Infinity" not in contents
        if relative.endswith(".json"):
            json.loads(
                contents,
                parse_constant=lambda value: pytest.fail(f"non-strict JSON token: {value}"),
            )

    config = json.loads((first / "config.json").read_text(encoding="utf-8"))
    compute = json.loads((first / "compute_provenance.json").read_text(encoding="utf-8"))
    decision = json.loads((first / "decision.json").read_text(encoding="utf-8"))
    verification = json.loads((first / "verification.json").read_text(encoding="utf-8"))
    baseline = _read_csv(first / "baseline_boundary_anatomy.csv")
    calibration = _read_csv(first / "expanded_calibration_results.csv")
    validation = _read_csv(first / "expanded_validation_results.csv")
    summaries = _read_csv(first / "expanded_truth_cell_summary.csv")
    paired = _read_csv(first / "paired_boundary_transitions.csv")
    comparison = _read_csv(first / "domain_comparison.csv")
    profiles = _read_csv(first / "representative_profiles.csv")

    assert config["candidate_etas_expanded"][-2:] == [2.25, 2.5]
    assert config["candidate_rhos_unchanged"] is True
    assert config["selected_cell_order"] == ["cell-06", "cell-07", "cell-08"]
    assert config["production_scale"] is False
    assert compute["provenance_validation_passed"] is True
    assert compute["worker_count"] == 1
    assert len(baseline) == 27
    assert len(calibration) == len(validation) == len(paired) == 18
    assert len(summaries) == len(comparison) == 9
    assert len(profiles) == 3 * 3 * 11 * 3
    assert decision["outcome"] == small_result.outcome
    assert decision["goal009_reclassified"] is False
    assert decision["predictive_role"] == "guard_not_identifiability_evidence"
    assert verification["expected_artifact_file_count"] == 14
    assert verification["observed_artifact_file_count"] == 14
    assert verification["baseline_pack_validated"] is True
    assert all(verification["invariants"].values())
    assert set(verification["sha256"]) == _expected_files() - {"verification.json"}
    for relative, expected in verification["sha256"].items():
        assert hashlib.sha256((first / relative).read_bytes()).hexdigest() == expected

    for name in ("boundary_anatomy.svg", "domain_comparison.svg"):
        svg = (first / "visuals" / name).read_text(encoding="utf-8")
        assert svg.lstrip().startswith("<?xml")
        assert "<svg" in svg
        assert len(svg) > 5_000
        assert "dc:date" not in svg


def test_writer_refuses_stale_or_blocked_outputs_and_validator_detects_tampering(
    tmp_path: Path,
    small_result: benchmark.Goal010Result,
) -> None:
    stale = tmp_path / "stale"
    stale.mkdir()
    (stale / "unexpected.txt").write_text("stale\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="stale"):
        artifacts.write_review_bundle(small_result, stale, _test_provenance())

    blocked = replace(small_result, outcome="implementation_blocked")
    blocked_target = tmp_path / "blocked"
    with pytest.raises(ValueError, match="implementation_blocked"):
        artifacts.write_review_bundle(blocked, blocked_target, _test_provenance())
    assert not blocked_target.exists()

    target = tmp_path / "tampered"
    artifacts.write_review_bundle(small_result, target, _test_provenance())
    (target / "decision.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        artifacts.validate_review_bundle(target)


@pytest.mark.parametrize(
    ("missing_key", "replacement"),
    [
        ("bundle_verified", None),
        ("goal009_input_manifest_verified", False),
        ("detached_head", False),
        ("remote_head_clean", False),
        ("focused_tests_passed", False),
        ("smoke_passed", False),
        ("environment_verified", False),
        ("source_commit", None),
        ("bundle_sha256", None),
        ("uv_lock_sha256", None),
        ("goal009_input_manifest_sha256", None),
    ],
)
def test_production_provenance_rejects_missing_or_false_trust_fields_before_compute(
    missing_key: str,
    replacement: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    declaration: dict[str, object] = {
        "provenance_mode": "production",
        "run_id": "goal010-production-test",
        "host_id": "deep-server",
        "bundle_verified": True,
        "goal009_input_manifest_verified": True,
        "detached_head": True,
        "remote_head_clean": True,
        "focused_tests_passed": True,
        "smoke_passed": True,
        "environment_verified": True,
        "source_commit": "a" * 40,
        "bundle_sha256": "b" * 64,
        "uv_lock_sha256": "c" * 64,
        "goal009_input_manifest_sha256": "d" * 64,
        "worker_count": 3,
        "thread_limits": {name: "1" for name in benchmark.THREAD_LIMIT_NAMES},
        "python_version": "3.14.5",
        "numpy_version": "2.5.1",
        "uv_version": "uv 0.8.0",
        "os_identifier": "Linux-test",
        "production_command": "uv run --frozen python scripts/run_goal010.py --workers 3",
    }
    complete_declaration = dict(declaration)
    if replacement is None:
        declaration.pop(missing_key)
    else:
        declaration[missing_key] = replacement

    with pytest.raises(ValueError, match="production provenance"):
        artifacts.validate_pre_campaign_provenance(
            declaration,
            workers=3,
            smoke=False,
        )
    if missing_key == "bundle_verified":
        monkeypatch.setattr(platform, "node", lambda: "not-deep-server")
        with pytest.raises(ValueError, match="runtime host"):
            artifacts.validate_pre_campaign_provenance(
                complete_declaration,
                workers=3,
                smoke=False,
            )


def test_cli_reduced_smoke_writes_bundle_and_bad_provenance_never_starts_compute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    goal009 = _write_small_goal009_pack(tmp_path / "goal009")
    output = tmp_path / "smoke-output"
    provenance_path = tmp_path / "smoke-provenance.json"
    provenance_path.write_text(json.dumps(_test_provenance()), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scripts/run_goal010.py",
            "--goal009-pack",
            str(goal009),
            "--output-dir",
            str(output),
            "--workers",
            "1",
            "--compute-provenance-json",
            str(provenance_path),
            "--smoke",
        ],
    )

    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal010.py", run_name="__main__")

    assert raised.value.code == 0
    assert "reduced smoke" in capsys.readouterr().out
    assert artifacts.validate_review_bundle(output)["bundle_validated"] is True
    assert {
        path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()
    } == _expected_files()

    bad_path = tmp_path / "bad-provenance.json"
    bad_path.write_text(json.dumps({"provenance_mode": "production"}), encoding="utf-8")
    no_output = tmp_path / "must-not-exist"
    monkeypatch.setattr(
        benchmark,
        "run_campaign",
        lambda *args, **kwargs: pytest.fail("compute started after provenance failure"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scripts/run_goal010.py",
            "--goal009-pack",
            str(goal009),
            "--output-dir",
            str(no_output),
            "--workers",
            "3",
            "--compute-provenance-json",
            str(bad_path),
        ],
    )
    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal010.py", run_name="__main__")

    assert raised.value.code == 1
    assert "did not start" in capsys.readouterr().err
    assert not no_output.exists()

    required = subprocess.run(
        [sys.executable, "scripts/run_goal010.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert required.returncode == 2
    assert "--goal009-pack" in required.stderr
    assert "--compute-provenance-json" in required.stderr

    tuned = subprocess.run(
        [
            sys.executable,
            "scripts/run_goal010.py",
            "--goal009-pack",
            str(goal009),
            "--compute-provenance-json",
            str(provenance_path),
            "--eta-grid",
            "3.0",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert tuned.returncode == 2
    assert "unrecognized arguments" in tuned.stderr


def test_default_artifact_destination_is_ignored() -> None:
    completed = subprocess.run(
        ["git", "check-ignore", "-q", str(artifacts.DEFAULT_OUTPUT_DIR)],
        check=False,
    )
    assert completed.returncode == 0
