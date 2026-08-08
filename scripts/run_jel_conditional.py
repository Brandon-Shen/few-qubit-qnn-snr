"""Run the frozen conditional-J point estimates and 2,000-draw bootstraps."""
from __future__ import annotations
import hashlib,json,platform
from pathlib import Path
import numpy as np,pandas as pd,scipy
from qnn_snr.stats.jel_conditional import bootstrap_draw,conditional_indices,configuration_rms,init_sufficient_statistics,validate_exact

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/jel_conditional';PLAN='645521db6511ca049d89e64f810e65a3407a7b52'
INPUTS={"original":ROOT/'results/production_confirmatory/raw/exact.parquet',"independent_seed":ROOT/'results/h2_replication_v1/_pipeline_output_stage1/raw/exact.parquet'};SEEDS={"original":255001,"independent_seed":255002}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,default=float)+'\n',encoding='utf-8')
def main():
 if OUT.exists():raise FileExistsError(OUT)
 OUT.mkdir(parents=True);all_summary=[];seed_sets={}
 for label,path in INPUTS.items():
  od=OUT/label;od.mkdir();d=pd.read_parquet(path);v=validate_exact(d,label);v['input_sha256']=sha(path);dump(od/'validation.json',v);seed_sets[label]=set(d.initialization_seed)
  g=configuration_rms(d);point=conditional_indices(g)
  if label=='original':
   independent=np.sqrt((d.exact_gradient**2).groupby(d.configuration_id).sum()/d.groupby('configuration_id').size()).to_dict();check=conditional_indices(independent)
   if abs(point['J_EL_given_R0']-1.2417603765323095)>1e-12 or abs(check['J_EL_given_R0']-point['J_EL_given_R0'])>1e-15:raise RuntimeError('historical J acceptance failed')
  sums,counts=init_sufficient_statistics(d);rows=[];fail=[]
  for i in range(2000):
   try:rows.append(bootstrap_draw(sums,counts,SEEDS[label],i))
   except Exception as e:fail.append({'iteration':i,'reason':repr(e)})
  draws=pd.DataFrame(rows);draws.to_parquet(od/'bootstrap_draws.parquet',index=False);pd.DataFrame(fail,columns=['iteration','reason']).to_csv(od/'failure_log.csv',index=False)
  endpoints=[]
  for n in [100,250,400,1000,2000]:
   for name in ['J_EL_given_R0','J_EL_given_R1']:
    lo,med,hi=np.percentile(draws.sort_values('iteration').iloc[:n][name],[2.5,50,97.5]);endpoints.append({'completed':n,'estimand':name,'median':med,'ci_lo':lo,'ci_hi':hi})
  pd.DataFrame(endpoints).to_csv(od/'bootstrap_endpoints.csv',index=False)
  for name,val in point.items():
   lo,med,hi=np.percentile(draws[name],[2.5,50,97.5]);all_summary.append({'dataset':label,'estimand':name,'estimate':val,'percent_above_one':100*(val-1),'bootstrap_median':med,'ci_lo':lo,'ci_hi':hi,'completed':len(draws),'failed':len(fail)})
  dump(od/'definition.json',{'G':{str(k):v for k,v in g.items()},'aggregation':'sqrt(mean(exact_gradient^2)) pooling rows before RMS','seed':SEEDS[label],'attempted':2000,'completed':len(draws),'failed':fail})
 if seed_sets['original']&seed_sets['independent_seed']:raise RuntimeError('seed overlap')
 summary=pd.DataFrame(all_summary);summary.to_csv(OUT/'summary.csv',index=False);dump(OUT/'summary.json',all_summary)
 dump(OUT/'manifest.json',{'plan_commit':PLAN,'analysis_commit':None,'inputs':{k:sha(v) for k,v in INPUTS.items()},'seeds':SEEDS,'commands':['python scripts/run_jel_conditional.py'],'environment':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__},'dataset_pooling':False})
 lines=['# Conditional J_EL bootstrap results','',f'**Status:** post-primary descriptive; plan `{PLAN}`. These ratios are not centered-H1 equivalents.','']
 for r in all_summary:lines.append(f"- {r['dataset']} {r['estimand']}: {r['estimate']:.6f} ({r['percent_above_one']:+.1f}% vs 1), bootstrap median {r['bootstrap_median']:.6f}, percentile 95% CI [{r['ci_lo']:.6f}, {r['ci_hi']:.6f}], {r['completed']} completed, {r['failed']} failed.")
 lines += ['','R0 uses configurations 5/1/(2/3); R1 uses 8/4/(6/7). RMS pools unique exact-gradient parameter rows before aggregation, so deeper depths receive greater parameter/observation weight. No optimization, trainability, or shot-saving claim follows.']
 (ROOT/'verification/jel_conditional_bootstrap_results.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');dump(ROOT/'verification/jel_conditional_bootstrap_results.json',{'status':'post_primary_descriptive','plan_commit':PLAN,'analysis_commit':None,'results':all_summary})
if __name__=='__main__':main()
