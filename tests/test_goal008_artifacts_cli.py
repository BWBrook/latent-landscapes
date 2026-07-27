from __future__ import annotations

import csv
import hashlib
import json
import runpy
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from latent_landscapes.goal008 import artifacts, benchmark


def tiny_config() -> benchmark.Goal008Config:
    cells = tuple(
        benchmark.TruthCell(
            cell_id=f"cell-{eta_index * 3 + rho_index:02d}",
            rho=rho,
            eta=eta,
            rho_index=rho_index,
            eta_index=eta_index,
        )
        for eta_index, eta in ((0, 0.5), (1, 1.0), (2, 1.5))
        for rho_index, rho in enumerate((0.5, 1.0, 2.0))
    )
    return benchmark.Goal008Config(
        master_seed=83,
        bank_size=2,
        calibration_blocks=2,
        validation_blocks=2,
        calibration_rank_one_based=2,
        rhos=(0.5, 1.0, 2.0),
        etas=(0.5, 1.0, 1.5),
        truth_cells=cells,
    )


def _expected_files() -> set[str]:
    return {
        "config.json",
        "compute_provenance.json",
        "seed_manifest.csv",
        "truth_cell_summary.csv",
        "calibration_results.csv",
        "validation_results.csv",
        "predictive_summary.csv",
        "representative_profiles.csv",
        "central_reconciliation.json",
        "summary.json",
        "verification.json",
        "review.md",
        "visuals/truth_grid_recovery.svg",
        "visuals/truth_grid_calibration.svg",
        "visuals/truth_grid_ridge.svg",
        "visuals/truth_grid_predictive.svg",
    }


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(csv.DictReader(handle))


def _test_provenance() -> dict[str, object]:
    return {
        "provenance_mode": "test",
        "run_id": "goal008-tiny-test",
        "host_id": "local-test-host",
    }


def _blocked_result(result: benchmark.Goal008Result) -> benchmark.Goal008Result:
    cell_invariants = {
        cell: dict(invariants) for cell, invariants in result.cell_invariants.items()
    }
    cell_invariants["cell-08"]["finite_likelihoods_and_scores"] = False
    campaign_invariants = dict(result.invariants)
    campaign_invariants["cell_invariants"] = False
    summaries = (
        replace(
            result.cell_bank_summaries[0],
            paired_brier_interval=replace(
                result.cell_bank_summaries[0].paired_brier_interval,
                estimate=float("inf"),
            ),
        ),
        *result.cell_bank_summaries[1:],
    )
    central = replace(
        result.central_reconciliation,
        production_reference_checked=True,
        production_reference_match=False,
        checks={"canonical_validation": False},
    )
    return replace(
        result,
        cell_bank_summaries=summaries,
        central_reconciliation=central,
        cell_invariants=cell_invariants,
        invariants=campaign_invariants,
        outcome="implementation_blocked",
    )


@pytest.fixture(scope="module")
def small_result() -> benchmark.Goal008Result:
    return benchmark.run_campaign(tiny_config(), workers=1)


def test_exact_deterministic_review_pack_checksums_and_surfaces(
    tmp_path: Path,
    small_result: benchmark.Goal008Result,
) -> None:
    provenance = _test_provenance()
    first = tmp_path / "first"
    second = tmp_path / "second"

    written = artifacts.write_review_bundle(small_result, first, provenance)
    artifacts.write_review_bundle(small_result, second, provenance)

    observed = {path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()}
    assert observed == _expected_files()
    assert len(written) == 16
    assert {path.relative_to(first).as_posix() for path in written} == observed
    for relative in observed:
        assert (first / relative).read_bytes() == (second / relative).read_bytes()
        contents = (first / relative).read_bytes()
        assert b"/Users/" not in contents
        assert b"/tmp/" not in contents
        assert b"NaN" not in contents
        assert b"Infinity" not in contents

    config = json.loads((first / "config.json").read_text(encoding="utf-8"))
    compute = json.loads((first / "compute_provenance.json").read_text(encoding="utf-8"))
    cells = _read_csv(first / "truth_cell_summary.csv")
    calibration = _read_csv(first / "calibration_results.csv")
    validation = _read_csv(first / "validation_results.csv")
    predictive = _read_csv(first / "predictive_summary.csv")
    representative = _read_csv(first / "representative_profiles.csv")
    central = json.loads((first / "central_reconciliation.json").read_text(encoding="utf-8"))
    summary = json.loads((first / "summary.json").read_text(encoding="utf-8"))
    verification = json.loads((first / "verification.json").read_text(encoding="utf-8"))
    review = (first / "review.md").read_text(encoding="utf-8")

    assert config["method"] == "site-history simulated composite likelihood"
    assert config["independent_unit"] == "shock block"
    assert config["truth_cell_order"] == [cell.cell_id for cell in tiny_config().truth_cells]
    assert compute["provenance_mode"] == "test"
    assert compute["run_id"] == "goal008-tiny-test"
    assert compute["host_id"] == "local-test-host"
    assert compute["worker_count"] == 1
    assert compute["campaign_exit_success"] is True
    assert len(compute["cell_telemetry"]) == 9
    assert all(row["exit_status"] == 0 for row in compute["cell_telemetry"])
    assert all(row["wall_time_seconds"] >= 0.0 for row in compute["cell_telemetry"])
    assert all(row["maximum_rss_bytes"] > 0 for row in compute["cell_telemetry"])
    assert compute["python_version"]
    assert compute["uv_version"]
    assert compute["numpy_version"]
    assert compute["os_identifier"]
    assert len(cells) == len(predictive) == 9 * 3
    assert len(calibration) == len(validation) == 9 * 3 * 2
    assert len(representative) == 9 * 3 * 3 * 3
    assert {row["truth_cell"] for row in cells} == {
        cell.cell_id for cell in tiny_config().truth_cells
    }
    assert all(row["truth_cell"] == row["cutoff_source_cell"] for row in validation)
    allowed_faces = {"rho_min", "rho_max", "eta_min", "eta_max"}
    assert all(
        set(json.loads(row["support_boundary_faces"])) <= allowed_faces for row in validation
    )
    assert {
        "rho_min_contact_count",
        "rho_max_contact_count",
        "eta_min_contact_count",
        "eta_max_contact_count",
    }.issubset(cells[0])
    assert central["truth_cell"] == "cell-04"
    assert central["production_reference_checked"] is False
    assert summary["truth_cell_count"] == 9
    assert summary["truth_cell_bank_count"] == 27
    assert summary["pointwise_not_familywise"] is True
    assert verification["expected_artifact_file_count"] == 16
    assert verification["observed_artifact_file_count"] == 16
    assert all(verification["invariants"].values())
    for relative, expected in verification["sha256"].items():
        assert relative != "verification.json"
        assert hashlib.sha256((first / relative).read_bytes()).hexdigest() == expected
    assert "500 independent shock blocks" in review
    assert "paired correlated counterfactuals" in review
    assert "pointwise, not familywise" in review
    assert "not a full joint spatial likelihood" in review
    assert "negative or mixed" in review

    for filename in (
        "truth_grid_recovery.svg",
        "truth_grid_calibration.svg",
        "truth_grid_ridge.svg",
        "truth_grid_predictive.svg",
    ):
        svg = (first / "visuals" / filename).read_text(encoding="utf-8")
        assert svg.lstrip().startswith("<?xml")
        assert "<svg" in svg
        assert len(svg) > 5_000
        assert "dc:date" not in svg


def test_review_pack_rejects_stale_blocked_and_nonportable_provenance(
    tmp_path: Path,
    small_result: benchmark.Goal008Result,
) -> None:
    stale = tmp_path / "stale"
    stale.mkdir()
    (stale / "unexpected.txt").write_text("stale\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="stale"):
        artifacts.write_review_bundle(small_result, stale, _test_provenance())
    with pytest.raises(ValueError, match="implementation-blocked"):
        artifacts.write_review_bundle(
            replace(small_result, outcome="implementation_blocked"),
            tmp_path / "blocked",
            _test_provenance(),
        )
    with pytest.raises(ValueError, match="portable"):
        artifacts.write_review_bundle(
            small_result,
            tmp_path / "nonportable",
            _test_provenance() | {"scratch_path": "/tmp/private-run"},
        )
    production_like = replace(small_result, config=benchmark.DEFAULT_CONFIG)
    with pytest.raises(ValueError, match="production provenance"):
        artifacts.write_review_bundle(
            production_like,
            tmp_path / "untrusted-production",
            _test_provenance(),
        )
    assert not (tmp_path / "blocked").exists()
    assert not (tmp_path / "nonportable").exists()
    assert not (tmp_path / "untrusted-production").exists()


def test_blocked_diagnostics_are_exact_strict_deterministic_and_complete(
    tmp_path: Path,
    small_result: benchmark.Goal008Result,
) -> None:
    blocked = _blocked_result(small_result)
    first = tmp_path / "first-blocked"
    second = tmp_path / "second-blocked"

    written = artifacts.write_blocked_diagnostics(blocked, first, _test_provenance())
    artifacts.write_blocked_diagnostics(blocked, second, _test_provenance())

    expected = {"diagnostics.json", "compute_provenance.json", "verification.json"}
    observed = {path.relative_to(first).as_posix() for path in first.iterdir()}
    assert observed == expected
    assert len(written) == 3
    assert {path.relative_to(first).as_posix() for path in written} == expected
    for relative in expected:
        assert (first / relative).read_bytes() == (second / relative).read_bytes()
        json.loads(
            (first / relative).read_text(encoding="utf-8"),
            parse_constant=lambda value: pytest.fail(f"non-strict JSON token: {value}"),
        )

    diagnostics = json.loads((first / "diagnostics.json").read_text(encoding="utf-8"))
    provenance = json.loads((first / "compute_provenance.json").read_text(encoding="utf-8"))
    verification = json.loads((first / "verification.json").read_text(encoding="utf-8"))

    assert diagnostics["outcome"] == "implementation_blocked"
    assert diagnostics["scientific_review_pack_accepted"] is False
    assert diagnostics["false_campaign_invariants"] == ["cell_invariants"]
    assert diagnostics["campaign_invariants"]["cell_invariants"] is False
    assert len(diagnostics["cell_invariants"]) == 9
    cell_08 = next(row for row in diagnostics["cell_invariants"] if row["truth_cell"] == "cell-08")
    assert cell_08["false_invariants"] == ["finite_likelihoods_and_scores"]
    assert len(diagnostics["cell_bank_surface"]) == 27
    assert {
        (row["truth_cell"], row["bank_variant"]) for row in diagnostics["cell_bank_surface"]
    } == {
        (cell.cell_id, bank)
        for cell in blocked.config.truth_cells
        for bank in benchmark.BANK_VARIANT_NAMES
    }
    assert diagnostics["execution_telemetry"]["campaign_exit_status"] == 0
    assert len(diagnostics["execution_telemetry"]["cell_telemetry"]) == 9
    assert diagnostics["source_identity"] == benchmark.SOURCE_IDENTITY
    assert diagnostics["campaign_digest"] == benchmark.campaign_digest(blocked)
    assert diagnostics["central_reconciliation"]["raw_hashes"]
    assert diagnostics["central_reconciliation"]["canonical_hashes"]
    assert diagnostics["central_reconciliation"]["structural_hashes"]
    assert diagnostics["nonfinite_encoding"]["strategy"] == "tagged_string"
    assert diagnostics["nonfinite_values"] == [
        {
            "path": "$.cell_bank_surface[0].paired_brier_estimate",
            "tag": "__nonfinite_float__:positive_infinity",
        }
    ]
    assert (
        diagnostics["cell_bank_surface"][0]["paired_brier_estimate"]
        == "__nonfinite_float__:positive_infinity"
    )
    assert provenance["provenance_validation_passed"] is True
    assert verification["expected_artifact_file_count"] == 3
    assert verification["observed_artifact_file_count"] == 3
    assert verification["scientific_review_pack_accepted"] is False
    assert set(verification["sha256"]) == {"diagnostics.json", "compute_provenance.json"}
    for relative, expected_hash in verification["sha256"].items():
        assert hashlib.sha256((first / relative).read_bytes()).hexdigest() == expected_hash


def test_blocked_diagnostics_refuse_stale_or_nonblocked_results(
    tmp_path: Path,
    small_result: benchmark.Goal008Result,
) -> None:
    stale = tmp_path / "stale-diagnostics"
    stale.mkdir()
    with pytest.raises(RuntimeError, match="stale"):
        artifacts.write_blocked_diagnostics(
            _blocked_result(small_result),
            stale,
            _test_provenance(),
        )
    with pytest.raises(ValueError, match="implementation_blocked"):
        artifacts.write_blocked_diagnostics(
            small_result,
            tmp_path / "not-blocked",
            _test_provenance(),
        )
    assert not (tmp_path / "not-blocked").exists()


def test_artifact_destinations_are_ignored() -> None:
    for path in (
        "artifacts/goal008_joint_rho_eta_cross_truth_perfect_detection",
        "artifacts/goal008_joint_rho_eta_cross_truth_perfect_detection_repeat",
        "artifacts/goal009_cross_truth_blocked_diagnostics",
    ):
        completed = subprocess.run(["git", "check-ignore", "-q", path], check=False)
        assert completed.returncode == 0


def test_cli_writes_completed_negative_and_rejects_scientific_tuning(
    tmp_path: Path,
    small_result: benchmark.Goal008Result,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    negative = replace(small_result, outcome="joint_cross_truth_recovery_imprecise")
    output_dir = tmp_path / "negative"
    diagnostics_dir = tmp_path / "unexpected-diagnostics"
    provenance_path = tmp_path / "compute.json"
    provenance_path.write_text(
        json.dumps(_test_provenance()),
        encoding="utf-8",
    )
    monkeypatch.setattr(benchmark, "run_campaign", lambda *, workers: negative)
    monkeypatch.setattr(
        artifacts,
        "validate_pre_campaign_provenance",
        lambda declared, *, workers: None,
    )
    monkeypatch.setattr(artifacts, "DEFAULT_BLOCKED_DIAGNOSTICS_DIR", diagnostics_dir)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scripts/run_goal008.py",
            "--output-dir",
            str(output_dir),
            "--workers",
            "2",
            "--compute-provenance-json",
            str(provenance_path),
        ],
    )

    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal008.py", run_name="__main__")

    assert raised.value.code == 0
    assert "joint_cross_truth_recovery_imprecise" in capsys.readouterr().out
    assert {
        path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*") if path.is_file()
    } == _expected_files()
    assert not diagnostics_dir.exists()

    required = subprocess.run(
        [sys.executable, "scripts/run_goal008.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert required.returncode == 2
    assert "--compute-provenance-json" in required.stderr
    assert "required" in required.stderr

    for option in ("--bank-size", "--truth-rho", "--calibration-blocks", "--eta-grid"):
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/run_goal008.py",
                "--compute-provenance-json",
                str(provenance_path),
                option,
                "2",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 2
        assert "unrecognized arguments" in completed.stderr


def test_cli_writes_only_quarantine_for_returned_block_and_none_for_exceptions(
    tmp_path: Path,
    small_result: benchmark.Goal008Result,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    blocked = _blocked_result(small_result)
    output_dir = tmp_path / "scientific"
    diagnostics_dir = tmp_path / "blocked-diagnostics"
    provenance_path = tmp_path / "compute.json"
    provenance_path.write_text(json.dumps(_test_provenance()), encoding="utf-8")
    monkeypatch.setattr(benchmark, "run_campaign", lambda *, workers: blocked)
    monkeypatch.setattr(
        artifacts,
        "validate_pre_campaign_provenance",
        lambda declared, *, workers: None,
    )
    monkeypatch.setattr(artifacts, "DEFAULT_BLOCKED_DIAGNOSTICS_DIR", diagnostics_dir)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scripts/run_goal008.py",
            "--output-dir",
            str(output_dir),
            "--workers",
            "2",
            "--compute-provenance-json",
            str(provenance_path),
        ],
    )

    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal008.py", run_name="__main__")

    captured = capsys.readouterr()
    assert raised.value.code == 1
    assert "completed blocked campaign diagnostics" in captured.err
    assert not output_dir.exists()
    assert {path.name for path in diagnostics_dir.iterdir()} == {
        "diagnostics.json",
        "compute_provenance.json",
        "verification.json",
    }

    exception_dir = tmp_path / "exception-diagnostics"
    monkeypatch.setattr(artifacts, "DEFAULT_BLOCKED_DIAGNOSTICS_DIR", exception_dir)
    monkeypatch.setattr(
        benchmark,
        "run_campaign",
        lambda *, workers: (_ for _ in ()).throw(RuntimeError("worker failed")),
    )
    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal008.py", run_name="__main__")

    captured = capsys.readouterr()
    assert raised.value.code == 1
    assert "campaign did not complete" in captured.err
    assert "completed blocked campaign diagnostics" not in captured.err
    assert not exception_dir.exists()

    pre_campaign_dir = tmp_path / "pre-campaign-diagnostics"
    monkeypatch.setattr(
        artifacts,
        "DEFAULT_BLOCKED_DIAGNOSTICS_DIR",
        pre_campaign_dir,
    )
    monkeypatch.setattr(
        artifacts,
        "validate_pre_campaign_provenance",
        lambda declared, *, workers: (_ for _ in ()).throw(ValueError("untrusted provenance")),
    )
    monkeypatch.setattr(
        benchmark,
        "run_campaign",
        lambda *, workers: pytest.fail("campaign started after trust failure"),
    )
    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal008.py", run_name="__main__")

    captured = capsys.readouterr()
    assert raised.value.code == 1
    assert "campaign did not start" in captured.err
    assert "completed blocked campaign diagnostics" not in captured.err
    assert not pre_campaign_dir.exists()
