"""Perfect direct-predator observations for the Goal 007 positive control."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal001.design import DesignSite
from latent_landscapes.goal001.observations import Observation
from latent_landscapes.goal004.observations import SURVEY_TIMES as SURVEY_TIMES

REPLICATES = (1, 2)
CATEGORY_COUNT = len(SURVEY_TIMES) + 1


class ArrivalTruthLike(Protocol):
    @property
    def arrival(self) -> NDArray[np.float64]: ...


@dataclass(frozen=True, slots=True)
class CollapsedObservation:
    """One distinct perfect-detection site-time outcome."""

    cluster_id: str
    split: str
    stratum_index: int
    site_id: str
    site_offset_index: int
    row: int
    col: int
    time: int
    detected: int


def generate_perfect_observations(
    sites: tuple[DesignSite, ...],
    truth: ArrivalTruthLike,
) -> tuple[Observation, ...]:
    """Retain the two frozen same-time visits as exact deterministic duplicates."""
    records: list[Observation] = []
    arrival = np.asarray(truth.arrival, dtype=np.float64)
    for site in sorted(sites, key=lambda value: (value.cluster_id, value.site_offset_index)):
        for time in SURVEY_TIMES:
            detected = int(arrival[site.row, site.col] <= time)
            for replicate in REPLICATES:
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


def collapse_duplicate_visits(
    records: Sequence[Observation],
) -> tuple[CollapsedObservation, ...]:
    """Verify exact duplicate agreement and retain one outcome per site and time."""
    if not records:
        raise ValueError("analyst-facing observations must not be empty")
    expected = {(time, replicate) for time in SURVEY_TIMES for replicate in REPLICATES}
    by_site: dict[str, dict[tuple[int, int], Observation]] = {}
    metadata: dict[str, tuple[str, str, int, int, int, int]] = {}
    for record in records:
        if record.detected not in (0, 1):
            raise ValueError("detected outcome must be binary")
        key = (record.time, record.replicate)
        if key not in expected:
            raise ValueError("record has an unknown survey time or replicate")
        site_history = by_site.setdefault(record.site_id, {})
        if key in site_history:
            raise ValueError("site history contains a duplicate analyst-facing record")
        site_history[key] = record
        values = (
            record.cluster_id,
            record.split,
            record.stratum_index,
            record.site_offset_index,
            record.row,
            record.col,
        )
        if record.site_id in metadata and metadata[record.site_id] != values:
            raise ValueError("site metadata are inconsistent across visits")
        metadata[record.site_id] = values
    if any(set(history) != expected for history in by_site.values()):
        raise ValueError("each observed site must have a complete 12-record history")

    order = sorted(
        by_site,
        key=lambda site_id: (
            str(metadata[site_id][0]),
            int(metadata[site_id][3]),
            site_id,
        ),
    )
    collapsed: list[CollapsedObservation] = []
    for site_id in order:
        history = by_site[site_id]
        for time in SURVEY_TIMES:
            visits = tuple(history[(time, replicate)] for replicate in REPLICATES)
            if len({visit.detected for visit in visits}) != 1:
                raise ValueError("same-time duplicate visits disagree under perfect detection")
            source = visits[0]
            collapsed.append(
                CollapsedObservation(
                    cluster_id=source.cluster_id,
                    split=source.split,
                    stratum_index=source.stratum_index,
                    site_id=source.site_id,
                    site_offset_index=source.site_offset_index,
                    row=source.row,
                    col=source.col,
                    time=source.time,
                    detected=source.detected,
                )
            )
    return tuple(collapsed)


def site_onset_categories(
    *,
    site_ids: tuple[str, ...],
    records: Sequence[CollapsedObservation],
    survey_times: tuple[int, ...] = SURVEY_TIMES,
) -> tuple[tuple[str, ...], NDArray[np.int64]]:
    """Reduce each complete monotone perfect history to one onset category."""
    if not survey_times or any(left >= right for left, right in pairwise(survey_times)):
        raise ValueError("survey times must be nonempty and strictly increasing")
    if len(survey_times) + 1 != CATEGORY_COUNT:
        raise ValueError("survey calendar must define exactly seven onset categories")
    if len(set(site_ids)) != len(site_ids):
        raise ValueError("site identifiers must be unique")
    if not records:
        raise ValueError("collapsed observations must not be empty")
    known = set(site_ids)
    observed = {record.site_id for record in records}
    if not observed <= known:
        raise ValueError("records contain an unknown site identifier")
    selected = tuple(site_id for site_id in site_ids if site_id in observed)
    histories: dict[str, dict[int, int]] = {site_id: {} for site_id in selected}
    for record in records:
        if record.detected not in (0, 1):
            raise ValueError("detected outcome must be binary")
        if record.time not in survey_times:
            raise ValueError("record has an unknown survey time")
        if record.time in histories[record.site_id]:
            raise ValueError("collapsed site history contains a duplicate time")
        histories[record.site_id][record.time] = record.detected
    if any(set(history) != set(survey_times) for history in histories.values()):
        raise ValueError("each observed site must have a complete six-time history")

    categories = np.empty(len(selected), dtype=np.int64)
    for site_index, site_id in enumerate(selected):
        outcomes = tuple(histories[site_id][time] for time in survey_times)
        if any(left > right for left, right in pairwise(outcomes)):
            raise ValueError("perfect-detection histories must be monotone")
        categories[site_index] = next(
            (index for index, detected in enumerate(outcomes) if detected),
            CATEGORY_COUNT - 1,
        )
    return selected, categories


generate_observations = generate_perfect_observations
