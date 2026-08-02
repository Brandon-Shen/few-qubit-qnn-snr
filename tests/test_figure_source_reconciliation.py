import hashlib
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def test_archived_protected_bytes_are_lossless():
 p=ROOT/'verification/figure_source_archive/fig0_el_primary_source.pre_reconciliation.csv'
 assert sha(p)=='f89ccd263f2ea2e3fb92aed4677d0e32292851eda316244d014ccd49342a9a11'
def test_reconciled_source_is_conditional_and_referenced():
 d=pd.read_csv(ROOT/'paper/figure_data/fig0_el_primary_source.csv')
 assert set(d.metric)=={'I_EL_given_R0','J_EL_given_R0'}
 assert set(d.git_commit)=={'cbbeafa853b0e87e153a783296fed1f9c750681a'}
 main=(ROOT/'paper/main.tex').read_text(encoding='utf-8')
 assert 'figures/fig0_el_primary.pdf' in main
