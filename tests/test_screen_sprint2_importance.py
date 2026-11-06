from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def screen(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("screen_sprint2_importance")


def parent_args(screen, tmp_path, monkeypatch, failure="resolved"):
    monkeypatch.setattr(screen, "load_panel_data", lambda args: (None, {}))
    source = {"commit": "a" * 40, "working_tree_changes": []}
    monkeypatch.setattr(screen.adapter, "_git_identity", lambda root: source)
    search = tmp_path / "search.json"
    search.write_text("{}")
    receipt = tmp_path / "fit.json"
    receipt.write_text(
        json.dumps(
            {
                "schema": "fit-dataset-v1",
                "failure_class": failure,
                "input_sha256": {},
                "inputs": {},
                "data_identity": {},
                "source": source,
                "search": {
                    "receipt": str(search),
                    "receipt_sha256": screen.adapter.sha256_file(search),
                },
            }
        )
    )
    return SimpleNamespace(receipt=receipt, identity="q-case", output_dir=tmp_path / "screen")


def test_integration_preserves_scientific_parent_failure(screen, tmp_path, monkeypatch):
    args = parent_args(screen, tmp_path, monkeypatch, "family_fit_failed")
    result = screen.run(args)
    assert result["status"] == "unavailable_scientific_fit"
    assert result["history"] == []
    assert result["fit_receipt_sha256"] == screen.adapter.sha256_file(args.receipt)


def test_integration_does_not_complete_parent_execution_error(screen, tmp_path, monkeypatch):
    args = parent_args(screen, tmp_path, monkeypatch, "execution_error")
    with pytest.raises(OSError, match="execution error"):
        screen.run(args)
    assert not (args.output_dir / "receipt.json").exists()


@pytest.mark.parametrize("error_type", [MemoryError, OSError, RuntimeError])
def test_screen_separates_execution_and_scientific_unavailability(
    screen, tmp_path, monkeypatch, error_type
):
    args = parent_args(screen, tmp_path, monkeypatch)

    def fail(search):
        raise error_type("target unavailable")

    monkeypatch.setattr(screen, "selected_fits", fail)
    if error_type is RuntimeError:
        result = screen.run(args)
        assert result["status"] == "unavailable"
        assert "target unavailable" in result["reason"]
    else:
        with pytest.raises(error_type):
            screen.run(args)
        assert not (args.output_dir / "receipt.json").exists()


@pytest.mark.parametrize("root_present", [False, True])
def test_screen_runs_two_streams_and_retains_cap_indeterminacy(
    screen, tmp_path, monkeypatch, root_present
):
    args = parent_args(screen, tmp_path, monkeypatch)
    fit = {
        "positive_sigma": {"h": 3.0, "criterion": -1.0},
        "sigma_zero": {"h": 3.0, "criterion": -2.0},
    }
    monkeypatch.setattr(
        screen,
        "selected_fits",
        lambda search: {"free": fit, **({"root-0": fit} if root_present else {})},
    )
    monkeypatch.setattr(screen, "load_panel_data", lambda args: (None, {}))
    monkeypatch.setattr(screen, "coordinates", lambda row: None)
    criterion = SimpleNamespace(
        evaluate_sigma_zero=lambda *args, **kwargs: SimpleNamespace(success=True, criterion=-2.0)
    )
    monkeypatch.setattr(screen, "direct_criterion", lambda data: criterion)
    target = SimpleNamespace(proposal=None, mode_diagnostics={})
    monkeypatch.setattr(screen, "prepare_target", lambda *args, **kwargs: target)
    calls = []

    def integrate(*args, **kwargs):
        calls.append((kwargs["stream"], kwargs["draws"]))
        return SimpleNamespace(summary=lambda: {"draws": kwargs["draws"]})

    monkeypatch.setattr(screen, "integrate", integrate)
    monkeypatch.setattr(screen, "summarize", lambda estimates, fits: {})
    monkeypatch.setattr(screen, "stable_comparison", lambda left, right: False)
    monkeypatch.setattr(screen, "decision", lambda *args: "indeterminate")
    result = screen.run(args)
    assert result["status"] == ("indeterminate" if root_present else "no_root_contrasts")
    levels = (16384, 32768, 65536, 131072, 262144) if root_present else (16384,)
    assert calls == [
        (stream, draws)
        for draws in levels
        for stream in (0, 1)
        for _ in range(2 if root_present else 1)
    ]
    assert len(result["history"]) == len(levels)
    assert result["reoptimised_profile"] is False
    assert result["optimized_root_movement_quantified"] is False


@pytest.mark.parametrize(
    "bad_source",
    [
        {"commit": None, "working_tree_changes": []},
        {"commit": "a" * 40, "working_tree_changes": ["modified"]},
    ],
)
def test_screen_requires_clean_committed_source(screen, tmp_path, monkeypatch, bad_source):
    args = parent_args(screen, tmp_path, monkeypatch)
    parent = json.loads(args.receipt.read_text())
    parent["source"] = bad_source
    args.receipt.write_text(json.dumps(parent))
    monkeypatch.setattr(screen.adapter, "_git_identity", lambda root: bad_source)
    with pytest.raises(ValueError, match="clean committed"):
        screen.run(args)


def test_screen_rejects_loaded_identity_drift(screen, tmp_path, monkeypatch):
    args = parent_args(screen, tmp_path, monkeypatch)
    monkeypatch.setattr(screen, "load_panel_data", lambda args: (None, {"changed": True}))
    with pytest.raises(ValueError, match="data identity"):
        screen.run(args)
    assert not (args.output_dir / "receipt.json").exists()
