from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from latent_landscapes import capstone_public as cap
from latent_landscapes import preinvasion_likelihood as likelihood


def _module() -> Any:
    path = Path(__file__).resolve().parents[1] / "scripts/prepare_profile_sensitivity_banks.py"
    spec = importlib.util.spec_from_file_location("profile_sensitivity_banks_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def public_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("sensitivity-public") / "inputs"
    cap.freeze_public_inputs(path, root=987654321)
    return path


def test_offset_addresses_preserve_seed_rule_and_separate_original_rows() -> None:
    module = _module()
    original = module.row_seeds(987654321, 0, 8)
    fresh = module.row_seeds(987654321, 8, 16)
    assert not set(original).intersection(fresh)
    expected = np.asarray(
        [
            np.random.SeedSequence([987654321, 59, 3, row]).generate_state(1, dtype=np.uint64)[0]
            for row in range(8, 24)
        ]
    )
    np.testing.assert_array_equal(fresh, expected)
    np.testing.assert_array_equal(fresh[:8], module.row_seeds(987654321, 8, 8))
    np.testing.assert_array_equal(fresh[8:], module.row_seeds(987654321, 16, 8))


def test_serial_spawn_and_derivation_preserve_rows_and_pseudo_mass(
    tmp_path: Path, public_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _module()

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("arrival-bank generation must not reconstruct exposure or setup")

    monkeypatch.setattr(cap, "load_public_inputs", forbidden)
    monkeypatch.setattr(cap, "build_generator_setup", forbidden)
    serial = module.generate_bank(
        public_dir, tmp_path / "serial", row_start=8, bank_size=4, workers=1, chunk_size=3
    )
    parallel = module.generate_bank(
        public_dir, tmp_path / "parallel", row_start=8, bank_size=4, workers=2, chunk_size=2
    )
    assert serial["array_sha256"] == parallel["array_sha256"]
    assert parallel["state"] == "complete"
    assert sum(row["rows"] for row in parallel["chunks"]) == 4
    assert parallel["input_sha256"][str((public_dir / "public_inputs.json").resolve())] == (
        module._sha(public_dir / "public_inputs.json")
    )
    with np.load(tmp_path / "parallel/seed_ledger.npz") as ledger:
        np.testing.assert_array_equal(ledger["row_addresses"], np.arange(8, 12))
        np.testing.assert_array_equal(ledger["seeds"], module.row_seeds(987654321, 8, 4))
    with pytest.raises(FileExistsError, match="refusing"):
        module.generate_bank(public_dir, tmp_path / "parallel", row_start=8, bank_size=4, workers=1)
    derived = module.derive_banks(tmp_path / "parallel", tmp_path / "derived", half_size=2)
    pooled = np.load(tmp_path / "parallel/arrivals.npy")
    for name, selection in (("A", slice(0, 2)), ("B", slice(2, 4)), ("AB", slice(0, 4))):
        raw = np.load(tmp_path / f"derived/{name}/arrivals.npy")
        np.testing.assert_array_equal(raw, pooled[selection])
        product = derived["products"][name]
        assert product["normalization_denominator"] == len(raw) + 7
        expected = likelihood.compress_bank(raw, serial["site_ids"], series_order=192)
        with np.load(tmp_path / f"derived/{name}/compressed.npz") as compressed:
            np.testing.assert_array_equal(compressed["power_moments"], expected.power_moments)
            np.testing.assert_array_equal(compressed["category_mass"], expected.category_mass)
            assert compressed["bank_checksum"].item() == expected.bank_checksum
            assert compressed["max_x"].item() == 40.0
    with pytest.raises(FileExistsError, match="refusing"):
        module.derive_banks(tmp_path / "parallel", tmp_path / "derived", half_size=2)
    with (tmp_path / "parallel/arrivals.npy").open("ab") as handle:
        handle.write(b"identity changed")
    with pytest.raises(ValueError, match="identity changed"):
        module.derive_banks(tmp_path / "parallel", tmp_path / "tampered", half_size=2)
    assert not (tmp_path / "tampered").exists()


def test_rejects_public_identity_failure_before_output(
    tmp_path: Path, public_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _module()
    original_load = module.load_arrival_inputs

    def drift(path: Path) -> Any:
        public = original_load(path)
        metadata_path = path / "public_inputs.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["test_drift"] = True
        metadata_path.write_text(json.dumps(metadata))
        return public

    copied = tmp_path / "public"
    shutil.copytree(public_dir, copied)
    monkeypatch.setattr(module, "load_arrival_inputs", drift)
    with pytest.raises(ValueError, match="identity changed"):
        module.generate_bank(copied, tmp_path / "output", row_start=8, bank_size=2, workers=1)
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "field, value",
    [
        ("state", "qualification_failed"),
        ("schema_version", "other"),
        ("namespace", 58),
        ("root", -1),
        ("map_seed", 1),
    ],
)
def test_arrival_loader_rejects_metadata_and_seed_changes(
    tmp_path: Path, public_dir: Path, field: str, value: Any
) -> None:
    module = _module()
    copied = tmp_path / "public"
    shutil.copytree(public_dir, copied)
    path = copied / "public_inputs.json"
    metadata = json.loads(path.read_text())
    metadata[field] = value
    path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError):
        module.load_arrival_inputs(copied)


@pytest.mark.parametrize("change", ["dtype", "shape", "value", "keys"])
def test_arrival_loader_checks_frozen_array_identity_beyond_file_hash(
    tmp_path: Path, public_dir: Path, change: str
) -> None:
    module = _module()
    copied = tmp_path / "public"
    shutil.copytree(public_dir, copied)
    archive = copied / "public_inputs.npz"
    with np.load(archive) as frozen:
        arrays = {name: frozen[name] for name in frozen.files}
    if change == "dtype":
        arrays["site_rows"] = arrays["site_rows"].astype(np.int32)
    elif change == "shape":
        arrays["site_rows"] = arrays["site_rows"][None, :]
    elif change == "value":
        arrays["site_rows"][0] += 1
    else:
        arrays["extra"] = np.array([1])
    np.savez_compressed(archive, **arrays)
    path = copied / "public_inputs.json"
    metadata = json.loads(path.read_text())
    metadata["public_inputs_sha256"] = module._sha(archive)
    path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="fixed-array"):
        module.load_arrival_inputs(copied)
