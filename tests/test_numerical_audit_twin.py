from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest


@pytest.mark.parametrize("correct_prefix", [True, False])
def test_only_a_live_stopped_worker_with_its_registered_prefix_certifies_the_kill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, correct_prefix: bool
) -> None:
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    twin: Any = importlib.import_module("run_numerical_audit_twin")
    store = tmp_path / "checkpoints"
    (store / "audit").mkdir(parents=True)
    for index in range(twin.STOP):
        (store / f"audit/row-{index:06d}.json").write_text(str(index))
    supplied = twin.prefix(store) if correct_prefix else "wrong-prefix"
    job = "123.test"
    code = """
import json, os, signal, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from run_interrupted_twin import seal
value = json.loads(sys.argv[3])
seal(Path(sys.argv[2]) / 'paused.json', {**value, 'pid': os.getpid()})
os.kill(os.getpid(), signal.SIGSTOP)
"""
    binding = {"test": "native-process"}
    data = {
        "binding": binding,
        "job": job,
        "row_index": twin.STOP,
        "row": {"performed": True},
        "prefix_sha256": supplied,
    }
    cmd = [sys.executable, "-c", code, str(scripts), str(tmp_path), json.dumps(data)]
    if correct_prefix:
        twin.interrupt_child(cmd, tmp_path, store, binding, job)
        result = twin.legacy.unseal(tmp_path / "killed.json")
        assert result["signal_exit"] == -9
        assert result["prefix_sha256"] == twin.prefix(store)
    else:
        with pytest.raises(ValueError, match="interruption witness"):
            twin.interrupt_child(cmd, tmp_path, store, binding, job)
        assert not (tmp_path / "killed.json").exists()
