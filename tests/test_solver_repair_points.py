import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_solver_repair_points import frozen_fixtures, load_criterion


def test_replaced_original_task_fails_before_opening_model_inputs(tmp_path):
    path = tmp_path / "work/qualification-results/task-id/_task.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"task": "replaced"}')
    with pytest.raises(ValueError, match="digest differs from frozen selection"):
        load_criterion(tmp_path, "task-id", "0" * 64)


def test_external_fixture_cannot_supply_unfrozen_point_coordinates(tmp_path):
    root = tmp_path / "candidate"
    root.mkdir()
    fixture = tmp_path / "unfrozen.json"
    fixture.write_text("{}")
    with pytest.raises(ValueError, match="outside candidate checkout"):
        frozen_fixtures(root, [fixture])
