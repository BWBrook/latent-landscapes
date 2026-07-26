"""Frozen imperfect-detection observations for Goal 004."""

from __future__ import annotations

import numpy as np

from latent_landscapes.goal001.design import DesignSite
from latent_landscapes.goal001.observations import Observation
from latent_landscapes.goal003.spread import StochasticSpreadTruth

SURVEY_TIMES = (10, 20, 30, 40, 50, 60)
REPLICATES = (1, 2)
DETECTION_PROBABILITY = 0.65


def generate_observations(
    sites: tuple[DesignSite, ...],
    truth: StochasticSpreadTruth,
    detection_rng: np.random.Generator,
) -> tuple[Observation, ...]:
    """Generate the complete training and holdout history from one truth."""
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
