from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from latent_landscapes import capstone_public as public_api
from latent_landscapes import capstone_qualification as qualification
from latent_landscapes.misspecification_generator import build_generator_setup

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/audit_capstone_recovery_repair.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("audit_capstone_recovery_repair", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
repair = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = repair
SPEC.loader.exec_module(repair)

MECHANICAL_ROOT = 987654321


class ReachedUnchangedPanelAudit(RuntimeError):
    """Sentinel raised only after the unchanged completion gate passes."""


@pytest.fixture(scope="module")
def public() -> public_api.PublicInputs:
    fixed = public_api._make_fixed(
        public_api._u64_seed(MECHANICAL_ROOT, public_api.MAP_STAGE, 0),
        public_api._u64_seed(MECHANICAL_ROOT, public_api.SAMPLING_STAGE, 0),
    )
    return public_api.PublicInputs(
        fixed, build_generator_setup(fixed), {"root": MECHANICAL_ROOT}
    )


def _write_bank(
    directory: Path, public: public_api.PublicInputs
) -> tuple[np.ndarray[Any, Any], dict[str, Any], dict[str, Any]]:
    directory.mkdir()
    arrivals = np.zeros((32, len(public.setup.site_ids)), dtype=np.float64)
    np.save(directory / "arrivals.npy", arrivals)
    seeds = np.asarray(
        [
            public_api._u64_seed(MECHANICAL_ROOT, public_api.BANK_STAGE, index)
            for index in range(len(arrivals))
        ],
        dtype=np.uint64,
    )
    np.savez_compressed(
        directory / "seed_ledger.npz",
        seeds=seeds,
        root=np.asarray(MECHANICAL_ROOT, dtype=np.int64),
        namespace=np.asarray(public_api.NAMESPACE, dtype=np.int64),
        stage=np.asarray(public_api.BANK_STAGE, dtype=np.int64),
    )
    np.savez_compressed(
        directory / "chunk-00000000.npz",
        offset=np.asarray(0, dtype=np.int64),
        seeds=seeds,
        arrivals=arrivals,
    )
    started = {
        "schema_version": "goal059-arrival-bank-start-v1",
        "root": MECHANICAL_ROOT,
        "namespace": public_api.NAMESPACE,
        "stage": public_api.BANK_STAGE,
        "bank_size": len(arrivals),
        "site_ids": list(public.setup.site_ids),
        "public_input_array_sha256": public_api._array_hashes(public.fixed),
        "map_a_sha256": qualification._array_sha(public.setup.exposure_score),
        "ledger_sha256": qualification._array_sha(seeds),
        "ledger_file_sha256": qualification._sha(directory / "seed_ledger.npz"),
    }
    (directory / "started.json").write_text(
        json.dumps(started, sort_keys=True), encoding="utf-8"
    )
    chunk_path = directory / "chunk-00000000.npz"
    manifest = {
        "schema_version": "goal059-arrival-bank-v1",
        "root": MECHANICAL_ROOT,
        "namespace": public_api.NAMESPACE,
        "stage": public_api.BANK_STAGE,
        "array_shape": list(arrivals.shape),
        "bank_size": len(arrivals),
        "site_ids": list(public.setup.site_ids),
        "array_sha256": qualification._array_sha(arrivals),
        "arrivals_file_sha256": qualification._sha(directory / "arrivals.npy"),
        "started_receipt_sha256": qualification._sha(directory / "started.json"),
        "ledger_sha256": qualification._array_sha(seeds),
        "ledger_file_sha256": qualification._sha(directory / "seed_ledger.npz"),
        "public_input_array_sha256": public_api._array_hashes(public.fixed),
        "map_a_sha256": qualification._array_sha(public.setup.exposure_score),
        "chunks": [
            {
                "offset": 0,
                "rows": len(arrivals),
                "seed_sha256": qualification._array_sha(seeds),
                "chunk_sha256": qualification._array_sha(arrivals),
                "file_sha256": qualification._sha(chunk_path),
            }
        ],
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )
    producer_manifest = qualification.validate_bank_manifest(
        public, directory, expected_bank_size=len(arrivals)
    )
    raw, bank_result = repair.base.audit_arrival_bank(
        directory,
        public.setup.site_ids,
        expected_size=len(arrivals),
        expected_root=MECHANICAL_ROOT,
    )
    assert np.array_equal(raw, arrivals)
    return arrivals, producer_manifest, bank_result


def _write_completed(
    directory: Path,
    arrivals: np.ndarray[Any, Any],
    producer_manifest: dict[str, Any],
) -> dict[str, str]:
    directory.mkdir()
    panel_bindings = {
        "observations_sha256": "1" * 64,
        "evaluator_sha256": "2" * 64,
        "manifest_sha256": "3" * 64,
    }
    completed = {
        "schema_version": "goal059-public-panel-v1",
        "status": "completed",
        "histories": 8,
        "representations": ["full", "first_half", "second_half"],
        "bank_manifest": producer_manifest,
        "raw_arrivals_sha256": repair.base.array_sha256(arrivals),
        "observations_sha256": panel_bindings["observations_sha256"],
        "evaluator_sha256": panel_bindings["evaluator_sha256"],
        "panel_manifest_sha256": panel_bindings["manifest_sha256"],
    }
    repair.base.write_json(directory / "completed.json", completed)
    return panel_bindings


def _stop_after_completion_gate(*args: Any, **kwargs: Any) -> None:
    raise ReachedUnchangedPanelAudit


def test_repair_recreates_producer_manifest_and_reaches_unchanged_gate(
    public: public_api.PublicInputs,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bank = tmp_path / "bank"
    arrivals, producer_manifest, bank_result = _write_bank(bank, public)
    results = tmp_path / "results"
    panel_bindings = _write_completed(results, arrivals, producer_manifest)
    raw_manifest = repair.recovery.read_json(bank / "manifest.json")

    assert "manifest_sha256" not in raw_manifest
    assert producer_manifest == {
        **raw_manifest,
        "manifest_sha256": repair.recovery.sha256_file(bank / "manifest.json"),
    }
    assert repair.audited_panel_bank_manifest(bank, bank_result) == producer_manifest

    monkeypatch.setattr(
        repair.base, "make_direct_bank", _stop_after_completion_gate
    )
    with pytest.raises(ReachedUnchangedPanelAudit):
        repair.audit_panel_results_repaired(
            results,
            arrivals,
            SimpleNamespace(site_ids=tuple(public.setup.site_ids)),
            np.empty((0,), dtype=np.int8),
            np.empty((0,), dtype=np.int8),
            (),
            bank_directory=bank,
            bank_result=bank_result,
            panel_bindings=panel_bindings,
        )


@pytest.mark.parametrize(
    "bank_result",
    (
        {"passed": True},
        {"passed": True, "manifest_sha256": "0" * 64},
        {"passed": False, "manifest_sha256": "0" * 64},
    ),
)
def test_repair_rejects_missing_or_wrong_independent_hash(
    public: public_api.PublicInputs,
    tmp_path: Path,
    bank_result: dict[str, Any],
) -> None:
    bank = tmp_path / "bank"
    _write_bank(bank, public)
    with pytest.raises(ValueError, match="file hash binding failed"):
        repair.audited_panel_bank_manifest(bank, bank_result)


def test_repair_rejects_bank_manifest_file_tampering(
    public: public_api.PublicInputs, tmp_path: Path
) -> None:
    bank = tmp_path / "bank"
    _, _, bank_result = _write_bank(bank, public)
    path = bank / "manifest.json"
    manifest = repair.recovery.read_json(path)
    manifest["bank_size"] = 33
    repair.base.write_json(path, manifest)
    with pytest.raises(ValueError, match="file hash binding failed"):
        repair.audited_panel_bank_manifest(bank, bank_result)


def test_unchanged_gate_rejects_substantive_completed_manifest_tampering(
    public: public_api.PublicInputs,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bank = tmp_path / "bank"
    arrivals, producer_manifest, bank_result = _write_bank(bank, public)
    results = tmp_path / "results"
    panel_bindings = _write_completed(results, arrivals, producer_manifest)
    completed_path = results / "completed.json"
    completed = repair.recovery.read_json(completed_path)
    completed["bank_manifest"]["bank_size"] = 33
    repair.base.write_json(completed_path, completed)

    monkeypatch.setattr(
        repair.base, "make_direct_bank", _stop_after_completion_gate
    )
    with pytest.raises(ValueError, match="panel completion provenance bindings"):
        repair.audit_panel_results_repaired(
            results,
            arrivals,
            SimpleNamespace(site_ids=tuple(public.setup.site_ids)),
            np.empty((0,), dtype=np.int8),
            np.empty((0,), dtype=np.int8),
            (),
            bank_directory=bank,
            bank_result=bank_result,
            panel_bindings=panel_bindings,
        )


def test_original_failed_audit_binding_is_exact(tmp_path: Path) -> None:
    original = REPO / "artifacts/goal060_execution/independent-audit/audit.json"
    result = repair.audit_original_failure(original)
    assert result["passed"] is True
    assert result["audit_sha256"] == repair.ORIGINAL_FAILED_AUDIT_SHA256

    changed = tmp_path / "audit.json"
    receipt = repair.recovery.read_json(original)
    receipt["error"] = "different failure"
    repair.base.write_json(changed, receipt)
    with pytest.raises(ValueError, match="failed-audit binding mismatch"):
        repair.audit_original_failure(changed)


def test_repair_receipt_keeps_common_audit_schema(tmp_path: Path) -> None:
    original = REPO / "artifacts/goal060_execution/independent-audit/audit.json"
    output = tmp_path / "repair-audit"
    missing = tmp_path / "missing"
    argv = ["--original-failed-audit", str(original)]
    for option in (
        "--original-public-inputs",
        "--public-inputs",
        "--predecessor-audit",
        "--predecessor-source-freeze",
        "--predecessor-registration",
        "--source-freeze",
        "--runtime",
        "--registration",
        "--bank",
        "--qualification",
        "--panel",
        "--panel-results",
        "--calibration-fixture",
        "--confirmatory-addresses",
    ):
        argv.extend((option, str(missing)))
    argv.extend(("--output", str(output)))

    with pytest.raises(FileNotFoundError):
        repair.main(argv)
    receipt = repair.recovery.read_json(output / "audit.json")
    assert receipt["schema_version"] == repair.AUDIT_SCHEMA
    assert receipt["repair"]["schema_version"] == repair.REPAIR_SCHEMA
    assert receipt["repair"]["original_failure"]["audit_sha256"] == (
        repair.ORIGINAL_FAILED_AUDIT_SHA256
    )
