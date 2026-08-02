"""Resume independent H1 bootstrap with a persistent worker pool."""
import json,time
from concurrent.futures import ProcessPoolExecutor
import numpy as np,pandas as pd
from run_independent_seed_h1 import OUT,PLAN,SEED,endpoints,init_worker,one
from qnn_snr.stats.factor_coding import transform_bootstrap_draws
def main():
 direct=pd.read_parquet(OUT/'bootstrap_direct_checkpoint.parquet');meta=json.loads((OUT/'bootstrap_meta.json').read_text());fail=meta['failed'];start=int(direct.iteration.max())+1;started=time.time()-meta['elapsed_seconds']
 with ProcessPoolExecutor(max_workers=16,initializer=init_worker) as ex:
  for lo in range(start,2000,100):
   res=list(ex.map(one,range(lo,min(lo+100,2000))));good=[{k:v for k,v in x.items() if k not in ['status','reason']} for x in res if x['status']=='completed'];fail += [x for x in res if x['status']=='failed'];direct=pd.concat([direct,pd.DataFrame(good)],ignore_index=True);cent=transform_bootstrap_draws(direct,'h1');direct.to_parquet(OUT/'bootstrap_direct_checkpoint.parquet',index=False);cent.to_parquet(OUT/'bootstrap_centered.parquet',index=False);pd.DataFrame(endpoints(cent)).to_csv(OUT/'bootstrap_endpoints.csv',index=False);(OUT/'bootstrap_meta.json').write_text(json.dumps({'plan_commit':PLAN,'seed':SEED,'attempted':min(lo+100,2000),'completed':len(cent),'failed':fail,'elapsed_seconds':time.time()-started},indent=2)+'\n')
 cent=transform_bootstrap_draws(direct,'h1');a=json.loads((OUT/'model_summary.json').read_text());lo,med,hi=np.percentile(cent['E_c:L_c'],[2.5,50,97.5]);orig=json.loads(open('verification/factor_coding_correction_results.json').read())['primary_family'][0];e=a['estimate'];cat='direction and magnitude retained' if np.sign(e)==np.sign(orig['estimate']) and orig['ci_95'][0]<=e<=orig['ci_95'][1] else ('direction retained but magnitude uncertain' if np.sign(e)==np.sign(orig['estimate']) else 'direction not retained');a.update({'bootstrap_completed':len(cent),'bootstrap_ci':[lo,hi],'bootstrap_median':med,'classification':cat,'plan_commit':PLAN});(OUT/'summary.json').write_text(json.dumps(a,indent=2)+'\n');pd.DataFrame([{'dataset':'original','estimate':orig['estimate'],'se':orig['standard_error'],'ci_lo':orig['ci_95'][0],'ci_hi':orig['ci_95'][1]},{'dataset':'independent_seed','estimate':e,'se':a['se'],'ci_lo':a['ci'][0],'ci_hi':a['ci'][1]}]).to_csv(OUT/'original_vs_independent.csv',index=False)
if __name__=='__main__':main()
