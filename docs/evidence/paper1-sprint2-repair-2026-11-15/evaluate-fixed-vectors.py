"""Post-outcome diagnostic; evaluate retained vectors without optimization."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import benchmark_spatial_profile as adapter
import numpy as np
import run_development_profile as loader
from latent_landscapes import spatial_profile
from latent_landscapes.differentiable_likelihood import prepare_site_likelihood


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluation(value):
    mode = value.mode
    return {
        "criterion": value.criterion,
        "criterion_gradient": value.criterion_gradient.tolist(),
        "success": bool(value.success),
        "message": value.message,
        "mode": None if mode is None else {
            name: getattr(mode, name)
            for name in ("success", "message", "score_inf", "iterations",
                         "evaluations", "newton_step_inf", "newton_decrement")
        },
    }


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--plan", type=Path, required=True)
parser.add_argument("--original-root", type=Path, required=True)
parser.add_argument("--repo", type=Path, required=True)
parser.add_argument("--version", choices=("baseline", "candidate"), required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
started = time.perf_counter()
plan = json.loads(args.plan.read_text())
root = args.repo.resolve()
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
assert commit == plan["sources"][args.version]
assert not subprocess.check_output(
    ["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, text=True
).strip()
for module in (adapter, loader, spatial_profile):
    assert Path(module.__file__).resolve().is_relative_to(root)
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    assert os.environ[name] == "1"
rows, identities = [], []
for group in plan["tasks"]:
    task_path = args.original_root / "work/qualification-results" / group["task_id"] / "_task.json"
    assert sha(task_path) == group["task_record_sha256"]
    task = json.loads(task_path.read_text())["task"]
    assert task["task_id"] == group["task_id"]
    assert task["source_commit"] == plan["sources"]["baseline"]
    input_hashes = {}
    for name, expected in task["input_sha256"].items():
        path = Path(name)
        assert sha(path) == expected
        input_hashes[str(path.relative_to(args.original_root))] = expected
    argv = task["argv"]
    data_args = argparse.Namespace(**{
        flag.replace("-", "_"): Path(argv[argv.index("--" + flag) + 1])
        for flag in ("input-dir", "observations", "arrival-bank", "compressed-bank")
    })
    data, identity = loader.load_panel_data(data_args)
    identities.append({"task_id": group["task_id"], "data_identity": identity,
                       "task_record_sha256": sha(task_path), "input_sha256": input_hashes})
    for vector in group["vectors"]:
        criterion = spatial_profile.SpatialProfileCriterion(
            data, evaluator_factory=lambda h, sd: prepare_site_likelihood(
                data.observed, data.bank, h, detection_sd=sd))
        point = np.asarray(vector["parameters"], dtype=float)
        positive = evaluation(criterion.evaluate_positive(point, fixed_h=group["h"], nuisance_fd=True))
        zero = evaluation(criterion.evaluate_sigma_zero(np.delete(point, 2), fixed_h=group["h"], nuisance_fd=True))
        assert positive["success"] and zero["success"]
        rows.append({"task_id": group["task_id"], "state": vector["state"],
                     "h": group["h"], "parameters": point.tolist(),
                     "positive": positive, "sigma_zero_at_same_nuisance": zero,
                     "criterion_stats": criterion.stats})
result = {"schema": "repair-fixed-vector-diagnostic-v1", "post_outcome": True,
          "optimization_run": False, "source_commit": commit, "version": args.version,
          "plan_sha256": sha(args.plan), "script_sha256": sha(Path(__file__)),
          "runtime_sif_sha256": os.environ["LL_RUNTIME_SIF_SHA256"],
          "python": sys.version, "platform": platform.platform(),
          "source_sha256": {str(p.relative_to(root)): sha(p) for p in
                            [*sorted((root / "src/latent_landscapes").rglob("*.py")),
                             root / "scripts/run_development_profile.py",
                             root / "scripts/benchmark_spatial_profile.py"]},
          "gradient_labels": ["alpha", "beta", "log_sigma", "detection_sd"],
          "sigma_zero_gradient_labels": ["alpha", "beta", "detection_sd"],
          "data": identities, "rows": rows, "elapsed_seconds": time.perf_counter() - started}
with args.output.open("x") as handle:
    json.dump(adapter._jsonable(result), handle, indent=2, allow_nan=False)
    handle.write("\n")
