from __future__ import annotations

from dataclasses import replace

from latent_landscapes.goal016.benchmark import (
    DEFAULT_CONFIG,
    _classify_outcome,
    run_goal016,
    smoke_config,
)


def test_reduced_information_funnel_reuses_whole_waves_across_every_rung() -> None:
    config = smoke_config()

    result = run_goal016(config)

    assert result.outcome == "reduced_smoke_complete"
    assert result.invariants
    assert all(result.invariants.values())
    assert {row.representation for row in result.funnel_performance} == {
        "global_time_only",
        "full_map_centered_log",
        "full_map_ranks",
        "sample_sites_centered_log",
        "sample_sites_perfect_occupancy",
        "sample_sites_imperfect_detection",
        "current_composite_statistic",
    }
    assert sum(
        row.representation == "sample_sites_imperfect_detection"
        for row in result.funnel_performance
    ) == len(config.rho_values)
    assert sum(
        row.representation == "current_composite_statistic" for row in result.funnel_performance
    ) == len(config.rho_values)
    assert len(result.final_wave_scores) == (2 * 2 * len(config.rho_values) * config.test_per_class)
    assert result.full_map_coefficient.shape == (result.positive_cell_count,)
    assert result.detection_coefficient.shape == (len(result.site_ids), 6)


def test_reduced_information_funnel_is_deterministic_from_its_frozen_root() -> None:
    config = replace(smoke_config(), train_per_class=6, validation_per_class=4)

    first = run_goal016(config)
    second = run_goal016(config)

    assert first.invariants == second.invariants
    assert first.funnel_performance == second.funnel_performance
    assert first.final_wave_scores == second.final_wave_scores
    assert first.partition_digest == second.partition_digest


def test_deepest_useful_rung_controls_the_information_loss_diagnosis() -> None:
    smoke = run_goal016(smoke_config())
    performance = tuple(
        replace(
            row,
            practically_useful=row.representation == "current_composite_statistic",
        )
        for row in smoke.funnel_performance
    )

    outcome = _classify_outcome(DEFAULT_CONFIG, performance, {"implementation": True})

    assert outcome == "information_retained_support_target_limited"
