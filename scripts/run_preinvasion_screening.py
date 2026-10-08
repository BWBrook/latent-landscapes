"""Freeze, qualify, or run the Goal057 public screening pilot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import time
from pathlib import Path

import numpy as np

from latent_landscapes import preinvasion_screening as screening


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(screening.jsonable(value), indent=2, sort_keys=True) + "\n")


def _array_sha256(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).view(np.uint8)).hexdigest()


def freeze(panel_path: Path, output: Path) -> dict[str, object]:
    if output.exists():
        raise FileExistsError("preserve an existing Goal057 freeze")
    panel = screening.load_public_panel(panel_path)
    output.mkdir(parents=True)
    ledger_path = output / "seed_ledger.npz"
    screening.write_seed_ledger(ledger_path)
    receipt: dict[str, object] = {
        "status": "frozen",
        "root_seed": screening.ROOT_SEED,
        "seed_namespace": screening.SEED_NAMESPACE,
        "stages": list(screening.STAGES),
        "reference_count": screening.REFERENCE_COUNT,
        "grid_size": screening.GRID_SIZE,
        "panel_sha256": panel.panel_sha256,
        "public_inputs": {
            "site_count": len(panel.observations.site_ids),
            "training_site_count": int(panel.observations.training_mask.sum()),
            "map_shape": list(panel.map_a.shape),
            "site_ids_sha256": _array_sha256(np.asarray(panel.observations.site_ids)),
            "map_a_sha256": _array_sha256(panel.map_a),
            "site_a_sha256": _array_sha256(panel.site_a),
        },
        "seed_ledger_sha256": screening.file_sha256(ledger_path),
        "draws_performed": False,
    }
    _write_json(output / "freeze.json", receipt)
    return receipt


def qualify(panel_path: Path, freeze_path: Path, output: Path) -> dict[str, object]:
    if output.exists():
        raise FileExistsError("preserve an existing Goal057 qualification")
    freeze_receipt = json.loads((freeze_path / "freeze.json").read_text())
    if freeze_receipt.get("status") != "frozen" or freeze_receipt.get("draws_performed"):
        raise ValueError("qualification requires a draw-freeze receipt")
    screening.validate_seed_ledger(
        freeze_path / "seed_ledger.npz", str(freeze_receipt["seed_ledger_sha256"])
    )
    panel = screening.load_public_panel(panel_path)
    if panel.panel_sha256 != freeze_receipt.get("panel_sha256"):
        raise ValueError("panel changed after freeze")
    started = time.perf_counter()
    equivalence = screening.vectorized_equivalence(panel, count=3)
    checks = {
        "panel_histories": int(panel.observations.prey_counts.shape[0]) == 16,
        "panel_sites": int(panel.observations.prey_counts.shape[1]) == 160,
        "training_sites": int(panel.observations.training_mask.sum()) == 120,
        "grid_size": screening.GRID_SIZE == 3645,
        "reference_count": screening.REFERENCE_COUNT == 99,
        "vectorized_point_batch_equivalence": equivalence,
    }
    passed = bool(
        all(
            value is True
            for key, value in checks.items()
            if key != "vectorized_point_batch_equivalence"
        )
        and equivalence["passed"]
    )
    output.mkdir(parents=True)
    receipt: dict[str, object] = {
        "status": "qualified" if passed else "failed",
        "passed": passed,
        "panel_sha256": panel.panel_sha256,
        "checks": checks,
        "elapsed_seconds": time.perf_counter() - started,
        "draws_performed": False,
    }
    _write_json(output / "qualification.json", receipt)
    if not passed:
        raise RuntimeError("mechanical Goal057 qualification failed")
    return receipt


def run(
    panel_path: Path, freeze_path: Path, qualification_path: Path, output: Path, workers: int
) -> dict[str, object]:
    if output.exists():
        raise FileExistsError("preserve an existing Goal057 run attempt")
    freeze_receipt = json.loads((freeze_path / "freeze.json").read_text())
    qualification_receipt = json.loads((qualification_path / "qualification.json").read_text())
    if (
        freeze_receipt.get("status") != "frozen"
        or qualification_receipt.get("status") != "qualified"
    ):
        raise ValueError("run requires frozen and qualified inputs")
    screening.validate_seed_ledger(
        freeze_path / "seed_ledger.npz", str(freeze_receipt["seed_ledger_sha256"])
    )
    panel = screening.load_public_panel(panel_path)
    if panel.panel_sha256 != freeze_receipt.get(
        "panel_sha256"
    ) or panel.panel_sha256 != qualification_receipt.get("panel_sha256"):
        raise ValueError("panel changed after freeze or qualification")
    output.mkdir(parents=True)
    started = time.perf_counter()
    true_nodes = screening.true_panel_nodes(panel)
    diagnostic_nodes = tuple(sorted(set(int(value) for value in true_nodes)))
    reference, timing, node_results = screening.run_reference_screen(
        panel,
        workers=workers,
        diagnostic_nodes=diagnostic_nodes,
        checkpoint_dir=output / "node_results",
    )
    diagnostic_persistence_started = time.perf_counter()
    np.savez_compressed(
        output / "reference_contrasts.npz",
        reference_contrasts=reference,
        node_indices=np.arange(screening.GRID_SIZE, dtype=np.int64),
    )
    _write_json(output / "reference_timing.json", timing)
    diagnostic_counts: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for node in diagnostic_nodes:
        result = node_results[node]
        if result.training_counts is None or result.predator_counts is None:
            raise RuntimeError("diagnostic node did not retain its 99 reference counts")
        diagnostic_counts[node] = (result.training_counts, result.predator_counts)
    np.savez_compressed(
        output / "diagnostic_counts.npz",
        node_indices=np.asarray(diagnostic_nodes, dtype=np.int64),
        node_for_reference=np.repeat(
            np.asarray(diagnostic_nodes, dtype=np.int64), screening.REFERENCE_COUNT
        ),
        reference_indices=np.tile(
            np.arange(screening.REFERENCE_COUNT, dtype=np.int64), len(diagnostic_nodes)
        ),
        prey_counts=np.concatenate([diagnostic_counts[node][0] for node in diagnostic_nodes]),
        predator_counts=np.concatenate([diagnostic_counts[node][1] for node in diagnostic_nodes]),
        site_ids=np.asarray(panel.observations.site_ids),
        training_mask=np.asarray(panel.observations.training_mask),
        prey_times=np.asarray(panel.observations.prey_times[:7]),
        predator_times=np.asarray(panel.observations.predator_times),
    )
    timing["diagnostic_count_serialization_seconds"] = (
        time.perf_counter() - diagnostic_persistence_started
    )
    independent = importlib.import_module("latent_landscapes.preinvasion_independent")
    diagnostic_fit_started = time.perf_counter()
    fit_rows = screening.fit_diagnostic_references(
        panel,
        diagnostic_counts,
        independent_module=independent,
        progress_path=output / "diagnostic_fit_rows.jsonl",
    )
    timing["diagnostic_fit_wall_seconds"] = time.perf_counter() - diagnostic_fit_started
    timing["diagnostic_independent_check_seconds"] = float(
        sum(float(row.get("independent_check_seconds", 0.0)) for row in fit_rows)
    )
    screening.jsonable(fit_rows)
    _write_json(output / "diagnostic_fit_rows.json", fit_rows)
    with (output / "diagnostic_fit_rows.csv").open("w", newline="") as handle:
        fields = sorted(
            {key for row in fit_rows for key in row if not isinstance(row[key], (list, tuple))}
        )
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in fit_rows:
            writer.writerow({key: screening.jsonable(row.get(key)) for key in fields})
    surface_started = time.perf_counter()
    observed_surface, observed_contrasts = screening.score_open_surfaces(panel)
    timing["observed_surface_scoring_seconds"] = time.perf_counter() - surface_started
    serialization_started = time.perf_counter()
    manifest = screening.write_screen_outputs(
        output / "screening", reference, observed_surface, observed_contrasts, panel
    )
    timing["screen_output_serialization_seconds"] = time.perf_counter() - serialization_started
    _write_json(output / "reference_timing.json", timing)
    receipt = {
        "status": "completed",
        "panel_sha256": panel.panel_sha256,
        "reference_count": int(reference.size),
        "reference_shape": list(reference.shape),
        "diagnostic_fit_count": len(fit_rows),
        "diagnostic_node_count": len(diagnostic_nodes),
        "workers": workers,
        "timing": timing,
        "screening": manifest,
        "elapsed_seconds": time.perf_counter() - started,
    }
    _write_json(output / "completed.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("freeze", "qualify", "run"))
    parser.add_argument("--panel", type=Path, default=screening.DEFAULT_PANEL)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--qualification", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.mode == "freeze":
        result = freeze(args.panel, args.output)
    elif args.mode == "qualify":
        if args.freeze is None:
            parser.error("qualify requires --freeze")
        result = qualify(args.panel, args.freeze, args.output)
    else:
        if args.freeze is None or args.qualification is None:
            parser.error("run requires --freeze and --qualification")
        result = run(args.panel, args.freeze, args.qualification, args.output, args.workers)
    print(json.dumps(screening.jsonable(result), sort_keys=True))


if __name__ == "__main__":
    main()
