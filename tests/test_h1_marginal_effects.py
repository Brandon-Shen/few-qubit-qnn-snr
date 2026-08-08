import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def test_generated_h1_marginal_effects_reproduce_h1():
    p = json.loads((ROOT / "results/h1_marginal_effects/h1_marginal_effects.json").read_text())
    assert np.isclose(sum(p["depth_weights"].values()), 1.0)
    assert p["h1_reproduction"]["absolute_estimate_error"] < 1e-12
    assert p["h1_reproduction"]["absolute_se_error"] < 1e-12
    assert len(p["predictions"]) == 4
    assert len(p["contrasts"]) == 3
