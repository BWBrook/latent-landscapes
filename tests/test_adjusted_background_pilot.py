"""Identity and interrupted-write controls for the bounded row cache."""

from pathlib import Path

import numpy as np
import pytest

from latent_landscapes.adjusted_background_pilot import (
    ROW_SHAPES,
    load_row,
    save_row,
    verify_legacy_sources,
)


def test_authenticated_row_roundtrip_and_identity_rejection(tmp_path: Path) -> None:
    data, receipt_path = tmp_path / "row.npz", tmp_path / "row.json"
    values = {name: np.zeros(shape, dtype=np.float64) for name, shape in ROW_SHAPES.items()}
    receipt = {"fingerprint": "registered", "index": 40, "beta": 0.0, "seconds": 1.0}
    save_row(data, receipt_path, values, receipt)
    loaded = load_row(data, receipt_path, fingerprint="registered", index=40, beta=0.0)
    assert loaded is not None
    assert all(np.array_equal(loaded[0][name], value) for name, value in values.items())
    with pytest.raises(ValueError, match="identity"):
        load_row(data, receipt_path, fingerprint="changed-source", index=40, beta=0.0)
    with pytest.raises(ValueError, match="identity"):
        load_row(data, receipt_path, fingerprint="registered", index=41, beta=0.0)
    data.write_bytes(b"interrupted or altered payload")
    with pytest.raises(ValueError, match="identity"):
        load_row(data, receipt_path, fingerprint="registered", index=40, beta=0.0)


@pytest.mark.parametrize("bad", ["shape", "dtype", "nonfinite", "key"])
def test_even_authenticated_bad_row_schema_is_rejected(tmp_path: Path, bad: str) -> None:
    data, receipt_path = tmp_path / "row.npz", tmp_path / "row.json"
    values = {name: np.zeros(shape, dtype=np.float64) for name, shape in ROW_SHAPES.items()}
    if bad == "shape":
        values["latent_training"] = np.zeros((23, 181))
    elif bad == "dtype":
        values["latent_training"] = np.zeros((24, 181), dtype=np.float32)
    elif bad == "nonfinite":
        values["latent_training"][0, 0] = np.nan
    else:
        del values["latent_training"]
    save_row(data, receipt_path, values, {"fingerprint": "f", "index": 0, "beta": -2.0})
    with pytest.raises(ValueError, match=r"schema|values/shapes"):
        load_row(data, receipt_path, fingerprint="f", index=0, beta=-2.0)


def test_interrupted_pair_is_preserved_and_can_be_recomputed(tmp_path: Path) -> None:
    data, receipt = tmp_path / "row.npz", tmp_path / "row.json"
    data.write_bytes(b"old incomplete data")
    assert load_row(data, receipt, fingerprint="f", index=0, beta=-2.0) is None
    assert not data.exists()
    preserved = list(tmp_path.glob("row.npz.uncommitted-*"))
    assert len(preserved) == 1
    assert preserved[0].read_bytes() == b"old incomplete data"
    values = {name: np.zeros(shape, dtype=np.float64) for name, shape in ROW_SHAPES.items()}
    save_row(data, receipt, values, {"fingerprint": "f", "index": 0, "beta": -2.0})
    assert load_row(data, receipt, fingerprint="f", index=0, beta=-2.0) is not None


def test_untrusted_legacy_manifest_cannot_redefine_expected_hashes(tmp_path: Path) -> None:
    manifest = tmp_path / "run_contract.json"
    manifest.write_text('{"source_hashes": {}}')
    with pytest.raises(ValueError, match="run-contract digest"):
        verify_legacy_sources(tmp_path, manifest)
