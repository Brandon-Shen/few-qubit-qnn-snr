"""Generate frozen prepared-state initialization metrics and bootstrap summaries."""
from __future__ import annotations
import hashlib,json,platform
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np,pandas as pd
from qnn_snr.config import load_config
from qnn_snr.task_metrics import regenerate,validate_regeneration,summarize
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/task_metrics/prepared_state';PLAN='645521db6511ca049d89e64f810e65a3407a7b52'
CFG={'original':ROOT/'configs/confirmatory.yaml','independent_seed':ROOT/'configs/h2_replication_v1_stage1.yaml'};EXACT={'original':ROOT/'results/production_confirmatory/raw/exact.parquet','independent_seed':ROOT/'results/h2_replication_v1/_pipeline_output_stage1/raw/exact.parquet'};SEEDS={'original':355001,'independent_seed':355002}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,default=float)+'\n',encoding='utf-8')
def main():
 if OUT.exists():raise FileExistsError(OUT)
 OUT.mkdir(parents=True);frames=[];valid=[]
 for label in CFG:
  cfg=load_config(CFG[label]);m=regenerate(cfg,label);e=pd.read_parquet(EXACT[label]);valid.append(validate_regeneration(cfg,label,e,m));frames.append(m)
 metrics=pd.concat(frames,ignore_index=True);metrics.to_csv(OUT/'prepared_state_metrics.csv',index=False);metrics.to_parquet(OUT/'prepared_state_metrics.parquet',index=False)
 base=summarize(metrics);drawrows=[]
 for label in CFG:
  x=metrics[metrics.dataset==label];cells=x[['configuration_id','depth']].drop_duplicates().sort_values(['configuration_id','depth']);arr={m:x.pivot(index='initialization_id',columns=['configuration_id','depth'],values=m).loc[:,pd.MultiIndex.from_frame(cells)].to_numpy() for m in ['prepared_state_energy','normalized_prepared_state_energy','prepared_state_fidelity','prepared_state_infidelity']}
  for it in range(2000):
   pick=np.random.default_rng((SEEDS[label],it)).integers(0,50,50)
   for metric,a in arr.items():
    means=a[pick].mean(axis=0)
    for j,(cid,d) in enumerate(cells.itertuples(index=False,name=None)):drawrows.append({'dataset':label,'iteration':it,'configuration_id':cid,'depth':d,'metric':metric,'mean':means[j]})
 draws=pd.DataFrame(drawrows);draws.to_parquet(OUT/'bootstrap_draws.parquet',index=False)
 ci=draws.groupby(['dataset','configuration_id','depth','metric'])['mean'].apply(lambda x:pd.Series({'bootstrap_median':np.percentile(x,50),'bootstrap_ci_lo':np.percentile(x,2.5),'bootstrap_ci_hi':np.percentile(x,97.5)})).unstack().reset_index();summary=base.merge(ci,on=['dataset','configuration_id','depth','metric'],validate='one_to_one');summary.to_csv(OUT/'configuration_depth_summary.csv',index=False)
 pd.DataFrame(valid).to_json(OUT/'validation.json',orient='records',indent=2);pd.DataFrame(columns=['dataset','iteration','reason']).to_csv(OUT/'failure_log.csv',index=False)
 source=summary[summary.metric.isin(['normalized_prepared_state_energy','prepared_state_fidelity'])].copy();source.to_csv(OUT/'figure_source.csv',index=False)
 fig,axes=plt.subplots(2,1,figsize=(6.5,6),sharex=True);markers=['o','s','^','v','D','P','X','*']
 for ax,metric,ylabel in zip(axes,['normalized_prepared_state_energy','prepared_state_fidelity'],['Normalized prepared-state energy','Prepared-state target fidelity']):
  for cid,mk in zip(range(1,9),markers):
   for label,ls in [('original','-'),('independent_seed','--')]:
    z=source.query('metric==@metric and configuration_id==@cid and dataset==@label').sort_values('depth');ax.plot(z.depth,z['mean'],marker=mk,linestyle=ls,label=f'C{cid} {label}' if ax is axes[0] else None,linewidth=.8,markersize=3)
  ax.set_ylabel(ylabel);ax.set_xticks([1,2,3,4,6])
 axes[1].set_xlabel('Block count D');axes[0].legend(ncol=4,fontsize=6,frameon=False);fig.tight_layout();fig.savefig(OUT/'prepared_state_metrics.pdf');fig.savefig(OUT/'prepared_state_metrics.png',dpi=200);plt.close(fig)
 dump(OUT/'manifest.json',{'plan_commit':PLAN,'analysis_commit':None,'input_sha256':{**{str(v.relative_to(ROOT)):sha(v) for v in CFG.values()},**{str(v.relative_to(ROOT)):sha(v) for v in EXACT.values()}},'seeds':SEEDS,'bootstrap_completed':{'original':2000,'independent_seed':2000},'failures':0,'command':'python scripts/run_task_metrics.py','environment':{'python':platform.python_version()}})
 # Descriptive range-based report; no significance testing.
 lines=['# Prepared-state task metrics','',f'**Status:** post-primary descriptive initialization-state metrics; plan `{PLAN}`. No optimization was performed.','',f'Generated {len(metrics)} unique terminal-block prepared states; all bounds/complementarity and predeclared exact-gradient checks passed.','']
 for label in CFG:
  z=summary[(summary.dataset==label)&(summary.metric=='prepared_state_fidelity')];q=summary[(summary.dataset==label)&(summary.metric=='normalized_prepared_state_energy')];lines.append(f"- {label}: configuration-depth mean fidelity spans {z['mean'].min():.4f} to {z['mean'].max():.4f}; mean normalized energy spans {q['mean'].min():.4f} to {q['mean'].max():.4f}.")
 lines += ['','These are prepared-state-at-initialization descriptions. They do not demonstrate optimization convergence, final performance, trainability, hardware advantage, or savings.']
 (ROOT/'verification/task_metrics_results.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');dump(ROOT/'verification/task_metrics_results.json',{'status':'post_primary_descriptive','plan_commit':PLAN,'analysis_commit':None,'validation':valid,'summary_path':'results/task_metrics/prepared_state/configuration_depth_summary.csv'})
if __name__=='__main__':main()
