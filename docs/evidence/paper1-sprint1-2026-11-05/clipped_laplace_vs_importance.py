"""Compare standard and curvature-clipped Laplace with archived importance integrals.

Descriptive, post-outcome: the challenge importance screens are reused as a
reference for the positive-family integral at fixed outer parameters. The
clipped variant replaces positive site curvature by zero in the determinant
term only (sharp clip; the smooth production clip differs negligibly).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from run_development_profile import load_panel_data  # noqa: E402

from latent_landscapes.differentiable_likelihood import prepare_site_likelihood  # noqa: E402
from latent_landscapes.spatial_profile import SpatialProfileCriterion  # noqa: E402

PANEL = ROOT / "artifacts/paper1_development_challenge_20261101"
REVIEW = PANEL / "completed-review"


def inputs(dataset: str):
    manifest = json.loads((PANEL / "panel-manifest.json").read_text())
    if dataset.startswith("C-"):
        case = next(c for c in manifest["optional_c_cases"] if c["dataset_id"] == dataset)
        index = case["map_index"]
        return argparse.Namespace(
            input_dir=PANEL / "master-public" / f"map-{index:02d}",
            observations=PANEL / dataset / "observations.npz",
            arrival_bank=REVIEW / "master-banks" / f"map-{index:02d}/B0/arrivals.npy",
            compressed_bank=REVIEW / "master-banks" / f"map-{index:02d}/B0/compressed.npz",
        )
    return argparse.Namespace(
        input_dir=PANEL / "archived-panel/public/legacy",
        observations=PANEL / f"archived-panel/datasets/{dataset}/observations.npz",
        arrival_bank=Path(manifest["banks"]["B0"]["raw"]),
        compressed_bank=Path(manifest["banks"]["B0"]["compressed"]),
    )


def positive_fit(receipt: dict, key: str) -> dict | None:
    if key == "free":
        return receipt["free"].get("True", {}).get("positive_sigma")
    h = float(key)
    for tight in ("True", "False"):
        for point in receipt["points"].get(tight, []):
            if point["h"] == h and point.get("positive_sigma"):
                return point["positive_sigma"]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    directory = REVIEW / "importance" / args.dataset
    receipt = json.loads((REVIEW / f"profiles/{args.dataset}-B0/dense/receipt.json").read_text())
    data, _ = load_panel_data(inputs(args.dataset))
    criterion = SpatialProfileCriterion(
        data,
        evaluator_factory=lambda h, d: prepare_site_likelihood(
            data.observed, data.bank, h, detection_sd=d
        ),
    )
    files = sorted(directory.glob("point-*-s*-n*.json"))
    best: dict[tuple[str, str], tuple[int, dict]] = {}
    for path in files:
        _, number, stream, draws = path.stem.split("-")
        n = int(draws[1:])
        if best.get((number, stream), (0, None))[0] < n:
            best[(number, stream)] = (n, json.loads(path.read_text()))
    rows = []
    for number in sorted({k[0] for k in best}):
        streams = [best[k][1] for k in best if k[0] == number]
        key = streams[0]["key"]
        fit = positive_fit(receipt, key)
        if fit is None or fit["parameters"]["log_sigma"] < math.log(1e-3):
            continue
        p = fit["parameters"]
        h = fit["h"]
        x = np.array([p["alpha"], p["beta"], p["log_sigma"], p["detection_sd"]])
        e = criterion.evaluate_positive(x, fixed_h=h)
        if not e.success:
            continue
        c = criterion.curves(h, p["detection_sd"]).evaluate(e.mode.eta)[2]
        chol = math.exp(p["log_sigma"]) * criterion._k_cholesky
        clipped = np.minimum(c, 0.0)
        m = np.eye(len(c)) - chol.T @ (clipped[:, None] * chol)
        clip_value = e.mode.value - 0.5 * np.linalg.slogdet(m)[1]
        estimates = [s["estimate"]["log_integral"] for s in streams]
        batches = np.concatenate([s["estimate"]["batch_log_integrals"] for s in streams])
        se = float(np.std(batches, ddof=1) / math.sqrt(len(batches)))
        rows.append(
            {
                "dataset": args.dataset,
                "point": number,
                "key": key,
                "h": h,
                "sigma": math.exp(p["log_sigma"]),
                "positive_curvature_sites": int((c > 0).sum()),
                "importance": float(np.mean(estimates)),
                "importance_se": se,
                "laplace": e.criterion,
                "clipped": float(clip_value),
                "relative_ess_min": min(
                    s["estimate"]["diagnostics"]["relative_ess"] for s in streams
                ),
            }
        )
    args.output.write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main()
