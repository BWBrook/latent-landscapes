from __future__ import annotations

import hashlib
import math

import numpy as np
import pytest

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes.arc2c_likelihood import BridgeIntegration, build_joint_integration
from latent_landscapes.goal004.observations import SURVEY_TIMES
from latent_landscapes.integration_weights import reweight_integration


@pytest.fixture
def integration() -> tuple[BridgeIntegration, np.ndarray]:
    bank = np.asarray(
        [
            [5.0, 15.0],
            [15.0, 25.0],
            [25.0, 35.0],
            [35.0, 45.0],
            [45.0, 55.0],
            [55.0, 65.0],
            [70.0, 80.0],
        ]
    )
    return (
        build_joint_integration(bank, ("left", "right"), (1.0, 2.0), (1.0, 3.0)),
        bank,
    )


@pytest.mark.parametrize(("new_alpha", "hazard"), [(0.25, 0.002), (1.0, 0.004)])
def test_reweight_matches_independent_empirical_plus_pseudo_formula(
    integration: tuple[BridgeIntegration, np.ndarray], new_alpha: float, hazard: float
) -> None:
    _, bank = integration
    original = build_joint_integration(
        bank, ("left", "right"), (1.0, 2.0), (1.0, 3.0), background_hazard=hazard
    )
    transformed = reweight_integration(
        original, bank.shape[0], from_pseudocount=0.5, to_pseudocount=new_alpha,
        background_hazard=hazard
    )

    categories = len(arc2b.PSEUDO_ARRIVALS)
    denominator = bank.shape[0] + categories * new_alpha
    times = np.asarray((0.0, *SURVEY_TIMES), dtype=np.float64)
    expected_mass = np.empty_like(original.category_mass)
    expected_moments = tuple(np.empty_like(moment) for moment in original.survival_moments)
    survey_times = np.asarray(SURVEY_TIMES)
    for rho_index, rho in enumerate(original.rhos):
        scaled_bank = bank / rho
        arrival_categories = np.searchsorted(survey_times, scaled_bank, side="left")
        current = expected_moments[rho_index]
        for site_index in range(bank.shape[1]):
            for category, pseudo in enumerate(arc2b.PSEUDO_ARRIVALS):
                arrivals = scaled_bank[arrival_categories[:, site_index] == category, site_index]
                expected_mass[rho_index, site_index, category] = (
                    arrivals.size + new_alpha
                ) / denominator
                for effect_index, effect in enumerate(original.effects):
                    empirical_survival = (
                        np.exp(
                            -hazard
                            * (
                                times[None, :]
                                + (effect - 1.0)
                                * np.maximum(times[None, :] - arrivals[:, None], 0.0)
                            )
                        ).sum(axis=0)
                        if arrivals.size
                        else np.zeros(times.size)
                    )
                    pseudo_survival = np.exp(
                        -hazard * (times + (effect - 1.0) * np.maximum(times - pseudo, 0.0))
                    )
                    current[effect_index, site_index, :, category] = (
                        empirical_survival + new_alpha * pseudo_survival
                    ) / denominator

    np.testing.assert_allclose(transformed.category_mass, expected_mass, rtol=0, atol=1e-14)
    for observed, expected in zip(
        transformed.survival_moments, expected_moments, strict=True
    ):
        np.testing.assert_allclose(observed, expected, rtol=0, atol=1e-14)
    np.testing.assert_allclose(transformed.category_mass.sum(axis=2), 1.0, rtol=0, atol=1e-14)
    assert transformed.bank_checksum == hashlib.sha256(bank.tobytes(order="C")).hexdigest()


def test_identity_returns_original_after_validation(
    integration: tuple[BridgeIntegration, np.ndarray],
) -> None:
    original, bank = integration
    assert reweight_integration(original, bank.shape[0]) is original
    assert reweight_integration(original, bank.shape[0], 0.5, 0.5, 0.004) is original


def test_round_trip_recovers_original_arrays(
    integration: tuple[BridgeIntegration, np.ndarray],
) -> None:
    original, bank = integration
    transformed = reweight_integration(original, bank.shape[0], to_pseudocount=0.25)
    round_trip = reweight_integration(
        transformed, bank.shape[0], from_pseudocount=0.25, to_pseudocount=0.5
    )
    np.testing.assert_allclose(round_trip.category_mass, original.category_mass, rtol=0, atol=2e-15)
    for observed, expected in zip(
        round_trip.survival_moments, original.survival_moments, strict=True
    ):
        np.testing.assert_allclose(observed, expected, rtol=0, atol=2e-15)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"bank_size": 0}, "bank_size"),
        ({"bank_size": 2.0}, "bank_size"),
        ({"bank_size": True}, "bank_size"),
        ({"from_pseudocount": 0.0}, "from_pseudocount"),
        ({"to_pseudocount": math.inf}, "to_pseudocount"),
        ({"to_pseudocount": -0.1}, "to_pseudocount"),
        ({"background_hazard": 0.0}, "background_hazard"),
        ({"background_hazard": math.nan}, "background_hazard"),
    ],
)
def test_invalid_parameters_fail(
    integration: tuple[BridgeIntegration, np.ndarray], kwargs: dict[str, object], message: str
) -> None:
    original, bank = integration
    kwargs.setdefault("bank_size", bank.shape[0])
    with pytest.raises(ValueError, match=message):
        reweight_integration(original, **kwargs)


def test_reweight_does_not_mutate_input_arrays(
    integration: tuple[BridgeIntegration, np.ndarray],
) -> None:
    original, bank = integration
    original_mass = original.category_mass.copy()
    original_moments = tuple(moment.copy() for moment in original.survival_moments)
    reweight_integration(original, bank.shape[0], to_pseudocount=1.0)
    np.testing.assert_array_equal(original.category_mass, original_mass)
    for observed, expected in zip(original.survival_moments, original_moments, strict=True):
        np.testing.assert_array_equal(observed, expected)
