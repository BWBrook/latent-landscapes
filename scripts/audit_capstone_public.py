#!/usr/bin/env python3
"""Independent numerical and provenance audit for Goal 059 public preparation.

The direct scorer is reused from the Goal 056 independent auditor.  This file
does not import the production pre-invasion likelihood, hazard normalizer,
fitter, public-preparation module, qualification module, or calibration module.
It never refits a model and never generates a registered public or sealed draw.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import platform
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from audit_preinvasion_feasibility import (
    DirectBank,
    direct_score,
    direct_survival_moments,
    normalized_hazards,
    predator_emissions,
    prey_factors,
)
from numpy.typing import NDArray

from latent_landscapes.arc3_design import build_sampling_pair
from latent_landscapes.arc3_landscapes import build_landscape
from latent_landscapes.goal006.spread import compute_contrast_spread, sample_edge_shock_vector
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.misspecification_generator import build_generator_setup

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

PUBLIC_ROOT = 2026100403
PUBLIC_NAMESPACE = 59
MAP_DOMAIN = 1
SAMPLING_DOMAIN = 2
BANK_DOMAIN = 3
FIXTURE_DOMAIN = 4
SCREEN_DOMAIN = 5
EFFECT_DOMAIN = 6
BANK_SIZE = 131_072
HALF_BANK_SIZE = 65_536
SITE_COUNT = 160
SCORE_TOLERANCE = 1e-8
STATISTIC_TOLERANCE = 1e-6
STABILITY_TOLERANCE = 0.5
PROFILE_CORE = 10.0
PREY_TIMES = np.arange(-60.0, 61.0, 10.0)
PREDATOR_TIMES = np.arange(10.0, 61.0, 10.0)
PSEUDO_ARRIVALS = np.asarray((5.0, 15.0, 25.0, 35.0, 45.0, 55.0, 70.0))
MODEL_NAMES = (
    "constant_free_h",
    "adjusted_free_h",
    "constant_h1",
    "adjusted_h1",
)
PUBLIC_STREAM_STAGES = {
    "spread": 1,
    "prey_loss": 2,
    "predator_visits": 3,
    "site_detection": 4,
    "prey_visits": 5,
    "background_field": 6,
}


@dataclass(frozen=True)
class AuditContext:
    site_ids: tuple[str, ...]
    training: NDArray[np.bool_]
    map_a: FloatArray
    site_a: FloatArray
    cluster_ids: tuple[str, ...]


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def array_sha256(value: NDArray[Any]) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_jsonable(value), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def public_seed(domain: int, index: int, *, root: int = PUBLIC_ROOT) -> int:
    return int(
        np.random.SeedSequence([root, PUBLIC_NAMESPACE, domain, index]).generate_state(
            1, dtype=np.uint64
        )[0]
    )


def public_fixture_seed(index: int, stage: int, *, root: int = PUBLIC_ROOT) -> int:
    return int(
        np.random.SeedSequence(
            [root, PUBLIC_NAMESPACE, FIXTURE_DOMAIN, index, stage]
        ).generate_state(1, dtype=np.uint64)[0]
    )


def public_fixture_streams(index: int, *, root: int = PUBLIC_ROOT) -> dict[str, int]:
    return {
        name: public_fixture_seed(index, stage, root=root)
        for name, stage in PUBLIC_STREAM_STAGES.items()
    }


def confirmatory_seed(
    domain: int, node: int, reference: int, stage: int, *, root: int = 2026100404
) -> int:
    if domain not in {SCREEN_DOMAIN, EFFECT_DOMAIN}:
        raise ValueError("confirmatory domain must be screening or effects")
    return int(
        np.random.SeedSequence(
            [root, PUBLIC_NAMESPACE, domain, node, reference, stage]
        ).generate_state(1, dtype=np.uint64)[0]
    )


def _fixed_arrays(fixed: FixedInputs) -> dict[str, NDArray[Any]]:
    landscape = fixed.landscape
    sites = tuple(sorted(fixed.design.sites, key=lambda site: site.site_id))
    return {
        "passable": np.asarray(landscape.passable),
        "source_reachable": np.asarray(landscape.source_reachable),
        "habitat_class": np.asarray(landscape.habitat_class),
        "quality": np.asarray(landscape.quality),
        "patch_id": np.asarray(landscape.patch_id),
        "corridor_id": np.asarray(landscape.corridor_id),
        "source_zone": np.asarray(landscape.source_zone),
        "water_neighbor_count": np.asarray(landscape.water_neighbor_count),
        "access_network": np.asarray(fixed.design.network),
        "site_ids": np.asarray([site.site_id for site in sites]),
        "site_rows": np.asarray([site.row for site in sites], dtype=np.int64),
        "site_cols": np.asarray([site.col for site in sites], dtype=np.int64),
        "site_splits": np.asarray([site.split for site in sites], dtype="U16"),
        "site_clusters": np.asarray([site.cluster_id for site in sites], dtype="U32"),
        "site_strata": np.asarray([site.stratum_index for site in sites], dtype=np.int64),
        "site_center_rows": np.asarray([site.center_row for site in sites], dtype=np.int64),
        "site_center_cols": np.asarray([site.center_col for site in sites], dtype=np.int64),
    }


def reconstruct_structurally_valid_fixed(
    map_seed: int, sampling_seed: int
) -> FixedInputs:
    """Apply the public structural predicate without production public helpers."""
    landscape = build_landscape("connected", map_seed)
    access, balanced = build_sampling_pair(landscape, sampling_seed)
    passable = np.asarray(landscape.passable, dtype=bool)
    graph_has_edge = bool(
        np.any(passable[:, 1:] & passable[:, :-1])
        or np.any(passable[1:, :] & passable[:-1, :])
    )
    checks: dict[str, bool] = {
        "landscape_shape": landscape.shape == (72, 84),
        "landscape_counts": int(passable.sum()) == 5225
        and int((~passable).sum()) == 823,
        "graph_edge_count": graph_has_edge,
        "site_count": len(access.sites) == 160,
        "training_sites": sum(site.split == "training" for site in access.sites)
        == 120,
        "holdout_sites": sum(site.split == "holdout" for site in access.sites) == 40,
        "cluster_count": len(access.clusters) == 32,
        "cluster_isolation": all(
            len(
                {
                    site.split
                    for site in access.sites
                    if site.cluster_id == cluster.cluster_id
                }
            )
            == 1
            for cluster in access.clusters
        ),
    }
    heldout: list[set[tuple[int, int, str, str]]] = []
    for name, design in (("access", access), ("balanced", balanced)):
        training = tuple(site for site in design.sites if site.split == "training")
        holdout = tuple(site for site in design.sites if site.split == "holdout")
        heldout.append(
            {
                (site.row, site.col, site.site_id, site.cluster_id)
                for site in holdout
            }
        )
        checks[f"sampling_{name}_site_counts"] = (
            len(training) == 120 and len(holdout) == 40
        )
        checks[f"sampling_{name}_unique_physical_sites"] = (
            len({(site.row, site.col) for site in design.sites}) == 160
        )
        checks[f"sampling_{name}_source_reachable"] = all(
            passable[site.row, site.col]
            and landscape.source_reachable[site.row, site.col]
            for site in design.sites
        )
        checks[f"sampling_{name}_stratum_allocation"] = all(
            sum(site.stratum_index == stratum for site in training) == 30
            and sum(site.stratum_index == stratum for site in holdout) == 10
            for stratum in range(4)
        )
        checks[f"sampling_{name}_cluster_separation"] = all(
            (first.center_row - second.center_row) ** 2
            + (first.center_col - second.center_col) ** 2
            >= 64.0
            for first, second in itertools.combinations(design.clusters, 2)
        )
        checks[f"sampling_{name}_cluster_split_isolation"] = not {
            site.cluster_id for site in training
        }.intersection(site.cluster_id for site in holdout)
    checks["sampling_identical_holdout"] = heldout[0] == heldout[1]
    checks["sampling_access_centres_on_network"] = all(
        access.network[cluster.center_row, cluster.center_col]
        for cluster in access.clusters
        if cluster.split == "training"
    )
    if not all(checks.values()):
        raise ValueError("independent public map/design structural invariants failed")
    return FixedInputs(landscape, access, checks)


def reconstruct_public_inputs(
    directory: Path, *, expected_root: int = PUBLIC_ROOT
) -> tuple[FixedInputs, Any, AuditContext, dict[str, Any]]:
    """Rebuild the accepted public map/design without production public code."""
    metadata = read_json(directory / "public_inputs.json")
    accepted_receipt = read_json(directory / "accepted_candidate.json")
    ledger_receipt = read_json(directory / "seed_ledger.json")
    failed_sidecar = json.loads(
        (directory / "failed_attempts.json").read_text(encoding="utf-8")
    )
    root = int(metadata.get("root", -1))
    attempt = int(metadata.get("attempt", -1))
    expected_map_seed = public_seed(MAP_DOMAIN, attempt, root=root)
    expected_sampling_seed = public_seed(SAMPLING_DOMAIN, attempt, root=root)
    if metadata.get("map_seed") != expected_map_seed or metadata.get(
        "sampling_seed"
    ) != expected_sampling_seed:
        raise ValueError("public map/sampling seed address mismatch")

    # Every earlier candidate must remain structurally infeasible under the
    # same final constructors. Numerical certificates are deliberately absent
    # from this selection replay.
    unexpected_earlier: list[int] = []
    for prior in range(attempt):
        try:
            reconstruct_structurally_valid_fixed(
                public_seed(MAP_DOMAIN, prior, root=root),
                public_seed(SAMPLING_DOMAIN, prior, root=root),
            )
        except Exception:
            continue
        unexpected_earlier.append(prior)
    if unexpected_earlier:
        raise ValueError(f"earlier structurally valid attempts exist: {unexpected_earlier}")

    fixed = reconstruct_structurally_valid_fixed(
        expected_map_seed, expected_sampling_seed
    )
    setup = build_generator_setup(fixed)
    arrays = _fixed_arrays(fixed)
    with np.load(directory / "public_inputs.npz", allow_pickle=False) as stored:
        if set(stored.files) != set(arrays):
            raise ValueError("public input array schema mismatch")
        array_matches = {
            name: bool(np.array_equal(np.asarray(stored[name]), value))
            for name, value in arrays.items()
        }
    with np.load(directory / "exposure.npz", allow_pickle=False) as exposure:
        exposure_schema = set(exposure.files)
        stored_map_a = np.asarray(exposure["map_a"], dtype=np.float64)
        stored_site_a = np.asarray(exposure["site_a"], dtype=np.float64)
        stored_mask = np.asarray(exposure["accepted_mask"], dtype=bool)
    hashes = {name: array_sha256(value) for name, value in arrays.items()}
    expected_ledger = [
        {
            "attempt": candidate,
            "map_seed": public_seed(MAP_DOMAIN, candidate, root=root),
            "sampling_seed": public_seed(SAMPLING_DOMAIN, candidate, root=root),
        }
        for candidate in range(100)
    ]
    failures = metadata.get("failed_attempts")
    checks = {
        "state_qualified": metadata.get("state") == "qualified",
        "root": root == expected_root,
        "namespace": metadata.get("namespace") == PUBLIC_NAMESPACE,
        "attempt_nonnegative": attempt >= 0,
        "no_earlier_valid_attempt": not unexpected_earlier,
        "arrays_match_reconstruction": all(array_matches.values()),
        "array_hashes_match": metadata.get("array_sha256") == hashes,
        "artifact_hash_matches": metadata.get("public_inputs_sha256")
        == sha256_file(directory / "public_inputs.npz"),
        "accepted_receipt_matches": all(
            accepted_receipt.get(key) == metadata.get(key)
            for key in (
                "root",
                "namespace",
                "attempt",
                "map_seed",
                "sampling_seed",
                "array_sha256",
                "public_inputs_sha256",
            )
        )
        and accepted_receipt.get("state") == "structurally_frozen",
        "seed_ledger_matches": ledger_receipt
        == {
            "root": root,
            "namespace": PUBLIC_NAMESPACE,
            "map_stage": MAP_DOMAIN,
            "sampling_stage": SAMPLING_DOMAIN,
            "candidates": expected_ledger,
        }
        and metadata.get("seed_ledger_sha256")
        == sha256_file(directory / "seed_ledger.json"),
        "failed_attempts_complete": isinstance(failures, list)
        and len(failures) == attempt
        and [item.get("attempt") for item in failures] == list(range(attempt)),
        "failed_attempts_sidecar": failed_sidecar == failures,
        "failed_attempt_seed_addresses": isinstance(failures, list)
        and all(
            item.get("map_seed") == expected_ledger[index]["map_seed"]
            and item.get("sampling_seed") == expected_ledger[index]["sampling_seed"]
            for index, item in enumerate(failures)
        ),
        "exposure_schema": exposure_schema == {"map_a", "site_a", "accepted_mask"},
        "exposure_arrays_match": np.array_equal(stored_map_a, setup.exposure_score)
        and np.array_equal(
            stored_site_a,
            setup.exposure_score[setup.site_rows, setup.site_cols],
        )
        and np.array_equal(stored_mask, setup.accepted_mask),
        "exposure_hashes_match": metadata.get("exposure_sha256")
        == sha256_file(directory / "exposure.npz")
        and metadata.get("map_a_sha256") == array_sha256(stored_map_a)
        and metadata.get("site_a_sha256") == array_sha256(stored_site_a),
        "canonical_site_order": tuple(setup.site_ids) == tuple(sorted(setup.site_ids)),
        "site_counts": len(setup.site_ids) == SITE_COUNT
        and tuple(setup.site_splits).count("training") == 120
        and tuple(setup.site_splits).count("holdout") == 40,
        "exposure_standardized": abs(float(setup.exposure_score.mean())) <= 1e-12
        and abs(float(setup.exposure_score.std(ddof=0)) - 1.0) <= 1e-12,
    }
    if not all(checks.values()):
        raise ValueError("public input reconstruction failed")
    training = np.asarray(setup.site_splits) == "training"
    context = AuditContext(
        tuple(setup.site_ids),
        training,
        np.asarray(setup.exposure_score, dtype=np.float64),
        np.asarray(
            setup.exposure_score[setup.site_rows, setup.site_cols], dtype=np.float64
        ),
        tuple(setup.site_cluster_ids),
    )
    return fixed, setup, context, {
        "passed": True,
        "checks": checks,
        "array_matches": array_matches,
        "array_sha256": hashes,
        "attempt": attempt,
        "map_seed": expected_map_seed,
        "sampling_seed": expected_sampling_seed,
        "accepted_candidate_sha256": sha256_file(directory / "accepted_candidate.json"),
        "seed_ledger_sha256": sha256_file(directory / "seed_ledger.json"),
        "exposure_sha256": sha256_file(directory / "exposure.npz"),
        "public_inputs_sha256": sha256_file(directory / "public_inputs.npz"),
    }


def make_direct_bank(arrivals: NDArray[Any], site_ids: Sequence[str]) -> DirectBank:
    """Build the alpha=1 direct empirical representation at arbitrary K."""
    values = np.asarray(arrivals, dtype=np.float64)
    identifiers = tuple(str(value) for value in site_ids)
    if (
        values.ndim != 2
        or values.shape[1] != len(identifiers)
        or len(set(identifiers)) != len(identifiers)
        or not np.isfinite(values).all()
        or (values < 0).any()
    ):
        raise ValueError("raw arrival bank is invalid")
    categories = np.searchsorted(PREDATOR_TIMES, values, side="left")
    denominator = len(values) + len(PSEUDO_ARRIVALS)
    grouped: list[tuple[FloatArray, ...]] = []
    masses = np.empty((len(identifiers), 7), dtype=np.float64)
    for site in range(len(identifiers)):
        site_values = tuple(
            np.asarray(values[categories[:, site] == category, site], dtype=np.float64)
            for category in range(7)
        )
        grouped.append(site_values)
        masses[site] = np.asarray(
            [(len(category_values) + 1.0) / denominator for category_values in site_values]
        )
    return DirectBank(identifiers, len(values), denominator, tuple(grouped), masses)


def audit_arrival_bank(
    directory: Path,
    site_ids: Sequence[str],
    *,
    fixed: FixedInputs | None = None,
    map_a: NDArray[Any] | None = None,
    expected_size: int = BANK_SIZE,
    expected_root: int = PUBLIC_ROOT,
) -> tuple[NDArray[np.float64], dict[str, Any]]:
    manifest = read_json(directory / "manifest.json")
    started = read_json(directory / "started.json")
    raw = np.load(directory / "arrivals.npy", mmap_mode="r", allow_pickle=False)
    expected_seeds = np.asarray(
        [public_seed(BANK_DOMAIN, index, root=expected_root) for index in range(expected_size)],
        dtype=np.uint64,
    )
    with np.load(directory / "seed_ledger.npz", allow_pickle=False) as ledger_file:
        ledger_schema = set(ledger_file.files)
        ledger = np.asarray(ledger_file["seeds"], dtype=np.uint64)
        ledger_header = {
            "root": int(ledger_file["root"]),
            "namespace": int(ledger_file["namespace"]),
            "stage": int(ledger_file["stage"]),
        }
    checks = {
        "manifest_schema": manifest.get("schema_version") == "goal059-arrival-bank-v1",
        "manifest_address": manifest.get("root") == expected_root
        and manifest.get("namespace") == PUBLIC_NAMESPACE
        and manifest.get("stage") == BANK_DOMAIN
        and manifest.get("bank_size") == expected_size,
        "shape": tuple(raw.shape) == (expected_size, len(site_ids)),
        "finite_nonnegative": bool(np.isfinite(raw).all() and (raw >= 0).all()),
        "site_order": manifest.get("site_ids") == list(site_ids),
        "manifest_array_hash": manifest.get("array_sha256") == array_sha256(raw),
        "arrival_file_hash": manifest.get("arrivals_file_sha256")
        == sha256_file(directory / "arrivals.npy"),
        "started_receipt_hash": manifest.get("started_receipt_sha256")
        == sha256_file(directory / "started.json"),
        "started_identity": all(
            started.get(key) == manifest.get(key)
            for key in ("root", "namespace", "stage", "bank_size", "site_ids")
        ),
        "ledger_schema": ledger_schema == {"seeds", "root", "namespace", "stage"},
        "ledger_header": ledger_header
        == {"root": expected_root, "namespace": PUBLIC_NAMESPACE, "stage": BANK_DOMAIN},
        "ledger_values": ledger.shape == expected_seeds.shape
        and np.array_equal(ledger, expected_seeds),
        "ledger_unique": len(np.unique(ledger)) == len(ledger),
        "started_ledger_hash": started.get("ledger_sha256") == array_sha256(ledger),
        "started_ledger_file_hash": started.get("ledger_file_sha256")
        == sha256_file(directory / "seed_ledger.npz"),
    }
    if fixed is not None and map_a is not None:
        fixed_hashes = {
            name: array_sha256(value) for name, value in _fixed_arrays(fixed).items()
        }
        map_hash = array_sha256(np.asarray(map_a))
        checks.update(
            {
                "manifest_public_inputs": manifest.get("public_input_array_sha256")
                == fixed_hashes,
                "manifest_map_a": manifest.get("map_a_sha256") == map_hash,
                "started_public_inputs": started.get("public_input_array_sha256")
                == fixed_hashes,
                "started_map_a": started.get("map_a_sha256") == map_hash,
            }
        )
    chunk_failures: list[int] = []
    next_offset = 0
    for item in manifest.get("chunks", []):
        offset = int(item["offset"])
        if offset != next_offset or int(item.get("rows", -1)) <= 0:
            chunk_failures.append(offset)
        path = directory / f"chunk-{offset:08d}.npz"
        if not path.is_file():
            chunk_failures.append(offset)
            continue
        with np.load(path, allow_pickle=False) as saved:
            seeds = np.asarray(saved["seeds"], dtype=np.uint64)
            arrivals = np.asarray(saved["arrivals"], dtype=np.float64)
            saved_offset = int(saved["offset"])
        stop = offset + len(arrivals)
        valid = (
            saved_offset == offset
            and int(item["rows"]) == len(arrivals) == len(seeds)
            and np.array_equal(seeds, ledger[offset:stop])
            and np.array_equal(arrivals, raw[offset:stop])
            and item.get("seed_sha256") == array_sha256(seeds)
            and item.get("chunk_sha256") == array_sha256(arrivals)
            and item.get("file_sha256") == sha256_file(path)
        )
        if not valid:
            chunk_failures.append(offset)
        next_offset = stop
    checks["all_chunks_match"] = not chunk_failures and sum(
        int(item.get("rows", 0)) for item in manifest.get("chunks", [])
    ) == expected_size and next_offset == expected_size
    representative_matches: dict[str, bool] = {}
    if fixed is not None:
        sites = tuple(sorted(fixed.design.sites, key=lambda site: site.site_id))
        if tuple(site.site_id for site in sites) != tuple(site_ids):
            raise ValueError("bank audit fixed-input site order mismatch")
        representative = sorted(
            {0, expected_size // 2 - 1, expected_size // 2, expected_size - 1}
        )
        for index in representative:
            seed = int(expected_seeds[index])
            shocks = sample_edge_shock_vector(
                fixed.landscape, np.random.default_rng(seed)
            )
            spread = compute_contrast_spread(
                fixed.landscape, 1.0, edge_shocks=shocks, rho=1.0
            )
            replay = np.asarray(
                [spread.arrival[site.row, site.col] for site in sites],
                dtype=np.float64,
            )
            representative_matches[str(index)] = np.array_equal(replay, raw[index])
        checks["representative_row_replays"] = all(representative_matches.values())
    if not all(checks.values()):
        raise ValueError("arrival bank provenance audit failed")
    return raw, {
        "passed": True,
        "checks": checks,
        "chunk_failures": chunk_failures,
        "representative_row_replays": representative_matches,
        "array_sha256": array_sha256(raw),
        "file_sha256": sha256_file(directory / "arrivals.npy"),
        "ledger_sha256": array_sha256(ledger),
        "manifest_sha256": sha256_file(directory / "manifest.json"),
    }


def independent_hazard_map(
    setup: Any,
    *,
    background: str,
    beta: float,
    mu: float,
    background_seed: int,
) -> FloatArray:
    if background == "exact":
        scaled = beta * np.asarray(setup.exposure_score, dtype=np.float64)
        shift = float(np.max(scaled))
        raw = np.exp(scaled - shift)
    elif background == "B100-A":
        gaussian = setup.field_sampler.sample(np.random.default_rng(background_seed))
        z = 0.7 * setup.exposure_score + math.sqrt(0.51) * gaussian
        raw = np.exp(math.sqrt(math.log(2.0)) * z)
    else:
        raise ValueError("unknown public background branch")
    result = mu * raw / float(raw.mean())
    if not np.isfinite(result).all() or (result <= 0).any():
        raise ValueError("independent hazard map is invalid")
    return np.asarray(result, dtype=np.float64)


def independent_hazard_box_certificate(map_a: FloatArray, site_a: FloatArray) -> dict[str, Any]:
    """Recompute the registered continuous-beta transform-domain bound."""
    edges = np.linspace(-2.0, 2.0, 81)
    whole = np.asarray(map_a, dtype=np.float64).ravel()
    sites = np.asarray(site_a, dtype=np.float64)
    bounds: list[float] = []
    for lower, upper in itertools.pairwise(edges):
        denominator_lower = float(
            np.minimum(np.exp(lower * whole), np.exp(upper * whole)).mean()
        )
        numerator_upper = np.maximum(np.exp(lower * sites), np.exp(upper * sites))
        bounds.append(float(0.006 * np.max(numerator_upper / denominator_lower)))
    maximum = float(np.nextafter(max(bounds) * (1.0 + 1e-12), np.inf))
    transform = 10.0 * maximum * 9.0
    return {
        "method": "interval_numerator_upper_whole_map_denominator_lower",
        "beta_interval": [-2.0, 2.0],
        "interval_count": 80,
        "mu_upper": 0.006,
        "h_upper": 10.0,
        "site_hazard_upper": maximum,
        "transform_x_upper": transform,
        "required_transform_domain_upper": 5.0,
        "passes": transform <= 5.0,
    }


def audit_failed_public_inputs(
    directory: Path, *, expected_root: int = PUBLIC_ROOT
) -> dict[str, Any]:
    """Verify a terminal first-structural-candidate numerical failure."""
    metadata = read_json(directory / "public_inputs.json")
    accepted = read_json(directory / "accepted_candidate.json")
    ledger = read_json(directory / "seed_ledger.json")
    failures = json.loads((directory / "failed_attempts.json").read_text(encoding="utf-8"))
    root = int(metadata.get("root", -1))
    attempt = int(metadata.get("attempt", -1))
    if metadata.get("state") != "qualification_failed":
        raise ValueError("map-failure audit requires qualification_failed state")
    expected_ledger = [
        {
            "attempt": index,
            "map_seed": public_seed(MAP_DOMAIN, index, root=root),
            "sampling_seed": public_seed(SAMPLING_DOMAIN, index, root=root),
        }
        for index in range(100)
    ]
    if ledger != {
        "root": root,
        "namespace": PUBLIC_NAMESPACE,
        "map_stage": MAP_DOMAIN,
        "sampling_stage": SAMPLING_DOMAIN,
        "candidates": expected_ledger,
    }:
        raise ValueError("failed-map seed ledger mismatch")
    unexpected_earlier: list[int] = []
    for prior in range(attempt):
        try:
            reconstruct_structurally_valid_fixed(
                public_seed(MAP_DOMAIN, prior, root=root),
                public_seed(SAMPLING_DOMAIN, prior, root=root),
            )
        except Exception:
            continue
        unexpected_earlier.append(prior)
    if unexpected_earlier:
        raise ValueError("failed map was not the first structurally valid candidate")
    fixed = reconstruct_structurally_valid_fixed(
        public_seed(MAP_DOMAIN, attempt, root=root),
        public_seed(SAMPLING_DOMAIN, attempt, root=root),
    )
    arrays = _fixed_arrays(fixed)
    with np.load(directory / "public_inputs.npz", allow_pickle=False) as stored:
        arrays_match = set(stored.files) == set(arrays) and all(
            np.array_equal(stored[name], value) for name, value in arrays.items()
        )
    checks: dict[str, bool] = {
        "root": root == expected_root,
        "namespace": metadata.get("namespace") == PUBLIC_NAMESPACE,
        "attempt": attempt >= 0,
        "first_structural_candidate": not unexpected_earlier,
        "arrays_match": arrays_match,
        "array_hashes_match": metadata.get("array_sha256")
        == {name: array_sha256(value) for name, value in arrays.items()},
        "public_array_hash": metadata.get("public_inputs_sha256")
        == sha256_file(directory / "public_inputs.npz"),
        "accepted_receipt": accepted.get("state") == "structurally_frozen"
        and all(
            accepted.get(key) == metadata.get(key)
            for key in ("root", "namespace", "attempt", "map_seed", "sampling_seed")
        ),
        "earlier_failures": isinstance(failures, list)
        and len(failures) == attempt
        and [int(item["attempt"]) for item in failures] == list(range(attempt))
        and all(
            item.get("map_seed") == expected_ledger[index]["map_seed"]
            and item.get("sampling_seed") == expected_ledger[index]["sampling_seed"]
            for index, item in enumerate(failures)
        )
        and metadata.get("failed_attempts") == failures,
        "ledger_hash": metadata.get("seed_ledger_sha256")
        == sha256_file(directory / "seed_ledger.json"),
    }
    try:
        setup = build_generator_setup(fixed)
    except Exception as error:
        checks["failure_reproduced"] = metadata.get("error_type") == type(error).__name__
        if not all(checks.values()):
            raise ValueError("failed-map audit did not reproduce setup failure") from error
        return {
            "passed": True,
            "terminal_negative_qualification": True,
            "checks": checks,
            "attempt": attempt,
            "error_type": type(error).__name__,
        }
    site_a = np.asarray(
        setup.exposure_score[setup.site_rows, setup.site_cols], dtype=np.float64
    )
    exposure_path = directory / "exposure.npz"
    with np.load(exposure_path, allow_pickle=False) as exposure:
        exposure_matches = (
            set(exposure.files) == {"map_a", "site_a", "accepted_mask"}
            and np.array_equal(exposure["map_a"], setup.exposure_score)
            and np.array_equal(exposure["site_a"], site_a)
            and np.array_equal(exposure["accepted_mask"], setup.accepted_mask)
        )
    certificate = independent_hazard_box_certificate(
        np.asarray(setup.exposure_score, dtype=np.float64), site_a
    )
    field = setup.field_sampler
    numerical_pass = bool(
        certificate["passes"]
        and field.field_shape == (72, 84)
        and field.embedding_shape == (142, 166)
        and field.minimum_eigenvalue > 0
        and field.reconstruction_max_abs_error <= 1e-12
    )
    checks.update(
        {
            "certificate_matches": metadata.get("hazard_certificate") == certificate,
            "exposure_matches": exposure_matches,
            "exposure_hashes": metadata.get("exposure_sha256")
            == sha256_file(exposure_path)
            and metadata.get("map_a_sha256") == array_sha256(setup.exposure_score)
            and metadata.get("site_a_sha256") == array_sha256(site_a),
            "field_checks_match": metadata.get("field_checks")
            == {
                "field_shape": list(field.field_shape),
                "embedding_shape": list(field.embedding_shape),
                "minimum_eigenvalue": field.minimum_eigenvalue,
                "reconstruction_max_abs_error": field.reconstruction_max_abs_error,
            },
            "numerical_failure_reproduced": not numerical_pass,
        }
    )
    if not all(checks.values()):
        raise ValueError("failed-map numerical qualification audit failed")
    return {
        "passed": True,
        "terminal_negative_qualification": True,
        "checks": checks,
        "attempt": attempt,
        "hazard_certificate": certificate,
        "error_type": metadata.get("error_type"),
    }


def audit_no_structural_candidate(
    directory: Path, *, expected_root: int = PUBLIC_ROOT
) -> dict[str, Any]:
    """Verify exhaustion of all 100 registered structural candidates."""
    if any(
        (directory / name).exists()
        for name in ("public_inputs.json", "accepted_candidate.json", "public_inputs.npz")
    ):
        raise ValueError("structural-exhaustion directory contains an accepted candidate")
    ledger = read_json(directory / "seed_ledger.json")
    failures = json.loads((directory / "failed_attempts.json").read_text(encoding="utf-8"))
    expected_ledger = [
        {
            "attempt": index,
            "map_seed": public_seed(MAP_DOMAIN, index, root=expected_root),
            "sampling_seed": public_seed(SAMPLING_DOMAIN, index, root=expected_root),
        }
        for index in range(100)
    ]
    if ledger != {
        "root": expected_root,
        "namespace": PUBLIC_NAMESPACE,
        "map_stage": MAP_DOMAIN,
        "sampling_stage": SAMPLING_DOMAIN,
        "candidates": expected_ledger,
    }:
        raise ValueError("structural-exhaustion seed ledger mismatch")
    if (
        not isinstance(failures, list)
        or len(failures) != 100
        or [int(item["attempt"]) for item in failures] != list(range(100))
    ):
        raise ValueError("structural-exhaustion failure ledger is incomplete")
    unexpectedly_valid: list[int] = []
    for candidate in expected_ledger:
        try:
            reconstruct_structurally_valid_fixed(
                candidate["map_seed"], candidate["sampling_seed"]
            )
        except Exception:
            continue
        unexpectedly_valid.append(int(candidate["attempt"]))
    if unexpectedly_valid:
        raise ValueError(f"structurally valid candidates were skipped: {unexpectedly_valid}")
    return {
        "passed": True,
        "terminal_negative_qualification": True,
        "reason": "no_structurally_valid_candidate",
        "attempts": 100,
        "seed_ledger_sha256": sha256_file(directory / "seed_ledger.json"),
        "failed_attempts_sha256": sha256_file(directory / "failed_attempts.json"),
    }


def audit_negative_public_map(
    directory: Path, *, expected_root: int = PUBLIC_ROOT
) -> dict[str, Any]:
    if (directory / "public_inputs.json").is_file():
        return audit_failed_public_inputs(directory, expected_root=expected_root)
    return audit_no_structural_candidate(directory, expected_root=expected_root)


def _loss_times(
    arrivals: FloatArray, hazards: FloatArray, h: float, thresholds: FloatArray
) -> FloatArray:
    output = np.empty_like(arrivals)
    for index, (arrival, hazard, threshold) in enumerate(
        zip(arrivals, hazards, thresholds, strict=True)
    ):
        predator_arrival = float(arrival) + 60.0
        before = float(hazard) * predator_arrival
        if threshold <= before:
            calendar = threshold / hazard
        else:
            calendar = predator_arrival + (threshold - before) / (hazard * h)
        output[index] = calendar - 60.0
    return output


def replay_public_history(
    fixed: FixedInputs,
    setup: Any,
    truth: Mapping[str, Any],
    streams: Mapping[str, int],
) -> dict[str, NDArray[Any]]:
    """Replay one public fixture without production orchestration code."""
    required = set(PUBLIC_STREAM_STAGES)
    if set(streams) != required:
        raise ValueError("public fixture stream schema mismatch")
    shocks = sample_edge_shock_vector(
        fixed.landscape, np.random.default_rng(int(streams["spread"]))
    )
    spread = compute_contrast_spread(fixed.landscape, 1.0, edge_shocks=shocks, rho=1.0)
    arrival = np.asarray(spread.arrival[setup.site_rows, setup.site_cols], dtype=np.float64)
    hazard_map = independent_hazard_map(
        setup,
        background=str(truth["background"]),
        beta=float(truth["beta"] if truth.get("beta") is not None else 0.0),
        mu=float(truth.get("mu", truth.get("mean_hazard"))),
        background_seed=int(streams["background_field"]),
    )
    site_hazard = np.asarray(hazard_map[setup.site_rows, setup.site_cols], dtype=np.float64)
    thresholds = np.random.default_rng(int(streams["prey_loss"])).exponential(
        size=SITE_COUNT
    )
    loss = _loss_times(arrival, site_hazard, float(truth.get("h", truth.get("effect"))), thresholds)
    detection_sd = float(truth["detection_sd"])
    if detection_sd == 0.0:
        detection = np.full(SITE_COUNT, 0.65)
    else:
        concentration = 0.65 * 0.35 / detection_sd**2 - 1.0
        detection = np.random.default_rng(int(streams["site_detection"])).beta(
            0.65 * concentration, 0.35 * concentration, size=SITE_COUNT
        )
    predator_alive = arrival[:, None] <= PREDATOR_TIMES[None, :]
    prey_alive = loss[:, None] > PREY_TIMES[None, :]
    predator = (
        (
            np.random.default_rng(int(streams["predator_visits"]))
            .random((SITE_COUNT, len(PREDATOR_TIMES), 2))
            .__lt__(0.65)
            .sum(axis=2)
        )
        * predator_alive
    ).astype(np.int8)
    prey = (
        (
            np.random.default_rng(int(streams["prey_visits"]))
            .random((SITE_COUNT, len(PREY_TIMES), 2))
            < detection[:, None, None]
        ).sum(axis=2)
        * prey_alive
    ).astype(np.int8)
    return {
        "arrival": arrival,
        "loss": loss,
        "site_hazard": site_hazard,
        "site_detection": detection,
        "prey_alive": prey_alive,
        "predator_counts": predator,
        "prey_counts": prey,
        "hazard_map": hazard_map,
    }


def direct_point_score(
    bank: DirectBank,
    context: AuditContext,
    prey_counts: IntArray,
    predator_counts: IntArray,
    parameters: Mapping[str, Any],
) -> dict[str, Any]:
    emissions = predator_emissions(np.asarray(predator_counts, dtype=np.int64))
    score = direct_score(
        bank,
        np.asarray(prey_counts, dtype=np.int64),
        emissions,
        context.map_a,
        context.site_a,
        h=float(parameters["h"]),
        beta=float(parameters["beta"]),
        mu=float(parameters.get("mu", parameters.get("mean_hazard"))),
        detection_sd=float(parameters["detection_sd"]),
    )
    training = float(np.sum(score.joint_site[context.training], dtype=np.float64))
    holdout_site = np.asarray(score.conditional_prey_site[~context.training], dtype=np.float64)
    cluster_totals: dict[str, float] = {}
    holdout_clusters = np.asarray(context.cluster_ids)[~context.training]
    for cluster in sorted(set(holdout_clusters.tolist())):
        cluster_totals[str(cluster)] = float(np.sum(holdout_site[holdout_clusters == cluster]))
    return {
        "training_logjoint": training,
        "holdout_conditional_prey_total": float(np.sum(holdout_site)),
        "holdout_conditional_prey_site": holdout_site,
        "holdout_cluster_totals": cluster_totals,
    }


def centered_lr(values: Sequence[float]) -> FloatArray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or not len(array) or not np.isfinite(array).all():
        raise ValueError("profile values must be a finite vector")
    return np.asarray(2.0 * (float(np.max(array)) - array), dtype=np.float64)


def profile_stability(
    primary_values: Sequence[float],
    half_values: Sequence[float],
    *,
    tolerance: float = STABILITY_TOLERANCE,
) -> dict[str, Any]:
    primary = centered_lr(primary_values)
    half = centered_lr(half_values)
    if primary.shape != half.shape:
        raise ValueError("profile grids differ")
    core = (primary <= PROFILE_CORE) | (half <= PROFILE_CORE)
    movement = float(np.max(np.abs(primary[core] - half[core])))
    return {
        "passed": movement <= tolerance,
        "maximum_core_movement": movement,
        "core_nodes": int(core.sum()),
        "tolerance": tolerance,
    }


def heldout_contrasts(scores: Mapping[str, float]) -> dict[str, float]:
    if set(scores) != set(MODEL_NAMES):
        raise ValueError("held-out scores must contain all four registered models")
    return {
        f"{left}_minus_{right}": float(scores[left] - scores[right])
        for left, right in itertools.combinations(MODEL_NAMES, 2)
    }


def stability_predicates(
    primary: Mapping[str, Any], half: Mapping[str, Any], *, exact_family: bool
) -> dict[str, Any]:
    profile_names = ("constant_h", "adjusted_h", "adjusted_beta")
    profiles = {
        name: profile_stability(
            primary["profiles"][name]["values"], half["profiles"][name]["values"]
        )
        for name in profile_names
    }
    h_movement = abs(
        float(primary["generating_lr"]["h"]) - float(half["generating_lr"]["h"])
    )
    beta_movement: float | None = (
        abs(
            float(primary["generating_lr"]["beta"])
            - float(half["generating_lr"]["beta"])
        )
        if exact_family
        else None
    )
    direct_lr: dict[str, float | None] = {
        "h": h_movement,
        "beta": (
            beta_movement
        ),
    }
    primary_contrasts = heldout_contrasts(primary["holdout_scores"])
    half_contrasts = heldout_contrasts(half["holdout_scores"])
    contrast_movement = {
        name: abs(primary_contrasts[name] - half_contrasts[name]) for name in primary_contrasts
    }
    checks = {
        "T": abs(float(primary["T"]) - float(half["T"])) <= STABILITY_TOLERANCE,
        "profiles": all(value["passed"] for value in profiles.values()),
        "generating_h": h_movement <= STABILITY_TOLERANCE,
        "generating_beta": beta_movement is None
        or beta_movement <= STABILITY_TOLERANCE,
        "heldout_contrasts": max(contrast_movement.values()) <= STABILITY_TOLERANCE,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "T_movement": abs(float(primary["T"]) - float(half["T"])),
        "profiles": profiles,
        "generating_lr_movement": direct_lr,
        "heldout_contrast_movement": contrast_movement,
        "tolerance": STABILITY_TOLERANCE,
    }


def nuisance_grid() -> tuple[tuple[float, float, float], ...]:
    return tuple(
        (float(beta), float(mu), float(sd))
        for beta, mu, sd in itertools.product(
            np.arange(-2.0, 2.0001, 0.25),
            (0.0005, 0.001, 0.0016, 0.002, 0.0025, 0.0032, 0.004, 0.005, 0.006),
            (0.0, 0.1, 0.2, 0.3, 0.4),
        )
    )


def nuisance_neighbors(index: int) -> tuple[int, ...]:
    if not 0 <= index < 765:
        raise ValueError("nuisance node index is outside [0,764]")
    beta_index, remainder = divmod(index, 9 * 5)
    mu_index, sd_index = divmod(remainder, 5)
    indices = {index}
    for delta_beta, delta_mu, delta_sd in (
        (-1, 0, 0),
        (1, 0, 0),
        (0, -1, 0),
        (0, 1, 0),
        (0, 0, -1),
        (0, 0, 1),
    ):
        b = beta_index + delta_beta
        m = mu_index + delta_mu
        s = sd_index + delta_sd
        if 0 <= b < 17 and 0 <= m < 9 and 0 <= s < 5:
            indices.add((b * 9 + m) * 5 + s)
    return tuple(sorted(indices))


def local_discrepancy(surface: Sequence[float], node: int) -> float:
    values = np.asarray(surface, dtype=np.float64)
    if values.shape != (765,) or not np.isfinite(values).all():
        raise ValueError("screen surface must contain 765 finite scores")
    neighbours = nuisance_neighbors(node)
    return max(0.0, 2.0 * (float(np.max(values[list(neighbours)])) - float(values[node])))


def inclusive_rank(observed: float, references: Sequence[float]) -> float:
    values = np.asarray(references, dtype=np.float64)
    if (
        not math.isfinite(observed)
        or values.ndim != 1
        or not len(values)
        or not np.isfinite(values).all()
    ):
        raise ValueError("rank inputs must be finite")
    tolerance = 1e-10 + 1e-12 * max(1.0, abs(observed))
    return float((1 + np.sum(values >= observed - tolerance)) / (len(values) + 1))


def screen_sets(
    observed_surfaces: NDArray[Any], screen_reference_statistics: NDArray[Any]
) -> tuple[tuple[int, ...], ...]:
    observed = np.asarray(observed_surfaces, dtype=np.float64)
    references = np.asarray(screen_reference_statistics, dtype=np.float64)
    if observed.ndim != 2 or observed.shape[1] != 765 or references.shape != (765, 99):
        raise ValueError("screen arrays have the wrong frozen shape")
    retained = []
    for case in range(observed.shape[0]):
        nodes = []
        for node in range(765):
            discrepancy = local_discrepancy(observed[case], node)
            if inclusive_rank(discrepancy, references[node]) > 0.01:
                nodes.append(node)
        retained.append(tuple(nodes))
    return tuple(retained)


def effect_decision(
    observed_T: float,
    retained: Sequence[int],
    effect_reference_statistics: Mapping[int, Sequence[float]],
) -> dict[str, Any]:
    nodes = tuple(int(value) for value in retained)
    if not nodes:
        return {"p_BB": 1.0, "declare": False, "abstain": True, "node_p": {}}
    node_p = {node: inclusive_rank(observed_T, effect_reference_statistics[node]) for node in nodes}
    p_bb = min(1.0, 0.01 + max(node_p.values()))
    return {"p_BB": p_bb, "declare": p_bb <= 0.05, "abstain": False, "node_p": node_p}


def _require_keys(value: Mapping[str, Any], required: set[str], label: str) -> None:
    missing = required.difference(value)
    if missing:
        raise ValueError(f"{label} is missing {sorted(missing)}")


def registered_public_truths() -> tuple[dict[str, Any], ...]:
    exact = (
        (0, 1.0, 0.0, 0.0025, 0.2),
        (1, 3.0, 0.0, 0.0025, 0.2),
        (2, 1.0, -1.0, 0.001, 0.0),
        (3, 3.0, -1.0, 0.001, 0.0),
        (4, 1.0, 1.0, 0.004, 0.3),
        (5, 3.0, 1.0, 0.004, 0.3),
    )
    rows = [
        {
            "index": index,
            "effect": effect,
            "mean_hazard": mean_hazard,
            "beta": beta,
            "detection_sd": detection_sd,
            "background": "exact",
        }
        for index, effect, beta, mean_hazard, detection_sd in exact
    ]
    rows.extend(
        {
            "index": index,
            "effect": effect,
            "mean_hazard": 0.0025,
            "beta": None,
            "detection_sd": 0.2,
            "background": "B100-A",
        }
        for index, effect in ((6, 1.0), (7, 3.0))
    )
    return tuple(rows)


def audit_source_freeze(
    repository: Path,
    source_freeze_path: Path,
    runtime_path: Path,
    registration_path: Path,
) -> dict[str, Any]:
    """Bind the running checkout and runtime to the prospective freeze."""
    manifest = read_json(source_freeze_path)
    runtime = read_json(runtime_path)
    hashes = manifest.get("source_hashes")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("source freeze must contain a nonempty source_hashes mapping")
    actual: dict[str, str | None] = {}
    for relative in hashes:
        candidate = (repository / str(relative)).resolve()
        if not candidate.is_relative_to(repository.resolve()):
            raise ValueError("source freeze path escapes the running repository")
        actual[str(relative)] = sha256_file(candidate) if candidate.is_file() else None
    registration_relative = str(registration_path.resolve().relative_to(repository.resolve()))
    checks = {
        "source_hashes_match": actual == hashes,
        "registration_is_bound": hashes.get(registration_relative)
        == sha256_file(registration_path),
        "runtime_hash_matches": manifest.get("runtime_sha256")
        == sha256_file(runtime_path),
        "python_version_matches": runtime.get("python_version")
        in {platform.python_version(), sys.version},
        "numpy_version_matches": runtime.get("numpy_version") == np.__version__,
        "bit_generator": runtime.get("bit_generator") in {"PCG64", "numpy.random.PCG64"},
    }
    if not all(checks.values()):
        raise ValueError("source/runtime freeze audit failed")
    return {
        "passed": True,
        "checks": checks,
        "source_manifest_sha256": sha256_file(source_freeze_path),
        "runtime_sha256": sha256_file(runtime_path),
        "registration_sha256": sha256_file(registration_path),
        "source_hashes": actual,
    }


def audit_public_panel(
    directory: Path,
    fixed: FixedInputs,
    setup: Any,
    context: AuditContext,
    *,
    expected_root: int = PUBLIC_ROOT,
) -> tuple[IntArray, IntArray, tuple[dict[str, Any], ...], dict[str, Any]]:
    """Verify the eight public fixtures and independently replay every stream."""
    manifest = read_json(directory / "manifest.json")
    ledger = read_json(directory / "seed_ledger.json")
    pre_draw = read_json(directory / "pre_draw.json")
    truth_object = read_json(directory / "truths.json")
    evaluator_json = read_json(directory / "evaluator.json")
    truths_raw = truth_object.get("truths")
    if not isinstance(truths_raw, list) or len(truths_raw) != 8:
        raise ValueError("public fixture truth table must contain eight rows")
    truths = tuple(dict(value) for value in truths_raw)
    if truths != registered_public_truths():
        raise ValueError("public fixture truth table differs from the registration")
    expected_streams = [public_fixture_streams(index, root=expected_root) for index in range(8)]
    expected_seed_rows = [
        {
            "root": expected_root,
            "namespace": PUBLIC_NAMESPACE,
            "stage": FIXTURE_DOMAIN,
            "index": index,
            "stream_stages": PUBLIC_STREAM_STAGES,
            "streams": expected_streams[index],
        }
        for index in range(8)
    ]
    flattened_seeds = [
        seed for streams in expected_streams for seed in streams.values()
    ]
    with np.load(directory / "observations.npz", allow_pickle=False) as observations:
        observation_schema = set(observations.files)
        prey = np.asarray(observations["prey_counts"], dtype=np.int64)
        predator = np.asarray(observations["predator_counts"], dtype=np.int64)
        site_ids = tuple(str(value) for value in observations["site_ids"])
        initial_alive = np.asarray(observations["initial_alive"], dtype=bool)
    with np.load(directory / "evaluator.npz", allow_pickle=False) as evaluator:
        evaluator_schema = set(evaluator.files)
        stored_evaluator = {name: np.asarray(evaluator[name]) for name in evaluator.files}
    expected_evaluator_schema = {
        "arrival",
        "loss",
        "site_hazard",
        "site_detection",
        "prey_alive",
        "map_hazard",
        "stream_seeds",
    }
    checks = {
        "manifest_schema": manifest.get("schema_version") == "goal059-public-fixture-manifest-v1"
        or manifest.get("schema_version") == "goal059-public-fixture-predraw-v1",
        "ledger_schema": ledger.get("schema_version") == "goal059-public-fixture-ledger-v1",
        "predraw_address": pre_draw.get("root") == expected_root
        and pre_draw.get("namespace") == PUBLIC_NAMESPACE
        and pre_draw.get("stage") == FIXTURE_DOMAIN,
        "ledger_address": ledger.get("root") == expected_root
        and ledger.get("namespace") == PUBLIC_NAMESPACE
        and ledger.get("stage") == FIXTURE_DOMAIN
        and ledger.get("stream_stages") == PUBLIC_STREAM_STAGES
        and ledger.get("indices") == list(range(8))
        and ledger.get("seeds") == expected_seed_rows,
        "fixture_seeds_unique": len(set(flattened_seeds)) == 8 * len(PUBLIC_STREAM_STAGES),
        "observation_schema": observation_schema
        == {"prey_counts", "predator_counts", "site_ids", "initial_alive"},
        "evaluator_schema": evaluator_schema == expected_evaluator_schema,
        "observation_shapes": prey.shape == (8, SITE_COUNT, len(PREY_TIMES))
        and predator.shape == (8, SITE_COUNT, len(PREDATOR_TIMES)),
        "site_order": site_ids == context.site_ids,
        "initial_alive": initial_alive.shape == (SITE_COUNT,) and bool(initial_alive.all()),
        "predraw_hashes": pre_draw.get("seed_ledger_sha256")
        == sha256_file(directory / "seed_ledger.json")
        and pre_draw.get("truths_sha256") == sha256_file(directory / "truths.json"),
        "manifest_hashes": manifest.get("observations_sha256")
        == sha256_file(directory / "observations.npz")
        and manifest.get("evaluator_npz_sha256") == sha256_file(directory / "evaluator.npz")
        and manifest.get("evaluator_json_sha256") == sha256_file(directory / "evaluator.json"),
        "evaluator_json_hashes": evaluator_json.get("seed_ledger_sha256")
        == sha256_file(directory / "seed_ledger.json")
        and evaluator_json.get("arrays", {}).get("observations_sha256")
        == sha256_file(directory / "observations.npz")
        and evaluator_json.get("arrays", {}).get("evaluator_sha256")
        == sha256_file(directory / "evaluator.npz"),
        "evaluator_truths": evaluator_json.get("truths") == truths_raw,
        "manifest_state": manifest.get("state") == "generated"
        and manifest.get("site_ids") == list(context.site_ids)
        and manifest.get("observation_shape") == [SITE_COUNT, len(PREY_TIMES)],
    }
    replay_fields = {
        "arrival": "arrival",
        "loss": "loss",
        "site_hazard": "site_hazard",
        "site_detection": "site_detection",
        "prey_alive": "prey_alive",
        "hazard_map": "map_hazard",
    }
    replay_matches: dict[str, dict[str, bool]] = {}
    for index, truth in enumerate(truths):
        if int(truth.get("index", -1)) != index:
            raise ValueError("public fixture truth indices are not canonical")
        replay = replay_public_history(fixed, setup, truth, expected_streams[index])
        row_matches = {
            "prey_counts": np.array_equal(replay["prey_counts"], prey[index]),
            "predator_counts": np.array_equal(replay["predator_counts"], predator[index]),
        }
        for replay_name, stored_name in replay_fields.items():
            row_matches[stored_name] = np.array_equal(
                replay[replay_name], stored_evaluator[stored_name][index], equal_nan=True
            )
        expected_seed_vector = np.asarray(
            [expected_streams[index][name] for name in PUBLIC_STREAM_STAGES], dtype=np.uint64
        )
        row_matches["stream_seeds"] = np.array_equal(
            stored_evaluator["stream_seeds"][index], expected_seed_vector
        )
        replay_matches[str(index)] = row_matches
    checks["all_replays_bitwise"] = all(
        all(row.values()) for row in replay_matches.values()
    )
    if not all(checks.values()):
        raise ValueError("public fixture provenance or replay audit failed")
    return prey, predator, truths, {
        "passed": True,
        "checks": checks,
        "replay_matches": replay_matches,
        "observations_sha256": sha256_file(directory / "observations.npz"),
        "evaluator_sha256": sha256_file(directory / "evaluator.npz"),
        "manifest_sha256": sha256_file(directory / "manifest.json"),
        "qualification_sha256": pre_draw.get("qualification_sha256"),
        "mechanical_receipt_sha256": pre_draw.get("mechanical_receipt_sha256"),
        "public_inputs_sha256": pre_draw.get("public_inputs_sha256"),
    }


def subset_direct_bank(bank: DirectBank, mask: NDArray[Any]) -> DirectBank:
    indices = np.flatnonzero(np.asarray(mask, dtype=bool))
    if not len(indices):
        raise ValueError("direct bank subset is empty")
    return DirectBank(
        tuple(bank.site_ids[index] for index in indices),
        bank.bank_size,
        bank.denominator,
        tuple(bank.values[index] for index in indices),
        np.asarray(bank.category_mass[indices], dtype=np.float64),
    )


def direct_training_score(
    bank: DirectBank,
    context: AuditContext,
    prey_counts: IntArray,
    predator_counts: IntArray,
    parameters: Mapping[str, Any],
) -> float:
    result = direct_point_score(bank, context, prey_counts, predator_counts, parameters)
    return float(result["training_logjoint"])


def direct_multi_training_scores(
    bank: DirectBank,
    context: AuditContext,
    prey_counts: IntArray,
    predator_counts: IntArray,
    parameters: Mapping[str, Any],
) -> FloatArray:
    """Score several histories while constructing direct bank moments once."""
    hazards = normalized_hazards(
        float(parameters["beta"]),
        float(parameters["mu"]),
        context.map_a,
        context.site_a,
    )
    moments = direct_survival_moments(bank, hazards, float(parameters["h"]))
    values = np.empty(len(prey_counts), dtype=np.float64)
    for history in range(len(prey_counts)):
        predator_probability = predator_emissions(predator_counts[history])
        events, alive = prey_factors(
            prey_counts[history], float(parameters["detection_sd"])
        )
        weighted = np.einsum(
            "stc,sc->st", moments, predator_probability, optimize=True
        )
        probability = np.sum(
            (weighted[:, :-1] - weighted[:, 1:]) * events, axis=1
        )
        probability += weighted[:, -1] * alive
        if not np.isfinite(probability).all() or (probability <= 0).any():
            raise ValueError("independent multi-history probabilities are invalid")
        values[history] = float(np.log(probability)[context.training].sum())
    return values


def _fit_parameters(row: Mapping[str, Any]) -> dict[str, float]:
    return {
        "h": float(row["h"]),
        "beta": float(row["beta"]),
        "mu": float(row["mu"]),
        "detection_sd": float(row["detection_sd"]),
    }


def audit_result_row(
    row: Mapping[str, Any],
    bank: DirectBank,
    context: AuditContext,
    prey_counts: IntArray,
    predator_counts: IntArray,
) -> dict[str, Any]:
    """Replay every stored main and profile point with the direct scorer."""
    fits_value = row.get("fits")
    profiles_value = row.get("profiles")
    heldout_value = row.get("heldout_scores")
    if not isinstance(fits_value, dict) or not isinstance(profiles_value, dict):
        raise ValueError("panel row lacks raw fit/profile/heldout tables")
    if not isinstance(heldout_value, dict):
        raise ValueError("panel row lacks raw fit/profile/heldout tables")
    fits: dict[str, Any] = fits_value
    profiles: dict[str, Any] = profiles_value
    heldout: dict[str, Any] = heldout_value
    if set(fits) != set(MODEL_NAMES) or set(heldout) != set(MODEL_NAMES):
        raise ValueError("panel row model identities are incomplete")
    main_errors: dict[str, float] = {}
    holdout_total_errors: dict[str, float] = {}
    holdout_site_errors: dict[str, float] = {}
    holdout_cluster_errors: dict[str, float] = {}
    for model in MODEL_NAMES:
        parameters = _fit_parameters(fits[model])
        if (
            not 1.0 <= parameters["h"] <= 10.0
            or not -2.0 <= parameters["beta"] <= 2.0
            or not 0.0005 <= parameters["mu"] <= 0.006
            or not 0.0 <= parameters["detection_sd"] <= 0.4
            or (model.startswith("constant") and parameters["beta"] != 0.0)
            or (model.endswith("h1") and parameters["h"] != 1.0)
        ):
            raise ValueError(f"stored fit violates model constraints: {model}")
        direct = direct_point_score(bank, context, prey_counts, predator_counts, parameters)
        main_errors[model] = abs(
            direct["training_logjoint"] - float(fits[model]["raw_logjoint"])
        )
        stored_holdout = heldout[model]
        if set(stored_holdout["cluster_contributions_nats"]) != set(
            direct["holdout_cluster_totals"]
        ):
            raise ValueError("held-out cluster identities are incomplete")
        holdout_total_errors[model] = abs(
            direct["holdout_conditional_prey_total"]
            - float(stored_holdout["conditional_prey_total_nats"])
        )
        holdout_site_errors[model] = float(
            np.max(
                np.abs(
                    direct["holdout_conditional_prey_site"]
                    - np.asarray(stored_holdout["conditional_prey_site_nats"], dtype=np.float64)
                )
            )
        )
        holdout_cluster_errors[model] = max(
            (
                abs(
                    direct["holdout_cluster_totals"][cluster]
                    - float(stored_holdout["cluster_contributions_nats"][cluster])
                )
                for cluster in direct["holdout_cluster_totals"]
            ),
            default=0.0,
        )
    expected_profiles = {
        "constant_h": ("h", np.linspace(1.0, 10.0, 181)),
        "adjusted_h": ("h", np.linspace(1.0, 10.0, 181)),
        "adjusted_beta": ("beta", np.linspace(-2.0, 2.0, 81)),
    }
    profile_errors: dict[str, float] = {}
    for name, (coordinate, expected_grid) in expected_profiles.items():
        expected_length = len(expected_grid)
        profile = profiles.get(name)
        if not isinstance(profile, dict):
            raise ValueError(f"missing profile {name}")
        values = np.asarray(profile.get("values"), dtype=np.float64)
        grid = np.asarray(profile.get("grid"), dtype=np.float64)
        parameters_value = profile.get("parameters")
        statuses = profile.get("statuses")
        if (
            values.shape != (expected_length,)
            or not np.array_equal(grid, expected_grid)
            or profile.get("coordinate") != coordinate
            or not isinstance(parameters_value, list)
            or len(parameters_value) != expected_length
            or not isinstance(statuses, list)
            or len(statuses) != expected_length
        ):
            raise ValueError(f"profile {name} is incomplete")
        profile_parameters: list[Any] = parameters_value
        for index, parameter_row in enumerate(profile_parameters):
            parsed = _fit_parameters(parameter_row)
            if parsed[coordinate] != float(grid[index]):
                raise ValueError(f"profile {name} does not fix its registered coordinate")
            if name == "constant_h" and parsed["beta"] != 0.0:
                raise ValueError("constant-h profile changed beta")
        errors = [
            abs(
                direct_training_score(
                    bank,
                    context,
                    prey_counts,
                    predator_counts,
                    _fit_parameters(profile_parameters[index]),
                )
                - float(values[index])
            )
            for index in range(expected_length)
        ]
        profile_errors[name] = max(errors)
    direct_T = max(
        0.0,
        2.0
        * (
            float(fits["adjusted_free_h"]["raw_logjoint"])
            - float(fits["adjusted_h1"]["raw_logjoint"])
        ),
    )
    stored_T = float(row["paired"]["T"])
    maximum = max(
        *main_errors.values(),
        *profile_errors.values(),
        *holdout_total_errors.values(),
        *holdout_site_errors.values(),
        *holdout_cluster_errors.values(),
    )
    audit_checks = {
        "direct_scores": maximum <= SCORE_TOLERANCE,
        "T": abs(direct_T - stored_T) <= STATISTIC_TOLERANCE,
    }
    profile_main_gaps = {
        name: float(
            np.max(np.asarray(profiles[name]["values"], dtype=np.float64))
            - float(
                fits[
                    "constant_free_h" if name == "constant_h" else "adjusted_free_h"
                ]["raw_logjoint"]
            )
        )
        for name in expected_profiles
    }
    stored_profile_gaps = row.get("profile_main_gaps", {})
    profile_gap_error = max(
        (
            abs(profile_main_gaps[name] - float(stored_profile_gaps[name]))
            for name in expected_profiles
        ),
        default=0.0,
    )
    nesting_gaps = {
        "constant": float(fits["constant_h1"]["raw_logjoint"])
        - float(fits["constant_free_h"]["raw_logjoint"]),
        "adjusted": float(fits["adjusted_h1"]["raw_logjoint"])
        - float(fits["adjusted_free_h"]["raw_logjoint"]),
    }
    nesting_gap_error = max(
        abs(nesting_gaps[name] - float(row["nesting_gaps"][name]))
        for name in nesting_gaps
    )
    audit_checks.update(
        {
            "profile_gap_arithmetic": profile_gap_error <= SCORE_TOLERANCE,
            "nesting_gap_arithmetic": nesting_gap_error <= SCORE_TOLERANCE,
        }
    )
    scientific_checks = {
        "main_statuses": all(
            fits[model].get("numerical_status") == "converged" for model in MODEL_NAMES
        ),
        "profile_statuses": all(
            status == "converged"
            for name in expected_profiles
            for status in profiles[name]["statuses"]
        ),
        "nesting": all(
            float(value) <= STATISTIC_TOLERANCE
            for value in nesting_gaps.values()
        ),
        "main_dominates_profiles": all(
            value <= STATISTIC_TOLERANCE for value in profile_main_gaps.values()
        ),
    }
    if not all(audit_checks.values()):
        raise ValueError("direct panel score audit failed")
    return {
        "passed": True,
        "scientific_qualification_passed": all(scientific_checks.values()),
        "audit_checks": audit_checks,
        "scientific_checks": scientific_checks,
        "maximum_score_abs_error": maximum,
        "main_abs_error": main_errors,
        "profile_max_abs_error": profile_errors,
        "holdout_total_abs_error": holdout_total_errors,
        "holdout_site_max_abs_error": holdout_site_errors,
        "holdout_cluster_max_abs_error": holdout_cluster_errors,
        "profile_main_gaps": profile_main_gaps,
        "profile_main_gap_max_abs_error": profile_gap_error,
        "nesting_gap_max_abs_error": nesting_gap_error,
        "T": direct_T,
    }


def audit_coarse_grid(
    path: Path,
    bank: DirectBank,
    context: AuditContext,
    prey_counts: IntArray,
    predator_counts: IntArray,
    rows: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    """Directly score each of the 1,350 stored lower-bound lattice points."""
    grid = read_json(path)
    raw_points = grid.get("raw_points")
    if grid.get("points") != 1350 or not isinstance(raw_points, list) or len(raw_points) != 1350:
        raise ValueError("coarse-grid raw point surface is incomplete")
    coarse_h = (1.0, 1.5, 3.0, 6.0, 10.0)
    coarse_beta = (-2.0, -1.0, 0.0, 0.6, 1.0, 2.0)
    coarse_mu = (0.0005, 0.001, 0.0016, 0.002, 0.0025, 0.0032, 0.004, 0.005, 0.006)
    coarse_sd = (0.0, 0.1, 0.2, 0.3, 0.4)
    expected_grid = {
        "h": list(coarse_h),
        "beta": list(coarse_beta),
        "mu": list(coarse_mu),
        "detection_sd": list(coarse_sd),
    }
    if grid.get("grid") != expected_grid or grid.get("expected_points") != 1350:
        raise ValueError("coarse-grid support differs from the frozen diagnostic grid")
    expected_support = {
        (h, beta, mu, sd)
        for h in coarse_h
        for beta in coarse_beta
        for mu in coarse_mu
        for sd in coarse_sd
    }
    observed_support: set[tuple[float, float, float, float]] = set()
    maximum_error = 0.0
    reconstructed = {name: np.full(8, -np.inf, dtype=np.float64) for name in MODEL_NAMES}
    for point_row in raw_points:
        point = _fit_parameters(point_row["point"])
        coordinate = (
            point["h"], point["beta"], point["mu"], point["detection_sd"]
        )
        if coordinate in observed_support:
            raise ValueError("coarse-grid contains a duplicated coordinate")
        observed_support.add(coordinate)
        expected_models = (
            list(MODEL_NAMES)
            if point["beta"] == 0.0
            else ["adjusted_free_h", "adjusted_h1"]
        )
        if point_row.get("applicable_models") != expected_models:
            raise ValueError("coarse-grid applicable-model identity is invalid")
        try:
            h_index = coarse_h.index(point["h"])
        except ValueError as error:
            raise ValueError("coarse-grid h coordinate is not registered") from error
        stored = np.asarray(point_row["training_logjoint_by_history_and_h"], dtype=np.float64)
        if stored.shape != (8, 5):
            raise ValueError("coarse-grid point has the wrong score shape")
        direct_values = direct_multi_training_scores(
            bank, context, prey_counts, predator_counts, point
        )
        for history in range(8):
            value = float(direct_values[history])
            maximum_error = max(maximum_error, abs(value - float(stored[history, h_index])))
            for model in point_row["applicable_models"]:
                if model.endswith("h1") and point["h"] != 1.0:
                    continue
                reconstructed[str(model)][history] = max(
                    reconstructed[str(model)][history], value
                )
    if observed_support != expected_support:
        raise ValueError("coarse-grid does not contain the canonical support exactly once")
    maxima_errors = {
        model: float(
            np.max(
                np.abs(
                    reconstructed[model]
                    - np.asarray(grid["max_logjoint"][model], dtype=np.float64)
                )
            )
        )
        for model in MODEL_NAMES
    }
    dominance_gaps = {
        model: {
            str(history): float(
                reconstructed[model][history]
                - float(rows[history]["fits"][model]["raw_logjoint"])
            )
            for history in range(8)
        }
        for model in MODEL_NAMES
    }
    audit_checks = {
        "direct_scores": maximum_error <= SCORE_TOLERANCE,
        "maxima": max(maxima_errors.values()) <= SCORE_TOLERANCE,
    }
    scientific_passed = all(
        value <= STATISTIC_TOLERANCE
        for model in dominance_gaps.values()
        for value in model.values()
    )
    if not all(audit_checks.values()):
        raise ValueError("coarse-grid direct audit failed")
    return {
        "passed": True,
        "scientific_qualification_passed": scientific_passed,
        "audit_checks": audit_checks,
        "maximum_score_abs_error": maximum_error,
        "maxima_abs_error": maxima_errors,
        "main_fit_gaps": dominance_gaps,
        "points": 1350,
    }


def audit_calibration_fixture(directory: Path) -> dict[str, Any]:
    """Independently exercise 765-node screening and effect arithmetic."""
    metadata = read_json(directory / "fixture.json")
    with np.load(directory / "fixture.npz", allow_pickle=False) as fixture:
        required = {
            "observed_pre_scores",
            "screen_reference_D",
            "observed_effect_T",
            "effect_reference_T",
            "observed_fit_valid",
            "reference_fit_valid",
        }
        if set(fixture.files) != required:
            raise ValueError("calibration fixture array schema mismatch")
        observed_scores = np.asarray(fixture["observed_pre_scores"], dtype=np.float64)
        reference_D = np.asarray(fixture["screen_reference_D"], dtype=np.float64)
        observed_T = np.asarray(fixture["observed_effect_T"], dtype=np.float64)
        effect_T = np.asarray(fixture["effect_reference_T"], dtype=np.float64)
        observed_valid = np.asarray(fixture["observed_fit_valid"], dtype=bool)
        reference_valid = np.asarray(fixture["reference_fit_valid"], dtype=bool)
    if (
        observed_scores.shape != (4, 765)
        or reference_D.shape != (99, 765)
        or observed_T.shape != (4,)
        or effect_T.shape != (765, 999)
        or observed_valid.shape != (4,)
        or reference_valid.shape != (765, 999)
    ):
        raise ValueError("calibration fixture has the wrong frozen shape")
    observed_D = np.asarray(
        [[local_discrepancy(row, node) for node in range(765)] for row in observed_scores],
        dtype=np.float64,
    )
    q_values = np.asarray(
        [
            [
                inclusive_rank(observed_D[case, node], reference_D[:, node].tolist())
                for node in range(765)
            ]
            for case in range(4)
        ],
        dtype=np.float64,
    )
    retained = screen_sets(observed_scores, reference_D.T)
    union = tuple(sorted(set().union(*(set(case) for case in retained))))
    decisions: list[dict[str, Any]] = []
    for case in range(4):
        if not observed_valid[case] or not retained[case]:
            decisions.append({"p_BB": 1.0, "declare": False, "abstain": True})
            continue
        if any(not bool(reference_valid[node].all()) for node in retained[case]):
            decisions.append({"p_BB": 1.0, "declare": False, "abstain": True})
            continue
        result = effect_decision(
            float(observed_T[case]),
            retained[case],
            {node: effect_T[node] for node in retained[case]},
        )
        decisions.append(
            {
                "p_BB": result["p_BB"],
                "declare": result["declare"],
                "abstain": result["abstain"],
            }
        )
    actual = {
        "candidate_indices": [list(case) for case in retained],
        "union": list(union),
        "decisions": decisions,
    }
    expected = metadata.get("expected")
    if expected is not None and expected != actual:
        raise ValueError("calibration fixture expected result mismatch")
    contract = metadata.get("address_contract")
    if not isinstance(contract, dict):
        raise ValueError("calibration fixture lacks its address contract")
    nodes = [
        {
            "index": index,
            "beta": beta,
            "mu": mu,
            "detection_sd": detection_sd,
        }
        for index, (beta, mu, detection_sd) in enumerate(nuisance_grid())
    ]
    node_bytes = json.dumps(nodes, sort_keys=True, separators=(",", ":")).encode()
    expected_contract = {
        "schema": "goal059-capstone-address-v1",
        "root": int(contract.get("root", -1)),
        "namespace": PUBLIC_NAMESPACE,
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
    }
    if contract != expected_contract:
        raise ValueError("calibration fixture address contract mismatch")
    if metadata.get("fixture_npz_sha256") != sha256_file(directory / "fixture.npz"):
        raise ValueError("calibration fixture NPZ hash mismatch")
    if not np.array_equal(q_values, np.asarray(metadata.get("q_values"), dtype=np.float64)):
        raise ValueError("calibration fixture q-value surface mismatch")
    return {
        "passed": True,
        "observed_D_sha256": array_sha256(observed_D),
        "q_values_sha256": array_sha256(q_values),
        "address_contract_sha256": hashlib.sha256(
            json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "candidate_counts": [len(case) for case in retained],
        "union_count": len(union),
        "decisions": decisions,
        "fixture_npz_sha256": sha256_file(directory / "fixture.npz"),
        "fixture_json_sha256": sha256_file(directory / "fixture.json"),
    }


def _profile_coordinate_lr(profile: Mapping[str, Any], coordinate: float) -> float:
    grid = np.asarray(profile["grid"], dtype=np.float64)
    values = np.asarray(profile["values"], dtype=np.float64)
    matches = np.flatnonzero(np.isclose(grid, coordinate, rtol=0.0, atol=1e-12))
    if len(matches) != 1:
        raise ValueError("generating coordinate is absent or duplicated in profile grid")
    lr = centered_lr(values.tolist())
    return float(lr[int(matches[0])])


def independent_stability(
    rows: Mapping[str, Mapping[str, Any]], truth: Mapping[str, Any]
) -> dict[str, Any]:
    """Reconstruct every registered full-versus-half stability predicate."""
    if set(rows) != {"full", "first_half", "second_half"}:
        raise ValueError("stability rows must contain the three registered bank views")
    primary = rows["full"]
    exact = truth["background"] == "exact"
    generating_h = float(truth["effect"])
    generating_beta = float(truth["beta"]) if exact else None
    task_status = {
        name: (
            all(
                row["fits"][model].get("numerical_status") == "converged"
                for model in MODEL_NAMES
            )
            and all(
                status == "converged"
                for profile in row["profiles"].values()
                for status in profile["statuses"]
            )
            and all(
                float(value) <= STATISTIC_TOLERANCE
                for value in row["nesting_gaps"].values()
            )
            and all(
                float(value) <= STATISTIC_TOLERANCE
                for value in row["profile_main_gaps"].values()
            )
        )
        for name, row in rows.items()
    }
    halves: dict[str, Any] = {}
    for name in ("first_half", "second_half"):
        half = rows[name]
        profile_rows: dict[str, Any] = {}
        for profile_name in ("constant_h", "adjusted_h", "adjusted_beta"):
            primary_profile = primary["profiles"][profile_name]
            half_profile = half["profiles"][profile_name]
            if primary_profile["grid"] != half_profile["grid"]:
                raise ValueError("profile grids differ across bank representations")
            primary_r = centered_lr(primary_profile["values"])
            half_r = centered_lr(half_profile["values"])
            core = (primary_r <= PROFILE_CORE) | (half_r <= PROFILE_CORE)
            core_movement = float(np.max(np.abs(primary_r[core] - half_r[core])))
            generating_coordinate: float | None
            if profile_name in {"constant_h", "adjusted_h"}:
                generating_coordinate = generating_h
            elif exact:
                generating_coordinate = generating_beta
            else:
                generating_coordinate = None
            generating_movement = (
                abs(
                    _profile_coordinate_lr(primary_profile, float(generating_coordinate))
                    - _profile_coordinate_lr(half_profile, float(generating_coordinate))
                )
                if generating_coordinate is not None
                else None
            )
            profile_rows[profile_name] = {
                "core_maximum_movement": core_movement,
                "core_nodes": int(core.sum()),
                "generating_coordinate": generating_coordinate,
                "generating_movement": generating_movement,
                "passed": core_movement <= STABILITY_TOLERANCE
                and (
                    generating_movement is None
                    or generating_movement <= STABILITY_TOLERANCE
                ),
            }
        primary_scores = {
            model: float(
                primary["heldout_scores"][model]["conditional_prey_total_nats"]
            )
            for model in MODEL_NAMES
        }
        half_scores = {
            model: float(half["heldout_scores"][model]["conditional_prey_total_nats"])
            for model in MODEL_NAMES
        }
        primary_contrasts = heldout_contrasts(primary_scores)
        half_contrasts = heldout_contrasts(half_scores)
        contrast_movement = {
            contrast: abs(half_contrasts[contrast] - primary_contrasts[contrast])
            for contrast in primary_contrasts
        }
        T_movement = abs(float(half["paired"]["T"]) - float(primary["paired"]["T"]))
        gates = {
            "adjusted_T": T_movement <= STABILITY_TOLERANCE,
            "profiles": all(value["passed"] for value in profile_rows.values()),
            "heldout_candidate_contrasts": max(contrast_movement.values())
            <= STABILITY_TOLERANCE,
            "main_and_profile_status": task_status["full"] and task_status[name],
        }
        halves[name] = {
            "passed": all(gates.values()),
            "gates": gates,
            "adjusted_T_movement": T_movement,
            "profiles": profile_rows,
            "heldout_candidate_contrast_movement": contrast_movement,
        }
    return {
        "passed": all(value["passed"] for value in halves.values()),
        "tolerance": STABILITY_TOLERANCE,
        "generating_nodes": {"h": generating_h, "beta": generating_beta},
        "halves": halves,
    }


def audit_panel_results(
    directory: Path,
    raw_arrivals: NDArray[np.float64],
    context: AuditContext,
    prey_counts: IntArray,
    predator_counts: IntArray,
    truths: Sequence[Mapping[str, Any]],
    *,
    bank_manifest: Mapping[str, Any],
    panel_bindings: Mapping[str, Any],
) -> dict[str, Any]:
    """Audit all 24 fit tasks, lattice surfaces and final stability gates."""
    completed_path = directory / "completed.json"
    completed = read_json(completed_path)
    if completed.get("schema_version") != "goal059-public-panel-v1":
        raise ValueError("panel completion receipt has the wrong schema")
    artifact_hashes: dict[str, str] = {}
    completed_checks = {
        "status": completed.get("status") == "completed",
        "histories": completed.get("histories") == 8,
        "representations": completed.get("representations")
        == ["full", "first_half", "second_half"],
        "bank_manifest": completed.get("bank_manifest") == bank_manifest,
        "raw_arrivals": completed.get("raw_arrivals_sha256")
        == array_sha256(raw_arrivals),
        "observations": completed.get("observations_sha256")
        == panel_bindings.get("observations_sha256"),
        "evaluator": completed.get("evaluator_sha256")
        == panel_bindings.get("evaluator_sha256"),
        "panel_manifest": completed.get("panel_manifest_sha256")
        == panel_bindings.get("manifest_sha256"),
    }
    if not all(completed_checks.values()):
        raise ValueError("panel completion provenance bindings are invalid")
    representations = {
        "full": np.asarray(raw_arrivals),
        "first_half": np.asarray(raw_arrivals[:HALF_BANK_SIZE]),
        "second_half": np.asarray(raw_arrivals[HALF_BANK_SIZE:]),
    }
    all_rows: dict[int, dict[str, dict[str, Any]]] = {index: {} for index in range(8)}
    representation_results: dict[str, Any] = {}
    for representation, arrivals in representations.items():
        direct_bank = make_direct_bank(arrivals, context.site_ids)
        row_results: dict[str, Any] = {}
        representation_rows: dict[int, dict[str, Any]] = {}
        for history in range(8):
            row_path = directory / "results" / f"history-{history:02d}-{representation}.json"
            row = read_json(row_path)
            if row.get("history") != history or row.get("representation") != representation:
                raise ValueError("panel result task identity mismatch")
            main_path = (
                directory
                / "results"
                / f"history-{history:02d}-{representation}-main.json"
            )
            main = read_json(main_path)
            expected_main = {
                key: row[key]
                for key in (
                    "history",
                    "representation",
                    "bank_size",
                    "paired",
                    "adjusted_T",
                    "constant_T",
                    "fits",
                )
            }
            if main != expected_main:
                raise ValueError("preserved pre-profile main fit differs from final result")
            artifact_hashes[str(row_path.relative_to(directory))] = sha256_file(row_path)
            artifact_hashes[str(main_path.relative_to(directory))] = sha256_file(main_path)
            representation_rows[history] = row
            all_rows[history][representation] = row
            row_results[str(history)] = audit_result_row(
                row,
                direct_bank,
                context,
                prey_counts[history],
                predator_counts[history],
            )
        coarse_path = directory / f"coarse-grid-{representation}.json"
        coarse_result = audit_coarse_grid(
            coarse_path,
            direct_bank,
            context,
            prey_counts,
            predator_counts,
            representation_rows,
        )
        representation_results[representation] = {
            "rows": row_results,
            "coarse_grid": coarse_result,
        }
        artifact_hashes[str(coarse_path.relative_to(directory))] = sha256_file(coarse_path)
    stability = {
        str(history): independent_stability(all_rows[history], truths[history])
        for history in range(8)
    }
    stability_path = directory / "bank-stability.json"
    production_stability = read_json(stability_path)
    if completed.get("bank_stability") != production_stability:
        raise ValueError("completion receipt and stability sidecar differ")
    artifact_hashes[str(stability_path.relative_to(directory))] = sha256_file(stability_path)
    artifact_hashes[str(completed_path.relative_to(directory))] = sha256_file(completed_path)
    stability_agreement = {
        str(history): bool(production_stability[str(history)]["passed"])
        == stability[str(history)]["passed"]
        for history in range(8)
    }
    independent_pass = all(value["passed"] for value in stability.values())
    all_task_science = all(
        row["scientific_qualification_passed"]
        for representation in representation_results.values()
        for row in representation["rows"].values()
    )
    all_lattice_science = all(
        representation["coarse_grid"]["scientific_qualification_passed"]
        for representation in representation_results.values()
    )
    scientific_pass = independent_pass and all_task_science and all_lattice_science
    checks = {
        "all_direct_rows": all(
            row["passed"]
            for representation in representation_results.values()
            for row in representation["rows"].values()
        ),
        "all_lattices": all(
            representation["coarse_grid"]["passed"]
            for representation in representation_results.values()
        ),
        "stability_agrees": all(stability_agreement.values()),
        "completed_pass_agrees": bool(completed.get("passed")) == scientific_pass,
        "completed_provenance": all(completed_checks.values()),
    }
    if not all(checks.values()):
        raise ValueError("panel result independent audit failed")
    return {
        "passed": scientific_pass,
        "audit_completed": True,
        "checks": checks,
        "all_task_status_and_nesting_passed": all_task_science,
        "all_lattice_dominance_passed": all_lattice_science,
        "representations": representation_results,
        "bank_stability": stability,
        "stability_agreement": stability_agreement,
        "artifact_sha256": dict(sorted(artifact_hashes.items())),
        "completed_sha256": sha256_file(completed_path),
    }


def audit_mechanical_receipts(directory: Path) -> dict[str, Any]:
    qualification_path = directory / "qualification.json"
    mechanical_path = directory / "mechanical-receipt.json"
    qualification = read_json(qualification_path)
    mechanical = read_json(mechanical_path)
    comparisons = mechanical.get("compressed_exact", {})
    repeated = mechanical.get("mechanical_fits", {})
    primitive = mechanical.get("adjusted_pair_primitive", {})
    checks = {
        "qualification_schema": qualification.get("schema_version")
        == "goal059-qualification-v1",
        "mechanical_schema": mechanical.get("schema_version")
        == "goal059-mechanical-receipt-v1",
        "mechanical_hash": qualification.get("mechanical_receipt_sha256")
        == sha256_file(mechanical_path),
        "domain_complete": len(mechanical.get("mechanical_domain", [])) == 17,
        "compressed_direct_passed": comparisons.get("passed") is True
        and comparisons.get("points") == 17
        and float(comparisons.get("tolerance", math.inf)) == SCORE_TOLERANCE,
        "repeat_fits_passed": repeated.get("passed") is True,
        "pair_primitive_passed": primitive.get("passed") is True,
        "overall_passed": mechanical.get("passed") is True
        and qualification.get("passed") is True,
    }
    if not all(checks.values()):
        raise ValueError("mechanical qualification receipt audit failed")
    return {
        "passed": True,
        "checks": checks,
        "qualification_sha256": sha256_file(qualification_path),
        "mechanical_receipt_sha256": sha256_file(mechanical_path),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("full", "map-failure"), default="full")
    parser.add_argument("--map-only", action="store_true", help="audit a terminal map failure")
    parser.add_argument("--public-inputs", type=Path, required=True)
    parser.add_argument("--bank", type=Path)
    parser.add_argument("--qualification", type=Path)
    parser.add_argument(
        "--panel", type=Path, help="generated public fixture directory"
    )
    parser.add_argument("--panel-results", type=Path)
    parser.add_argument("--calibration-fixture", type=Path)
    parser.add_argument("--source-freeze", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.output.exists():
        raise FileExistsError("refusing to replace an earlier independent audit")
    args.output.mkdir(parents=True)
    repository = Path(__file__).resolve().parents[1]
    receipt: dict[str, Any] = {
        "schema_version": "goal059-independent-public-audit-v1",
        "status": "incomplete",
        "audit_passed": False,
    }
    try:
        source = audit_source_freeze(
            repository,
            args.source_freeze,
            args.runtime,
            args.registration,
        )
        if args.mode == "map-failure" or args.map_only:
            failed_map = audit_negative_public_map(args.public_inputs)
            receipt.update(
                {
                    "status": "completed",
                    "audit_passed": True,
                    "scientific_qualification_passed": False,
                    "terminal_negative_qualification": True,
                    "source_freeze": source,
                    "public_inputs": failed_map,
                }
            )
            write_json(args.output / "audit.json", receipt)
            return 0
        required_full = {
            "bank": args.bank,
            "qualification": args.qualification,
            "panel": args.panel,
            "panel_results": args.panel_results,
            "calibration_fixture": args.calibration_fixture,
        }
        missing = [name for name, path in required_full.items() if path is None]
        if missing:
            raise ValueError(f"full audit is missing arguments: {missing}")
        assert args.bank is not None
        assert args.qualification is not None
        assert args.panel is not None
        assert args.panel_results is not None
        assert args.calibration_fixture is not None
        bank_path = Path(args.bank)
        qualification_path = Path(args.qualification)
        panel_path = Path(args.panel)
        panel_results_path = Path(args.panel_results)
        calibration_fixture_path = Path(args.calibration_fixture)
        fixed, setup, context, public_result = reconstruct_public_inputs(args.public_inputs)
        raw, bank_result = audit_arrival_bank(
            bank_path,
            context.site_ids,
            fixed=fixed,
            map_a=setup.exposure_score,
        )
        mechanical = audit_mechanical_receipts(qualification_path)
        prey, predator, truths, fixture_result = audit_public_panel(
            panel_path, fixed, setup, context
        )
        fixture_bindings = {
            "qualification": fixture_result["qualification_sha256"]
            == mechanical["qualification_sha256"],
            "mechanical_receipt": fixture_result["mechanical_receipt_sha256"]
            == mechanical["mechanical_receipt_sha256"],
            "public_inputs": fixture_result["public_inputs_sha256"]
            == public_result["public_inputs_sha256"],
        }
        if not all(fixture_bindings.values()):
            raise ValueError("public fixture predraw bindings do not match audited inputs")
        fixture_result["audited_predraw_bindings"] = fixture_bindings
        panel_result = audit_panel_results(
            panel_results_path,
            raw,
            context,
            prey,
            predator,
            truths,
            bank_manifest=read_json(bank_path / "manifest.json"),
            panel_bindings=fixture_result,
        )
        calibration = audit_calibration_fixture(calibration_fixture_path)
        receipt.update(
            {
                "status": "completed",
                "audit_passed": True,
                "scientific_qualification_passed": panel_result["passed"],
                "source_freeze": source,
                "public_inputs": public_result,
                "arrival_bank": bank_result,
                "mechanical_qualification": mechanical,
                "public_fixtures": fixture_result,
                "panel_results": panel_result,
                "calibration_fixture": calibration,
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
        write_json(args.output / "audit.json", receipt)
        raise
    write_json(args.output / "audit.json", receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
