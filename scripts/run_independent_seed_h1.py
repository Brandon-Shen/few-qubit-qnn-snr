"""Validate, fit, and bootstrap corrected independent-seed H1."""
from __future__ import annotations
import json,time,warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np,pandas as pd
from scipy import stats
from qnn_snr.stats.bootstrap import _relabel_outer_resample
from qnn_snr.stats.factor_coding import H1_CENTERED_FORMULA,add_centered_factors,transform_bootstrap_draws
from qnn_snr.stats.models import H1_FORMULA,build_h1_dataset,fit_mixed_model
ROOT=Path(__file__).resolve().parents[1]; INP=ROOT/'results/h2_replication_v1/_pipeline_output_stage1/raw/exact.parquet'; OUT=ROOT/'results/independent_seed_h1/effect_coded'; SEED=155001; PLAN='7cdb9a2b9a820799fe1b05491f9498b838f5a15c'; _D=None
def init_worker():
 global _D;_D=pd.read_parquet(INP)
def one(it):
 try:
  s=_relabel_outer_resample(_D,np.random.default_rng((SEED,it)))
  with warnings.catch_warnings(record=True) as w:warnings.simplefilter('always');r=fit_mixed_model(H1_FORMULA,build_h1_dataset(s),'a')
  if r.error or not r.converged:return {'iteration':it,'status':'failed','reason':r.error or 'nonconverged'}
  return {'iteration':it,'status':'completed','warnings':' | '.join(sorted(set(str(x.message) for x in w))),**r.params}
 except Exception as e:return {'iteration':it,'status':'failed','reason':repr(e)}
def endpoints(c):
 z=[]
 for n in [100,250,400,1000,2000]:
  if len(c)>=n:
   lo,med,hi=np.percentile(c.sort_values('iteration').iloc[:n]['E_c:L_c'],[2.5,50,97.5]);z.append({'completed_fits':n,'lo':lo,'median':med,'hi':hi})
 return z
def main():
 if OUT.exists():raise FileExistsError(OUT)
 d=pd.read_parquet(INP);orig=pd.read_parquet(ROOT/'results/production_confirmatory/raw/exact.parquet'); key=['initialization_id','configuration_id','depth','parameter_id']
 validation={'rows':len(d),'clusters':d.initialization_id.nunique(),'configurations':sorted(d.configuration_id.unique().tolist()),'depths':sorted(d.depth.unique().tolist()),'duplicate_keys':int(d.duplicated(key).sum()),'parameter_counts_by_depth':d.groupby('depth').parameter_id.nunique().to_dict(),'seed_root_original':20260726,'seed_root_independent':3872531887,'initialization_seed_overlap':sorted(set(d.initialization_seed)&set(orig.initialization_seed))}
 if validation['rows']!=25600 or validation['clusters']!=50 or validation['configurations']!=list(range(1,9)) or validation['depths']!=[1,2,3,4,6] or validation['duplicate_keys'] or validation['initialization_seed_overlap']:raise ValueError(validation)
 dc=add_centered_factors(build_h1_dataset(d))
 with warnings.catch_warnings(record=True) as w:warnings.simplefilter('always');fit=fit_mixed_model(H1_CENTERED_FORMULA,dc,'a')
 if fit.error or not fit.converged:raise RuntimeError(fit.error)
 e=fit.params['E_c:L_c'];se=fit.bse['E_c:L_c'];model={'estimate':e,'se':se,'ci':[e-1.95996398454*se,e+1.95996398454*se],'p_raw':float(2*stats.norm.sf(abs(e/se))),'optimizer':fit.optimizer_used,'converged':fit.converged,'singular':fit.singular_fit,'random_effect_variances':fit.random_effect_variances,'n_obs':fit.n_obs,'n_groups':fit.n_groups,'warnings':sorted(set(str(x.message) for x in w))}
 OUT.mkdir(parents=True);(OUT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n');(OUT/'model_summary.json').write_text(json.dumps(model,indent=2)+'\n')
 direct=pd.DataFrame();fail=[];started=time.time()
 for start in range(0,2000,50):
  with ProcessPoolExecutor(max_workers=16,initializer=init_worker) as ex:res=list(ex.map(one,range(start,start+50)))
  good=[{k:v for k,v in x.items() if k not in ['status','reason']} for x in res if x['status']=='completed'];fail += [x for x in res if x['status']=='failed'];direct=pd.concat([direct,pd.DataFrame(good)],ignore_index=True);cent=transform_bootstrap_draws(direct,'h1');direct.to_parquet(OUT/'bootstrap_direct_checkpoint.parquet',index=False);cent.to_parquet(OUT/'bootstrap_centered.parquet',index=False);pd.DataFrame(endpoints(cent)).to_csv(OUT/'bootstrap_endpoints.csv',index=False);(OUT/'bootstrap_meta.json').write_text(json.dumps({'plan_commit':PLAN,'seed':SEED,'attempted':start+50,'completed':len(cent),'failed':fail,'elapsed_seconds':time.time()-started},indent=2)+'\n')
 cent=transform_bootstrap_draws(direct,'h1');lo,med,hi=np.percentile(cent['E_c:L_c'],[2.5,50,97.5]);origm=json.loads((ROOT/'verification/factor_coding_correction_results.json').read_text())['primary_family'][0];cat='direction and magnitude retained' if np.sign(e)==np.sign(origm['estimate']) and origm['ci_95'][0]<=e<=origm['ci_95'][1] else ('direction retained but magnitude uncertain' if np.sign(e)==np.sign(origm['estimate']) else 'direction not retained')
 summary={**model,'bootstrap_completed':len(cent),'bootstrap_ci':[lo,hi],'bootstrap_median':med,'classification':cat,'plan_commit':PLAN};(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');pd.DataFrame([{'dataset':'original','estimate':origm['estimate'],'se':origm['standard_error'],'ci_lo':origm['ci_95'][0],'ci_hi':origm['ci_95'][1]},{'dataset':'independent_seed','estimate':e,'se':se,'ci_lo':model['ci'][0],'ci_hi':model['ci'][1]}]).to_csv(OUT/'original_vs_independent.csv',index=False)
if __name__=='__main__':main()
