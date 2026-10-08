from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes import capstone_calibration as calibration
from latent_landscapes import preinvasion_fitting as fitting

SCRIPT = Path(__file__).parents[1] / "scripts/run_capstone_training.py"
SPEC = importlib.util.spec_from_file_location("run_capstone_training", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

BINDING = "a" * 64


def _pair(
    null: float,
    free: float,
    *,
    null_status: str = "converged",
    free_status: str = "converged",
    adjusted_t: float = 9.0,
) -> fitting.PairedFitResult:
    fits = {
        "adjusted_h1": fitting.FitResult(
            "adjusted_h1", 1.0, 0.0, 0.0025, 0.2, null, null_status, 1, 0.0
        ),
        "adjusted_free_h": fitting.FitResult(
            "adjusted_free_h", 1.0, 0.0, 0.0025, 0.2, free, free_status, 1, 0.0
        ),
    }
    return fitting.PairedFitResult(
        adjusted_t,
        fits,
        {"adjusted": adjusted_t},
        fitting.CostSummary(0, 0, 0, 0.0, 0.0, 0.0),
    )


def _fit_row(pair: fitting.PairedFitResult) -> dict[str, object]:
    def payload(fit: fitting.FitResult) -> dict[str, object]:
        return {
            "model": fit.model,
            "h": fit.h,
            "beta": fit.beta,
            "mu": fit.mu,
            "detection_sd": fit.detection_sd,
            "raw_logjoint": fit.raw_logjoint,
            "numerical_status": fit.numerical_status,
            "nfev": fit.nfev,
            "elapsed_seconds": fit.elapsed_seconds,
        }

    return {
        "adjusted_T": pair.T,
        "fits": {name: payload(fit) for name, fit in pair.fits.items()},
    }


def test_parser_requires_mode_and_binding_and_keeps_worker_default() -> None:
    parser = runner.build_parser()
    args = parser.parse_args(
        [
            "fit",
            "--package",
            "qualified",
            "--training-directory",
            "training",
            "--output",
            "analysis",
            "--binding",
            BINDING,
        ]
    )
    assert args.mode == "fit"
    assert args.workers == 16
    with pytest.raises(ValueError, match="64-character"):
        runner._binding("bad")


def test_audit_gate_requires_explicit_passed_receipt(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires"):
        runner._require_audit(None, "effect", binding=BINDING, output=tmp_path)
    failed = tmp_path / "failed.json"
    failed.write_text(json.dumps({"passed": False}), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        runner._require_audit(failed, "effect", binding=BINDING, output=tmp_path)
    passed = tmp_path / "passed.json"
    passed.write_text(json.dumps({"passed": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        runner._require_audit(passed, "effect", binding=BINDING, output=tmp_path)


def test_audit_gate_binds_stage_summary_and_artifacts(tmp_path: Path) -> None:
    stage = tmp_path / "screen"
    stage.mkdir()
    summary = stage / "screen.json"
    summary.write_text(
        json.dumps(
            {
                "schema": runner.ANALYSIS_SCHEMA,
                "mode": "screen",
                "status": "complete",
                "binding_sha256": BINDING,
            }
        ),
        encoding="utf-8",
    )
    receipt = tmp_path / "screen-audit.json"
    receipt.write_text(
        json.dumps(
            {
                "schema": runner.AUDIT_SCHEMA,
                "kind": "screen",
                "passed": True,
                "binding_sha256": BINDING,
                "stage_sha256": runner._sha256(summary),
                "files": {"screen/screen.json": runner._sha256(summary)},
            }
        ),
        encoding="utf-8",
    )
    assert runner._require_audit(
        receipt, "screen", binding=BINDING, output=tmp_path
    )["passed"] is True
    (stage / "progress.json").write_text("{}", encoding="utf-8")
    (stage / "node-0000.sqlite-wal").write_bytes(b"mutable")
    assert runner._require_audit(
        receipt, "screen", binding=BINDING, output=tmp_path
    )["passed"] is True
    summary.write_text(summary.read_text() + "\nchanged", encoding="utf-8")
    with pytest.raises(ValueError, match="stage summary"):
        runner._require_audit(receipt, "screen", binding=BINDING, output=tmp_path)


def test_prerequisite_summary_binding_is_rejected(tmp_path: Path) -> None:
    stage = tmp_path / "fit"
    stage.mkdir()
    (stage / "fit.json").write_text(
        json.dumps(
            {
                "schema": runner.ANALYSIS_SCHEMA,
                "mode": "fit",
                "status": "complete",
                "binding_sha256": "b" * 64,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="binding"):
        runner._load_fit_summary(tmp_path, BINDING)


def test_observed_batch_preserves_main_t_and_invalidates_negative_nesting(tmp_path: Path) -> None:
    pair = _pair(-10.0, -10.000002, adjusted_t=17.0)
    (tmp_path / "fit").mkdir()
    (tmp_path / "fit" / "case.json").write_text(
        json.dumps(_fit_row(pair)), encoding="utf-8"
    )
    summary = {"cases": [{"fit_json": "case.json"}]}
    batch = runner._observed_effect_batch(tmp_path, summary)
    assert pair.T == 17.0
    assert np.isnan(batch.statistics()[0])


def test_observed_batch_decodes_json_null_scores_as_casewise_invalid(tmp_path: Path) -> None:
    pair = _pair(-10.0, -9.0, adjusted_t=12.0)
    payload = _fit_row(pair)
    cast_fit = payload["fits"]
    assert isinstance(cast_fit, dict)
    cast_fit["adjusted_h1"]["raw_logjoint"] = None
    (tmp_path / "fit").mkdir()
    (tmp_path / "fit" / "case.json").write_text(json.dumps(payload), encoding="utf-8")
    batch = runner._observed_effect_batch(
        tmp_path, {"cases": [{"fit_json": "case.json"}]}
    )
    assert np.isnan(batch.statistics()[0])


def test_nonfinite_observed_screen_case_is_preserved_casewise() -> None:
    observed = np.ones((2, calibration.GRID_SIZE))
    observed[1, 10] = np.nan
    contrasts = runner._observed_screen_contrasts(observed)
    assert np.isfinite(contrasts[0]).all()
    assert np.isnan(contrasts[1]).all()
    reference = np.ones((99, calibration.GRID_SIZE))
    screens = calibration.screen_cases(("case-00", "case-01"), contrasts, reference)
    assert screens[0].status in {"ready", "empty"}
    assert screens[1].status == "no_fit"


def test_effect_stage_requires_screen_audit_before_reference_generation(tmp_path: Path) -> None:
    screen = tmp_path / "screen"
    screen.mkdir(parents=True)
    (screen / "screen.json").write_text(
        json.dumps(
            {
                "schema": runner.ANALYSIS_SCHEMA,
                "mode": "screen",
                "status": "complete",
                "binding_sha256": BINDING,
                "required_effect_nodes": [0],
            }
        ),
        encoding="utf-8",
    )
    args = runner.build_parser().parse_args(
        [
            "effect",
            "--package",
            "qualified",
            "--training-directory",
            "training",
            "--output",
            str(tmp_path),
            "--binding",
            BINDING,
        ]
    )
    with pytest.raises(ValueError, match="audit"):
        runner.run_effect(args)
    assert not (tmp_path / "effect").exists()


def test_decision_never_turns_pending_effect_table_into_partial_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fit = tmp_path / "fit"
    screen = tmp_path / "screen"
    effect = tmp_path / "effect"
    fit.mkdir()
    screen.mkdir()
    effect.mkdir()
    (fit / "fit.json").write_text(
        json.dumps(
            {
                "schema": runner.ANALYSIS_SCHEMA,
                "mode": "fit",
                "status": "complete",
                "binding_sha256": BINDING,
                "cases": [],
            }
        ),
        encoding="utf-8",
    )
    (screen / "screen.json").write_text(
        json.dumps(
            {
                "schema": runner.ANALYSIS_SCHEMA,
                "mode": "screen",
                "status": "complete",
                "binding_sha256": BINDING,
                "required_effect_nodes": [0],
                "cases": [],
            }
        ),
        encoding="utf-8",
    )
    (effect / "effect.json").write_text(
        json.dumps(
            {
                "schema": runner.ANALYSIS_SCHEMA,
                "mode": "effect",
                "status": "complete",
                "binding_sha256": BINDING,
                "required_effect_nodes": [0],
            }
        ),
        encoding="utf-8",
    )
    for name, kind in (("screen-audit.json", "screen"), ("effect-audit.json", "effect")):
        artifact = tmp_path / kind / f"{kind}.json"
        (tmp_path / name).write_text(
            json.dumps(
                {
                    "schema": runner.AUDIT_SCHEMA,
                    "kind": kind,
                    "passed": True,
                    "binding_sha256": BINDING,
                    "stage_sha256": runner._sha256(artifact),
                    "files": {str(Path(kind) / artifact.name): runner._sha256(artifact)},
                }
            ),
            encoding="utf-8",
        )
    monkeypatch.setattr(
        runner.references,
        "_metadata",
        lambda *args: {"references": 999},
    )
    monkeypatch.setattr(runner.references, "load_context", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        runner.references,
        "load_effect_batch",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            calibration.CalibrationPendingError("pending")
        ),
    )
    args = runner.build_parser().parse_args(
        [
            "decide",
            "--package",
            "qualified",
            "--training-directory",
            "training",
            "--output",
            str(tmp_path),
            "--binding",
            BINDING,
            "--screen-audit",
            str(tmp_path / "screen-audit.json"),
            "--effect-audit",
            str(tmp_path / "effect-audit.json"),
        ]
    )
    with pytest.raises(calibration.CalibrationPendingError):
        runner.run_decide(args)
    assert not (tmp_path / "decide" / "decide.json").exists()
