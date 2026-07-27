import numpy as np
import pytest

from qnn_snr.stats.holm import HYPOTHESES, build_confirmatory_table, holm_bonferroni, wald_test
from qnn_snr.stats.models import MixedModelResult


def _mock_result(params, bse):
    return MixedModelResult(
        formula="mock", converged=True, optimizer_used="lbfgs", attempted_optimizers=["lbfgs"],
        params=params, bse=bse, cov_params=None, random_effect_variances={}, n_obs=100,
        n_groups=10, n_vc_levels=50, condition_number=5.0, singular_fit=False,
        residual_diagnostics={}, raw_result=None, error=None,
    )


def test_holm_bonferroni_matches_known_reference():
    # classic textbook example: p = [0.01, 0.02, 0.03, 0.04], alpha=0.05
    p = [0.01, 0.02, 0.03, 0.04]
    adjusted, reject = holm_bonferroni(p, alpha=0.05)
    assert adjusted == pytest.approx([0.04, 0.06, 0.06, 0.06])
    assert reject == [True, False, False, False]


def test_holm_bonferroni_monotone_nondecreasing_in_sorted_order():
    p = [0.2, 0.001, 0.15, 0.04]
    adjusted, _ = holm_bonferroni(p, alpha=0.05)
    order = np.argsort(p)
    sorted_adj = [adjusted[i] for i in order]
    assert all(sorted_adj[i] <= sorted_adj[i + 1] for i in range(len(sorted_adj) - 1))


def test_holm_all_significant():
    p = [0.001, 0.002, 0.003, 0.004]
    adjusted, reject = holm_bonferroni(p, alpha=0.05)
    assert all(reject)


def test_holm_none_significant():
    p = [0.5, 0.6, 0.7, 0.8]
    adjusted, reject = holm_bonferroni(p, alpha=0.05)
    assert not any(reject)


def test_wald_test_two_sided():
    z, p = wald_test(1.0, 0.5)
    assert z == pytest.approx(2.0)
    assert p == pytest.approx(2 * (1 - 0.9772498680518208), abs=1e-8)


def test_wald_test_invalid_se_returns_nan():
    z, p = wald_test(1.0, 0.0)
    assert np.isnan(z) and np.isnan(p)


def test_confirmatory_table_has_one_row_per_hypothesis():
    h1 = _mock_result({"E:L": -0.5}, {"E:L": 0.1})
    h2h4 = _mock_result({"E:L": 0.3, "E:R": 0.0, "L:R:depth_z": 0.02},
                         {"E:L": 0.1, "E:R": 0.1, "L:R:depth_z": 0.05})
    table = build_confirmatory_table(h1, h2h4, alpha=0.05)
    assert list(table["hypothesis"]) == ["H1", "H2", "H3", "H4"]
    assert len(table) == 4


def test_confirmatory_table_applies_joint_holm_across_all_four():
    # H1 and H2 have tiny p-values, H3/H4 near-zero coefficients (large p)
    h1 = _mock_result({"E:L": -1.0}, {"E:L": 0.05})  # huge |z|, tiny p
    h2h4 = _mock_result({"E:L": 0.8, "E:R": 0.0001, "L:R:depth_z": 0.0001},
                         {"E:L": 0.05, "E:R": 1.0, "L:R:depth_z": 1.0})
    table = build_confirmatory_table(h1, h2h4, alpha=0.05)
    assert table.set_index("hypothesis").loc["H1", "reject_after_holm"] == True
    assert table.set_index("hypothesis").loc["H3", "reject_after_holm"] == False
    assert table.set_index("hypothesis").loc["H4", "reject_after_holm"] == False


def test_failure_to_reject_language_is_not_equivalence():
    h1 = _mock_result({"E:L": 0.01}, {"E:L": 5.0})
    h2h4 = _mock_result({"E:L": 0.01, "E:R": 0.01, "L:R:depth_z": 0.01},
                         {"E:L": 5.0, "E:R": 5.0, "L:R:depth_z": 5.0})
    table = build_confirmatory_table(h1, h2h4, alpha=0.05)
    for _, row in table.iterrows():
        assert row["reject_after_holm"] == False
        text = row["interpretation"].lower()
        assert "equivalence" not in text or "not evidence of" in text
        assert "proof" not in text
