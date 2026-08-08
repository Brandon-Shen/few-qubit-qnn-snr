import numpy as np,pandas as pd
from qnn_snr.task_metrics import summarize

def test_metric_bounds_complement_and_uniqueness():
 d=pd.DataFrame({'dataset':['x','x'],'initialization_id':[0,1],'configuration_id':[1,1],'E':[0,0],'L':[0,0],'R':[0,0],'depth':[1,1],'prepared_state_energy':[0.,1.],'normalized_prepared_state_energy':[.5,.6],'prepared_state_fidelity':[.2,.8],'prepared_state_infidelity':[.8,.2]})
 assert not d.duplicated(['dataset','initialization_id','configuration_id','depth']).any();assert np.allclose(d.prepared_state_fidelity+d.prepared_state_infidelity,1);assert d.normalized_prepared_state_energy.between(0,1).all();assert len(summarize(d))==4
def test_no_budget_or_parameter_columns_in_state_key():
 key=['dataset','initialization_id','configuration_id','depth'];assert 'budget' not in key and 'parameter_id' not in key
