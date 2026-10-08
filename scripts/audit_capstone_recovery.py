#!/usr/bin/env python3
"""Independent Goal 060 certificate-recovery and public-package audit.

The Goal 060 layer verifies byte identity to the closed Goal 059 map package,
reconstructs the fixed 1,024-interval certificate, and binds both source
freezes and registrations.  Full mode then composes the unchanged Goal 059
direct-bank, public-replay, panel and calibration audits.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import audit_capstone_public as base
import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]

RECOVERY_INTERVALS = 1_024
RECOVERY_SCHEMA = "goal060-public-recovery-v1"
CONFIRMATORY_ROOT = 2026100404
MECHANICAL_ROOT = 987654321
SCREEN_DOMAIN = 5
EFFECT_DOMAIN = 6
GOAL059_AUDIT_SHA256 = "06ad70058ac680c5c3d8fc2d282307cf3643033e9104cf6cc00b07c58d1feb7a"
GOAL059_SOURCE_SHA256 = "e63af340a6c2180914db6c779e4b3316ef9db99e3f27b169156ef6168e289867"
GOAL059_REGISTRATION_SHA256 = (
    "3c1c007d1d46897c81ae2464feaf8168bac3c30f8d7e36776312d963d803fe5e"
)
GOAL059_ORIGINAL_HASHES = {
    "accepted_candidate.json": "ddf4f17657bfd2ae28952542fcf5dec464d370e5d7b6717256e072e9cc1e9513",
    "exposure.npz": "b74004fc9ecf03499cfdc9ecca4919b0e17987eba405709f4e3f95f9bc9c0831",
    "failed_attempts.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "public_inputs.json": "7c5d2f21ab94505bca0dc874a9375aa4a4434d1a61f75f7e8b0846aef0823161",
    "public_inputs.npz": "f5c590d1b600c74a686a77215488844e78e19e30fdc59fe34ab44f39acebdfc2",
    "seed_ledger.json": "ead7b2705bbf5777aaeb901414dff1438a7e2dfdaab7180fdd6cb56437c12e2f",
}
GOAL059_CALIBRATION_FIXTURE_HASHES = {
    "fixture.json": "b22642b94e835252e16e5a692b078773687d1f3f17de24972bcb02eae931186e",
    "fixture.npz": "231713b589d230a24370dfd8abd011b49e9e32b19329084eff1a9436b4f07fe0",
}
ORIGINAL_FILES = (
    "accepted_candidate.json",
    "exposure.npz",
    "failed_attempts.json",
    "public_inputs.json",
    "public_inputs.npz",
    "seed_ledger.json",
)
PRESERVED_NAMES = (
    "accepted_candidate.json",
    "exposure.npz",
    "failed_attempts.json",
    "public_inputs.npz",
    "seed_ledger.json",
)


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return base.read_json(path)


def certificate_1024(
    map_a: NDArray[Any],
    site_a: NDArray[Any],
    *,
    intervals: int = RECOVERY_INTERVALS,
    max_mu: float = 0.006,
    max_h: float = 10.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reconstruct the fixed enclosure without production certificate code."""
    whole = np.asarray(map_a, dtype=np.float64).ravel()
    sites = np.asarray(site_a, dtype=np.float64).ravel()
    if (
        intervals <= 0
        or not len(whole)
        or not len(sites)
        or not np.isfinite(whole).all()
        or not np.isfinite(sites).all()
        or not math.isfinite(max_mu)
        or not math.isfinite(max_h)
        or not max_mu > 0.0
        or not max_h >= 1.0
    ):
        raise ValueError("invalid recovery hazard box")
    edges = np.linspace(-2.0, 2.0, intervals + 1, dtype=np.float64)
    raw_maximum = -math.inf
    winning_interval = -1
    winning_site = -1
    minimum_denominator = math.inf
    midpoint_minimum_slack = math.inf
    for index, (lower, upper) in enumerate(itertools.pairwise(edges)):
        lower_map = np.exp(lower * whole)
        upper_map = np.exp(upper * whole)
        denominator_lower = float(np.minimum(lower_map, upper_map).mean())
        if not math.isfinite(denominator_lower) or denominator_lower <= 0.0:
            raise ValueError("recovery denominator lower bound is not positive")
        minimum_denominator = min(minimum_denominator, denominator_lower)
        numerator_upper = np.maximum(np.exp(lower * sites), np.exp(upper * sites))
        site_bounds = max_mu * (numerator_upper / denominator_lower)
        site_index = int(np.argmax(site_bounds))
        interval_maximum = float(site_bounds[site_index])
        if interval_maximum > raw_maximum:
            raw_maximum = interval_maximum
            winning_interval = index
            winning_site = site_index

        midpoint = 0.5 * (lower + upper)
        actual_midpoint = max_mu * np.exp(midpoint * sites) / float(
            np.exp(midpoint * whole).mean()
        )
        midpoint_minimum_slack = min(
            midpoint_minimum_slack,
            float(np.min(site_bounds - actual_midpoint)),
        )
    inflated = raw_maximum * (1.0 + 1e-12)
    guarded = float(np.nextafter(inflated, np.inf))
    transform = 10.0 * guarded * (max_h - 1.0)
    certificate = {
        "method": "interval_numerator_upper_whole_map_denominator_lower",
        "beta_interval": [-2.0, 2.0],
        "interval_count": intervals,
        "mu_upper": max_mu,
        "h_upper": max_h,
        "site_hazard_upper": guarded,
        "transform_x_upper": transform,
        "required_transform_domain_upper": 5.0,
        "passes": bool(transform <= 5.0),
    }
    diagnostics = {
        "passed": True,
        "interval_count": intervals,
        "edge_count": len(edges),
        "interval_width": float(edges[1] - edges[0]),
        "coverage": [float(edges[0]), float(edges[-1])],
        "edges_sha256": base.array_sha256(edges),
        "raw_site_hazard_upper": raw_maximum,
        "inflated_site_hazard_upper": inflated,
        "guarded_site_hazard_upper": guarded,
        "outward_guard_strict": guarded > inflated > raw_maximum,
        "winning_interval_index": winning_interval,
        "winning_interval": [
            float(edges[winning_interval]),
            float(edges[winning_interval + 1]),
        ],
        "winning_site_index": winning_site,
        "minimum_denominator_lower": minimum_denominator,
        "midpoint_minimum_bound_slack": midpoint_minimum_slack,
    }
    if (
        diagnostics["coverage"] != [-2.0, 2.0]
        or len(edges) != intervals + 1
        or not np.all(np.diff(edges) > 0.0)
        or midpoint_minimum_slack < -1e-15
        or not diagnostics["outward_guard_strict"]
    ):
        raise ValueError("independent recovery certificate diagnostics failed")
    return certificate, diagnostics


def mechanical_rejection_fixture() -> dict[str, Any]:
    """Exercise the fixed gate on a deterministic box that must be rejected."""
    map_a = np.zeros(1_024, dtype=np.float64)
    map_a[0] = 3.0
    certificate, diagnostics = certificate_1024(map_a, map_a[:1])
    if certificate["passes"]:
        raise ValueError("mechanical recovery certificate failed to reject")
    return {
        "passed": True,
        "certificate": certificate,
        "diagnostics": diagnostics,
        "map_a_sha256": base.array_sha256(map_a),
    }


def expected_confirmatory_contract(
    *, source_manifest: Path, runtime: Path, registration: Path
) -> dict[str, Any]:
    """Reconstruct the complete unchanged Goal 059 address contract."""
    nodes = [
        {
            "index": index,
            "beta": beta,
            "mu": mu,
            "detection_sd": detection_sd,
        }
        for index, (beta, mu, detection_sd) in enumerate(base.nuisance_grid())
    ]
    node_bytes = json.dumps(nodes, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema": "goal059-capstone-address-v1",
        "root": CONFIRMATORY_ROOT,
        "namespace": base.PUBLIC_NAMESPACE,
        "numpy_version": np.__version__,
        "seed_algorithm": "SeedSequence(address).generate_state(1,dtype=uint64)[0]",
        "generator": "numpy.random.default_rng/PCG64",
        "address_order": ["root", "namespace", "domain", "node", "reference", "stage"],
        "domains": {"screen": SCREEN_DOMAIN, "effect": EFFECT_DOMAIN},
        "stages": {
            "spread": 1,
            "prey_loss": 2,
            "predator_visits": 3,
            "site_detection": 4,
            "prey_visits": 5,
        },
        "screen_stages": ["prey_loss", "site_detection", "prey_visits"],
        "screen_references": 99,
        "effect_references": 999,
        "node_count": 765,
        "nodes": nodes,
        "nodes_sha256": hashlib.sha256(node_bytes).hexdigest(),
        "screen_histories": 765 * 99,
        "maximum_effect_histories": 765 * 999,
        "screen_seed_count": 765 * 99 * 3,
        "effect_seed_count": 765 * 999 * 5,
        "rule": "complete retained union; lazy materialization at fixed addresses",
        "source_manifest_sha256": sha256_file(source_manifest),
        "runtime_sha256": sha256_file(runtime),
        "registration_sha256": sha256_file(registration),
    }


def audit_confirmatory_addresses(
    path: Path, *, source_manifest: Path, runtime: Path, registration: Path
) -> dict[str, Any]:
    """Require the persisted contract to equal an independent reconstruction."""
    actual = read_json(path)
    expected = expected_confirmatory_contract(
        source_manifest=source_manifest,
        runtime=runtime,
        registration=registration,
    )
    if actual != expected:
        raise ValueError("Goal 060 confirmatory address contract mismatch")
    return {
        "passed": True,
        "root": CONFIRMATORY_ROOT,
        "contract_sha256": sha256_file(path),
        "nodes_sha256": expected["nodes_sha256"],
        "screen_histories": expected["screen_histories"],
        "maximum_effect_histories": expected["maximum_effect_histories"],
    }


def audit_registered_calibration_fixture(directory: Path) -> dict[str, Any]:
    """Bind the unchanged fixture before exercising its registered arithmetic."""
    actual_hashes = {
        name: sha256_file(directory / name)
        for name in GOAL059_CALIBRATION_FIXTURE_HASHES
    }
    if actual_hashes != GOAL059_CALIBRATION_FIXTURE_HASHES:
        raise ValueError("Goal 059 calibration fixture identity mismatch")
    metadata = read_json(directory / "fixture.json")
    contract = metadata.get("address_contract")
    if not isinstance(contract, dict) or contract.get("root") != MECHANICAL_ROOT:
        raise ValueError("Goal 059 calibration fixture root mismatch")
    result = base.audit_calibration_fixture(directory)
    result["registered_fixture_hashes"] = actual_hashes
    result["required_root"] = MECHANICAL_ROOT
    return result


def _load_exposure(path: Path) -> tuple[FloatArray, FloatArray, NDArray[np.bool_]]:
    with np.load(path, allow_pickle=False) as value:
        if set(value.files) != {"map_a", "site_a", "accepted_mask"}:
            raise ValueError("recovery exposure schema mismatch")
        return (
            np.asarray(value["map_a"], dtype=np.float64),
            np.asarray(value["site_a"], dtype=np.float64),
            np.asarray(value["accepted_mask"], dtype=bool),
        )


def audit_recovery_inputs(
    original: Path,
    recovered: Path,
    *,
    predecessor_audit: Path,
    predecessor_source: Path,
    predecessor_registration: Path,
    registration: Path,
) -> tuple[Any, Any, base.AuditContext, dict[str, Any]]:
    """Audit the Goal 060 amendment and reconstruct the unchanged public map."""
    receipt_path = recovered / "recovery.json"
    receipt = read_json(receipt_path)
    original_metadata_path = original / "public_inputs.json"
    preserved_metadata_path = recovered / "original-public-inputs.json"
    new_metadata_path = recovered / "public_inputs.json"
    original_metadata = read_json(original_metadata_path)
    preserved_metadata = read_json(preserved_metadata_path)
    new_metadata = read_json(new_metadata_path)

    original_hashes = {
        name: sha256_file(original / name) for name in ORIGINAL_FILES
    }
    expected_output_names = {
        *PRESERVED_NAMES,
        "original-public-inputs.json",
        "public_inputs.json",
    }
    output_entries = tuple(recovered.iterdir())
    output_names = {path.name for path in output_entries if path.name != "recovery.json"}
    output_hashes = {
        name: sha256_file(recovered / name) for name in sorted(output_names)
    }
    byte_identity = {
        name: (original / name).read_bytes() == (recovered / name).read_bytes()
        for name in PRESERVED_NAMES
    }
    predecessor = read_json(predecessor_audit)
    source_manifest = read_json(predecessor_source)
    registered_hash = sha256_file(registration)

    original_map, original_sites, original_mask = _load_exposure(
        original / "exposure.npz"
    )
    recovered_map, recovered_sites, recovered_mask = _load_exposure(
        recovered / "exposure.npz"
    )
    certificate, certificate_diagnostics = certificate_1024(
        recovered_map, recovered_sites
    )

    allowed_metadata_changes = {
        "state",
        "error",
        "error_type",
        "hazard_certificate",
        "qualification_goal",
        "recovery_receipt",
    }
    original_common = {
        key: value
        for key, value in original_metadata.items()
        if key not in allowed_metadata_changes
    }
    recovered_common = {
        key: value
        for key, value in new_metadata.items()
        if key not in allowed_metadata_changes
    }
    checks = {
        "receipt_schema": receipt.get("schema_version") == RECOVERY_SCHEMA,
        "receipt_state": receipt.get("state") == "qualified",
        "original_state": original_metadata.get("state") == "qualification_failed"
        and receipt.get("original_state") == "qualification_failed",
        "fixed_identity": original_metadata.get("root") == base.PUBLIC_ROOT
        and original_metadata.get("attempt") == 0
        and original_metadata.get("map_seed") == 2286118029579671682
        and original_metadata.get("sampling_seed") == 12049465925351981407,
        "original_hashes": receipt.get("source_hashes") == original_hashes,
        "registered_original_hashes": original_hashes == GOAL059_ORIGINAL_HASHES,
        "preserved_bytes": all(byte_identity.values()),
        "negative_metadata_preserved": preserved_metadata == original_metadata
        and sha256_file(preserved_metadata_path)
        == original_hashes["public_inputs.json"],
        "output_names": output_names == expected_output_names
        and {path.name for path in output_entries} == expected_output_names | {"recovery.json"}
        and all(path.is_file() and not path.is_symlink() for path in output_entries),
        "output_hashes": receipt.get("outputs_sha256") == output_hashes,
        "preserved_array_files": receipt.get("preserved_array_files")
        == ["public_inputs.npz", "exposure.npz"],
        "exposure_byte_identity": np.array_equal(original_map, recovered_map)
        and np.array_equal(original_sites, recovered_sites)
        and np.array_equal(original_mask, recovered_mask),
        "predecessor_hashes": sha256_file(predecessor_audit)
        == GOAL059_AUDIT_SHA256
        and sha256_file(predecessor_source) == GOAL059_SOURCE_SHA256
        and sha256_file(predecessor_registration) == GOAL059_REGISTRATION_SHA256
        and receipt.get("predecessor_audit_sha256") == GOAL059_AUDIT_SHA256
        and receipt.get("predecessor_source_manifest_sha256")
        == GOAL059_SOURCE_SHA256
        and receipt.get("predecessor_registration_sha256")
        == GOAL059_REGISTRATION_SHA256,
        "predecessor_negative": predecessor.get("audit_passed") is True
        and predecessor.get("scientific_qualification_passed") is False
        and predecessor.get("terminal_negative_qualification") is True
        and predecessor.get("public_inputs", {}).get("attempt") == 0,
        "predecessor_source_bound": predecessor.get("source_freeze", {}).get(
            "source_manifest_sha256"
        )
        == GOAL059_SOURCE_SHA256
        and source_manifest.get("source_hashes", {}).get(
            "docs/goals/059-capstone-preparation/registration-2026-10-04.md"
        )
        == GOAL059_REGISTRATION_SHA256,
        "registration_hash": receipt.get("registration_sha256") == registered_hash,
        "certificate_intervals": receipt.get("certificate_intervals")
        == RECOVERY_INTERVALS,
        "certificate_exact": receipt.get("certificate") == certificate
        and new_metadata.get("hazard_certificate") == certificate,
        "certificate_passed": certificate["passes"] is True,
        "field_checks_unchanged": receipt.get("field_checks")
        == original_metadata.get("field_checks")
        == new_metadata.get("field_checks"),
        "metadata_common_unchanged": recovered_common == original_common,
        "new_metadata_qualified": new_metadata.get("state") == "qualified"
        and "error" not in new_metadata
        and "error_type" not in new_metadata,
        "goal60_binding_present": new_metadata.get("qualification_goal") == 60
        and new_metadata.get("recovery_receipt") == "recovery.json",
    }
    if not all(checks.values()):
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise ValueError(f"Goal 060 recovery audit failed: {failed}")

    fixed, setup, context, reconstructed = base.reconstruct_public_inputs(recovered)
    return fixed, setup, context, {
        "passed": True,
        "checks": checks,
        "byte_identity": byte_identity,
        "certificate": certificate,
        "certificate_diagnostics": certificate_diagnostics,
        "mechanical_rejection": mechanical_rejection_fixture(),
        "base_reconstruction": reconstructed,
        "source_hashes": original_hashes,
        "output_sha256": output_hashes,
        "recovery_sha256": sha256_file(receipt_path),
        "original_negative_sha256": sha256_file(preserved_metadata_path),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map-only", action="store_true")
    parser.add_argument("--original-public-inputs", type=Path, required=True)
    parser.add_argument("--public-inputs", type=Path, required=True)
    parser.add_argument("--predecessor-audit", type=Path, required=True)
    parser.add_argument("--predecessor-source-freeze", type=Path, required=True)
    parser.add_argument("--predecessor-registration", type=Path, required=True)
    parser.add_argument("--source-freeze", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--bank", type=Path)
    parser.add_argument("--qualification", type=Path)
    parser.add_argument("--panel", type=Path)
    parser.add_argument("--panel-results", type=Path)
    parser.add_argument("--calibration-fixture", type=Path)
    parser.add_argument("--confirmatory-addresses", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.output.exists():
        raise FileExistsError("refusing to replace an earlier Goal 060 audit")
    args.output.mkdir(parents=True)
    repository = Path(__file__).resolve().parents[1]
    receipt: dict[str, Any] = {
        "schema_version": "goal060-independent-public-audit-v1",
        "status": "incomplete",
        "audit_passed": False,
    }
    try:
        source = base.audit_source_freeze(
            repository, args.source_freeze, args.runtime, args.registration
        )
        fixed, setup, context, recovery = audit_recovery_inputs(
            args.original_public_inputs,
            args.public_inputs,
            predecessor_audit=args.predecessor_audit,
            predecessor_source=args.predecessor_source_freeze,
            predecessor_registration=args.predecessor_registration,
            registration=args.registration,
        )
        if args.map_only:
            receipt.update(
                {
                    "status": "completed",
                    "audit_passed": True,
                    "scientific_qualification_passed": True,
                    "source_freeze": source,
                    "recovery": recovery,
                }
            )
            base.write_json(args.output / "audit.json", receipt)
            return 0

        required = {
            "bank": args.bank,
            "qualification": args.qualification,
            "panel": args.panel,
            "panel_results": args.panel_results,
            "calibration_fixture": args.calibration_fixture,
            "confirmatory_addresses": args.confirmatory_addresses,
        }
        missing = [name for name, path in required.items() if path is None]
        if missing:
            raise ValueError(f"full recovery audit is missing arguments: {missing}")
        assert args.bank is not None
        assert args.qualification is not None
        assert args.panel is not None
        assert args.panel_results is not None
        assert args.calibration_fixture is not None
        assert args.confirmatory_addresses is not None
        confirmatory_addresses = audit_confirmatory_addresses(
            args.confirmatory_addresses,
            source_manifest=args.source_freeze,
            runtime=args.runtime,
            registration=args.registration,
        )
        calibration = audit_registered_calibration_fixture(args.calibration_fixture)
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
            == recovery["base_reconstruction"]["public_inputs_sha256"],
        }
        if not all(fixture_bindings.values()):
            raise ValueError("Goal 060 public fixture predraw bindings are invalid")
        fixture["audited_predraw_bindings"] = fixture_bindings
        panel = base.audit_panel_results(
            args.panel_results,
            raw,
            context,
            prey,
            predator,
            truths,
            bank_manifest=read_json(args.bank / "manifest.json"),
            panel_bindings=fixture,
        )
        receipt.update(
            {
                "status": "completed",
                "audit_passed": True,
                "scientific_qualification_passed": panel["passed"],
                "source_freeze": source,
                "recovery": recovery,
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
