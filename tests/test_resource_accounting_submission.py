import numpy as np
from qnn_snr.resource_audit import resource_rows
def test_resource_completeness_conservation_and_remainder():
 t,j=resource_rows();assert len(t)==320;assert not t.duplicated(['configuration_id','depth','budget','analysis_mode']).any();assert (t.total_realized_shots==t.budget).all();assert (t.zero_shot_jobs==0).all();assert (j.shots>=0).all()
def test_resource_determinism_and_d6_ratio():
 a,_=resource_rows();b,_=resource_rows();assert a.equals(b);d=a.query('depth==6');lo=d.query("analysis_mode=='finite_shot_conditional' and L==0").total_jobs.unique().item();hi=d.query("analysis_mode=='finite_shot_end_to_end' and L==1").total_jobs.unique().item();assert (lo,hi)==(48,61);assert np.isclose((hi-lo)/lo,13/48)
def test_conditional_end_to_end_separated():
 t,_=resource_rows();assert set(t.analysis_mode)=={'finite_shot_conditional','finite_shot_end_to_end'};assert (t.query("analysis_mode=='finite_shot_conditional'").forward_feature_jobs==0).all()
