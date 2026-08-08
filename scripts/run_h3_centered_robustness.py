"""Run the frozen post-primary centered-H3 robustness package."""
from __future__ import annotations
import json, warnings
from pathlib import Path
import numpy as np, pandas as pd, patsy
from scipy import stats
from qnn_snr.stats.factor_coding import H2_H4_CENTERED_FORMULA, add_centered_factors, transform_bootstrap_draws
from qnn_snr.stats.models import build_h2h4_dataset, fit_mixed_model

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'results/h3_centered_robustness'; PLAN='7cdb9a2b9a820799fe1b05491f9498b838f5a15c'
DEPTHS=(1,2,3,4,6)
CAT_FORMULA=("y ~ E_c*L_c*R_c + C(depth, Sum) + log2_budget + "
 "E_c:C(depth, Sum)+L_c:C(depth, Sum)+R_c:C(depth, Sum)+"
 "E_c:R_c:C(depth, Sum)+L_c:R_c:C(depth, Sum)")

def fit(formula,d):
 with warnings.catch_warnings(record=True) as w:
  warnings.simplefilter('always'); r=fit_mixed_model(formula,d,'y')
 if r.error or not r.converged: raise RuntimeError(r.error or 'nonconverged')
 return r,sorted(set(str(x.message) for x in w))
def contrast(raw, rows, label):
 di=raw.model.data.design_info
 mats=[patsy.build_design_matrices([di],pd.DataFrame([x]),return_type='dataframe')[0].iloc[0] for x in rows]
 c=mats[0]-mats[1]-mats[2]+mats[3]
 tt=raw.t_test(c.values.reshape(1,-1)); est=float(np.ravel(tt.effect)[0]); se=float(np.ravel(tt.sd)[0])
 return {'contrast':label,'estimate':est,'se':se,'ci_lo':est-1.95996398454*se,'ci_hi':est+1.95996398454*se,'p_raw':float(2*stats.norm.sf(abs(est/se))),'linear_contrast':{k:float(v) for k,v in c.items() if abs(v)>1e-12}}
def er_rows(l,depth=3,budget=9):
 base={'L_c':l-.5,'depth':depth,'depth_z':(depth-3.2)/np.std([1,2,3,4,6],ddof=0),'log2_budget':budget}
 def row(e,r): return {**base,'E_c':e-.5,'R_c':r-.5}
 return [row(1,1),row(1,0),row(0,1),row(0,0)]
def simple(raw,prefix):
 a=contrast(raw,er_rows(0),prefix+'_L0'); b=contrast(raw,er_rows(1),prefix+'_L1')
 # average contrast and covariance-aware t-test
 di=raw.model.data.design_info
 def vec(l):
  ms=[patsy.build_design_matrices([di],pd.DataFrame([x]),return_type='dataframe')[0].iloc[0] for x in er_rows(l)]
  return ms[0]-ms[1]-ms[2]+ms[3]
 c=.5*(vec(0)+vec(1)); tt=raw.t_test(c.values.reshape(1,-1)); est=float(np.ravel(tt.effect)[0]); se=float(np.ravel(tt.sd)[0])
 avg={'contrast':prefix+'_L_average','estimate':est,'se':se,'ci_lo':est-1.95996398454*se,'ci_hi':est+1.95996398454*se,'p_raw':float(2*stats.norm.sf(abs(est/se))),'linear_contrast':{k:float(v) for k,v in c.items() if abs(v)>1e-12}}
 return [a,b,avg]
def main():
 if OUT.exists(): raise FileExistsError(OUT)
 pw=pd.read_parquet(ROOT/'results/production_confirmatory/pointwise_gradient_statistics.parquet')
 modes={m:add_centered_factors(build_h2h4_dataset(pw[pw.analysis_mode==m])) for m in ['finite_shot_end_to_end','finite_shot_conditional']}
 full,w1=fit(H2_H4_CENTERED_FORMULA,modes['finite_shot_end_to_end']); cond,w2=fit(H2_H4_CENTERED_FORMULA,modes['finite_shot_conditional'])
 active,w3=fit(H2_H4_CENTERED_FORMULA,modes['finite_shot_end_to_end'].query('depth >= 3'))
 cat,w4=fit(CAT_FORMULA,modes['finite_shot_end_to_end'])
 rows=simple(full.raw_result,'full_end_to_end')+simple(active.raw_result,'active_Dge3')+simple(cond.raw_result,'conditional_mode')
 depth=[]
 for d in DEPTHS:
  x=contrast(cat.raw_result,er_rows(0,d),f'D{d}_L0'); y=contrast(cat.raw_result,er_rows(1,d),f'D{d}_L1')
  # average via estimates with direct combined contrast
  di=cat.raw_result.model.data.design_info
  vs=[]
  for l in (0,1):
   ms=[patsy.build_design_matrices([di],pd.DataFrame([z]),return_type='dataframe')[0].iloc[0] for z in er_rows(l,d)]
   vs.append(ms[0]-ms[1]-ms[2]+ms[3])
  c=.5*(vs[0]+vs[1]); tt=cat.raw_result.t_test(c.values.reshape(1,-1)); e=float(np.ravel(tt.effect)[0]); s=float(np.ravel(tt.sd)[0])
  depth.append({'depth':d,'estimate':e,'se':s,'ci_lo':e-1.95996398454*s,'ci_hi':e+1.95996398454*s,'n_obs':int((modes['finite_shot_end_to_end'].depth==d).sum())})
 wt=cat.raw_result.wald_test_terms(skip_single=False,scalar=True).table.loc['E_c:R_c:C(depth, Sum)']
 boot=transform_bootstrap_draws(pd.read_parquet(ROOT/'results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_iterations.parquet'),'h2h4')
 boot['ER_L0']=boot['E:R']; boot['ER_L1']=boot['E:R']+boot['E:L:R']; boot['ER_L_average']=boot['E_c:R_c']
 bs=[]
 for c in ['ER_L0','ER_L1','ER_L_average']:
  lo,med,hi=np.percentile(boot[c],[2.5,50,97.5]); bs.append({'contrast':c,'iterations':len(boot),'median':med,'ci_lo':lo,'ci_hi':hi})
 OUT.mkdir(parents=True); pd.DataFrame(rows).to_csv(OUT/'simple_and_sensitivity_contrasts.csv',index=False); pd.DataFrame(depth).to_csv(OUT/'depth_contrasts.csv',index=False); pd.DataFrame(bs).to_csv(OUT/'bootstrap_simple_interactions.csv',index=False)
 pd.DataFrame({'iteration':boot.iteration,'stream':boot._stream,'seed':boot._seed,'ER_L0':boot.ER_L0,'ER_L1':boot.ER_L1,'ER_L_average':boot.ER_L_average}).to_parquet(OUT/'bootstrap_draws.parquet',index=False)
 meta={'plan_commit':PLAN,'omnibus':{'statistic':float(wt.statistic),'df':float(wt.df_constraint),'p':float(wt.pvalue)},'warnings':{'full':w1,'active':w3,'conditional':w2,'categorical':w4},'n':{k:len(v) for k,v in modes.items()},'loo_status':'pending_separate_execution'}
 (OUT/'summary.json').write_text(json.dumps(meta,indent=2)+'\n')
if __name__=='__main__': main()
