"""Goal 060's single approved certificate amendment on the frozen Goal 059 map."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import capstone_public as public
from latent_landscapes.misspecification_generator import build_generator_setup
from latent_landscapes.preinvasion_campaign import hazard_box_certificate

CERTIFICATE_INTERVALS = 1024
ORIGINAL_HASHES = {
    "accepted_candidate.json": "ddf4f17657bfd2ae28952542fcf5dec464d370e5d7b6717256e072e9cc1e9513",
    "exposure.npz": "b74004fc9ecf03499cfdc9ecca4919b0e17987eba405709f4e3f95f9bc9c0831",
    "failed_attempts.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "public_inputs.json": "7c5d2f21ab94505bca0dc874a9375aa4a4434d1a61f75f7e8b0846aef0823161",
    "public_inputs.npz": "f5c590d1b600c74a686a77215488844e78e19e30fdc59fe34ab44f39acebdfc2",
    "seed_ledger.json": "ead7b2705bbf5777aaeb901414dff1438a7e2dfdaab7180fdd6cb56437c12e2f",
}
PREDECESSOR_AUDIT_SHA256 = "06ad70058ac680c5c3d8fc2d282307cf3643033e9104cf6cc00b07c58d1feb7a"
PREDECESSOR_SOURCE_SHA256 = "e63af340a6c2180914db6c779e4b3316ef9db99e3f27b169156ef6168e289867"
PREDECESSOR_REGISTRATION_SHA256 = (
    "3c1c007d1d46897c81ae2464feaf8168bac3c30f8d7e36776312d963d803fe5e"
)


def fixed_hazard_certificate(
    map_a: NDArray[np.float64], site_a: NDArray[np.float64]
) -> dict[str, Any]:
    """Use exactly 1,024 intervals; retain the existing formula and outward margin."""
    return hazard_box_certificate(map_a, site_a, beta_edges=np.linspace(-2.0, 2.0, 1025))


def recover_public_inputs(
    original: Path,
    output: Path,
    *,
    predecessor_audit: Path,
    predecessor_source: Path,
    predecessor_registration: Path,
    registration: Path,
) -> dict[str, Any]:
    """Copy the accepted map unchanged, verify identity, then apply the amendment.

    This entry point has no map-selection, seed or refinement-count argument.
    A failed certificate leaves its copied inputs and negative receipt in place.
    """
    if output.exists():
        raise FileExistsError("preserve existing recovery; no replacement is permitted")
    source_hashes = {name: public._sha(original / name) for name in ORIGINAL_HASHES}
    if source_hashes != ORIGINAL_HASHES:
        raise ValueError("original public input identity mismatch")
    bindings = {
        "predecessor_audit_sha256": (predecessor_audit, PREDECESSOR_AUDIT_SHA256),
        "predecessor_source_manifest_sha256": (predecessor_source, PREDECESSOR_SOURCE_SHA256),
        "predecessor_registration_sha256": (
            predecessor_registration,
            PREDECESSOR_REGISTRATION_SHA256,
        ),
    }
    for path, expected in bindings.values():
        if public._sha(path) != expected:
            raise ValueError("predecessor evidence identity mismatch")
    metadata = json.loads((original / "public_inputs.json").read_text())
    expected_identity = {
        "state": "qualification_failed",
        "root": 2026100403,
        "namespace": 59,
        "attempt": 0,
        "map_seed": 2286118029579671682,
        "sampling_seed": 12049465925351981407,
    }
    if any(metadata.get(key) != value for key, value in expected_identity.items()):
        raise ValueError("original candidate or qualification state mismatch")
    audit = json.loads(predecessor_audit.read_text())
    if not audit["audit_passed"] or audit["scientific_qualification_passed"]:
        raise ValueError("predecessor audit does not preserve the negative qualification")
    registration_sha256 = public._sha(registration)
    output.mkdir(parents=True)
    for name in ORIGINAL_HASHES:
        destination = "original-public-inputs.json" if name == "public_inputs.json" else name
        shutil.copyfile(original / name, output / destination)
    receipt: dict[str, Any] = {
        "schema_version": "goal060-public-recovery-v1",
        "state": "verifying_fixed_map",
        "original_state": "qualification_failed",
        "source_hashes": source_hashes,
        **{name: expected for name, (_, expected) in bindings.items()},
        "registration_sha256": registration_sha256,
        "certificate_intervals": CERTIFICATE_INTERVALS,
        "preserved_array_files": ["public_inputs.npz", "exposure.npz"],
    }
    public._write_json(output / "recovery.json", receipt)
    metadata.update(qualification_goal=60, recovery_receipt="recovery.json")
    try:
        fixed = public._make_fixed(metadata["map_seed"], metadata["sampling_seed"])
        if public._array_hashes(fixed) != metadata["array_sha256"]:
            raise ValueError("reconstructed map/design array identity mismatch")
        with np.load(output / "public_inputs.npz", allow_pickle=False) as stored:
            arrays = public._fixed_arrays(fixed)
            if set(stored.files) != set(arrays) or any(
                not np.array_equal(stored[name], value) for name, value in arrays.items()
            ):
                raise ValueError("reconstructed map/design differs from frozen arrays")
        setup = build_generator_setup(fixed)
        site_a = setup.exposure_score[setup.site_rows, setup.site_cols]
        exposure = {
            "map_a": setup.exposure_score,
            "site_a": site_a,
            "accepted_mask": setup.accepted_mask,
        }
        with np.load(output / "exposure.npz", allow_pickle=False) as stored:
            if set(stored.files) != set(exposure) or any(
                not np.array_equal(stored[name], value) for name, value in exposure.items()
            ):
                raise ValueError("reconstructed exposure differs from frozen arrays")
        field = setup.field_sampler
        field_checks = {
            "field_shape": list(field.field_shape),
            "embedding_shape": list(field.embedding_shape),
            "minimum_eigenvalue": field.minimum_eigenvalue,
            "reconstruction_max_abs_error": field.reconstruction_max_abs_error,
        }
        if field_checks != metadata["field_checks"]:
            raise ValueError("fixed-field diagnostics changed")
        certificate = fixed_hazard_certificate(setup.exposure_score, site_a)
        receipt.update(certificate=certificate, field_checks=field_checks)
        metadata.update(hazard_certificate=certificate)
        if (
            not certificate["passes"]
            or field.field_shape != (72, 84)
            or field.embedding_shape != (142, 166)
            or field.minimum_eigenvalue <= 0
            or field.reconstruction_max_abs_error > 1e-12
        ):
            raise RuntimeError("fixed public map failed amended hazard or fixed-field certificate")
    except Exception as error:
        failure = {
            "state": "qualification_failed",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        metadata.update(failure)
        receipt.update(failure)
        public._write_json(output / "public_inputs.json", metadata)
        receipt["outputs_sha256"] = {
            p.name: public._sha(p) for p in sorted(output.iterdir()) if p.name != "recovery.json"
        }
        public._write_json(output / "recovery.json", receipt)
        raise
    metadata.pop("error_type", None)
    metadata.pop("error", None)
    metadata["state"] = "qualified"
    public._write_json(output / "public_inputs.json", metadata)
    receipt.update(
        state="qualified",
        outputs_sha256={
            p.name: public._sha(p) for p in sorted(output.iterdir()) if p.name != "recovery.json"
        },
    )
    public._write_json(output / "recovery.json", receipt)
    return receipt
