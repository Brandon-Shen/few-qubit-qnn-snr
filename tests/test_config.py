import numpy as np

from qnn_snr.config import (
    BASELINE_SCHEDULE,
    CONFIGURATION_TABLE,
    RESTRICTED_EVEN_SCHEDULE,
    RESTRICTED_ODD_SCHEDULE,
    ExperimentConfig,
    config_hash,
    entangling_pairs,
    load_config,
)


def test_configuration_table_matches_spec():
    expected = {
        1: (0, 0, 0), 2: (1, 0, 0), 3: (0, 1, 0), 4: (0, 0, 1),
        5: (1, 1, 0), 6: (1, 0, 1), 7: (0, 1, 1), 8: (1, 1, 1),
    }
    assert CONFIGURATION_TABLE == expected


def test_all_eight_configurations_present():
    assert set(CONFIGURATION_TABLE.keys()) == set(range(1, 9))


def test_entangling_schedules_have_four_cnots():
    for E in (0, 1):
        for layer_idx in range(6):
            pairs = entangling_pairs(layer_idx, E)
            assert len(pairs) == 4


def test_baseline_schedule_every_layer():
    for layer_idx in range(6):
        assert entangling_pairs(layer_idx, 0) == BASELINE_SCHEDULE


def test_restricted_schedule_alternates_odd_even():
    assert entangling_pairs(0, 1) == RESTRICTED_ODD_SCHEDULE  # layer 1 (1-indexed)
    assert entangling_pairs(1, 1) == RESTRICTED_EVEN_SCHEDULE  # layer 2
    assert entangling_pairs(2, 1) == RESTRICTED_ODD_SCHEDULE  # layer 3


def test_default_config_hash_deterministic():
    cfg1 = ExperimentConfig()
    cfg2 = ExperimentConfig()
    assert config_hash(cfg1) == config_hash(cfg2)


def test_config_hash_changes_with_content():
    cfg1 = ExperimentConfig()
    cfg2 = ExperimentConfig()
    cfg2.task.h = 0.7
    assert config_hash(cfg1) != config_hash(cfg2)


def test_gamma_and_cost_mapping_defaults():
    cfg = ExperimentConfig()
    assert cfg.gamma_for(0) == 0.0
    assert cfg.gamma_for(1) == 1.0
    assert cfg.cost_type_for(0) == "global"
    assert cfg.cost_type_for(1) == "local"


def test_load_config_smoke_yaml(tmp_path):
    import qnn_snr
    from pathlib import Path
    config_dir = Path(qnn_snr.__file__).resolve().parent.parent / "configs"
    cfg = load_config(config_dir / "smoke.yaml")
    assert isinstance(cfg, ExperimentConfig)
    assert cfg.design.n_initializations >= 1
