"""Read archived, uninterrupted probe checkpoint timestamps on the development target."""

import argparse
import json
from collections import Counter
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("work", type=Path)
args = parser.parse_args()
counts, seconds = Counter(), Counter()
setup, teardown = [], []
for path in sorted((args.work / "probe-results").glob("*/_task.json")):
    record = json.loads(path.read_text())
    task = record["task"]
    folder = args.work / "probe-checkpoints" / task["original_task_id"]
    receipt = json.loads((path.parent / record["attempt"] / task["result_path"]).read_text())
    if receipt["checkpoint_hits"] or len(receipt["anchors"]) != receipt["required_anchor_count"]:
        raise ValueError("probe was interrupted or lacks a registered anchor")
    last = (folder / "identity.json").stat().st_mtime
    setup.append(last - record["started_unix"])
    for anchor in receipt["anchors"]:
        view = anchor["view"]
        current = (folder / (view + "--" + anchor["log_h_hex"] + ".json")).stat().st_mtime
        if current < last:
            raise ValueError("checkpoint timestamps disagree with evaluation order")
        counts[view] += 1
        seconds[view] += current - last
        last = current
    teardown.append(record["started_unix"] + record["wall_seconds"] - last)
if len(setup) != 24 or sum(counts.values()) != 12460 or min(setup + teardown) < 0:
    raise ValueError("probe census differs from the accepted development replay")
print(
    json.dumps(
        {
            "worker_count": len(setup),
            "checkpoint_count": sum(counts.values()),
            "seconds_outside_checkpoint_intervals": sum(setup + teardown),
            "views": {
                v: {"count": counts[v], "seconds": s, "seconds_per_location": s / counts[v]}
                for v, s in seconds.items()
            },
        },
        sort_keys=True,
        indent=2,
    )
)
