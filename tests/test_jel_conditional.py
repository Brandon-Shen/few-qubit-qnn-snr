import numpy as np,pandas as pd
from qnn_snr.stats.jel_conditional import conditional_indices,bootstrap_draw

def test_j_identities():
 assert conditional_indices({i:2. for i in range(1,9)})=={'J_EL_given_R0':1.,'J_EL_given_R1':1.}
 g={i:1. for i in range(1,9)};g[5]=2;g[8]=.5
 out=conditional_indices(g);assert out['J_EL_given_R0']>1 and out['J_EL_given_R1']<1
def test_j_mapping():
 g={1:2,2:4,3:5,4:3,5:20,6:6,7:7,8:42}
 out=conditional_indices(g);assert out['J_EL_given_R0']==2 and out['J_EL_given_R1']==3
def test_bootstrap_determinism_and_cluster_resampling():
 sums=np.arange(1,401,dtype=float).reshape(50,8);counts=np.ones((50,8),int)
 assert bootstrap_draw(sums,counts,7,3)==bootstrap_draw(sums,counts,7,3)
 assert bootstrap_draw(sums,counts,7,3)!=bootstrap_draw(sums,counts,7,4)
