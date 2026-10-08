"""Cross-module controls for the screen's conditional-score boundary."""

from typing import Any, cast

import numpy as np

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes import misspecification_campaign as campaign
from latent_landscapes import misspecification_generator as generator
from latent_landscapes import misspecification_synthesis as synthesis
from latent_landscapes import model_adequacy_campaign as adequacy
from latent_landscapes.goal011 import benchmark as goal011


def test_real_history_score_uses_holdout_denominator_and_fixed_fitted_detection() -> None:
    fixed = goal011.build_fixed_inputs()
    setup = generator.build_generator_setup(fixed)
    seed = generator.spawn_generator_seeds(generator.SMOKE_ROOT, "smoke", 1)[0]
    cells = generator.generate_replicate(fixed, setup, seed)
    config = campaign.smoke_config(bank_size=16)
    bank, _ = campaign._load_bank(config, None, setup.site_ids)
    integration_config = adequacy.CampaignConfig(
        mode="smoke",
        effects=config.effects,
        evaluation_truths=config.truths,
        original_calibration_replicates=1,
        original_evaluation_replicates=1,
        fresh_calibration_replicates=1,
        fresh_evaluation_replicates=1,
        low_bank_size=8,
        high_bank_size=16,
    )
    integration = adequacy._build_primary_integration(bank, integration_config, setup.site_ids)
    scores = [adequacy._score_dataset(cell.dataset, integration) for cell in cells]
    holdout_denominators = []
    for cell, (prey, training_predator, mle, _profile, joint) in zip(cells, scores, strict=True):
        histories = cell.dataset.histories
        assert all(row.prey_detection_probability == 0.65 for row in histories)
        categories = arc2b._predator_category_probabilities(cast(Any, histories), 0.65)
        indices = np.asarray([integration.site_ids.index(row.site_id) for row in histories])
        probabilities = np.sum(integration.category_mass[0, indices] * categories, axis=1)
        training = np.asarray([row.split == "training" for row in histories], dtype=np.bool_)
        direct_training = np.log(probabilities[training]).sum()
        direct_holdout = np.log(probabilities[~training]).sum()
        np.testing.assert_allclose(training_predator, direct_training, rtol=0, atol=1e-10)
        np.testing.assert_allclose(prey, joint[mle] - direct_holdout, rtol=0, atol=1e-10)
        assert not np.isclose(training_predator, direct_holdout)
        holdout_denominators.append(direct_holdout)

    ordinary = [i for i, cell in enumerate(cells) if not cell.cell.cell_id.startswith("PD10")]
    np.testing.assert_allclose(
        np.asarray(holdout_denominators)[ordinary], holdout_denominators[0], rtol=0, atol=1e-10
    )
    effects = np.asarray(config.effects)
    evaluated = synthesis.evaluate_histories(
        effects,
        np.asarray([cell.cell.truth_h for cell in cells]),
        np.asarray([score[3] for score in scores])[:, None, :],
        np.asarray([score[0] for score in scores])[:, None],
        np.asarray([score[1] for score in scores])[:, None],
        np.asarray([score[2] for score in scores], dtype=np.int64)[:, None],
        np.asarray([score[4] for score in scores])[:, None, :],
        np.tile(np.linspace(-150, 0, 999), (len(effects), 1)),
        np.full(len(effects), 4.0),
        np.full(len(effects), 7.0),
    )
    primary = np.asarray(evaluated["primary_rejection"], dtype=np.bool_)
    plugin = np.asarray(evaluated["plugin_rejection"], dtype=np.bool_)
    misleading = np.asarray(evaluated["M"], dtype=np.bool_)
    assert not np.any(primary & ~plugin)
    assert np.array_equal(misleading & ~primary, evaluated["H_primary"])
