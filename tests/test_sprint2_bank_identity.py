from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def generator(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("generate_history")


def manifest(generator, tmp_path, replicate):
    record = {"spawn_key": [1, 2, 3]}
    seeds = generator.bank_seeds(record, 32, replicate)
    raw = tmp_path / f"raw-{replicate}"
    compressed = tmp_path / f"compressed-{replicate}"
    raw.write_bytes(seeds.tobytes())
    compressed.write_bytes(b"compressed" + seeds.tobytes())
    result = {
        "schema": "sprint2-map-arrival-bank-v1",
        "map": record,
        "map_input_sha256": {"input": "a" * 64},
        "bank_size": 32,
        "series_order": 192,
        "bank_replicate": replicate,
        "seed_sha256": hashlib.sha256(seeds.astype("<u8").tobytes()).hexdigest(),
        "raw": str(raw),
        "compressed": str(compressed),
        "raw_sha256": generator.sha256(raw),
        "compressed_sha256": generator.sha256(compressed),
    }
    path = tmp_path / f"manifest-{replicate}.json"
    path.write_text(json.dumps(result))
    return path


def test_bank_replicates_reconstruct_and_do_not_overlap(generator):
    record = {"spawn_key": [1, 2, 3]}
    first = generator.bank_seeds(record, 128, 0)
    second = generator.bank_seeds(record, 128, 1)
    np.testing.assert_array_equal(first[:64], generator.bank_seeds(record, 64, 0))
    assert not np.intersect1d(first, second).size
    with pytest.raises(ValueError):
        generator.bank_seeds(record, 1, -1)


def test_independent_bank_check_rejects_same_replicate_and_tampering(generator, tmp_path):
    left, right = manifest(generator, tmp_path, 0), manifest(generator, tmp_path, 1)
    generator.verify_independent_banks(left, right)
    with pytest.raises(ValueError, match="same replicate"):
        generator.verify_independent_banks(left, left)
    Path(json.loads(right.read_text())["raw"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="file hash"):
        generator.verify_independent_banks(left, right)
