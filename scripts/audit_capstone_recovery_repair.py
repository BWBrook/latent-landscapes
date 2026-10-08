#!/usr/bin/env python3
"""Run the bounded Goal 060 audit-interface repair.

This adapter preserves the original Goal 060 recovery and Goal 059 independent
audit logic.  Its only integration change reconstructs the producer's validated
bank-manifest object by attaching the independently audited file hash before
calling the unchanged panel-result audit.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import audit_capstone_public as base
import audit_capstone_recovery as recovery
import numpy as np
from numpy.typing import NDArray

ORIGINAL_FAILED_AUDIT_SHA256 = (
    "21cfa9c56e29d95b40524c8e5e6afbeba8c2dceef264f3494b1ddf99c5836132"
)
AUDIT_SCHEMA = "goal060-independent-public-audit-v1"
REPAIR_SCHEMA = "goal060-independent-public-audit-repair-v1"


def audit_original_failure(path: Path) -> dict[str, Any]:
    """Bind the repair to the preserved, known audit-interface failure."""
    receipt = recovery.read_json(path)
    checks = {
        "sha256": recovery.sha256_file(path) == ORIGINAL_FAILED_AUDIT_SHA256,
        "schema": receipt.get("schema_version") == AUDIT_SCHEMA,
        "status": receipt.get("status") == "failed",
        "audit_passed": receipt.get("audit_passed") is False,
        "error_type": receipt.get("error_type") == "ValueError",
        "error": receipt.get("error")
        == "panel completion provenance bindings are invalid",
    }
    if not all(checks.values()):
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise ValueError(f"original Goal 060 failed-audit binding mismatch: {failed}")
    return {
        "passed": True,
        "checks": checks,
        "audit_sha256": recovery.sha256_file(path),
    }


def audited_panel_bank_manifest(
    bank_directory: Path, bank_result: Mapping[str, Any]
) -> dict[str, Any]:
    """Reconstruct the producer's augmented manifest from audited evidence."""
    manifest_path = bank_directory / "manifest.json"
    raw_manifest = recovery.read_json(manifest_path)
    if "manifest_sha256" in raw_manifest:
        raise ValueError("raw bank manifest unexpectedly contains its derived file hash")
    audited_hash = bank_result.get("manifest_sha256")
    actual_hash = recovery.sha256_file(manifest_path)
    if (
        bank_result.get("passed") is not True
        or not isinstance(audited_hash, str)
        or audited_hash != actual_hash
    ):
        raise ValueError("independent bank-manifest file hash binding failed")
    return {**raw_manifest, "manifest_sha256": audited_hash}


def audit_panel_results_repaired(
    directory: Path,
    raw_arrivals: NDArray[np.float64],
    context: Any,
    prey_counts: NDArray[Any],
    predator_counts: NDArray[Any],
    truths: Sequence[Mapping[str, Any]],
    *,
    bank_directory: Path,
    bank_result: Mapping[str, Any],
    panel_bindings: Mapping[str, Any],
) -> dict[str, Any]:
    """Call the unchanged panel audit with the producer-form bank manifest."""
    return base.audit_panel_results(
        directory,
        raw_arrivals,
        context,
        prey_counts,
        predator_counts,
        truths,
        bank_manifest=audited_panel_bank_manifest(bank_directory, bank_result),
        panel_bindings=panel_bindings,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-failed-audit", type=Path, required=True)
    parser.add_argument("--original-public-inputs", type=Path, required=True)
    parser.add_argument("--public-inputs", type=Path, required=True)
    parser.add_argument("--predecessor-audit", type=Path, required=True)
    parser.add_argument("--predecessor-source-freeze", type=Path, required=True)
    parser.add_argument("--predecessor-registration", type=Path, required=True)
    parser.add_argument("--source-freeze", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--panel-results", type=Path, required=True)
    parser.add_argument("--calibration-fixture", type=Path, required=True)
    parser.add_argument("--confirmatory-addresses", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.output.exists():
        raise FileExistsError("refusing to replace an earlier Goal 060 audit repair")
    args.output.mkdir(parents=True)
    repository = Path(__file__).resolve().parents[1]
    receipt: dict[str, Any] = {
        "schema_version": AUDIT_SCHEMA,
        "status": "incomplete",
        "audit_passed": False,
    }
    try:
        original_failure = audit_original_failure(args.original_failed_audit)
        receipt["repair"] = {
            "schema_version": REPAIR_SCHEMA,
            "scope": "bank-manifest representation adapter only",
            "original_failure": original_failure,
        }
        source = base.audit_source_freeze(
            repository, args.source_freeze, args.runtime, args.registration
        )
        fixed, setup, context, recovered = recovery.audit_recovery_inputs(
            args.original_public_inputs,
            args.public_inputs,
            predecessor_audit=args.predecessor_audit,
            predecessor_source=args.predecessor_source_freeze,
            predecessor_registration=args.predecessor_registration,
            registration=args.registration,
        )
        confirmatory_addresses = recovery.audit_confirmatory_addresses(
            args.confirmatory_addresses,
            source_manifest=args.source_freeze,
            runtime=args.runtime,
            registration=args.registration,
        )
        calibration = recovery.audit_registered_calibration_fixture(
            args.calibration_fixture
        )
        raw, bank_result = base.audit_arrival_bank(
            args.bank,
            context.site_ids,
            fixed=fixed,
            map_a=setup.exposure_score,
        )
        mechanical = base.audit_mechanical_receipts(args.qualification)
        prey, predator, truths, fixture = base.audit_public_panel(
            args.panel, fixed, setup, context
        )
        fixture_bindings = {
            "qualification": fixture["qualification_sha256"]
            == mechanical["qualification_sha256"],
            "mechanical_receipt": fixture["mechanical_receipt_sha256"]
            == mechanical["mechanical_receipt_sha256"],
            "public_inputs": fixture["public_inputs_sha256"]
            == recovered["base_reconstruction"]["public_inputs_sha256"],
        }
        if not all(fixture_bindings.values()):
            raise ValueError("Goal 060 public fixture predraw bindings are invalid")
        fixture["audited_predraw_bindings"] = fixture_bindings
        panel = audit_panel_results_repaired(
            args.panel_results,
            raw,
            context,
            prey,
            predator,
            truths,
            bank_directory=args.bank,
            bank_result=bank_result,
            panel_bindings=fixture,
        )
        receipt.update(
            {
                "status": "completed",
                "audit_passed": True,
                "scientific_qualification_passed": panel["passed"],
                "repair": {
                    **receipt["repair"],
                    "manifest_sha256": bank_result["manifest_sha256"],
                },
                "source_freeze": source,
                "recovery": recovered,
                "arrival_bank": bank_result,
                "mechanical_qualification": mechanical,
                "public_fixtures": fixture,
                "panel_results": panel,
                "calibration_fixture": calibration,
                "confirmatory_addresses": confirmatory_addresses,
            }
        )
    except Exception as error:
        receipt.update(
            {
                "status": "failed",
                "audit_passed": False,
                "error_type": type(error).__name__,
                "error": str(error),
            }
        )
        base.write_json(args.output / "audit.json", receipt)
        raise
    base.write_json(args.output / "audit.json", receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
