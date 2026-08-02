import numpy as np
import pandas as pd
import pytest

from qnn_snr.stats.factor_coding import add_centered_factors, transform_bootstrap_draws


def test_centered_factor_values_and_input_preservation():
    source = pd.DataFrame({"E": [0, 1], "L": [1, 0], "R": [0, 1]})
    out = add_centered_factors(source)
    assert out["E_c"].tolist() == [-0.5, 0.5]
    assert out["L_c"].tolist() == [0.5, -0.5]
    assert out["R_c"].tolist() == [-0.5, 0.5]
    assert "E_c" not in source


def test_centered_factor_rejects_nonbinary_input():
    with pytest.raises(ValueError, match="not binary"):
        add_centered_factors(pd.DataFrame({"E": [2], "L": [0], "R": [1]}))


def test_pairwise_draw_transform_and_simple_effect_average():
    draws = pd.DataFrame({"E:L": [2.0], "E:R": [3.0], "L:R": [4.0],
                          "E:L:R": [6.0], "L:R:depth_z": [7.0]})
    out = transform_bootstrap_draws(draws, "h2h4")
    assert out.loc[0, "E_c:L_c"] == 5.0
    assert out.loc[0, "E_c:R_c"] == 6.0
    assert out.loc[0, "L_c:R_c"] == 7.0
    assert out.loc[0, "L_c:R_c:depth_z"] == 7.0
    el_r0 = draws.loc[0, "E:L"]
    el_r1 = el_r0 + draws.loc[0, "E:L:R"]
    assert out.loc[0, "E_c:L_c"] == np.mean([el_r0, el_r1])


def test_draw_transform_requires_three_way_coefficient():
    with pytest.raises(ValueError, match="required coefficients"):
        transform_bootstrap_draws(pd.DataFrame({"E:L": [1], "E:R": [2]}), "h1")
