from __future__ import annotations

import importlib.util
import json
import math
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from latent_landscapes import capstone_calibration as production_calibration
from latent_landscapes import capstone_recovery as production

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/audit_capstone_recovery.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("audit_capstone_recovery", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)

ORIGINAL = REPO / "artifacts/goal059_execution/public_inputs"
PREDECESSOR = REPO / "artifacts/goal059_execution"
REGISTRATION = REPO / "docs/goals/060-capstone-certificate-recovery/registration-2026-10-04.md"


def _run_recovery(output: Path) -> None:
    production.recover_public_inputs(
        ORIGINAL,
        output,
        predecessor_audit=PREDECESSOR / "map-audit/audit.json",
        predecessor_source=PREDECESSOR / "source-manifest.json",
        predecessor_registration=(
            REPO / "docs/goals/059-capstone-preparation/registration-2026-10-04.md"
        ),
        registration=REGISTRATION,
    )


def _audit_recovery(output: Path) -> Any:
    return audit.audit_recovery_inputs(
        ORIGINAL,
        output,
        predecessor_audit=PREDECESSOR / "map-audit/audit.json",
        predecessor_source=PREDECESSOR / "source-manifest.json",
        predecessor_registration=(
            REPO / "docs/goals/059-capstone-preparation/registration-2026-10-04.md"
        ),
        registration=REGISTRATION,
    )


def test_independent_certificate_matches_production_and_covers_box() -> None:
    map_a = np.linspace(-2.75, 3.25, 6 * 7, dtype=np.float64).reshape(6, 7)
    site_a = map_a.ravel()[np.asarray([0, 3, 17, 30, 41])]
    certificate, diagnostics = audit.certificate_1024(map_a, site_a)

    assert certificate == production.fixed_hazard_certificate(map_a, site_a)
    assert certificate["interval_count"] == 1_024
    assert certificate["beta_interval"] == [-2.0, 2.0]
    assert diagnostics["coverage"] == [-2.0, 2.0]
    assert diagnostics["edge_count"] == 1_025
    assert diagnostics["outward_guard_strict"] is True
    assert diagnostics["midpoint_minimum_bound_slack"] >= 0.0

    for beta in np.linspace(-2.0, 2.0, 257):
        hazards = 0.006 * np.exp(beta * site_a) / np.exp(beta * map_a).mean()
        assert float(np.max(hazards)) < certificate["site_hazard_upper"]


def test_frozen_array_certificate_matches_production_exactly() -> None:
    with np.load(ORIGINAL / "exposure.npz", allow_pickle=False) as exposure:
        map_a = np.asarray(exposure["map_a"], dtype=np.float64)
        site_a = np.asarray(exposure["site_a"], dtype=np.float64)
    certificate, _ = audit.certificate_1024(map_a, site_a)
    assert certificate == production.fixed_hazard_certificate(map_a, site_a)
    assert certificate["transform_x_upper"] == 4.928543927785195


def test_independent_certificate_rejects_and_validates_inputs() -> None:
    result = audit.mechanical_rejection_fixture()
    assert result["passed"] is True
    assert result["certificate"]["passes"] is False
    assert result["certificate"]["transform_x_upper"] > 5.0

    with pytest.raises(ValueError, match="invalid recovery hazard box"):
        audit.certificate_1024(np.asarray([]), np.asarray([0.0]))
    with pytest.raises(ValueError, match="invalid recovery hazard box"):
        audit.certificate_1024(np.asarray([0.0]), np.asarray([math.nan]))
    with pytest.raises(ValueError, match="invalid recovery hazard box"):
        audit.certificate_1024(np.asarray([0.0]), np.asarray([0.0]), intervals=0)
    with pytest.raises(ValueError, match="invalid recovery hazard box"):
        audit.certificate_1024(
            np.asarray([0.0]), np.asarray([0.0]), max_mu=math.inf
        )


def test_confirmatory_address_contract_is_exact_and_source_bound(tmp_path: Path) -> None:
    source = tmp_path / "source-manifest.json"
    runtime = tmp_path / "runtime.json"
    registration = tmp_path / "registration.md"
    source.write_text('{"source": true}\n', encoding="utf-8")
    runtime.write_text('{"runtime": true}\n', encoding="utf-8")
    registration.write_text("registered\n", encoding="utf-8")
    expected = audit.expected_confirmatory_contract(
        source_manifest=source,
        runtime=runtime,
        registration=registration,
    )
    production_contract = production_calibration.address_contract()
    production_contract.update(
        source_manifest_sha256=audit.sha256_file(source),
        runtime_sha256=audit.sha256_file(runtime),
        registration_sha256=audit.sha256_file(registration),
    )
    assert json.loads(json.dumps(production_contract)) == expected
    path = tmp_path / "confirmatory-addresses.json"
    audit.base.write_json(path, expected)

    result = audit.audit_confirmatory_addresses(
        path,
        source_manifest=source,
        runtime=runtime,
        registration=registration,
    )
    assert result["passed"] is True
    assert result["root"] == 2026100404
    assert result["screen_histories"] == 765 * 99
    assert result["maximum_effect_histories"] == 765 * 999

    expected["root"] = 2026100405
    audit.base.write_json(path, expected)
    with pytest.raises(ValueError, match="address contract mismatch"):
        audit.audit_confirmatory_addresses(
            path,
            source_manifest=source,
            runtime=runtime,
            registration=registration,
        )


def test_registered_calibration_fixture_identity_and_root() -> None:
    result = audit.audit_registered_calibration_fixture(
        PREDECESSOR / "calibration-fixture"
    )
    assert result["passed"] is True
    assert result["required_root"] == 987654321
    assert result["registered_fixture_hashes"] == (
        audit.GOAL059_CALIBRATION_FIXTURE_HASHES
    )


@pytest.mark.skipif(platform.system() != "Linux", reason="exact frozen Linux exposure replay")
def test_registered_recovery_audit_and_metadata_tamper_rejection(tmp_path: Path) -> None:
    output = tmp_path / "recovered"
    _run_recovery(output)

    _, _, _, result = _audit_recovery(output)
    assert result["passed"] is True
    assert result["certificate"]["interval_count"] == 1_024
    assert result["certificate"]["passes"] is True
    assert result["checks"]["preserved_bytes"] is True
    assert result["checks"]["predecessor_negative"] is True
    assert result["checks"]["goal60_binding_present"] is True

    metadata_path = output / "public_inputs.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["qualification_goal"] = 61
    audit.base.write_json(metadata_path, metadata)
    receipt_path = output / "recovery.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["outputs_sha256"]["public_inputs.json"] = audit.sha256_file(metadata_path)
    audit.base.write_json(receipt_path, receipt)

    with pytest.raises(ValueError, match="goal60_binding_present"):
        _audit_recovery(output)
