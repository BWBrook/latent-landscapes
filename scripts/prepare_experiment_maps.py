"""Prepare development and qualification map geometry for the Sprint 1 experiment.

Seed recipe (documented in the written commitment record as well): for role code r
(development=1, qualification=2, validation=3), archetype index a in ARCHETYPES order
and map index m, take ``ss = SeedSequence(2026110501, spawn_key=(r, a, m))`` and
``w = ss.generate_state(4, dtype=np.uint32) & 0x7fffffff``.  Then map_seed=w[0],
sampling_seed=w[1], holdout_seed=w[2], arm_seed=w[3].  Failures (geometry, design,
solver, surface) are kept as receipts; a failed seed is never replaced.
Validation maps are not generated; only the recipe, spawn keys and their hash are written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from latent_landscapes.arc3_landscapes import ARCHETYPES, build_landscape
from latent_landscapes.background_family import signal_window_surface
from latent_landscapes.capstone_public import _fixed_arrays
from latent_landscapes.development_challenge_data import build_general_site_setup, sha256
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.monitoring_design import build_master_monitoring_design

ROOT_SEED = 2026110501
ROLE_CODES = {"development": 1, "qualification": 2, "validation": 3}
MAPS_PER_ARCHETYPE = {"development": 10, "qualification": 3, "validation": 20}
OUTPUT = Path(__file__).resolve().parents[1] / "artifacts" / "sprint1" / "maps"


def derive_seeds(role: str, archetype_index: int, map_index: int) -> dict[str, int]:
    sequence = np.random.SeedSequence(
        ROOT_SEED, spawn_key=(ROLE_CODES[role], archetype_index, map_index)
    )
    w = [int(v) & 0x7FFFFFFF for v in sequence.generate_state(4, dtype=np.uint32)]
    return {"map_seed": w[0], "sampling_seed": w[1], "holdout_seed": w[2], "arm_seed": w[3]}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def prepare_map(job: tuple[str, int, int]) -> dict[str, Any]:
    role, archetype_index, map_index = job
    archetype = ARCHETYPES[archetype_index]
    directory = OUTPUT / role / f"{archetype}-{map_index}"
    record_path = directory / "record.json"
    if record_path.exists():
        loaded: dict[str, Any] = json.loads(record_path.read_text())
        return loaded
    directory.mkdir(parents=True, exist_ok=True)
    seeds = derive_seeds(role, archetype_index, map_index)
    record: dict[str, Any] = {
        "role": role,
        "archetype": archetype,
        "archetype_index": archetype_index,
        "map_index": map_index,
        "spawn_key": [ROLE_CODES[role], archetype_index, map_index],
        "seeds": seeds,
        "stage": "geometry",
    }
    try:
        landscape = build_landscape(archetype, seeds["map_seed"])
        record["admissible"] = True
        record["stage"] = "design"
        master = build_master_monitoring_design(
            landscape,
            sampling_seed=seeds["sampling_seed"],
            holdout_seed=seeds["holdout_seed"],
            arm_seed=seeds["arm_seed"],
            map_seed=seeds["map_seed"],
            solver_time_limit=30,
        )
        record["solver"] = master.solver_receipt.as_dict()
        record["stage"] = "setup"
        fixed = FixedInputs(landscape, master.sampling, {"master_design_verified": True})
        setup = build_general_site_setup(fixed)
        record["stage"] = "surfaces"
        surfaces = signal_window_surface(landscape, setup)
        record["surface_diagnostics"] = surfaces.diagnostics
        record["unreachable_tie_count"] = setup.unreachable_tie_count
        record["unreachable_tie_exposure_score"] = setup.unreachable_tie_exposure_score
        np.savez_compressed(directory / "public_inputs.npz", **_fixed_arrays(fixed))  # type: ignore[arg-type]
        np.savez_compressed(
            directory / "exposure.npz",
            map_a=setup.exposure_score,
            site_a=setup.exposure_score[setup.site_rows, setup.site_cols],
            accepted_mask=setup.accepted_mask,
        )
        np.savez_compressed(directory / "surfaces.npz", T=surfaces.signal, W=surfaces.window)
        write_json(
            directory / "design.json",
            {
                "clusters": [asdict(v) for v in master.sampling.clusters],
                "sites": [asdict(v) for v in master.sampling.sites],
                "eligible_centres": [asdict(v) for v in master.sampling.eligible_centres],
            },
        )
        record["baseline_site_ids"] = list(master.baseline_site_ids)
        record["holdout_site_ids"] = list(master.holdout_site_ids)
        record["c_site_ids"] = list(master.c_site_ids)
        record["files"] = {
            name: sha256(directory / name)
            for name in ("public_inputs.npz", "exposure.npz", "surfaces.npz", "design.json")
        }
        record["stage"] = "complete"
        record["status"] = "ok"
    except Exception as error:
        record["status"] = "failed"
        record["failure"] = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        }
    write_json(record_path, record)
    return record


def write_validation_commitment() -> dict[str, Any]:
    body = {
        "root_seed": ROOT_SEED,
        "role_code": ROLE_CODES["validation"],
        "recipe": (
            "SeedSequence(root_seed, spawn_key=(3, archetype_index, map_index)); "
            "generate_state(4, uint32) & 0x7fffffff -> map, sampling, holdout, arm seeds"
        ),
        "archetypes": list(ARCHETYPES),
        "maps_per_archetype": MAPS_PER_ARCHETYPE["validation"],
        "spawn_keys": [
            [ROLE_CODES["validation"], a, m]
            for a in range(len(ARCHETYPES))
            for m in range(MAPS_PER_ARCHETYPE["validation"])
        ],
    }
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    commitment = {**body, "commitment_sha256": digest}
    write_json(OUTPUT / "validation-commitment.json", commitment)
    return commitment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roles", nargs="*", default=["development", "qualification"])
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    commitment = write_validation_commitment()
    print("validation commitment", commitment["commitment_sha256"])
    for role in args.roles:
        if role not in ("development", "qualification"):
            raise SystemExit("validation maps are never generated")
        jobs = [
            (role, a, m) for a in range(len(ARCHETYPES)) for m in range(MAPS_PER_ARCHETYPE[role])
        ]
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            records = list(pool.map(prepare_map, jobs))
        counts: dict[str, dict[str, int]] = {}
        for record in records:
            tally = counts.setdefault(record["archetype"], {"ok": 0, "failed": 0})
            tally[record["status"]] += 1
        manifest = {
            "role": role,
            "root_seed": ROOT_SEED,
            "counts": counts,
            "maps": [
                {k: v for k, v in record.items() if k != "failure"}
                | (
                    {"failure": {k: v for k, v in record["failure"].items() if k != "traceback"}}
                    if "failure" in record
                    else {}
                )
                for record in records
            ],
        }
        write_json(OUTPUT / f"{role}-manifest.json", manifest)
        print(role, counts, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
