import numpy as np
import pandas as pd
import pytest

from qnn_snr.stats.interactions import compute_interaction_indices


def _pointwise(config_snr: dict[int, list[float]]) -> pd.DataFrame:
    rows = []
    for cid, vals in config_snr.items():
        for v in vals:
            rows.append({"configuration_id": cid, "SNR_est": v})
    return pd.DataFrame(rows)


def _exact(config_grad: dict[int, list[float]]) -> pd.DataFrame:
    rows = []
    for cid, vals in config_grad.items():
        for v in vals:
            rows.append({"configuration_id": cid, "exact_gradient": v})
    return pd.DataFrame(rows)


def test_multiplicative_independence_gives_index_one():
    # M_0=M_A=M_B=M_AB=2 -> I_AB = (2*2)/(2*2) = 1
    pw = _pointwise({1: [2, 2], 2: [2, 2], 3: [2, 2], 4: [2, 2], 5: [2, 2], 6: [2, 2], 7: [2, 2], 8: [2, 2]})
    ex = _exact({cid: [1.0, 1.0] for cid in range(1, 9)})
    out = compute_interaction_indices(pw, ex)
    row = out[out["pair"] == "E_L"].iloc[0]
    assert row["I_AB"] == pytest.approx(1.0)
    assert row["interpretation"] == "multiplicative independence"


def test_sub_additive_detected():
    # combined (config5) much smaller than product of singles
    vals = {1: [1.0], 2: [2.0], 3: [2.0], 4: [1.0], 5: [1.0], 6: [1.0], 7: [1.0], 8: [1.0]}
    pw = _pointwise(vals)
    ex = _exact({cid: [1.0] for cid in range(1, 9)})
    out = compute_interaction_indices(pw, ex)
    row = out[out["pair"] == "E_L"].iloc[0]
    # M_0=1, M_A(config2)=2, M_B(config3)=2, M_AB(config5)=1 -> I=(1*1)/(2*2)=0.25 < 1
    assert row["I_AB"] == pytest.approx(0.25)
    assert row["interpretation"] == "sub-additive fold change"


def test_zero_denominator_returns_undefined_not_epsilon():
    vals = {1: [1.0], 2: [0.0], 3: [2.0], 4: [1.0], 5: [1.0], 6: [1.0], 7: [1.0], 8: [1.0]}
    pw = _pointwise(vals)
    ex = _exact({cid: [1.0] for cid in range(1, 9)})
    out = compute_interaction_indices(pw, ex)
    row = out[out["pair"] == "E_L"].iloc[0]
    assert pd.isna(row["I_AB"])
    assert "zero-denominator" in row["I_AB_undefined_reason"]


def test_missing_configuration_gives_undefined():
    vals = {1: [1.0], 3: [2.0], 4: [1.0], 5: [1.0], 6: [1.0], 7: [1.0], 8: [1.0]}  # config 2 missing
    pw = _pointwise(vals)
    ex = _exact({cid: [1.0] for cid in vals})
    out = compute_interaction_indices(pw, ex)
    row = out[out["pair"] == "E_L"].iloc[0]
    assert pd.isna(row["I_AB"])


def test_all_three_pairs_present():
    vals = {cid: [1.5, 2.5] for cid in range(1, 9)}
    pw = _pointwise(vals)
    ex = _exact({cid: [1.0, 1.5] for cid in range(1, 9)})
    out = compute_interaction_indices(pw, ex)
    assert set(out["pair"]) == {"E_L", "E_R", "L_R"}
