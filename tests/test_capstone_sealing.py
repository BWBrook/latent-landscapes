from __future__ import annotations

import hashlib
import importlib.metadata
import io
import json
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes import capstone_public as cap
from latent_landscapes import capstone_sealing as sealing
from latent_landscapes.misspecification_generator import build_generator_setup

MECHANICAL_ROOT = 987654321


def _public() -> cap.PublicInputs:
    map_seed = cap._u64_seed(MECHANICAL_ROOT, cap.MAP_STAGE, 0)
    sampling_seed = cap._u64_seed(MECHANICAL_ROOT, cap.SAMPLING_STAGE, 0)
    fixed = cap._make_fixed(map_seed, sampling_seed)
    return cap.PublicInputs(fixed, build_generator_setup(fixed), {"root": MECHANICAL_ROOT})


def _ready_tree(tmp_path: Path, bank_size: int = 8) -> Path:
    root = tmp_path
    public_dir = root / "public_inputs"
    cap.freeze_public_inputs(public_dir, root=MECHANICAL_ROOT)
    recovery = {
        "schema_version": "goal060-public-recovery-v1",
        "state": "qualified",
        "original_state": "qualification_failed",
        "certificate_intervals": 1024,
        "certificate": {"passes": True},
        "source_hashes": {
            name: "mechanical"
            for name in (
                "accepted_candidate.json",
                "exposure.npz",
                "failed_attempts.json",
                "public_inputs.json",
                "public_inputs.npz",
                "seed_ledger.json",
            )
        },
    }
    (public_dir / "recovery.json").write_text(json.dumps(recovery) + "\n", encoding="utf-8")
    public = cap.load_public_inputs(public_dir)
    bank_dir = root / "arrival_bank"
    bank_dir.mkdir()
    arrivals = np.zeros((bank_size, 160), dtype=np.float64)
    np.save(bank_dir / "arrivals.npy", arrivals)
    bank_manifest = {
        "root": MECHANICAL_ROOT,
        "namespace": cap.NAMESPACE,
        "stage": cap.BANK_STAGE,
        "bank_size": bank_size,
        "site_ids": [str(site_id) for site_id in sorted(public.setup.site_ids)],
        "public_input_array_sha256": public.metadata["array_sha256"],
        "map_a_sha256": public.metadata["map_a_sha256"],
        "array_shape": [bank_size, 160],
        "array_sha256": hashlib.sha256(np.ascontiguousarray(arrivals).view(np.uint8)).hexdigest(),
        "arrivals_file_sha256": sealing.sha256_file(bank_dir / "arrivals.npy"),
    }
    (bank_dir / "manifest.json").write_text(json.dumps(bank_manifest), encoding="utf-8")
    audit_dir = root / "independent-audit"
    audit_dir.mkdir()
    (audit_dir / "audit.json").write_text("{}\n", encoding="utf-8")
    (root / "confirmatory-addresses.json").write_text(
        json.dumps(
            {
                "root": sealing.CONFIRMATORY_ROOT,
                "namespace": cap.NAMESPACE,
                "domains": {"screen": 5, "effect": 6},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    registration = root / "source" / "docs/goals/060-capstone-certificate-recovery"
    registration.mkdir(parents=True)
    (registration / "registration-2026-10-04.md").write_text("registration\n", encoding="utf-8")
    source_manifest = root / "source-manifest.json"
    runtime_manifest = root / "runtime.json"
    source_root = root / "source"
    repository = Path(__file__).resolve().parents[1]
    for module in (sealing, cap):
        loaded = Path(str(module.__file__)).resolve()
        relative = loaded.relative_to(repository)
        target = source_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(loaded, target)
    runtime_manifest.write_text(
        json.dumps(
            {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "sys_version": sys.version,
                "numpy_version": np.__version__,
                "scipy_version": importlib.metadata.version("scipy"),
                "bit_generator": "PCG64",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    source_hashes = {
        relative: sealing.sha256_file(source_root / relative)
        for relative in (
            "src/latent_landscapes/capstone_sealing.py",
            "src/latent_landscapes/capstone_public.py",
        )
    }
    source_manifest.write_text(
        json.dumps(
            {
                "source_hashes": source_hashes,
                "runtime_sha256": sealing.sha256_file(runtime_manifest),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "confirmatory-addresses.json").write_text(
        json.dumps(
            {
                "root": sealing.CONFIRMATORY_ROOT,
                "namespace": cap.NAMESPACE,
                "domains": {"screen": 5, "effect": 6},
                "address_order": ["root", "namespace", "domain", "node", "reference", "stage"],
                "screen_references": 99,
                "effect_references": 999,
                "node_count": 765,
                "source_manifest_sha256": sealing.sha256_file(source_manifest),
                "runtime_sha256": sealing.sha256_file(runtime_manifest),
                "registration_sha256": sealing.sha256_file(
                    registration / "registration-2026-10-04.md"
                ),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    recovery["registration_sha256"] = sealing.sha256_file(
        registration / "registration-2026-10-04.md"
    )
    (public_dir / "recovery.json").write_text(json.dumps(recovery) + "\n", encoding="utf-8")
    (audit_dir / "audit.json").write_text(
        json.dumps(
            {
                "schema_version": "goal060-independent-public-audit-v1",
                "status": "completed",
                "audit_passed": True,
                "scientific_qualification_passed": True,
                "source_freeze": {
                    "source_manifest_sha256": sealing.sha256_file(source_manifest),
                    "runtime_sha256": sealing.sha256_file(runtime_manifest),
                },
                "arrival_bank": {},
                "panel_results": {},
                "calibration_fixture": {},
                "confirmatory_addresses": {
                    "passed": True,
                    "root": sealing.CONFIRMATORY_ROOT,
                    "contract_sha256": sealing.sha256_file(root / "confirmatory-addresses.json"),
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    files = {}
    for path in (
        public_dir / "public_inputs.json",
        public_dir / "public_inputs.npz",
        public_dir / "exposure.npz",
        public_dir / "seed_ledger.json",
        public_dir / "recovery.json",
        bank_dir / "manifest.json",
        bank_dir / "arrivals.npy",
        audit_dir / "audit.json",
        root / "confirmatory-addresses.json",
        registration / "registration-2026-10-04.md",
    ):
        files[str(path.relative_to(root))] = sealing.sha256_file(path)
    readiness = root / "public-ready.json"
    readiness.write_text(
        json.dumps(
            {
                "schema_version": "goal060-public-ready-v1",
                "public_ready": True,
                "source_manifest_sha256": sealing.sha256_file(source_manifest),
                "runtime_sha256": sealing.sha256_file(runtime_manifest),
                "files": files,
            }
        ),
        encoding="utf-8",
    )
    return readiness


def test_truth_law_and_private_stream_addresses_are_deterministic() -> None:
    root = MECHANICAL_ROOT.to_bytes(32, "little")
    first = sealing._draw_truths(root)
    second = sealing._draw_truths(root)
    assert first == second
    assert len(first) == 4
    assert [row["index"] for row in first] == list(range(4))
    assert all(row["mean_hazard"] in sealing.MU_VALUES for row in first)
    assert all(row["detection_sd"] in sealing.SD_VALUES for row in first)
    for row in first:
        assert set(row["streams"]) == set(sealing.STREAM_STAGES)
        assert len(set(row["streams"].values())) == 6
        if row["background"] == "exact":
            assert row["beta"] in sealing.BETA_VALUES
        else:
            assert row["beta"] is None
        assert 1.0 <= row["effect"] <= 5.0


def test_registered_public_roots_cannot_be_private_roots() -> None:
    for value in (sealing.PUBLIC_ROOT, sealing.CONFIRMATORY_ROOT):
        for byteorder in ("little", "big"):
            with pytest.raises(sealing.SealingFailure):
                sealing._check_private_root(value.to_bytes(32, byteorder))
    sealing._check_private_root(MECHANICAL_ROOT.to_bytes(32, "little"))


def test_public_generator_replay_keeps_full_site_arrays_and_split_containment() -> None:
    public = _public()
    root = MECHANICAL_ROOT.to_bytes(32, "little")
    first = sealing._generate_cases(public, root)
    second = sealing._generate_cases(public, root)
    assert len(first) == len(second) == 4
    training = np.asarray(public.setup.site_splits) == "training"
    assert int(training.sum()) == 120
    for left, right in zip(first, second, strict=True):
        assert left["truth"] == right["truth"]
        np.testing.assert_array_equal(
            left["observed"]["prey_counts"], right["observed"]["prey_counts"]
        )
        np.testing.assert_array_equal(
            left["observed"]["predator_counts"], right["observed"]["predator_counts"]
        )
        assert left["observed"]["prey_counts"].shape == (160, 13)
        assert left["observed"]["predator_counts"].shape == (160, 6)
    training_bytes, manifest = sealing._build_training_package(public, first)
    assert json.loads(manifest)["site_count"] == 120
    with np.load(io.BytesIO(training_bytes), allow_pickle=False) as values:
        assert set(values.files) == {"case_ids", "site_ids", "prey_counts", "predator_counts"}
        assert values["prey_counts"].shape == (4, 120, 13)
        assert values["predator_counts"].shape == (4, 120, 6)
        assert values["site_ids"].shape == (120,)
        assert all(
            str(site) in set(np.asarray(public.setup.site_ids)[training])
            for site in values["site_ids"]
        )


def test_salted_archives_are_separate_and_training_has_no_private_fields() -> None:
    public = _public()
    root = MECHANICAL_ROOT.to_bytes(32, "little")
    cases = sealing._generate_cases(public, root)
    truth_a = sealing._build_truth_tar(root, b"a" * 32, cases)
    truth_b = sealing._build_truth_tar(root, b"b" * 32, cases)
    holdout_a = sealing._build_holdout_tar(public, b"a" * 32, cases)
    holdout_b = sealing._build_holdout_tar(public, b"b" * 32, cases)
    assert sealing.sha256_bytes(truth_a) != sealing.sha256_bytes(truth_b)
    assert sealing.sha256_bytes(holdout_a) != sealing.sha256_bytes(holdout_b)
    with tarfile.open(fileobj=io.BytesIO(truth_a), mode="r") as archive:
        names = archive.getnames()
        assert "private-root.bin" in names
        assert "truth-metadata.json" in names
        assert len([name for name in names if name.endswith("-latent.npz")]) == 4
    with tarfile.open(fileobj=io.BytesIO(holdout_a), mode="r") as archive:
        assert set(archive.getnames()) == {"holdout.npz", "padding.bin", "salt.bin"}
        extracted = archive.extractfile("holdout.npz")
        assert extracted is not None
        with np.load(extracted, allow_pickle=False) as values:
            assert values["prey_counts"].shape == (4, 40, 13)
            assert values["predator_counts"].shape == (4, 40, 6)
    assert len(truth_a) == sealing.TRUTH_ARCHIVE_BYTES
    assert len(holdout_a) == sealing.HOLDOUT_ARCHIVE_BYTES


def test_readiness_binds_all_public_hashes_before_entropy(tmp_path: Path) -> None:
    readiness = _ready_tree(tmp_path)
    checked = sealing.validate_public_readiness(
        readiness, expected_public_root=MECHANICAL_ROOT, expected_bank_size=8
    )
    assert checked["public_ready"]
    assert sealing.preflight_capstone(
        readiness, age_bin="age", expected_public_root=MECHANICAL_ROOT, expected_bank_size=8
    )["public_ready"]
    (tmp_path / "source-manifest.json").write_text('{"changed": true}\n', encoding="utf-8")
    with pytest.raises(ValueError):
        sealing.validate_public_readiness(
            readiness, expected_public_root=MECHANICAL_ROOT, expected_bank_size=8
        )


def test_readiness_rejects_failed_complete_audit_even_with_scientific_true(tmp_path: Path) -> None:
    readiness = _ready_tree(tmp_path)
    audit_path = tmp_path / "independent-audit" / "audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    audit["audit_passed"] = False
    audit_path.write_text(json.dumps(audit), encoding="utf-8")
    receipt = json.loads(readiness.read_text(encoding="utf-8"))
    receipt["files"]["independent-audit/audit.json"] = sealing.sha256_file(audit_path)
    readiness.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError):
        sealing.validate_public_readiness(
            readiness, expected_public_root=MECHANICAL_ROOT, expected_bank_size=8
        )


def test_readiness_checks_every_additional_file_binding(tmp_path: Path) -> None:
    readiness = _ready_tree(tmp_path)
    extra = tmp_path / "extra-bound.json"
    extra.write_text('{"bound": true}\n', encoding="utf-8")
    receipt = json.loads(readiness.read_text(encoding="utf-8"))
    receipt["files"]["extra-bound.json"] = sealing.sha256_file(extra)
    readiness.write_text(json.dumps(receipt), encoding="utf-8")
    sealing.validate_public_readiness(
        readiness, expected_public_root=MECHANICAL_ROOT, expected_bank_size=8
    )
    extra.write_text('{"tampered": true}\n', encoding="utf-8")
    with pytest.raises(ValueError):
        sealing.validate_public_readiness(
            readiness, expected_public_root=MECHANICAL_ROOT, expected_bank_size=8
        )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [("passed", False), ("root", 0), ("contract_sha256", "0" * 64)],
)
def test_readiness_requires_audited_confirmatory_contract(
    tmp_path: Path, field: str, replacement: object
) -> None:
    readiness = _ready_tree(tmp_path)
    audit_path = tmp_path / "independent-audit/audit.json"
    audit = json.loads(audit_path.read_text())
    audit["confirmatory_addresses"][field] = replacement
    audit_path.write_text(json.dumps(audit))
    receipt = json.loads(readiness.read_text())
    receipt["files"]["independent-audit/audit.json"] = sealing.sha256_file(audit_path)
    readiness.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="independent scientific audit has not passed"):
        sealing.validate_public_readiness(
            readiness, expected_public_root=MECHANICAL_ROOT, expected_bank_size=8
        )


def test_preflight_failure_preserves_generic_receipt_without_entropy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "failed"
    monkeypatch.setattr(sealing, "_read_entropy", lambda: (_ for _ in ()).throw(AssertionError()))
    with pytest.raises(sealing.SealingFailure):
        sealing.seal_capstone(
            tmp_path / "missing-readiness.json",
            output,
            expected_public_root=MECHANICAL_ROOT,
        )
    failure = (output / "failure.json").read_text(encoding="utf-8")
    assert "987654321" not in failure
    assert "root_hex" not in failure


def test_age_wrapper_accepts_only_ciphertext_and_hides_stderr(tmp_path: Path) -> None:
    fake = tmp_path / "fake-age"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "sys.stdin.buffer.read()\n"
        "sys.stderr.write('diagnostic\\n')\n"
        "sys.stdout.buffer.write(b'ciphertext')\n",
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    assert (
        sealing._age_encrypt(b"private", sealing.REGISTERED_RECIPIENT, str(fake)) == b"ciphertext"
    )


def test_age_round_trip_uses_only_sacrificial_test_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = tmp_path / "identity.age"
    generated = subprocess.run(
        ["age-keygen", "-o", str(identity)], check=True, capture_output=True, text=True
    )
    public_key = next(
        line.split(":", 1)[1].strip()
        for line in (generated.stdout + generated.stderr).splitlines()
        if line.startswith("Public key:")
    )
    monkeypatch.setattr(sealing, "REGISTERED_RECIPIENT", public_key)
    plaintext = b"sacrificial mechanical payload"
    ciphertext = sealing._age_encrypt(plaintext, public_key, "age")
    decrypted = subprocess.run(
        ["age", "-d", "-i", str(identity)], input=ciphertext, capture_output=True, check=True
    )
    assert decrypted.stdout == plaintext


def test_mechanical_seal_actual_age_roundtrip_uses_sacrificial_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readiness = _ready_tree(tmp_path / "ready")
    output = tmp_path / "sealed-age"
    identity = tmp_path / "identity.age"
    generated = subprocess.run(
        ["age-keygen", "-o", str(identity)], check=True, capture_output=True, text=True
    )
    public_key = next(
        line.split(":", 1)[1].strip()
        for line in (generated.stdout + generated.stderr).splitlines()
        if line.startswith("Public key:")
    )
    monkeypatch.setattr(sealing, "REGISTERED_RECIPIENT", public_key)
    monkeypatch.setattr(
        sealing,
        "_read_entropy",
        lambda: (MECHANICAL_ROOT).to_bytes(32, "little") + b"t" * 32 + b"h" * 32,
    )
    receipt = sealing.seal_capstone(
        readiness,
        output,
        recipient=public_key,
        age_bin="age",
        expected_public_root=MECHANICAL_ROOT,
        expected_bank_size=8,
    )
    manifest = json.loads((output / "sealed_manifest.json").read_text(encoding="utf-8"))
    for name, commitment in (
        ("truth.tar.age", "truth_plain_sha256"),
        ("holdout.tar.age", "holdout_plain_sha256"),
    ):
        decrypted = subprocess.run(
            ["age", "-d", "-i", str(identity)],
            input=(output / name).read_bytes(),
            capture_output=True,
            check=True,
        ).stdout
        assert sealing.sha256_bytes(decrypted) == manifest["commitments"][commitment]
    assert receipt["status"] == "sealed"
    assert not list(output.glob("*.tar"))


def test_mechanical_seal_is_single_entropy_and_publishes_only_ciphertexts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    readiness = _ready_tree(tmp_path / "ready")
    output = tmp_path / "sealed"
    fake = tmp_path / "fake-age-roundtrip"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "payload = sys.stdin.buffer.read()\n"
        "if '-r' in sys.argv: sys.stdout.buffer.write(b'cipher:' + payload)\n"
        "elif payload.startswith(b'cipher:'): sys.stdout.buffer.write(payload[7:])\n"
        "else: raise SystemExit(2)\n",
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    private_entropy = (MECHANICAL_ROOT).to_bytes(32, "little") + b"t" * 32 + b"h" * 32
    calls = 0

    def entropy() -> bytes:
        nonlocal calls
        calls += 1
        return private_entropy

    original_generate = sealing._generate_cases
    original_publish = sealing._publish

    def noisy_generate(public: cap.PublicInputs, root: bytes) -> tuple[dict[str, object], ...]:
        print("private-sentinel")
        import warnings

        warnings.warn("private-warning", stacklevel=1)
        return original_generate(public, root)

    def noisy_publish(*args: object, **kwargs: object) -> dict[str, object]:
        print("publish-private-sentinel")
        import warnings

        warnings.warn("publish-private-warning", stacklevel=1)
        return original_publish(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(sealing, "_read_entropy", entropy)
    monkeypatch.setattr(sealing, "_generate_cases", noisy_generate)
    monkeypatch.setattr(sealing, "_publish", noisy_publish)
    receipt = sealing.seal_capstone(
        readiness,
        output,
        age_bin=str(fake),
        expected_public_root=MECHANICAL_ROOT,
        expected_bank_size=8,
    )
    assert calls == 1
    assert capsys.readouterr().out == ""
    assert {path.name for path in output.iterdir()} == {
        "training_observations.npz",
        "training_manifest.json",
        "truth.tar.age",
        "holdout.tar.age",
        "sealed_manifest.json",
        "seal_receipt.json",
    }
    manifest = json.loads((output / "sealed_manifest.json").read_text(encoding="utf-8"))
    for name, commitment in (
        ("truth.tar.age", "truth_plain_sha256"),
        ("holdout.tar.age", "holdout_plain_sha256"),
    ):
        decrypted = subprocess.run(
            [str(fake), "-d"],
            input=(output / name).read_bytes(),
            capture_output=True,
            check=True,
        ).stdout
        assert sealing.sha256_bytes(decrypted) == manifest["commitments"][commitment]
    assert receipt["status"] == "sealed"


def test_output_refusal_happens_before_any_private_section(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    (output / "marker").write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        sealing.seal_capstone(
            tmp_path / "missing-readiness.json",
            output,
        )
    assert (output / "marker").read_text(encoding="utf-8") == "keep"


def test_private_baseexception_becomes_generic_failure_after_one_entropy_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readiness = _ready_tree(tmp_path / "ready")
    output = tmp_path / "interrupted"
    calls = 0

    def entropy() -> bytes:
        nonlocal calls
        calls += 1
        return (MECHANICAL_ROOT).to_bytes(32, "little") + b"t" * 32 + b"h" * 32

    def interrupted(public: cap.PublicInputs, root: bytes) -> tuple[dict[str, object], ...]:
        raise KeyboardInterrupt("private-sentinel")

    monkeypatch.setattr(sealing, "_read_entropy", entropy)
    monkeypatch.setattr(sealing, "_generate_cases", interrupted)
    with pytest.raises(sealing.SealingFailure):
        sealing.seal_capstone(
            readiness,
            output,
            expected_public_root=MECHANICAL_ROOT,
            expected_bank_size=8,
        )
    assert calls == 1
    failure = (output / "failure.json").read_text(encoding="utf-8")
    assert "private-sentinel" not in failure


def test_partial_age_failure_preserves_only_generic_failure_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readiness = _ready_tree(tmp_path / "ready")
    output = tmp_path / "age-failure"
    counter = tmp_path / "counter"
    fake = tmp_path / "fake-age-failure"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, sys\n"
        f"counter = pathlib.Path({str(counter)!r})\n"
        "count = int(counter.read_text()) if counter.exists() else 0\n"
        "counter.write_text(str(count + 1))\n"
        "payload = sys.stdin.buffer.read()\n"
        "if count == 0: sys.stdout.buffer.write(b'cipher:' + payload)\n"
        "else: sys.stderr.write('secret-age-diagnostic\\n'); raise SystemExit(7)\n",
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(
        sealing,
        "_read_entropy",
        lambda: (MECHANICAL_ROOT).to_bytes(32, "little") + b"t" * 32 + b"h" * 32,
    )
    with pytest.raises(sealing.SealingFailure):
        sealing.seal_capstone(
            readiness,
            output,
            age_bin=str(fake),
            expected_public_root=MECHANICAL_ROOT,
            expected_bank_size=8,
        )
    assert [path.name for path in output.iterdir()] == ["failure.json"]
    assert "secret-age-diagnostic" not in (output / "failure.json").read_text(encoding="utf-8")
