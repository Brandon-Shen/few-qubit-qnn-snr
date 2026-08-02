"""LOO and cluster-robust components of the frozen H3 plan."""
from __future__ import annotations
import json, warnings, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd, patsy, statsmodels.formula.api as smf
from scipy import stats
from qnn_snr.stats.factor_coding import H2_H4_CENTERED_FORMULA, add_centered_factors
from qnn_snr.stats.models import build_h2h4_dataset, fit_mixed_model
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'results/h3_centered_robustness'; _DATA=None
sys.path.insert(0,str(ROOT/'scripts'))
from run_h3_centered_robustness import CAT_FORMULA, DEPTHS, er_rows  # noqa: E402
def init_worker():
 global _DATA
 p=pd.read_parquet(ROOT/'results/production_confirmatory/pointwise_gradient_statistics.parquet')
 _DATA=add_centered_factors(build_h2h4_dataset(p[p.analysis_mode=='finite_shot_end_to_end']))
def one(i):
 with warnings.catch_warnings():
  warnings.simplefilter('ignore'); r=fit_mixed_model(H2_H4_CENTERED_FORMULA,_DATA[_DATA.initialization_id!=i],'y')
 if r.error or not r.converged:return {'excluded_initialization_id':i,'status':'failed','reason':r.error}
 b=r.raw_result.fe_params; v=r.raw_result.cov_params();
 def lin(name,sgn):
  c=pd.Series(0.,index=b.index);c['E_c:R_c']=1;c['E_c:L_c:R_c']=sgn*.5;e=float(c@b);s=float(np.sqrt(c@v.loc[b.index,b.index]@c));return e,s
 e0,s0=lin('L0',-1);e1,s1=lin('L1',1);e=float(b['E_c:R_c']);s=float(r.bse['E_c:R_c'])
 return {'excluded_initialization_id':i,'status':'completed','ER_average':e,'ER_average_se':s,'ER_average_p':float(2*stats.norm.sf(abs(e/s))),'ER_L0':e0,'ER_L0_se':s0,'ER_L1':e1,'ER_L1_se':s1}
def main():
 with ProcessPoolExecutor(max_workers=10,initializer=init_worker) as ex: loo=list(ex.map(one,range(50)))
 pd.DataFrame(loo).to_csv(OUT/'leave_one_initialization_out.csv',index=False)
 p=pd.read_parquet(ROOT/'results/production_confirmatory/pointwise_gradient_statistics.parquet');d=add_centered_factors(build_h2h4_dataset(p[p.analysis_mode=='finite_shot_end_to_end']))
 ols=smf.ols(CAT_FORMULA,d).fit(cov_type='cluster',cov_kwds={'groups':d.initialization_id})
 di=ols.model.data.design_info; rows=[]; vectors=[]
 for dep in DEPTHS:
  vs=[]
  for l in (0,1):
   ms=[patsy.build_design_matrices([di],pd.DataFrame([z]),return_type='dataframe')[0].iloc[0] for z in er_rows(l,dep)];vs.append(ms[0]-ms[1]-ms[2]+ms[3])
  c=.5*(vs[0]+vs[1]);vectors.append(c);t=ols.t_test(c.values.reshape(1,-1));e=float(np.ravel(t.effect)[0]);s=float(np.ravel(t.sd)[0]);rows.append({'depth':dep,'estimate':e,'se_cluster':s,'ci_lo':e-1.95996398454*s,'ci_hi':e+1.95996398454*s,'p':float(np.ravel(t.pvalue)[0])})
 pd.DataFrame(rows).to_csv(OUT/'depth_contrasts_cluster_robust.csv',index=False)
 base=vectors[0]; R=np.vstack([(v-base).values for v in vectors[1:]]); w=ols.wald_test(R,use_f=False,scalar=True)
 (OUT/'supplemental_summary.json').write_text(json.dumps({'loo_completed':sum(x['status']=='completed' for x in loo),'loo_failed':[x for x in loo if x['status']!='completed'],'cluster_robust_moderation':{'statistic':float(w.statistic),'df':4,'p':float(w.pvalue)}},indent=2)+'\n')
if __name__=='__main__':main()
