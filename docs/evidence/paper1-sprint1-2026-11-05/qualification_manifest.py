"""Emit the frozen fresh-qualification panel (no outcomes exist when this runs).

Strata and gates are documented in docs/paper1-sprint1-packet-2026-11-05.md.
Biological-history addresses use namespace 5 (qualification); rule training
uses 4, so no qualification history is reused for training or validation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STATIONARY = (
    "constant",
    "matched_exposure",
    "b100_anchor",
    "increased_heterogeneity",
    "window_low",
    "window_high",
)
MU = (0.001, 0.004)
BASE_H = (1.0, 3.0, 10.0)
ARCHETYPES = ("connected", "corridor", "barrier")


def main() -> None:
    maps = json.loads((HERE / "maps/qualification-manifest.json").read_text())["maps"]
    maps = sorted(maps, key=lambda m: (m["archetype_index"], m["map_index"]))
    if len(maps) != 9 or not all(m["admissible"] for m in maps):
        raise ValueError("qualification maps must be the nine admissible prepared maps")
    rows = []

    def add(
        stratum: str,
        code: int,
        m_index: int,
        m: dict,
        background: str,
        mu: float,
        h: float,
        arms: tuple[str, ...],
        rep: int = 0,
    ) -> None:
        address = [5, m_index, MU.index(mu), int(h), code, rep]
        for arm in arms:
            rows.append(
                {
                    "dataset_id": f"q-{stratum}-{m['archetype']}-{m['map_index']}-"
                    f"{background}-mu{mu:g}-h{h:g}-{arm}",
                    "stratum": stratum,
                    "map": f"{m['archetype']}-{m['map_index']}",
                    "archetype": m["archetype"],
                    "background": background,
                    "mu": mu,
                    "h": h,
                    "arm": arm,
                    "address": address,
                }
            )

    for m_index, m in enumerate(maps):
        for mu_index, mu in enumerate(MU):
            for h_index, h in enumerate(BASE_H):
                background = STATIONARY[(m_index + 3 * mu_index + h_index) % 6]
                add("base", 0, m_index, m, background, mu, h, ("A", "B", "C"))
        add("boundary", 1, m_index, m, "b100_anchor", 0.004, 25.0, ("A", "C"))
        for background in ("increased_heterogeneity", "window_high"):
            add("enriched", 2, m_index, m, background, 0.001, 1.0, ("B",))
        add("trend", 3, m_index, m, "temporal_trend", 0.004, 3.0, ("A",))
    base_histories = sorted({tuple(r["address"]) for r in rows if r["stratum"] == "base"})
    rng = np.random.default_rng(np.random.SeedSequence(2026110502))
    bank_histories = {
        tuple(base_histories[i]) for i in rng.choice(len(base_histories), 18, replace=False)
    }
    integration = {}
    for m_index, m in enumerate(maps):
        candidates = [
            r["dataset_id"]
            for r in rows
            if r["stratum"] == "base" and r["map"] == f"{m['archetype']}-{m['map_index']}"
        ]
        integration[candidates[int(rng.integers(len(candidates)))]] = True
    for row in rows:
        row["independent_bank"] = (
            row["stratum"] == "base" and tuple(row["address"]) in bank_histories
        )
        row["integration_screen"] = bool(integration.get(row["dataset_id"], False))
    # Exhaustive latent audit (no LR limit) on two base datasets per map: measures
    # the production audit margin. Added 5 Nov 2026 after review, before any outcome.
    audit_rng = np.random.default_rng(np.random.SeedSequence([2026110501, 6]))
    exhaustive: set[str] = set()
    for map_name in sorted({r["map"] for r in rows if r["stratum"] == "base"}):
        candidates = sorted(
            r["dataset_id"] for r in rows if r["stratum"] == "base" and r["map"] == map_name
        )
        exhaustive.update(audit_rng.choice(candidates, size=2, replace=False).tolist())
    for row in rows:
        row["exhaustive_audit"] = row["dataset_id"] in exhaustive
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["stratum"]] = counts.get(row["stratum"], 0) + 1
    background_balance = {
        b: sum(
            1
            for a in base_histories
            if any(r["background"] == b for r in rows if tuple(r["address"]) == a)
        )
        for b in STATIONARY
    }
    panel = {
        "schema": "paper1-fresh-qualification-panel-v1",
        "address_namespace": 5,
        "map_manifest_sha256": hashlib.sha256(
            (HERE / "maps/qualification-manifest.json").read_bytes()
        ).hexdigest(),
        "counts": counts,
        "base_histories": len(base_histories),
        "base_background_balance": background_balance,
        "independent_bank_histories": len(bank_histories),
        "integration_screens": len(integration),
        "exhaustive_audits": len(exhaustive),
        "datasets": rows,
    }
    out = HERE / "qualification-panel.json"
    out.write_text(json.dumps(panel, indent=1) + "\n")
    print(json.dumps({k: v for k, v in panel.items() if k != "datasets"}, indent=1))


if __name__ == "__main__":
    main()
