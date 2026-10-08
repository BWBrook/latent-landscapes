"""Reweight pseudo-arrival contributions in an accepted bridge integration."""

from __future__ import annotations

import math
from numbers import Integral, Real

import numpy as np

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes.arc2c_likelihood import BridgeIntegration
from latent_landscapes.goal004.observations import SURVEY_TIMES


def _positive_finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be finite and positive")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return numeric


def _bank_size(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError("bank_size must be a positive integer")
    return int(value)


def reweight_integration(
    integration: BridgeIntegration,
    bank_size: int,
    from_pseudocount: float = 0.5,
    to_pseudocount: float = 0.5,
    background_hazard: float = 0.002,
) -> BridgeIntegration:
    """Change only the category pseudo-count in a cached bridge integration.

    The empirical category counts and survival sums are recovered algebraically
    from the supplied integration, then combined with the new pseudo-arrival
    contribution.  This preserves the raw-bank checksum and avoids rerunning
    the accepted arrival integration kernel.
    """
    bank_size_value = _bank_size(bank_size)
    old_alpha = _positive_finite(from_pseudocount, "from_pseudocount")
    new_alpha = _positive_finite(to_pseudocount, "to_pseudocount")
    hazard = _positive_finite(background_hazard, "background_hazard")

    if old_alpha == new_alpha:
        return integration

    category_count = len(arc2b.PSEUDO_ARRIVALS)
    old_denominator = bank_size_value + category_count * old_alpha
    new_denominator = bank_size_value + category_count * new_alpha

    old_masses = np.asarray(integration.category_mass)
    category_mass = (
        old_masses * old_denominator + (new_alpha - old_alpha)
    ) / new_denominator

    effects = np.asarray(integration.effects, dtype=np.float64)
    times = np.asarray((0.0, *SURVEY_TIMES), dtype=np.float64)
    survival_moments: list[np.ndarray] = []
    for old_moment in integration.survival_moments:
        old_values = np.asarray(old_moment)
        transformed = np.empty_like(old_values)
        for category, pseudo in enumerate(arc2b.PSEUDO_ARRIVALS):
            pseudo_survival = np.exp(
                -hazard
                * (
                    times[None, :]
                    + (effects[:, None] - 1.0) * np.maximum(times[None, :] - pseudo, 0.0)
                )
            )
            empirical_sum = (
                old_values[:, :, :, category] * old_denominator
                - old_alpha * pseudo_survival[:, None, :]
            )
            transformed[:, :, :, category] = (
                empirical_sum + new_alpha * pseudo_survival[:, None, :]
            ) / new_denominator
        survival_moments.append(transformed)

    return BridgeIntegration(
        integration.rhos,
        integration.effects,
        integration.site_ids,
        category_mass,
        tuple(survival_moments),
        integration.bank_checksum,
    )
