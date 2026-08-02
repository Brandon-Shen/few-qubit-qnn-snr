"""Prepared-state metrics at initialization from authoritative exact regeneration."""
from __future__ import annotations
import numpy as np,pandas as pd
from qnn_snr.config import CONFIGURATION_TABLE
from qnn_snr.costs import evaluate_both_costs
from qnn_snr.gradients import forward_pass_exact,total_gradients_exact
from qnn_snr.hamiltonian import diagonalize_tfim
from qnn_snr.replicate import draw_theta_blocks
from qnn_snr.residual import init_classical_params
from qnn_snr.seeds import derive_seed

def regenerate(cfg,label:str)->pd.DataFrame:
 s=diagonalize_tfim(cfg.task.n_qubits,cfg.task.J,cfg.task.h);rows=[]
 for d in cfg.circuit.depths:
  for i in range(cfg.design.n_initializations):
   ts=derive_seed(cfg.seed_root,'init_theta',i,d);cs=derive_seed(cfg.seed_root,'init_classical',i,d)
   theta=draw_theta_blocks(ts,d,cfg.task.n_qubits,cfg.circuit.init_low,cfg.circuit.init_high)
   classical=init_classical_params(cs,d,cfg.task.n_qubits,cfg.resolved_hidden_dim(),cfg.residual.weight_init,cfg.residual.bias_init)
   for cid in cfg.design.configurations:
    E,L,R=CONFIGURATION_TABLE[cid];f=forward_pass_exact(theta,classical,E,cfg.gamma_for(R),cfg.cost_type_for(L),s,cfg.task.n_qubits,cfg.residual.x0_init);m=evaluate_both_costs(f.final_state,s)
    energy=float(m['final_tfim_energy']);fidelity=float(m['global_fidelity'])
    rows.append({'dataset':label,'initialization_id':i,'configuration_id':cid,'E':E,'L':L,'R':R,'depth':d,'theta_seed':ts,'classical_seed':cs,'prepared_state_energy':energy,'normalized_prepared_state_energy':(energy-s.E_0)/(s.E_max-s.E_0),'prepared_state_fidelity':fidelity,'prepared_state_infidelity':1-fidelity})
 return pd.DataFrame(rows)

def validate_regeneration(cfg,label,exact,metrics,tol=1e-10):
 key=['dataset','initialization_id','configuration_id','depth'];errors=[]
 if len(metrics)!=2000 or metrics.duplicated(key).any():errors.append('row uniqueness')
 for c in ['prepared_state_fidelity','prepared_state_infidelity','normalized_prepared_state_energy']:
  if ((metrics[c]<-tol)|(metrics[c]>1+tol)).any():errors.append(c+' bounds')
 if not np.allclose(metrics.prepared_state_fidelity+metrics.prepared_state_infidelity,1,atol=tol):errors.append('complement')
 s=diagonalize_tfim(cfg.task.n_qubits,cfg.task.J,cfg.task.h)
 if ((metrics.prepared_state_energy<s.E_0-tol)|(metrics.prepared_state_energy>s.E_max+tol)).any():errors.append('energy bounds')
 maxdiff=0.
 for d in [1,6]:
  for i in [0,49]:
   ts=derive_seed(cfg.seed_root,'init_theta',i,d);cs=derive_seed(cfg.seed_root,'init_classical',i,d);theta=draw_theta_blocks(ts,d,cfg.task.n_qubits,cfg.circuit.init_low,cfg.circuit.init_high);cl=init_classical_params(cs,d,cfg.task.n_qubits,cfg.resolved_hidden_dim(),cfg.residual.weight_init,cfg.residual.bias_init)
   for cid in [1,8]:
    E,L,R=CONFIGURATION_TABLE[cid];T,_=total_gradients_exact(theta,cl,E,cfg.gamma_for(R),cfg.cost_type_for(L),s,cfg.task.n_qubits,cfg.residual.x0_init)
    cell=exact.query('initialization_id==@i and depth==@d and configuration_id==@cid').sort_values(['block_index','qubit_index'])
    calc=np.concatenate([T[x] for x in range(1,d+1)]);maxdiff=max(maxdiff,float(np.max(np.abs(calc-cell.exact_gradient.to_numpy()))))
 if maxdiff>tol:errors.append('gradient validation')
 if errors:raise ValueError(f'{label}: {errors}')
 return {'dataset':label,'rows':len(metrics),'duplicate_keys':0,'bounds_tolerance':tol,'gradient_validation_max_abs_difference':maxdiff,'errors':[]}

def summarize(metrics):
 g=metrics.groupby(['dataset','configuration_id','E','L','R','depth'])
 rows=[]
 for keys,x in g:
  for m in ['prepared_state_energy','normalized_prepared_state_energy','prepared_state_fidelity','prepared_state_infidelity']:
   a=x[m].to_numpy();rows.append(dict(zip(['dataset','configuration_id','E','L','R','depth'],keys),metric=m,n=len(a),mean=np.mean(a),median=np.median(a),sd=np.std(a,ddof=1),q1=np.percentile(a,25),q3=np.percentile(a,75),iqr=np.percentile(a,75)-np.percentile(a,25),minimum=np.min(a),maximum=np.max(a)))
 return pd.DataFrame(rows)
