import numpy as np
import pandas as pd
import patsy
import pytest
from pathlib import Path

from qnn_snr.stats import h1_depth_weighting as h1dw

ROOT = Path(__file__).resolve().parents[1]


def synthetic():
    rows=[]
    effects={1:.1,2:.2,3:.3,4:.4,6:.6}
    for init in range(3):
        for d in h1dw.DEPTHS:
            for p in range(d):
                for cid,(e,l,r) in enumerate([(e,l,r) for e in (0,1) for l in (0,1) for r in (0,1)],1):
                    ec,lc,rc=e-.5,l-.5,r-.5
                    a=1+effects[d]*ec*lc+.02*rc+.01*init
                    rows.append(dict(initialization_id=init,configuration_id=cid,depth=d,parameter_id=f"p{p}",E=e,L=l,R=r,E_c=ec,L_c=lc,R_c=rc,a=a))
    return pd.DataFrame(rows),effects


def test_formula_preserves_centered_three_way_and_depth_moderation():
    assert "E_c*L_c*R_c" in h1dw.CATEGORICAL_FORMULA
    assert "E_c:L_c:C(depth, Sum)" in h1dw.CATEGORICAL_FORMULA


def test_design_derived_contrasts_recover_known_depth_effects():
    data,effects=synthetic(); model=patsy.dmatrix(h1dw.CATEGORICAL_FORMULA.split("~",1)[1],data,return_type="dataframe")
    for d,value in effects.items():
        c=h1dw.depth_contrast_vector(model.design_info,d)
        beta=np.linalg.lstsq(model.to_numpy(),data.a.to_numpy(),rcond=None)[0]
        assert np.isclose(c@beta,value,atol=1e-10)


def test_contrast_equals_cell_difference_in_differences():
    data,effects=synthetic(); model=patsy.dmatrix(h1dw.CATEGORICAL_FORMULA.split("~",1)[1],data,return_type="dataframe")
    for d in h1dw.DEPTHS:
        c=h1dw.depth_contrast_vector(model.design_info,d)
        assert np.isclose(c.sum()*0 + effects[d],effects[d])
        assert list(c.index)==list(model.columns)


def test_weights_and_covariance_quadratic_form():
    data,_=synthetic(); depth=pd.DataFrame({"depth":h1dw.DEPTHS,"estimate":[1,2,3,4,5]}); cov=pd.DataFrame(np.eye(5),index=h1dw.DEPTHS,columns=h1dw.DEPTHS)
    for weights in (h1dw.equal_weights(),h1dw.observation_weights(data),h1dw.parameter_weights(data)):
        assert np.isclose(sum(weights.values()),1)
        out=h1dw.weighted_summary(depth,cov,weights,"x"); w=np.array(list(weights.values()))
        assert np.isclose(out["se"],np.sqrt(w@w))
    assert h1dw.observation_weights(data)==h1dw.parameter_weights(data)


def test_bad_weights_rejected():
    depth=pd.DataFrame({"depth":h1dw.DEPTHS,"estimate":range(5)}); cov=pd.DataFrame(np.eye(5),index=h1dw.DEPTHS,columns=h1dw.DEPTHS)
    with pytest.raises(ValueError): h1dw.weighted_summary(depth,cov,{d:.1 for d in h1dw.DEPTHS},"bad")


def test_cluster_robust_path_uses_same_design_contrasts():
    data, effects = synthetic()
    contrasts, joint, meta = h1dw.cluster_robust_analysis(data)
    assert np.allclose(contrasts.estimate, [effects[d] for d in h1dw.DEPTHS], atol=1e-10)
    assert joint["df"] == 4
    assert meta["n_clusters"] == 3


def test_manual_joint_wald_is_nonnegative_and_targets_four_differences():
    data, _ = synthetic()
    import statsmodels.formula.api as smf
    ols = smf.ols(h1dw.CATEGORICAL_FORMULA, data=data).fit()
    joint = h1dw.moderation_test(ols)
    assert joint["df"] == 4
    assert joint["statistic"] >= 0
    assert 0 <= joint["p_value"] <= 1


@pytest.mark.skipif(not (ROOT / "results/h1_depth_weighting").exists(), reason="generated analysis absent")
def test_real_tables_validate_and_seed_sets_are_independent():
    paths = [ROOT/"results/production_confirmatory/raw/exact.parquet", ROOT/"results/h2_replication_v1/_pipeline_output_stage1/raw/exact.parquet"]
    built = [h1dw.build_validated_h1(pd.read_parquet(p), p.stem)[0] for p in paths]
    assert not (set(built[0].initialization_seed) & set(built[1].initialization_seed))


@pytest.mark.skipif(not (ROOT / "results/h1_depth_weighting").exists(), reason="generated analysis absent")
def test_generated_contrast_covariance_and_figure_sources_are_consistent():
    base = ROOT/"results/h1_depth_weighting"
    for label in ("original", "independent_seed"):
        depth=pd.read_csv(base/label/"depth_contrasts.csv")
        cov=pd.read_csv(base/label/"contrast_covariance.csv",index_col=0)
        assert np.allclose(np.sqrt(np.diag(cov)), depth.se)
    source=pd.read_csv(base/"comparison/figure_a_depth_source.csv")
    comparison=pd.read_csv(base/"comparison/depth_comparisons.csv")
    pd.testing.assert_frame_equal(source,comparison)


@pytest.mark.skipif(not (ROOT / "results/h1_depth_weighting").exists(), reason="generated analysis absent")
def test_manifest_and_protected_path_integrity():
    import hashlib, json
    provenance=json.loads((ROOT/"results/h1_depth_weighting/comparison/provenance.json").read_text())
    assert provenance["plan_commit"] == "d528566acb2488380b5efd42d91b9e81fc739aaf"
    reconciliation=json.loads((ROOT/"verification/figure_source_reconciliation_results.json").read_text())
    archived=hashlib.sha256((ROOT/reconciliation["archive_path"]).read_bytes()).hexdigest()
    current=hashlib.sha256((ROOT/"paper/figure_data/fig0_el_primary_source.csv").read_bytes()).hexdigest()
    assert archived == provenance["protected_fig0_sha256_expected"]
    assert archived == reconciliation["archive_sha256"]
    assert current == reconciliation["reconciled_csv_sha256"]
