from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path.cwd()
ARCHIVE = ROOT / "docs/evidence/paper1-direct-profile-2026-10-31"
CACHE = {}


def sha(path):
    resolved = path.resolve()
    if resolved not in CACHE:
        value = hashlib.sha256()
        with resolved.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                value.update(block)
        CACHE[resolved] = value.hexdigest()
    return CACHE[resolved]


def bindings(value):
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
            yield value["path"], value["sha256"]
        for key, child in value.items():
            if key in ("source_sha256", "input_sha256") and isinstance(child, dict):
                for path, digest in child.items():
                    if isinstance(digest, str) and len(digest) == 64:
                        yield path, digest
            else:
                yield from bindings(child)
    elif isinstance(value, list):
        for child in value:
            yield from bindings(child)


def main():
    snapshots = {sha(path): path for path in ARCHIVE.rglob("*.py")}
    entries = []
    profiles = []
    for receipt in sorted(ARCHIVE.rglob("*.json")):
        if receipt.name == "verification.json":
            continue
        data = json.loads(receipt.read_text())
        for named_path, expected in bindings(data):
            path = Path(named_path)
            if not path.is_absolute():
                path = ROOT / path
            current_match = path.is_file() and sha(path) == expected
            snapshot = None if current_match else snapshots.get(expected)
            entries.append(
                {
                    "receipt": str(receipt.relative_to(ARCHIVE)),
                    "bound_path": named_path,
                    "expected_sha256": expected,
                    "verified": bool(current_match or snapshot is not None),
                    "historical_source_snapshot": None
                    if snapshot is None
                    else str(snapshot.relative_to(ARCHIVE)),
                }
            )
        if data.get("schema") == "spatial-profile-benchmark-v2":
            profile = data["profile"]
            inputs = data["inputs"]
            profiles.append(
                {
                    "receipt": str(receipt.relative_to(ARCHIVE)),
                    "scope_valid": bool(
                        inputs["criterion_site_count"] == 120
                        and inputs["training_site_count"] == 120
                        and inputs["holdout_site_count"] == 40
                        and inputs["bank_size"] == 131072
                    and inputs["bank_has_raw_arrivals"]
                    and not data["truth_accessed"]
                        and not data["profile_certified"]
                        and data["runtime"]["single_thread_timing_contract"]
                    ),
                    "families_resolved": bool(profile["endpoint_families_resolved"]),
                    "envelope_passed": bool(profile["envelope_check_passed"]),
                    "grid_resolution": profile["family_resolution"],
                    "source_sha256": data["source_identity"]["spatial_profile_module"]["sha256"],
                }
            )
    payload = {
        str(path.relative_to(ARCHIVE)): sha(path)
        for path in sorted(ARCHIVE.rglob("*"))
        if path.is_file() and path.name != "verification.json"
    }
    result = {
        "schema": "paper1-direct-profile-evidence-verification-v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "bindings": entries,
        "profile_checks": profiles,
        "all_bindings_verified": all(row["verified"] for row in entries),
        "all_profile_scopes_valid": all(row["scope_valid"] for row in profiles),
        "payload_sha256": payload,
    }
    (ARCHIVE / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "bindings": len(entries),
                "profiles": len(profiles),
                "all_bindings_verified": result["all_bindings_verified"],
                "all_profile_scopes_valid": result["all_profile_scopes_valid"],
            }
        )
    )
    for row in entries:
        if not row["verified"]:
            print("UNVERIFIED", row["receipt"], row["bound_path"])


if __name__ == "__main__":
    main()
