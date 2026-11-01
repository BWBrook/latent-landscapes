from pathlib import Path
import argparse, hashlib, json

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write(path, value):
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(value, indent=2) + "\n")


parser = argparse.ArgumentParser()
parser.add_argument(
    "--phase",
    choices=["banks", "profiles", "profiles-archived", "screens", "comparisons"],
    required=True,
)
args = parser.parse_args()
plan = json.loads((BASE / "panel-manifest.json").read_text())
archived = json.loads((BASE / "archived-panel/manifest.json").read_text())
if archived["frozen_manifest_sha256"] != digest(BASE / "panel-manifest.json"):
    raise ValueError("archived panel/frozen manifest association differs")
if {r["dataset_id"] for r in archived["datasets"]} != {r["dataset_id"] for r in plan["datasets"]}:
    raise ValueError("archived panel case membership differs")
for name, expected in json.loads((BASE / "transfer-sha256.json").read_text()).items():
    if digest(ROOT / name) != expected:
        raise ValueError("transferred input identity drift: " + name)
original = Path(plan["original_source_root"])
rebase = lambda value: ROOT / Path(value).relative_to(original)
jobs = []
if args.phase == "banks":
    for index in range(3):
        for role in ("B0", "A"):
            public = BASE / "master-public" / f"map-{index:02d}"
            out = BASE / "master-banks" / f"map-{index:02d}" / role
            paths = [
                BASE / "panel-manifest.json",
                *(
                    public / name
                    for name in (
                        "public_inputs.json",
                        "public_inputs.npz",
                        "exposure.npz",
                        "design.json",
                    )
                ),
            ]
            jobs.append(
                {
                    "job_id": f"bank-map-{index:02d}-{role}",
                    "script": "scripts/prepare_development_banks.py",
                    "output_dir": str(out),
                    "arguments": [
                        "--public-dir",
                        str(public),
                        "--manifest",
                        str(BASE / "panel-manifest.json"),
                        "--source-root",
                        str(ROOT),
                        "--output-dir",
                        str(out),
                        "--role",
                        role,
                        "--bank-size",
                        "131072",
                        "--workers",
                        "8",
                    ],
                    "input_sha256": {str(p): digest(p) for p in paths},
                }
            )
elif args.phase in ("profiles", "profiles-archived"):
    records = []
    for record in archived["datasets"]:
        records.append(
            {
                **record,
                "input_dir": str(rebase(record["input_dir"])),
                "observations": str(rebase(record["observations"])),
                "report_h": plan["reporting"][record["biological_history_id"]]["h"],
                "banks": {
                    role: {k: str(rebase(plan["banks"][role][k])) for k in ("raw", "compressed")}
                    for role in record["bank_roles"]
                },
            }
        )
    for case in plan["optional_c_cases"] if args.phase == "profiles" else []:
        obs = BASE / case["dataset_id"] / "observations.npz"
        receipt = json.loads((BASE / case["dataset_id"] / "receipt.json").read_text())
        records.append(
            {
                **case,
                "biological_history_id": case["dataset_id"],
                "input_dir": str(BASE / "master-public" / f"map-{case['map_index']:02d}"),
                "observations": str(obs),
                "observations_sha256": receipt["observations_sha256"],
                "report_h": case["reporting"]["h"],
                "banks": {
                    role: {
                        "raw": str(
                            BASE
                            / "master-banks"
                            / f"map-{case['map_index']:02d}"
                            / role
                            / "arrivals.npy"
                        ),
                        "compressed": str(
                            BASE
                            / "master-banks"
                            / f"map-{case['map_index']:02d}"
                            / role
                            / "compressed.npz"
                        ),
                    }
                    for role in ("B0", "A")
                },
            }
        )
    for record in records:
        for role, bank in record["banks"].items():
            out = BASE / "profiles" / f"{record['dataset_id']}-{role}"
            public = Path(record["input_dir"])
            obs = Path(record["observations"])
            if digest(obs) != record["observations_sha256"]:
                raise ValueError("observation identity drift")
            bank_manifest_path = None
            if record["arm"] == "C":
                bank_manifest_path = Path(bank["raw"]).parent / "manifest.json"
                bank_manifest = json.loads(bank_manifest_path.read_text())
                if (
                    bank_manifest.get("state") != "complete"
                    or bank_manifest["role"] != role
                    or bank_manifest["bank_size"] != 131072
                    or bank_manifest["map_index"] != record["map_index"]
                ):
                    raise ValueError("C bank role/map/size/completion identity differs")
                required = [
                    BASE / "panel-manifest.json",
                    *(
                        public / n
                        for n in (
                            "public_inputs.json",
                            "public_inputs.npz",
                            "exposure.npz",
                            "design.json",
                        )
                    ),
                ]
                for path in required:
                    if bank_manifest["source_input_sha256"].get(str(path.resolve())) != digest(
                        path
                    ):
                        raise ValueError("C bank geometry/freeze association differs")
                for key in ("raw", "compressed"):
                    if digest(Path(bank[key])) != bank_manifest[key + "_sha256"]:
                        raise ValueError("C bank identity drift")
            paths = [
                obs,
                *(public / n for n in ("public_inputs.npz", "exposure.npz")),
                *(Path(bank[k]) for k in ("raw", "compressed")),
            ]
            if bank_manifest_path is not None:
                paths.append(bank_manifest_path)
            jobs.append(
                {
                    "job_id": f"{record['dataset_id']}-{role}",
                    "script": "scripts/run_development_profile.py",
                    "output_dir": str(out),
                    "profile_dir": str(out),
                    "dataset_id": record["dataset_id"],
                    "biological_history_id": record["biological_history_id"],
                    "arm": record["arm"],
                    "site_count": record["site_count"],
                    "observations_sha256": record["observations_sha256"],
                    "source_observations_sha256": record.get("source_observations_sha256"),
                    "bank_role": role,
                    "input_dir": str(public),
                    "observations": str(obs),
                    "arrival_bank": bank["raw"],
                    "compressed_bank": bank["compressed"],
                    "report_h": record["report_h"],
                    "integration_dir": str(BASE / "importance" / record["dataset_id"]),
                    "bank_comparison_dir": (
                        str(BASE / "bank-comparisons" / record["dataset_id"])
                        if "A" in record["banks"]
                        else None
                    ),
                    "arguments": [
                        "--input-dir",
                        str(public),
                        "--observations",
                        str(obs),
                        "--arrival-bank",
                        bank["raw"],
                        "--compressed-bank",
                        bank["compressed"],
                        "--output-dir",
                        str(out),
                        "--mode",
                        "paired" if role == "B0" else "dense",
                        "--report-h",
                        str(record["report_h"]),
                    ],
                    "input_sha256": {str(p): digest(p) for p in paths},
                }
            )
else:
    primary = json.loads((BASE / "jobs-profiles.json").read_text())["jobs"]
    lookup = {(j["dataset_id"], j["bank_role"]): j for j in primary}
    unavailable = []
    for job in primary:
        if job["bank_role"] != "B0":
            continue
        other = lookup.get((job["dataset_id"], "A"))
        if args.phase == "comparisons" and other is None:
            continue
        selected = Path(job["profile_dir"]) / "dense" / "receipt.json"
        parent = Path(job["profile_dir"]) / "receipt.json"
        if (
            not selected.exists()
            or not parent.exists()
            or json.loads(selected.read_text()).get("status") != "profile_numerically_resolved"
        ):
            unavailable.append(
                {"dataset_id": job["dataset_id"], "reason": "primary dense profile unavailable"}
            )
            continue
        if args.phase == "screens":
            out = Path(job["integration_dir"])
            commands = [
                "--input-dir",
                job["input_dir"],
                "--observations",
                job["observations"],
                "--arrival-bank",
                job["arrival_bank"],
                "--compressed-bank",
                job["compressed_bank"],
                "--profile",
                str(selected),
                "--output-dir",
                str(out),
                "--identity",
                job["dataset_id"],
                "--report-h",
                str(job["report_h"]),
            ]
            jobs.append(
                {
                    **job,
                    "job_id": job["dataset_id"],
                    "script": "scripts/screen_spatial_importance.py",
                    "output_dir": str(out),
                    "arguments": commands,
                }
            )
        else:
            secondary = Path(other["profile_dir"]) / "dense" / "receipt.json"
            if (
                not secondary.exists()
                or not (Path(other["profile_dir"]) / "receipt.json").exists()
                or json.loads(secondary.read_text()).get("status") != "profile_numerically_resolved"
            ):
                unavailable.append(
                    {
                        "dataset_id": job["dataset_id"],
                        "reason": "independent A dense profile unavailable",
                    }
                )
                continue
            out = Path(job["bank_comparison_dir"])
            commands = [
                "--b0-run-dir",
                job["profile_dir"],
                "--a-run-dir",
                other["profile_dir"],
                "--mode",
                "dense",
                "--input-dir",
                job["input_dir"],
                "--observations",
                job["observations"],
                "--b0-arrival-bank",
                job["arrival_bank"],
                "--b0-compressed-bank",
                job["compressed_bank"],
                "--a-arrival-bank",
                other["arrival_bank"],
                "--a-compressed-bank",
                other["compressed_bank"],
                "--report-h",
                str(job["report_h"]),
                "--output-dir",
                str(out),
            ]
            jobs.append(
                {
                    **job,
                    "job_id": job["dataset_id"],
                    "script": "scripts/compare_development_banks.py",
                    "output_dir": str(out),
                    "arguments": commands,
                }
            )
    write(BASE / f"unavailable-{args.phase}.json", unavailable)
write(
    BASE / f"jobs-{args.phase}.json",
    {
        "phase": args.phase,
        "frozen_panel_sha256": digest(BASE / "panel-manifest.json"),
        "prepared_inputs": {
            "archived": {
                "path": str(BASE / "archived-panel/manifest.json"),
                "sha256": digest(BASE / "archived-panel/manifest.json"),
            },
            "C": {
                case["dataset_id"]: {
                    "path": str(BASE / case["dataset_id"] / "receipt.json"),
                    "sha256": digest(BASE / case["dataset_id"] / "receipt.json"),
                }
                for case in plan["optional_c_cases"]
            },
        },
        "jobs": jobs,
    },
)
print(json.dumps({"phase": args.phase, "jobs": len(jobs)}))
