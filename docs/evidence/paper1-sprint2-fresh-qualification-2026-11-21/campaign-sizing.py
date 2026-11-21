"""Count archived exact pair grids and transfer the measured one-sided replay rate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_sprint2_pair import VIEWS, required_nodes, view_of  # noqa: E402

ORIGINAL = "99af5206b6a4e53f5b8e9d71cbf348f95e9ae574"
ACCEPTED = "432bb6e56e672f9e57f2f7bc369546023b07662e"
PANEL = ROOT / "docs/evidence/paper1-sprint1-2026-11-05/qualification-panel.json"
PANEL_HASH = "51006aa0355ab4ce9f28e572a4272f09c0dc9fcdb52ae6ed0570aacbb1cf240d"
Json = dict[str, Any]


def read(path: Path, digest: str | None = None) -> Json:
    payload = path.read_bytes()
    if digest is not None and hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f"archived evidence checksum differs: {path}")
    return json.loads(payload)


def result(record_path: Path, record: Json, source: str) -> Json:
    if record["source"]["commit"] != source or record["source"]["tracked_changes"]:
        raise ValueError(f"archived result has different source: {record_path}")
    name = record["task"]["result_path"]
    return read(record_path.parent / record["attempt"] / name, record["output_sha256"][name])


def original_grids(root: Path) -> Json:
    fits = {}
    for path in sorted(root.glob("*/_task.json")):
        record = read(path)
        if record["status"] == "resolved":
            fit = result(path, record, ORIGINAL)
            if fit["failure_class"] != "resolved" or fit["source"]["commit"] != ORIGINAL:
                raise ValueError(f"archived fit identity differs: {path}")
            fits[path.parent.name] = fit
    rows = read(PANEL, PANEL_HASH)["datasets"]
    grids = {}
    for label, left, right in (
        ("dense_lean", "dense", "lean"),
        ("bank", "lean", "independent_bank"),
    ):
        sizes = []
        totals: Counter[str] = Counter()
        selected = [row for row in rows if label == "dense_lean" or row["independent_bank"]]
        for row in selected:
            f, g = (fits.get(f"fit-{row['dataset_id']}-{role}") for role in (left, right))
            if f is None or g is None:
                continue
            counts = {
                name: len(required_nodes(view_of(f, name)) | required_nodes(view_of(g, name)))
                for name in VIEWS
            }
            sizes.append(sum(counts.values()))
            totals.update(counts)
        grids[label] = {
            "resolved_pairs": len(sizes),
            "required_fresh_pairs": len(selected),
            "union_nodes_by_view": dict(totals),
            "union_nodes": sum(sizes),
            "minimum_per_pair": min(sizes),
            "maximum_per_pair": max(sizes),
            "extrapolated_union_nodes": sum(sizes) * len(selected) / len(sizes),
        }
    return grids


def replay_rate(root: Path) -> Json:
    runs = calls = 0
    elapsed = 0.0
    mix: Counter[str] = Counter()
    for path in sorted(root.glob("*/_task.json")):
        record = read(path)
        probe = result(path, record, ACCEPTED)
        anchors = probe["anchors"]
        if (
            record["status"] != "completed"
            or probe["checkpoint_hits"] != 0
            or probe["required_anchor_count"] != len(anchors)
            or probe["errors"]
        ):
            raise ValueError(f"incomplete or resumed reference probe: {path}")
        runs += 1
        calls += len(anchors)
        elapsed += record["wall_seconds"]
        mix.update(a["view"] for a in anchors)
    return {
        "replays": runs,
        "one_side_calls": calls,
        "calls_by_view": dict(mix),
        "worker_wall_seconds": elapsed,
        "worker_wall_seconds_per_call": elapsed / calls,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-results", type=Path, required=True)
    parser.add_argument("--accepted-probes", type=Path, required=True)
    args = parser.parse_args()
    grids, rate = original_grids(args.original_results), replay_rate(args.accepted_probes)
    if (grids["dense_lean"]["resolved_pairs"], grids["bank"]["resolved_pairs"]) != (168, 50):
        raise ValueError("incomplete original archive")
    if (rate["replays"], rate["one_side_calls"]) != (24, 12460):
        raise ValueError("incomplete accepted replay archive")
    calls = 2 * sum(part["extrapolated_union_nodes"] for part in grids.values())
    anchor_hours = calls * rate["worker_wall_seconds_per_call"] / 3600
    timed = read(Path(__file__).with_name("campaign-probe-timing.json"))
    views = timed["views"]
    if {view: v["count"] for view, v in views.items()} != rate["calls_by_view"]:
        raise ValueError("native timestamp census differs from the verified replay")
    accounted = timed["seconds_outside_checkpoint_intervals"] + sum(
        v["seconds"] for v in views.values()
    )
    if abs(accounted - rate["worker_wall_seconds"]) > 0.001:
        raise ValueError("checkpoint intervals do not reconcile to the archived worker times")
    stratified_hours = (
        2
        / 3600
        * sum(
            part["required_fresh_pairs"]
            / part["resolved_pairs"]
            * part["union_nodes_by_view"][view]
            * timing["seconds_per_location"]
            for part in grids.values()
            for view, timing in views.items()
        )
    )
    print(
        json.dumps(
            {
                "original_pairs": grids,
                "accepted_rate": rate,
                "extrapolated_one_side_calls": calls,
                "anchor_core_hours_sensitivity": anchor_hours,
                "anchor_core_hours_by_view_sensitivity": stratified_hours,
                "fits_and_anchors_core_hours_by_view_sensitivity": [
                    4700 + stratified_hours,
                    6000 + stratified_hours,
                ],
                "fits_and_anchors_core_hours_sensitivity": [
                    4700 + anchor_hours,
                    6000 + anchor_hours,
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
