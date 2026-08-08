"""Deterministic implemented-protocol resource table construction."""
from __future__ import annotations
import numpy as np,pandas as pd
from qnn_snr.budget import enumerate_jobs,allocate_budget
from qnn_snr.config import CONFIGURATION_TABLE

def resource_rows(depths=(1,2,3,4,6),budgets=(250,500,1000,2000)):
 rows=[];details=[]
 for cid,(E,L,R) in CONFIGURATION_TABLE.items():
  cost='global' if L==0 else 'local'
  for d in depths:
   for B in budgets:
    for mode in ['finite_shot_conditional','finite_shot_end_to_end']:
     jobs=enumerate_jobs(d,4,cost,mode);alloc=allocate_budget(B,jobs);shots=np.array([alloc[j.job_id] for j in jobs],int)
     cats={c:sum(j.category==c for j in jobs) for c in ['forward_feature','node_jacobian','terminal_cost']}
     rows.append({'configuration_id':cid,'E':E,'L':L,'R':R,'depth':d,'budget':B,'analysis_mode':mode,'cost_type':cost,'total_requested_shots':B,'total_realized_shots':int(shots.sum()),'total_jobs':len(jobs),'shifted_jobs':sum(j.shift_sign!=0 for j in jobs),'forward_feature_jobs':cats['forward_feature'],'node_jacobian_jobs':cats['node_jacobian'],'objective_observable_jobs':cats['terminal_cost'],'objective_observable_settings':1 if cost=='global' else 2,'minimum_shots_per_job':int(shots.min()),'mean_shots_per_job':float(shots.mean()),'median_shots_per_job':float(np.median(shots)),'maximum_shots_per_job':int(shots.max()),'zero_shot_jobs':int((shots==0).sum()),'base_shots':B//len(jobs),'remainder_shots':B%len(jobs),'remainder_policy':'sorted(block,parameter,shift,basis)'})
     for j in jobs:details.append({'configuration_id':cid,'depth':d,'budget':B,'analysis_mode':mode,'job_id':j.job_id,'category':j.category,'basis':j.basis,'block_index':j.block_index,'parameter_index':j.parameter_index,'shift_sign':j.shift_sign,'shots':alloc[j.job_id]})
 return pd.DataFrame(rows),pd.DataFrame(details)

def validate_resource_table(table,production_summary):
 key=['analysis_mode','configuration_id','depth','budget'];errors=[]
 if len(table)!=320 or table.duplicated(key).any():errors.append('completeness')
 if not (table.total_requested_shots==table.total_realized_shots).all():errors.append('shot conservation')
 if (table.zero_shot_jobs!=0).any():errors.append('production zero-shot jobs')
 if (table.minimum_shots_per_job<0).any():errors.append('negative allocation')
 merged=table.merge(production_summary,on=key,validate='one_to_one')
 if not np.allclose(merged.total_realized_shots,merged.total_shots_mean):errors.append('raw summary disagreement')
 if errors:raise ValueError(errors)
 return {'rows':len(table),'duplicate_keys':0,'shot_conservation':True,'production_zero_shot_jobs':0,'raw_summary_max_abs_difference':float(np.max(np.abs(merged.total_realized_shots-merged.total_shots_mean))),'errors':[]}
