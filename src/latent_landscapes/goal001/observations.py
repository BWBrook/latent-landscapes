"""Imperfect-detection observations for the single Goal 001 realization."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .design import DesignSite
from .spread import SpreadTruth

SURVEY_TIMES = (10, 30, 50, 70, 90, 110)
REPLICATES = (1, 2)
DETECTION_PROBABILITY = 0.65


@dataclass(frozen=True, slots=True)
class Observation:
    cluster_id: str
    split: str
    stratum_index: int
    site_id: str
    site_offset_index: int
    row: int
    col: int
    time: int
    replicate: int
    detected: int

    def to_csv_row(self) -> dict[str, str | int]:
        return {
            "cluster_id": self.cluster_id,
            "split": self.split,
            "stratum_index": self.stratum_index,
            "site_id": self.site_id,
            "site_offset_index": self.site_offset_index,
            "row": self.row,
            "col": self.col,
            "time": self.time,
            "replicate": self.replicate,
            "detected": self.detected,
        }


def generate_observations(
    sites: tuple[DesignSite, ...],
    truth: SpreadTruth,
    detection_rng: np.random.Generator,
) -> tuple[Observation, ...]:
    records: list[Observation] = []
    for site in sorted(sites, key=lambda value: (value.cluster_id, value.site_offset_index)):
        for time in SURVEY_TIMES:
            occupied = bool(truth.arrival[site.row, site.col] <= time)
            for replicate in REPLICATES:
                detected = int(occupied and detection_rng.random() < DETECTION_PROBABILITY)
                records.append(
                    Observation(
                        cluster_id=site.cluster_id,
                        split=site.split,
                        stratum_index=site.stratum_index,
                        site_id=site.site_id,
                        site_offset_index=site.site_offset_index,
                        row=site.row,
                        col=site.col,
                        time=time,
                        replicate=replicate,
                        detected=detected,
                    )
                )
    return tuple(records)
