from __future__ import annotations

import copy
import importlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

spec = importlib.util.spec_from_file_location(
    "resume_fixture_helpers", Path(__file__).with_name("test_fit_dataset.py")
)
assert spec and spec.loader
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
fake_search = helpers.fake_search


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Any]:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    fit = importlib.import_module("fit_dataset")
    monkeypatch.setattr(fit, "_resume_search_class", fit.FitSearch, raising=False)
    return fit, importlib.import_module("fit_checkpoints")


def harness(
    modules: tuple[Any, Any],
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    *,
    fail_call: int | None = None,
) -> tuple[Any, Any, list[int]]:
    fit, checkpoint = modules
    calls = [0]
    monkeypatch.setattr(fit.adapter, "_candidate_summary", lambda row, **kw: dict(row))
    monkeypatch.setattr(
        fit.adapter, "_git_identity", lambda root: {"commit": "frozen", "working_tree_changes": []}
    )
    monkeypatch.setattr(fit, "input_hashes", lambda args: {"fixture": "same-input-sha"})
    monkeypatch.setattr(fit, "load_panel_data", lambda args: (object(), {"sites": "same"}))

    helper_fit = SimpleNamespace(**vars(fit))
    helper_fit.FitSearch = fit._resume_search_class

    def make_search(data: Any, mode: str, directory: Path) -> Any:
        result = fake_search(helper_fit, directory)
        original = result.criterion._fit_family

        def solve(**kw: Any) -> Any:
            calls[0] += 1
            if fail_call == calls[0]:
                raise SystemExit("simulated node loss inside search")
            return original(**kw)

        result.criterion._fit_family = solve
        return result

    monkeypatch.setattr(fit, "FitSearch", make_search)

    class Reduced:
        def __init__(self, name: str, criterion: Any, **kwargs: Any):
            self.name, self.points, self.fit_count = name, {}, 3

        def run(self, nodes: Any, cutoffs: Any) -> list[Any]:
            return []

        def result(self, levels: Any) -> dict[str, Any]:
            return {"status": "available", "fit_count": 3, "profile": [], "family": self.name}

    monkeypatch.setattr(fit, "ReducedFamily", Reduced)
    monkeypatch.setattr(
        fit,
        "audit_all",
        lambda *args, **kw: {
            "multimodal_latent": False,
            "wall_seconds": 0.0,
            "cpu_seconds": 0.0,
            "rows": [{"criterion": 1.25, "seconds": 0.0}],
        },
    )
    return fit, checkpoint, calls


def arguments(root: Path, label: str, *, resume: bool = False) -> Any:
    output = root / label
    output.mkdir()
    return SimpleNamespace(
        input_dir=root / "input",
        observations=root / "observations.npz",
        arrival_bank=root / "arrivals.npy",
        compressed_bank=root / "compressed.npz",
        output_dir=output,
        search="lean",
        exhaustive_audit=False,
        checkpoint_dir=root / "checkpoint",
        resume=resume,
    )


def equivalent(checkpoint: Any, left: dict[str, Any], right: dict[str, Any]) -> None:
    assert checkpoint.digest(checkpoint.scientific_payload(left)) == checkpoint.digest(
        checkpoint.scientific_payload(right)
    )
    lp, rp = [Path(row["search"]["receipt"]) for row in (left, right)]
    ls, rs = [json.loads(p.read_text()) for p in (lp, rp)]
    assert checkpoint.digest(
        checkpoint.scientific_payload(ls, artifact="search")
    ) == checkpoint.digest(checkpoint.scientific_payload(rs, artifact="search"))
    events = [
        [json.loads(line) for line in Path(s["evaluation_stream"]["path"]).read_text().splitlines()]
        for s in (ls, rs)
    ]
    assert checkpoint.digest(
        checkpoint.scientific_payload(events[0], artifact="events")
    ) == checkpoint.digest(checkpoint.scientific_payload(events[1], artifact="events"))


def test_resume_inside_search_replays_order_and_warm_state(
    modules: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    fit, checkpoint, full_calls = harness(modules, monkeypatch, tmp_path)
    baseline_args = arguments(tmp_path, "baseline-output")
    baseline = fit.fit_dataset(baseline_args)
    assert baseline["failure_class"] == "resolved"
    spatial = baseline["families"]["spatial"]
    for regime in ("standard", "tight"):
        assert "positive_sigma_closed" in spatial[regime]["free"]
        assert "positive_sigma_closed" in spatial[regime]["null"]
        assert all("positive_sigma_closed" in row for row in spatial[regime]["profile"])
    checkpoint_dir = tmp_path / "checkpoint"
    checkpoint_dir.rename(tmp_path / "baseline-checkpoint")
    fit, checkpoint, interrupted_calls = harness(modules, monkeypatch, tmp_path, fail_call=8)
    interrupted_args = arguments(tmp_path, "interrupted")
    with pytest.raises(SystemExit):
        fit.fit_dataset(interrupted_args)
    assert not (interrupted_args.output_dir / "receipt.json").exists()
    assert list(checkpoint_dir.glob("search/operation-*.json"))
    fit, checkpoint, remaining_calls = harness(modules, monkeypatch, tmp_path)
    resumed = fit.fit_dataset(arguments(tmp_path, "resumed", resume=True))
    assert remaining_calls[0] < full_calls[0]
    assert remaining_calls[0] + interrupted_calls[0] >= full_calls[0]
    equivalent(checkpoint, baseline, resumed)


@pytest.mark.parametrize(
    "boundary",
    [
        "search",
        "spatial_report",
        "family_exposure",
        "family_constant",
        "latent_audit",
        "envelope_guard_report",
        "fit_receipt",
    ],
)
def test_resume_at_every_stage_boundary(
    modules: Any, monkeypatch: Any, tmp_path: Path, boundary: str
) -> None:
    fit, checkpoint, _ = harness(modules, monkeypatch, tmp_path)
    baseline = fit.fit_dataset(arguments(tmp_path, "baseline-output"))
    (tmp_path / "checkpoint").rename(tmp_path / "baseline-checkpoint")
    original_save = checkpoint.FitCheckpoints.save

    def save(self: Any, name: str, payload: Any) -> None:
        original_save(self, name, payload)
        if name == "stages/" + boundary:
            raise SystemExit("simulated segment end after durable stage")

    monkeypatch.setattr(checkpoint.FitCheckpoints, "save", save)
    with pytest.raises(SystemExit):
        fit.fit_dataset(arguments(tmp_path, "interrupted"))
    monkeypatch.setattr(checkpoint.FitCheckpoints, "save", original_save)
    resumed = fit.fit_dataset(arguments(tmp_path, "resumed", resume=True))
    equivalent(checkpoint, baseline, resumed)


@pytest.mark.parametrize("change", ["source", "input", "runtime"])
def test_resume_rejects_changed_identity(
    modules: Any, monkeypatch: Any, tmp_path: Path, change: str
) -> None:
    fit, checkpoint, _ = harness(modules, monkeypatch, tmp_path)
    fit.fit_dataset(arguments(tmp_path, "first"))
    if change == "source":
        monkeypatch.setattr(fit.adapter, "_git_identity", lambda root: {"commit": "changed"})
    elif change == "input":
        monkeypatch.setattr(fit, "input_hashes", lambda args: {"fixture": "changed"})
    else:
        monkeypatch.setenv("LL_RUNTIME_SIF_SHA256", "changed")
    with pytest.raises(checkpoint.CheckpointError, match="differs"):
        fit.fit_dataset(arguments(tmp_path, "resumed", resume=True))


@pytest.mark.parametrize("damage", ["hash", "gap", "order"])
def test_resume_rejects_corrupt_search_journal(
    modules: Any, monkeypatch: Any, tmp_path: Path, damage: str
) -> None:
    fit, checkpoint, _ = harness(modules, monkeypatch, tmp_path, fail_call=9)
    with pytest.raises(SystemExit):
        fit.fit_dataset(arguments(tmp_path, "first"))
    path = tmp_path / "checkpoint/search/operation-000001.json"
    saved = json.loads(path.read_text())
    if damage == "gap":
        path.unlink()
    elif damage == "hash":
        saved["payload"]["fit"]["criterion"] += 1.0
        path.write_text(json.dumps(saved))
    else:
        saved["payload"]["operation_index"] = 999
        saved["payload_sha256"] = checkpoint.digest(saved["payload"])
        path.write_text(json.dumps(saved))
    fit, checkpoint, calls = harness(modules, monkeypatch, tmp_path)
    with pytest.raises(checkpoint.CheckpointError):
        fit.fit_dataset(arguments(tmp_path, "resumed", resume=True))
    assert calls[0] == 0


def test_normalization_does_not_hide_scientific_changes(modules: Any) -> None:
    _, checkpoint = modules
    original = {
        "cost": {
            "total_wall_seconds": 1,
            "criterion_stats": {
                "mode_failures": 0,
                "pd_failures": 0,
                "mode_branch_termination_converged": 8,
            },
        },
        "families": {
            "positive": {
                "criterion": 5,
                "iterations": 7,
                "evaluations": 10,
                "eligible": True,
                "input_sha256": "data",
            }
        },
    }
    assert checkpoint.scientific_payload(original)["families"] == original["families"]
    for field, value in [
        ("criterion", 6),
        ("iterations", 8),
        ("evaluations", 11),
        ("eligible", False),
        ("input_sha256", "different"),
    ]:
        changed = copy.deepcopy(original)
        changed["families"]["positive"][field] = value
        assert checkpoint.digest(checkpoint.scientific_payload(original)) != checkpoint.digest(
            checkpoint.scientific_payload(changed)
        )


@pytest.mark.parametrize(
    "field", ["mode_failures", "pd_failures", "mode_branch_termination_converged"]
)
def test_normalization_preserves_scientific_failure_counters(modules: Any, field: str) -> None:
    _, checkpoint = modules
    left = {"cost": {"criterion_stats": {field: 0}}}
    right = {"cost": {"criterion_stats": {field: 1}}}
    assert checkpoint.digest(checkpoint.scientific_payload(left)) != checkpoint.digest(
        checkpoint.scientific_payload(right)
    )


@pytest.mark.parametrize("damage", ["identity", "origin", "partial_identity"])
def test_resume_rejects_damaged_identity_header(
    modules: Any, monkeypatch: Any, tmp_path: Path, damage: str
) -> None:
    fit, checkpoint, _ = harness(modules, monkeypatch, tmp_path)
    fit.fit_dataset(arguments(tmp_path, "first"))
    header = tmp_path / "checkpoint/identity.json"
    value = json.loads(header.read_text())
    if damage == "identity":
        value["identity"]["search_mode"] = "dense"
        header.write_text(json.dumps(value))
    elif damage == "origin":
        value["origin"]["host"] = "changed"
        header.write_text(json.dumps(value))
    else:
        header.unlink()
        header.with_suffix(".json.tmp").write_text('{"unfinished":')
    with pytest.raises(checkpoint.CheckpointError):
        fit.fit_dataset(arguments(tmp_path, "resumed", resume=True))


def test_real_solver_operations_resume_with_identical_candidates_and_failure_counts(
    modules: Any, tmp_path: Path
) -> None:
    fit, checkpoint = modules

    def make(label: str, *, resume: bool) -> Any:
        directory = tmp_path / label
        directory.mkdir()
        q = fake_search(fit, directory)
        q.criterion = helpers.small_criterion(sites=3, h_penalty=True)
        store = checkpoint.FitCheckpoints(
            tmp_path / "checkpoint", {"real_solver_fixture": 1}, resume=resume
        )
        q.enable_checkpoints(store)
        return q

    def sequence(q: Any) -> None:
        q.point(0.0, direction="up")
        q.point(1.0, direction="up")
        q.point(0.0, refresh=True, direction="down")
        q.fit_free()
        q.point(2.0, tight=True)
        q.fit_free(tight=True)

    baseline = make("baseline", resume=False)
    sequence(baseline)
    (tmp_path / "checkpoint").rename(tmp_path / "baseline-checkpoint")
    interrupted = make("interrupted", resume=False)
    interrupted.point(0.0, direction="up")
    original = interrupted.criterion._fit_family
    calls = [0]

    def stop_inside_operation(**kwargs: Any) -> Any:
        calls[0] += 1
        if calls[0] == 2:
            raise SystemExit("simulated kill after partial real numerical operation")
        return original(**kwargs)

    interrupted.criterion._fit_family = stop_inside_operation
    with pytest.raises(SystemExit):
        interrupted.point(1.0, direction="up")
    resumed = make("resumed", resume=True)
    sequence(resumed)
    for name in ("points", "free", "directional"):
        assert checkpoint.digest(getattr(baseline, name)) == checkpoint.digest(
            getattr(resumed, name)
        )
    assert checkpoint.digest(
        checkpoint.scientific_payload(baseline.receipt(), artifact="search")
    ) == checkpoint.digest(checkpoint.scientific_payload(resumed.receipt(), artifact="search"))
    for key in (
        "mode_failures",
        "pd_failures",
        "mode_branch_termination_converged",
        "mode_branch_calls",
        "mode_invalid_trial_rejections",
    ):
        assert baseline.criterion.stats.get(key, 0) == resumed.criterion.stats.get(key, 0)


@pytest.mark.parametrize("damage", ["raw_stage", "nested_stream"])
def test_stage_and_nested_stream_corruption_are_not_normalized_away(
    modules: Any, monkeypatch: Any, tmp_path: Path, damage: str
) -> None:
    fit, checkpoint, _ = harness(modules, monkeypatch, tmp_path)
    fit.fit_dataset(arguments(tmp_path, "first"))
    path = tmp_path / "checkpoint/stages/search.json"
    saved = json.loads(path.read_text())
    if damage == "raw_stage":
        saved["payload"]["state"]["result"]["status"] = "tampered"
    else:
        saved["payload"]["search_receipt"]["evaluation_stream"]["sha256"] = "tampered"
        saved["payload_sha256"] = checkpoint.digest(saved["payload"])
    path.write_text(json.dumps(saved))
    with pytest.raises(checkpoint.CheckpointError):
        fit.fit_dataset(arguments(tmp_path, "resumed", resume=True))


def test_resumed_host_is_actual_and_origin_is_explicit(
    modules: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    fit, checkpoint, _ = harness(modules, monkeypatch, tmp_path)
    monkeypatch.setattr(fit.platform, "node", lambda: "first-node")
    baseline = fit.fit_dataset(arguments(tmp_path, "first"))
    monkeypatch.setattr(fit.platform, "node", lambda: "resume-node")
    resumed = fit.fit_dataset(arguments(tmp_path, "resumed", resume=True))
    assert resumed["host"] == "resume-node"
    assert resumed["checkpoint_origin_host"] == "first-node"
    equivalent(checkpoint, baseline, resumed)
