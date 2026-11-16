"""Atomic, identity-bound fit checkpoints; no serialized executable objects."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np


class CheckpointError(OSError):
    pass


def encode(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return encode(value.tolist())
    if isinstance(value, np.generic):
        return encode(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return {"__nonfinite_float__": repr(value)}
    if isinstance(value, dict):
        return {str(k): encode(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [encode(v) for v in value]
    return value


def decode(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {"__nonfinite_float__"}:
            return float(value["__nonfinite_float__"])
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(encode(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        json.dump(encode(value), handle, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


class FitCheckpoints:
    def __init__(
        self,
        directory: Path,
        identity: dict[str, Any],
        *,
        resume: bool,
        origin: dict[str, Any] | None = None,
    ):
        self.directory = directory
        self.identity = identity
        self.identity_sha256 = digest(identity)
        header = directory / "identity.json"
        if header.exists():
            if not resume:
                raise FileExistsError("checkpoint exists; use --resume")
            saved = self._read(header)
            if saved.get("header_sha256") != digest(
                {k: v for k, v in saved.items() if k != "header_sha256"}
            ):
                raise CheckpointError("checkpoint identity header hash differs")
            if saved["identity_sha256"] != self.identity_sha256 or saved["identity"] != identity:
                raise CheckpointError(
                    "checkpoint source, input, runtime or search contract differs"
                )
            self.origin = saved["origin"]
            for path in sorted(directory.rglob("*.json")):
                if path != header:
                    self.load(str(path.relative_to(directory).with_suffix("")))
        else:
            if resume:
                raise CheckpointError("resume checkpoint identity is missing")
            if directory.exists() and any(directory.iterdir()):
                raise CheckpointError("checkpoint directory is not empty")
            self.origin = origin or {}
            value = {
                "schema": "fit-checkpoint-identity-v1",
                "identity": identity,
                "identity_sha256": self.identity_sha256,
                "origin": self.origin,
            }
            value["header_sha256"] = digest(value)
            atomic_json(header, value)

    @staticmethod
    def _read(path: Path) -> Any:
        try:
            return decode(json.loads(path.read_text()))
        except (OSError, ValueError) as error:
            raise CheckpointError(f"unreadable checkpoint: {path.name}") from error

    def load(self, name: str) -> Any | None:
        path = self.directory / (name + ".json")
        if not path.exists():
            return None
        saved = self._read(path)
        if saved.get("identity_sha256") != self.identity_sha256:
            raise CheckpointError("checkpoint identity binding differs")
        payload = saved.get("payload")
        if saved.get("payload_sha256") != digest(payload):
            raise CheckpointError("checkpoint payload hash differs")
        return payload

    def save(self, name: str, payload: Any) -> None:
        atomic_json(
            self.directory / (name + ".json"),
            {
                "identity_sha256": self.identity_sha256,
                "payload_sha256": digest(payload),
                "payload": payload,
            },
        )


def scientific_payload(value: Any, *, artifact: str = "fit") -> Any:
    """Canonical equivalence excludes only declared execution diagnostics.

    Explicit timing/RSS/cache counters are performance telemetry affected by
    restarting a process. Mode/PD failures, branch reasons and all other
    scientific counters remain strict. Artifact paths and raw hashes
    of timing-bearing artifacts are omitted; their numerical contents are
    compared separately. Candidate iterations, evaluations, eligibility, model
    parameters, gradients and all scientific flags remain unchanged.
    """
    paths: dict[str, set[tuple[str, ...]]] = {
        "fit": {
            ("host",),
            ("checkpoint_origin_host",),
            ("cost", "stages"),
            ("cost", "total_wall_seconds"),
            ("cost", "total_cpu_seconds"),
            ("cost", "peak_rss_bytes"),
            ("search", "cost", "elapsed_seconds"),
            ("search", "receipt"),
            ("search", "receipt_sha256"),
            ("search", "seconds_before_tight_phase"),
            ("latent_audit", "wall_seconds"),
            ("latent_audit", "cpu_seconds"),
            ("latent_audit", "rows", "*", "seconds"),
        },
        "search": {
            ("cost", "search", "elapsed_seconds"),
            ("cost", "post_search_seconds"),
            ("cost", "process_peak_rss_bytes"),
            ("evaluation_stream",),
        },
        "events": {("*", "elapsed_seconds")},
    }
    if artifact not in paths:
        raise ValueError("unknown scientific artifact")
    stats_prefix = ("cost", "criterion_stats") if artifact == "fit" else ("criterion_stats",)
    backend_prefix = (
        ("cost", "backend_diagnostics") if artifact == "fit" else ("backend_diagnostics",)
    )
    for field in (
        "curve_builds",
        "curve_seconds",
        "curve_cache_evictions",
        "integration_cache_evictions",
        "nuisance_site_seconds",
    ):
        paths[artifact].add((*stats_prefix, field))
    paths[artifact].add((*backend_prefix, "evaluator_instances"))

    def clean(item: Any, path: tuple[str, ...]) -> Any:
        if isinstance(item, dict):
            return {
                k: clean(v, (*path, k))
                for k, v in item.items()
                if (*path, k) not in paths[artifact]
            }
        if isinstance(item, (list, tuple)):
            return [clean(v, (*path, "*")) for v in item]
        return item

    return clean(value, ())
