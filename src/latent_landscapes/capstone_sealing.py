"""Bounded, fail-closed sealer for the Goal 060 capstone handoff.

The public readiness check is deliberately separate from the private section.
No operating-system entropy is read until every public hash and readiness
predicate has passed. The private bundles are constructed in memory, then
encrypted directly through age; plaintext truth and holdout archives are
never written to the filesystem.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.metadata
import io
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import warnings
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import capstone_public as public_api

PUBLIC_ROOT = 2026100403
CONFIRMATORY_ROOT = 2026100404
NAMESPACE = 60
REGISTERED_RECIPIENT = "age194jmw2rywjfazsc6w8hqht3lnlxldkcp9dwl49xm54r6hk8y4vtslny0yr"
PRIVATE_TRUTH_STAGE = 0
PRIVATE_STREAM_STAGE = 1
STREAM_STAGES = {
    "spread": 1,
    "prey_loss": 2,
    "predator_visits": 3,
    "site_detection": 4,
    "prey_visits": 5,
    "background_field": 6,
}
MU_VALUES = (0.001, 0.0016, 0.002, 0.0025, 0.0032, 0.004)
SD_VALUES = (0.0, 0.1, 0.2, 0.3)
BETA_VALUES = (-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0)
SITE_COUNT = 160
TRAINING_COUNT = 120
HOLDOUT_COUNT = 40
ENTROPY_BYTES = 96
SALT_BYTES = 32
RECEIPT_SCHEMA = "goal060-capstone-sealing-v1"
PUBLIC_READY_SCHEMA = "goal060-public-ready-v1"
RECOVERY_SCHEMA = "goal060-public-recovery-v1"
# tarfile emits 10,240-byte records, so use fixed sizes on that boundary.
TRUTH_ARCHIVE_BYTES = 205 * 10240
HOLDOUT_ARCHIVE_BYTES = 26 * 10240

FloatArray = NDArray[np.float64]
SCIPY_VERSION = importlib.metadata.version("scipy")


class SealingFailure(RuntimeError):
    """A safe, non-secret sealing failure."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return _jsonable(asdict(value))
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(_jsonable(value), sort_keys=True, indent=2, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def _private_root(root: bytes) -> int:
    if not isinstance(root, bytes) or len(root) != SALT_BYTES:
        raise ValueError("private root must contain exactly 32 bytes")
    return int.from_bytes(root, "little", signed=False)


def _check_private_root(root: bytes) -> None:
    private_root = _private_root(root)
    registered = (PUBLIC_ROOT, CONFIRMATORY_ROOT)
    registered_encodings = tuple(
        encoding
        for value in registered
        for encoding in (
            value.to_bytes(SALT_BYTES, "little"),
            value.to_bytes(SALT_BYTES, "big"),
        )
    )
    if root in registered_encodings or private_root in registered:
        raise SealingFailure("private root collides with a registered public root")


def _address_seed(root: bytes, case: int, stage: int) -> int:
    private_root = _private_root(root)
    if case < 0 or stage < 0:
        raise ValueError("seed address components must be nonnegative")
    sequence = np.random.SeedSequence([private_root, NAMESPACE, case, stage])
    return int(sequence.generate_state(1, dtype=np.uint64)[0])


def fixture_streams(root: bytes, case: int) -> dict[str, int]:
    """Return deterministic private generator stream seeds for one case."""
    return {name: _address_seed(root, case, stage) for name, stage in STREAM_STAGES.items()}


def _draw_truths(root: bytes, count: int = 4) -> tuple[dict[str, Any], ...]:
    """Draw the registered four-case truth law from an explicit root."""
    if count != 4:
        raise ValueError("the registered sealer requires exactly four histories")
    truths: list[dict[str, Any]] = []
    for case in range(count):
        truth_seed = _address_seed(root, case, PRIVATE_TRUTH_STAGE)
        rng = np.random.default_rng(truth_seed)
        null = bool(rng.random() < 0.5)
        h = 1.0 if null else float(np.exp(rng.uniform(np.log(2.0), np.log(5.0))))
        background = "exact" if bool(rng.random() < 0.75) else "B100-A"
        mean_hazard = float(rng.choice(np.asarray(MU_VALUES, dtype=np.float64)))
        detection_sd = float(rng.choice(np.asarray(SD_VALUES, dtype=np.float64)))
        beta: float | None = (
            float(rng.choice(np.asarray(BETA_VALUES, dtype=np.float64)))
            if background == "exact"
            else None
        )
        truths.append(
            {
                "index": case,
                "effect": h,
                "mean_hazard": mean_hazard,
                "beta": beta,
                "detection_sd": detection_sd,
                "background": background,
                "h_null": null,
                "truth_seed": truth_seed,
                "streams": fixture_streams(root, case),
            }
        )
    return tuple(truths)


def _truth_object(row: Mapping[str, Any]) -> public_api.GeneralTruth:
    return public_api.GeneralTruth(
        int(row["index"]),
        float(row["effect"]),
        float(row["mean_hazard"]),
        float(row["beta"]) if row["beta"] is not None else 0.0,
        float(row["detection_sd"]),
        str(row["background"]),
    )


def _b100_field(setup: Any, seed: int) -> FloatArray:
    return np.asarray(setup.field_sampler.sample(np.random.default_rng(seed)), dtype=np.float64)


def _b100_hazard_from_field(setup: Any, field: FloatArray, mean_hazard: float) -> FloatArray:
    z = 0.7 * np.asarray(setup.exposure_score, dtype=np.float64) + math.sqrt(0.51) * field
    raw = np.exp(math.sqrt(math.log(2.0)) * z)
    return np.asarray(mean_hazard * raw / float(raw.mean()), dtype=np.float64)


def _generate_cases(public: public_api.PublicInputs, root: bytes) -> tuple[dict[str, Any], ...]:
    """Generate all four full histories and retain private evaluator arrays."""
    truths = _draw_truths(root)
    generated: list[dict[str, Any]] = []
    for row in truths:
        truth = _truth_object(row)
        stream_values = cast(Mapping[str, int], row["streams"])
        seeds = {
            "root": root.hex(),
            "namespace": NAMESPACE,
            "stage": PRIVATE_STREAM_STAGE,
            "index": truth.index,
            "stream_stages": dict(STREAM_STAGES),
            "streams": dict(stream_values),
        }
        if truth.background == "exact":
            observed, evaluator = public_api.generate_exact_history(
                public.fixed, public.setup, truth, seeds
            )
            field = np.empty((0,), dtype=np.float64)
        else:
            field = _b100_field(public.setup, int(stream_values["background_field"]))
            observed, evaluator = public_api.generate_b100_history(
                public.fixed, public.setup, truth, seeds
            )
            expected = _b100_hazard_from_field(public.setup, field, truth.mean_hazard)
            if not np.array_equal(expected, np.asarray(evaluator["map_hazard"])):
                raise SealingFailure("B100 field replay mismatch")
        generated.append(
            {
                "case_id": f"case-{truth.index:02d}",
                "truth": row,
                "observed": observed,
                "evaluator": evaluator,
                "field": field,
            }
        )
    return tuple(generated)


def _npz_bytes(**arrays: Any) -> bytes:
    output = io.BytesIO()
    np.savez_compressed(output, **arrays)
    return output.getvalue()


def _tar_bytes(entries: Mapping[str, bytes], *, target_bytes: int | None = None) -> bytes:
    if target_bytes is not None and target_bytes % 512:
        raise ValueError("padded archive size must be a 512-byte multiple")

    def build(values: Mapping[str, bytes]) -> bytes:
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w") as archive:
            for name in sorted(values):
                payload = values[name]
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                archive.addfile(info, io.BytesIO(payload))
        return output.getvalue()

    result = build(entries)
    if target_bytes is None:
        return result
    if len(result) > target_bytes or target_bytes - len(result) < 512:
        raise SealingFailure("sealed archive exceeds its registered size")
    low, high = 0, target_bytes - len(result)
    best: bytes | None = None
    while low <= high:
        padding = ((low + high) // 2) // 512 * 512
        candidate = build({**entries, "padding.bin": b"\0" * padding})
        if len(candidate) <= target_bytes:
            best = candidate
            low = padding + 512
        else:
            high = padding - 512
    if best is not None and len(best) == target_bytes:
        return best
    raise SealingFailure("sealed archive size verification failed")


def _public_site_order(public: public_api.PublicInputs) -> tuple[int, ...]:
    ids = tuple(str(value) for value in public.setup.site_ids)
    if ids != tuple(sorted(ids)) or len(ids) != SITE_COUNT:
        raise ValueError("public site order is not the registered canonical order")
    return tuple(int(index) for index in np.argsort(np.asarray(public.setup.site_ids)))


def _build_training_package(
    public: public_api.PublicInputs, cases: Sequence[Mapping[str, Any]]
) -> tuple[bytes, bytes]:
    order = _public_site_order(public)
    training = np.asarray(public.setup.site_splits) == "training"
    if int(training.sum()) != TRAINING_COUNT:
        raise ValueError("public training split is not 120 sites")
    indices = np.asarray(order, dtype=int)[training]
    prey = np.stack(
        [np.asarray(case["observed"]["prey_counts"], dtype=np.int8)[indices] for case in cases]
    )
    predator = np.stack(
        [np.asarray(case["observed"]["predator_counts"], dtype=np.int8)[indices] for case in cases]
    )
    site_ids = np.asarray(public.setup.site_ids, dtype="U32")[indices]
    case_ids = np.asarray([str(case["case_id"]) for case in cases], dtype="U16")
    training_bytes = _npz_bytes(
        case_ids=case_ids,
        site_ids=site_ids,
        prey_counts=prey,
        predator_counts=predator,
    )
    manifest = _json_bytes(
        {
            "schema_version": "goal060-training-v1",
            "case_count": len(cases),
            "site_count": TRAINING_COUNT,
            "prey_visits": len(public_api.PREY_TIMES),
            "predator_visits": len(public_api.PREDATOR_TIMES),
            "arrays_sha256": sha256_bytes(training_bytes),
        }
    )
    return training_bytes, manifest


def _build_truth_tar(root: bytes, salt: bytes, cases: Sequence[Mapping[str, Any]]) -> bytes:
    if len(salt) != SALT_BYTES:
        raise ValueError("truth salt must contain 32 bytes")
    metadata = {
        "schema_version": "goal060-truth-v1",
        "root_hex": root.hex(),
        "namespace": NAMESPACE,
        "truth_stage": PRIVATE_TRUTH_STAGE,
        "stream_stage": PRIVATE_STREAM_STAGE,
        "stream_stages": STREAM_STAGES,
        "truths": [case["truth"] for case in cases],
    }
    entries: dict[str, bytes] = {
        "salt.bin": salt,
        "private-root.bin": root,
        "truth-metadata.json": _json_bytes(metadata),
    }
    for case in cases:
        evaluator = case["evaluator"]
        entries[f"case-{case['truth']['index']:02d}-latent.npz"] = _npz_bytes(
            arrival=np.asarray(evaluator["arrival"]),
            loss=np.asarray(evaluator["loss"]),
            site_hazard=np.asarray(evaluator["site_hazard"]),
            site_detection=np.asarray(evaluator["site_detection"]),
            prey_alive=np.asarray(evaluator["prey_alive"]),
            map_hazard=np.asarray(evaluator.get("map_hazard", np.empty((0,)))),
            field=np.asarray(case["field"]),
            stream_seeds=np.asarray(list(case["truth"]["streams"].values()), dtype=np.uint64),
        )
    return _tar_bytes(entries, target_bytes=TRUTH_ARCHIVE_BYTES)


def _build_holdout_tar(
    public: public_api.PublicInputs, salt: bytes, cases: Sequence[Mapping[str, Any]]
) -> bytes:
    if len(salt) != SALT_BYTES:
        raise ValueError("holdout salt must contain 32 bytes")
    training = np.asarray(public.setup.site_splits) == "training"
    holdout = ~training
    if int(holdout.sum()) != HOLDOUT_COUNT:
        raise ValueError("public holdout split is not 40 sites")
    entries = {
        "salt.bin": salt,
        "holdout.npz": _npz_bytes(
            case_ids=np.asarray([str(case["case_id"]) for case in cases], dtype="U16"),
            site_ids=np.asarray(public.setup.site_ids, dtype="U32")[holdout],
            prey_counts=np.stack(
                [
                    np.asarray(case["observed"]["prey_counts"], dtype=np.int8)[holdout]
                    for case in cases
                ]
            ),
            predator_counts=np.stack(
                [
                    np.asarray(case["observed"]["predator_counts"], dtype=np.int8)[holdout]
                    for case in cases
                ]
            ),
        ),
    }
    return _tar_bytes(entries, target_bytes=HOLDOUT_ARCHIVE_BYTES)


@contextlib.contextmanager
def _private_section() -> Iterator[None]:
    """Suppress accidental diagnostics and best-effort core dumps."""
    previous: tuple[int, int] | None = None
    saved_fds: tuple[int, int] | None = None
    null_fd: int | None = None
    try:
        import resource

        previous = resource.getrlimit(resource.RLIMIT_CORE)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except (ImportError, OSError, ValueError):
        raise SealingFailure("private protection unavailable") from None
    try:
        saved_fds = (os.dup(1), os.dup(2))
        null_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(null_fd, 1)
        os.dup2(null_fd, 2)
    except OSError:
        if null_fd is not None:
            with contextlib.suppress(OSError):
                os.close(null_fd)
        if saved_fds is not None:
            for descriptor in saved_fds:
                with contextlib.suppress(OSError):
                    os.close(descriptor)
        saved_fds = None
        raise SealingFailure("private output protection unavailable") from None
    with (
        warnings.catch_warnings(),
        contextlib.redirect_stdout(io.StringIO()),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        warnings.simplefilter("ignore")
        try:
            yield
        finally:
            if previous is not None:
                with contextlib.suppress(OSError, ValueError):
                    resource.setrlimit(resource.RLIMIT_CORE, previous)
            if saved_fds is not None:
                with contextlib.suppress(OSError):
                    os.dup2(saved_fds[0], 1)
                    os.dup2(saved_fds[1], 2)
                for descriptor in saved_fds:
                    with contextlib.suppress(OSError):
                        os.close(descriptor)
            if null_fd is not None:
                with contextlib.suppress(OSError):
                    os.close(null_fd)


def _age_encrypt(payload: bytes, recipient: str, age_bin: str = "age") -> bytes:
    if recipient != REGISTERED_RECIPIENT:
        raise ValueError("recipient is not the registered public recipient")
    try:
        process = subprocess.Popen(
            [age_bin, "-r", recipient],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        encrypted, _error = process.communicate(payload)
    except (OSError, ValueError):
        raise SealingFailure("age encryption failed") from None
    if process.returncode != 0 or not encrypted:
        raise SealingFailure("age encryption failed")
    return encrypted


def _read_entropy() -> bytes:
    return os.urandom(ENTROPY_BYTES)


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(_json_bytes(value))
    temporary.replace(path)


def _file_record(path: Path, root: Path) -> dict[str, Any]:
    return {
        "name": str(path.relative_to(root)),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _write_failure(output: Path, phase: str) -> None:
    try:
        output.mkdir(parents=True, exist_ok=True)
        _write_json(
            output / "failure.json",
            {
                "schema_version": RECEIPT_SCHEMA,
                "status": "failed",
                "phase": phase,
                "error": "sealing failed; no private values recorded",
            },
        )
    except OSError:
        pass


def _validate_age_executable(age_bin: str, recipient: str) -> str:
    if recipient != REGISTERED_RECIPIENT:
        raise SealingFailure("recipient is not the registered public recipient")
    executable = shutil.which(age_bin)
    if executable is None or not os.access(executable, os.X_OK):
        raise SealingFailure("age executable is unavailable")
    try:
        probe = subprocess.run(
            [executable, "-r", recipient],
            input=b"goal060-public-age-probe",
            capture_output=True,
            check=False,
        )
    except (OSError, ValueError):
        raise SealingFailure("age recipient probe failed") from None
    if probe.returncode != 0 or not probe.stdout:
        raise SealingFailure("age recipient probe failed")
    return executable


def _validate_source_freeze(root: Path, source_manifest: Path, runtime_manifest: Path) -> None:
    source = json.loads(source_manifest.read_text(encoding="utf-8"))
    hashes = source.get("source_hashes")
    if not isinstance(hashes, Mapping) or not hashes:
        raise ValueError("source freeze must contain source_hashes")
    if source.get("runtime_sha256") != sha256_file(runtime_manifest):
        raise ValueError("source freeze runtime binding mismatch")
    source_root = (root / "source").resolve()
    for relative, expected in hashes.items():
        relative_path = Path(str(relative))
        candidate = (source_root / relative_path).resolve()
        if not candidate.is_relative_to(source_root) or not candidate.is_file():
            raise ValueError("source freeze path is invalid")
        if not isinstance(expected, str) or sha256_file(candidate) != expected:
            raise ValueError("source freeze hash mismatch")
    repository = Path(__file__).resolve().parents[2]
    for module in (sys.modules[__name__], public_api):
        loaded = Path(str(module.__file__)).resolve()
        relative = loaded.relative_to(repository).as_posix()
        frozen = source_root / relative
        if hashes.get(relative) != sha256_file(loaded) or not frozen.is_file():
            raise ValueError("running source is not bound to the frozen package")
        if sha256_file(frozen) != sha256_file(loaded):
            raise ValueError("frozen source does not match running source")
    runtime = json.loads(runtime_manifest.read_text(encoding="utf-8"))
    if (
        runtime.get("python_version") not in {platform.python_version(), sys.version}
        or runtime.get("platform") != platform.platform()
        or runtime.get("sys_version") != sys.version
        or runtime.get("numpy_version") != np.__version__
        or runtime.get("scipy_version") != SCIPY_VERSION
        or runtime.get("bit_generator") not in {"PCG64", "numpy.random.PCG64"}
    ):
        raise ValueError("runtime freeze does not match the running numerical stack")


def _validate_recovery(root: Path) -> None:
    recovery_path = root / "public_inputs" / "recovery.json"
    recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
    registration = (
        root / "source/docs/goals/060-capstone-certificate-recovery/registration-2026-10-04.md"
    )
    original_hashes = recovery.get("source_hashes")
    required_originals = {
        "accepted_candidate.json",
        "exposure.npz",
        "failed_attempts.json",
        "public_inputs.json",
        "public_inputs.npz",
        "seed_ledger.json",
    }
    if (
        recovery.get("schema_version") != RECOVERY_SCHEMA
        or recovery.get("state") != "qualified"
        or recovery.get("original_state") != "qualification_failed"
        or recovery.get("certificate_intervals") != 1024
        or not isinstance(recovery.get("certificate"), Mapping)
        or recovery["certificate"].get("passes") is not True
        or not isinstance(original_hashes, Mapping)
        or not required_originals.issubset(original_hashes)
        or recovery.get("registration_sha256") != sha256_file(registration)
    ):
        raise ValueError("public recovery certificate is not qualified")


def _validate_confirmatory_addresses(
    path: Path, source_manifest: Path, runtime_manifest: Path, registration: Path
) -> None:
    addresses = json.loads(path.read_text(encoding="utf-8"))
    if (
        addresses.get("root") != CONFIRMATORY_ROOT
        or addresses.get("namespace") != public_api.NAMESPACE
        or addresses.get("domains") != {"screen": 5, "effect": 6}
        or addresses.get("address_order")
        != ["root", "namespace", "domain", "node", "reference", "stage"]
        or addresses.get("screen_references") != 99
        or addresses.get("effect_references") != 999
        or addresses.get("node_count") != 765
        or addresses.get("source_manifest_sha256") != sha256_file(source_manifest)
        or addresses.get("runtime_sha256") != sha256_file(runtime_manifest)
        or addresses.get("registration_sha256") != sha256_file(registration)
    ):
        raise ValueError("confirmatory address contract is not registered")


def preflight_capstone(
    readiness_receipt: Path,
    *,
    age_bin: str = "age",
    expected_public_root: int = PUBLIC_ROOT,
    expected_bank_size: int = 131072,
) -> dict[str, Any]:
    readiness = validate_public_readiness(
        readiness_receipt,
        expected_public_root=expected_public_root,
        expected_bank_size=expected_bank_size,
    )
    _validate_age_executable(age_bin, REGISTERED_RECIPIENT)
    return readiness


def validate_public_readiness(
    readiness_receipt: Path,
    *,
    expected_public_root: int = PUBLIC_ROOT,
    expected_bank_size: int = 131072,
) -> dict[str, Any]:
    """Validate the finalized package-root readiness contract."""
    if readiness_receipt.name != "public-ready.json":
        raise ValueError("readiness receipt must be named public-ready.json")
    root = readiness_receipt.parent
    source_manifest = root / "source-manifest.json"
    runtime_manifest = root / "runtime.json"
    if not source_manifest.is_file() or not runtime_manifest.is_file():
        raise ValueError("source-manifest.json and runtime.json are required at package root")
    receipt = json.loads(readiness_receipt.read_text(encoding="utf-8"))
    if receipt.get("schema_version") != PUBLIC_READY_SCHEMA:
        raise ValueError("unsupported public readiness schema")
    required = (
        "public_ready",
        "source_manifest_sha256",
        "runtime_sha256",
        "files",
    )
    if any(key not in receipt for key in required) or receipt["public_ready"] is not True:
        raise ValueError("public readiness receipt is missing or negative")
    if receipt["source_manifest_sha256"] != sha256_file(source_manifest):
        raise ValueError("source manifest binding mismatch")
    if receipt["runtime_sha256"] != sha256_file(runtime_manifest):
        raise ValueError("runtime manifest binding mismatch")
    _validate_source_freeze(root, source_manifest, runtime_manifest)
    required_files = (
        "public_inputs/public_inputs.json",
        "public_inputs/public_inputs.npz",
        "public_inputs/exposure.npz",
        "public_inputs/seed_ledger.json",
        "public_inputs/recovery.json",
        "arrival_bank/manifest.json",
        "arrival_bank/arrivals.npy",
        "independent-audit/audit.json",
        "confirmatory-addresses.json",
        "source/docs/goals/060-capstone-certificate-recovery/registration-2026-10-04.md",
    )
    bindings = receipt["files"]
    if not isinstance(bindings, Mapping):
        raise ValueError("readiness file bindings must be a mapping")
    root_resolved = root.resolve()
    for relative, expected_hash in bindings.items():
        candidate = (root / str(relative)).resolve()
        if (
            not candidate.is_relative_to(root_resolved)
            or not candidate.is_file()
            or not isinstance(expected_hash, str)
            or sha256_file(candidate) != expected_hash
        ):
            raise ValueError(f"readiness file binding mismatch: {relative}")
    for relative in required_files:
        if relative not in bindings:
            raise ValueError(f"readiness file binding mismatch: {relative}")
    _validate_recovery(root)
    _validate_confirmatory_addresses(
        root / "confirmatory-addresses.json",
        source_manifest,
        runtime_manifest,
        root / "source/docs/goals/060-capstone-certificate-recovery/registration-2026-10-04.md",
    )
    public_inputs_dir = root / "public_inputs"
    public = public_api.load_public_inputs(public_inputs_dir)
    if (
        public.metadata.get("root") != expected_public_root
        or public.metadata.get("namespace") != public_api.NAMESPACE
    ):
        raise ValueError("public input root is not the registered root")
    audit = json.loads((root / "independent-audit" / "audit.json").read_text(encoding="utf-8"))
    source_freeze = audit.get("source_freeze")
    confirmatory = audit.get("confirmatory_addresses")
    if (
        audit.get("schema_version") != "goal060-independent-public-audit-v1"
        or audit.get("status") != "completed"
        or audit.get("audit_passed") is not True
        or audit.get("scientific_qualification_passed") is not True
        or not isinstance(source_freeze, Mapping)
        or source_freeze.get("source_manifest_sha256") != sha256_file(source_manifest)
        or source_freeze.get("runtime_sha256") != sha256_file(runtime_manifest)
        or not isinstance(audit.get("arrival_bank"), Mapping)
        or not isinstance(audit.get("panel_results"), Mapping)
        or not isinstance(audit.get("calibration_fixture"), Mapping)
        or not isinstance(confirmatory, Mapping)
        or confirmatory.get("passed") is not True
        or confirmatory.get("root") != CONFIRMATORY_ROOT
        or confirmatory.get("contract_sha256") != bindings["confirmatory-addresses.json"]
    ):
        raise ValueError("independent scientific audit has not passed")
    bank_manifest_path = root / "arrival_bank" / "manifest.json"
    bank_manifest = json.loads(bank_manifest_path.read_text(encoding="utf-8"))
    arrivals_path = root / "arrival_bank" / "arrivals.npy"
    arrivals = np.load(arrivals_path, mmap_mode="r", allow_pickle=False)
    if (
        bank_manifest.get("root") != expected_public_root
        or bank_manifest.get("namespace") != public_api.NAMESPACE
        or bank_manifest.get("stage") != public_api.BANK_STAGE
        or bank_manifest.get("bank_size") != expected_bank_size
        or bank_manifest.get("site_ids")
        != [str(site_id) for site_id in sorted(public.setup.site_ids)]
        or bank_manifest.get("public_input_array_sha256") != public.metadata.get("array_sha256")
        or bank_manifest.get("map_a_sha256") != public.metadata.get("map_a_sha256")
        or bank_manifest.get("array_shape") != [expected_bank_size, SITE_COUNT]
        or tuple(arrivals.shape) != (expected_bank_size, SITE_COUNT)
        or bank_manifest.get("arrivals_file_sha256") != sha256_file(arrivals_path)
        or bank_manifest.get("array_sha256")
        != hashlib.sha256(np.ascontiguousarray(arrivals).view(np.uint8)).hexdigest()
    ):
        raise ValueError("qualified arrival bank binding failed")
    return {
        "public_ready": True,
        "public_root": expected_public_root,
        "source_manifest_sha256": receipt["source_manifest_sha256"],
        "runtime_sha256": receipt["runtime_sha256"],
        "public_inputs_sha256": bindings["public_inputs/public_inputs.npz"],
        "qualified_bank_sha256": bindings["arrival_bank/manifest.json"],
        "independent_audit_sha256": bindings["independent-audit/audit.json"],
        "readiness_receipt_sha256": sha256_file(readiness_receipt),
        "package_root": str(root),
    }


def _publish(
    output: Path,
    stage: Path,
    *,
    readiness: Mapping[str, Any],
    truth_plain: bytes,
    holdout_plain: bytes,
    training_bytes: bytes,
    training_manifest: bytes,
    truth_cipher: bytes,
    holdout_cipher: bytes,
) -> dict[str, Any]:
    (stage / "training_observations.npz").write_bytes(training_bytes)
    (stage / "training_manifest.json").write_bytes(training_manifest)
    (stage / "truth.tar.age").write_bytes(truth_cipher)
    (stage / "holdout.tar.age").write_bytes(holdout_cipher)
    manifest = {
        "schema_version": RECEIPT_SCHEMA,
        "status": "sealed",
        "public_root": readiness["public_root"],
        "public_inputs_sha256": readiness["public_inputs_sha256"],
        "source_manifest_sha256": readiness["source_manifest_sha256"],
        "runtime_sha256": readiness["runtime_sha256"],
        "qualified_bank_sha256": readiness["qualified_bank_sha256"],
        "independent_audit_sha256": readiness["independent_audit_sha256"],
        "readiness_receipt_sha256": readiness["readiness_receipt_sha256"],
        "case_count": 4,
        "training_site_count": TRAINING_COUNT,
        "holdout_site_count": HOLDOUT_COUNT,
        "truth_archive_bytes": TRUTH_ARCHIVE_BYTES,
        "holdout_archive_bytes": HOLDOUT_ARCHIVE_BYTES,
        "commitments": {
            "truth_plain_sha256": sha256_bytes(truth_plain),
            "holdout_plain_sha256": sha256_bytes(holdout_plain),
            "truth_cipher_sha256": sha256_bytes(truth_cipher),
            "holdout_cipher_sha256": sha256_bytes(holdout_cipher),
        },
    }
    _write_json(stage / "sealed_manifest.json", manifest)
    receipt = {
        **manifest,
        "files": [
            _file_record(stage / name, stage)
            for name in (
                "training_observations.npz",
                "training_manifest.json",
                "truth.tar.age",
                "holdout.tar.age",
                "sealed_manifest.json",
            )
        ],
    }
    _write_json(stage / "seal_receipt.json", receipt)
    stage.replace(output)
    return receipt


def seal_capstone(
    readiness_receipt: Path,
    output: Path,
    *,
    recipient: str = REGISTERED_RECIPIENT,
    age_bin: str = "age",
    expected_public_root: int = PUBLIC_ROOT,
    expected_bank_size: int = 131072,
) -> dict[str, Any]:
    """Seal the four histories after public readiness has passed."""
    if output.exists():
        raise FileExistsError("refusing to overwrite an existing sealing output")
    stage = output.parent / f".{output.name}.staging"
    if stage.exists():
        raise FileExistsError("refusing to reuse an existing sealing staging directory")
    try:
        readiness = preflight_capstone(
            readiness_receipt,
            age_bin=age_bin,
            expected_public_root=expected_public_root,
            expected_bank_size=expected_bank_size,
        )
    except Exception:
        _write_failure(output, "preflight")
        raise SealingFailure("public readiness failed") from None
    try:
        public = public_api.load_public_inputs(readiness_receipt.parent / "public_inputs")
        output.parent.mkdir(parents=True, exist_ok=True)
        stage.mkdir()
        with _private_section():
            entropy = _read_entropy()
            root, truth_salt, holdout_salt = (
                entropy[:SALT_BYTES],
                entropy[SALT_BYTES : 2 * SALT_BYTES],
                entropy[2 * SALT_BYTES :],
            )
            _check_private_root(root)
            cases = _generate_cases(public, root)
            truth_plain = _build_truth_tar(root, truth_salt, cases)
            holdout_plain = _build_holdout_tar(public, holdout_salt, cases)
            training_bytes, training_manifest = _build_training_package(public, cases)
            truth_cipher = _age_encrypt(truth_plain, recipient, age_bin)
            holdout_cipher = _age_encrypt(holdout_plain, recipient, age_bin)
            return _publish(
                output,
                stage,
                readiness=readiness,
                truth_plain=truth_plain,
                holdout_plain=holdout_plain,
                training_bytes=training_bytes,
                training_manifest=training_manifest,
                truth_cipher=truth_cipher,
                holdout_cipher=holdout_cipher,
            )
    except FileExistsError:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        _write_failure(output, "private")
        raise SealingFailure("sealing failed") from None


def output_records(output: Path) -> list[dict[str, Any]]:
    return [_file_record(path, output) for path in sorted(output.iterdir()) if path.is_file()]


__all__ = [
    "BETA_VALUES",
    "CONFIRMATORY_ROOT",
    "HOLDOUT_ARCHIVE_BYTES",
    "MU_VALUES",
    "PUBLIC_ROOT",
    "REGISTERED_RECIPIENT",
    "SD_VALUES",
    "STREAM_STAGES",
    "TRUTH_ARCHIVE_BYTES",
    "SealingFailure",
    "_address_seed",
    "_age_encrypt",
    "_build_holdout_tar",
    "_build_training_package",
    "_build_truth_tar",
    "_check_private_root",
    "_draw_truths",
    "_generate_cases",
    "_read_entropy",
    "fixture_streams",
    "output_records",
    "preflight_capstone",
    "seal_capstone",
    "sha256_bytes",
    "sha256_file",
    "validate_public_readiness",
]
