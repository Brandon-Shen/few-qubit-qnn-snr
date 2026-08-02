"""Conditional multiplicative exact-gradient indices and cluster bootstrap."""
from __future__ import annotations
import numpy as np
import pandas as pd

MAPPING = {"R0": {"baseline": 1, "E": 2, "L": 3, "EL": 5},
           "R1": {"R": 4, "ER": 6, "LR": 7, "ELR": 8}}


def validate_exact(d: pd.DataFrame, label: str) -> dict:
    key=["initialization_id","configuration_id","depth","parameter_id"]
    errors=[]
    if len(d)!=25600: errors.append("rows")
    if d.duplicated(key).any(): errors.append("duplicates")
    if sorted(d.configuration_id.unique()) != list(range(1,9)): errors.append("configurations")
    if sorted(d.depth.unique()) != [1,2,3,4,6]: errors.append("depths")
    if d.initialization_id.nunique()!=50: errors.append("clusters")
    if set(d.analysis_mode)!= {"statevector_exact"}: errors.append("mode")
    if set(d.budget)!= {0}: errors.append("budget")
    if not np.isfinite(d.exact_gradient).all(): errors.append("gradient")
    if errors: raise ValueError(f"{label}: {errors}")
    return {"dataset":label,"rows":len(d),"clusters":50,"duplicate_keys":0,
            "configurations":list(range(1,9)),"depths":[1,2,3,4,6],"errors":[]}


def configuration_rms(d: pd.DataFrame) -> dict[int,float]:
    return d.groupby("configuration_id").exact_gradient.apply(lambda x: float(np.sqrt(np.mean(x.to_numpy()**2)))).to_dict()


def conditional_indices(g: dict[int,float]) -> dict[str,float]:
    den0=g[2]*g[3]; den1=g[6]*g[7]
    if not np.isfinite(den0) or den0==0 or not np.isfinite(den1) or den1==0:
        raise ZeroDivisionError("conditional J denominator is zero/nonfinite")
    return {"J_EL_given_R0":g[5]*g[1]/den0,"J_EL_given_R1":g[8]*g[4]/den1}


def init_sufficient_statistics(d: pd.DataFrame) -> tuple[np.ndarray,np.ndarray]:
    grouped=d.assign(sq=d.exact_gradient**2).groupby(["initialization_id","configuration_id"]).agg(sumsq=("sq","sum"),n=("sq","size"))
    ids=sorted(d.initialization_id.unique()); sums=np.empty((len(ids),8)); counts=np.empty((len(ids),8),dtype=int)
    for i,init in enumerate(ids):
        for c in range(1,9): sums[i,c-1]=grouped.loc[(init,c),"sumsq"];counts[i,c-1]=grouped.loc[(init,c),"n"]
    return sums,counts


def bootstrap_draw(sums:np.ndarray,counts:np.ndarray,seed:int,iteration:int)->dict:
    chosen=np.random.default_rng((seed,iteration)).integers(0,len(sums),size=len(sums))
    g=np.sqrt(sums[chosen].sum(axis=0)/counts[chosen].sum(axis=0))
    out=conditional_indices({c:float(g[c-1]) for c in range(1,9)})
    return {"iteration":iteration,**out}
