#!/usr/bin/env python3
"""Export Goal 062 additions around the byte-identical Goal 061 science."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from supervise_final_procedure_evaluation import load_carry_forward

REPOSITORY = Path(__file__).resolve().parents[1]
BASELINE = REPOSITORY / "artifacts/goal061_execution/qualification-repair3"
BASELINE_SHA = "5879fbdaf7b3880151358319a7b7c7c0837463b06ba06f1a34fb80a3fbc2e36a"
QUALIFIED = "/data/codex/scratch/goal060-capstone-recovery-20261004-audit-repair"
PRIOR = "/data/codex/scratch/goal061-capstone-training-20261005-qualification-repair3"
ADDITIONS = (
    "src/latent_landscapes/final_procedure_evaluation.py",
    "scripts/run_final_procedure_evaluation.py",
    "scripts/qualify_final_procedure_evaluation.py",
    "scripts/audit_final_procedure_evaluation.py",
    "scripts/supervise_final_procedure_evaluation.py",
    "scripts/freeze_final_procedure_evaluation.py",
    "scripts/summarize_final_procedure_evaluation.py",
    "tests/test_final_procedure_evaluation.py",
    "tests/test_final_procedure_evaluation_audit.py",
    "tests/test_final_procedure_evaluation_runner.py",
    "tests/test_final_procedure_evaluation_qualification.py",
    "tests/test_final_procedure_evaluation_synthesis.py",
    "docs/goals/062-final-procedure-evaluation/registration-2026-10-11.md",
    "docs/goals/062-final-procedure-evaluation/design-review-2026-10-11.md",
    "docs/goals/062-final-procedure-evaluation/compute-estimate.md",
    "docs/goals/062-final-procedure-evaluation/amendment-2026-10-11.md",
    "docs/goals/062-final-procedure-evaluation/amendment-review-2026-10-11.md",
    "docs/goals/062-final-procedure-evaluation/compute-estimate-amended-2026-10-11.md",
    "docs/decisions/1c886620-8524-4d69-8585-3b5ef960bea3.json",
    "docs/decisions/1c886620-8524-4d69-8585-3b5ef960bea3.md",
)


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_new(path: Path, data: object) -> None:
    with path.open("x") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def freeze(
    output: Path, remote_root: Path, carry_forward: Path | None = None
) -> dict[str, Any]:
    baseline_manifest = BASELINE / "source-manifest.json"
    if digest(baseline_manifest) != BASELINE_SHA:
        raise ValueError("original Goal 061 source manifest changed")
    baseline = json.loads(baseline_manifest.read_text())
    baseline_files = baseline["source_hashes"]
    for name, expected in baseline_files.items():
        if (
            name.startswith(("src/", "scripts/", "tests/")) or name in {"pyproject.toml", "uv.lock"}
        ) and digest(REPOSITORY / name) != expected:
            raise ValueError("inherited scientific source changed: " + name)
    if set(ADDITIONS) & set(baseline_files):
        raise ValueError("an addition would overwrite inherited source")
    for name in ADDITIONS:
        if not (REPOSITORY / name).is_file():
            raise FileNotFoundError(name)
    carry_path = carry_forward.resolve() if carry_forward is not None else None
    predecessor_path = (
        carry_path.with_name("predecessor-source-manifest.json")
        if carry_path is not None
        else None
    )
    output.mkdir(parents=True, exist_ok=False)
    with tarfile.open(BASELINE / "source.tar.gz") as archive:
        archive.extractall(output, filter="data")
    source = output / "source"
    for name, expected in baseline_files.items():
        if digest(source / name) != expected:
            raise ValueError("inherited archive payload changed: " + name)
    for name in ADDITIONS:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPOSITORY / name, target)
    shutil.copy2(BASELINE / "runtime.json", output / "original-runtime.json")
    shutil.copy2(baseline_manifest, output / "original-source-manifest.json")
    shutil.copy2(
        BASELINE / "analysis/computation-complete.json", output / "original-completion.json"
    )
    if carry_path is not None and predecessor_path is not None:
        shutil.copy2(carry_path, output / "carry-forward.json")
        shutil.copy2(predecessor_path, output / "predecessor-source-manifest.json")
    input_names = [
        "original-runtime.json",
        "original-source-manifest.json",
        "original-completion.json",
    ]
    if carry_path is not None:
        input_names.extend(("carry-forward.json", "predecessor-source-manifest.json"))
    new_files = sorted(set(baseline_files) | set(ADDITIONS))
    source_hashes = {name: digest(source / name) for name in new_files}
    input_hashes = {name: digest(output / name) for name in input_names}
    preliminary_manifest = {
        "remote_root": str(remote_root),
        "source_hashes": source_hashes,
        "input_hashes": input_hashes,
    }
    if carry_path is not None:
        load_carry_forward(output, preliminary_manifest)
    manifest = {
        "schema": "goal062-source-freeze-v1",
        "created_utc": datetime.now(UTC).isoformat(),
        "repository_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPOSITORY, text=True
        ).strip(),
        "remote_root": str(remote_root),
        "qualified_package": QUALIFIED,
        "prior_reference_root": PRIOR,
        "original_binding": BASELINE_SHA,
        "original_scientific_files_verified": sum(
            name.startswith(("src/", "scripts/", "tests/")) for name in baseline_files
        ),
        "scientific_source_changes": [],
        "source_hashes": source_hashes,
        "input_hashes": input_hashes,
        "maximum_workers": 51,
        "rss_cap_bytes": 64 * 1024**3,
        "minimum_scratch_bytes": 50 * 1024**3,
        "production_wall_seconds": 72 * 3600,
        "qualification_wall_seconds": 3 * 3600,
        "production_runtime_review_required_if_changed": True,
    }
    write_new(output / "source-manifest.json", manifest)
    with tarfile.open(output / "source.tar.gz", "x:gz") as archive:
        for name in new_files:
            archive.add(source / name, arcname=str(Path("source") / name), recursive=False)
    receipt = {
        "source_manifest_sha256": digest(output / "source-manifest.json"),
        "source_archive_sha256": digest(output / "source.tar.gz"),
        "source_archive_bytes": (output / "source.tar.gz").stat().st_size,
        "source_files": len(new_files),
        "scientific_source_changes": [],
        "original_scientific_files_verified": manifest["original_scientific_files_verified"],
    }
    write_new(output / "source-archive.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--remote-root", type=Path, required=True)
    parser.add_argument("--carry-forward", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            freeze(args.output.resolve(), args.remote_root, args.carry_forward), sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
