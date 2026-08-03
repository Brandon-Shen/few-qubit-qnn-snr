import hashlib,json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/final_submission_v1'
TEXT_SUFFIXES={'.py','.tex','.bib','.md','.txt','.json','.yaml','.yml','.csv','.tsv','.toml','.sha256'}
def sha(p):
 data=p.read_bytes()
 if p.suffix.lower() in TEXT_SUFFIXES:data=data.replace(b'\r\n',b'\n')
 return hashlib.sha256(data).hexdigest()
def test_final_rows_unique_and_required_fields():
 d=pd.read_csv(OUT/'final_numerical_results.csv');key=['analysis_identifier','dataset','estimand','depth','weighting','estimator_mode','interval_method'];assert not d.duplicated(key).any();required=json.loads((ROOT/'verification/final_numerical_results_freeze_plan.json').read_text())['required'];assert set(required)<=set(d.columns)
def test_final_manifest_references_exist_and_match():
 m=json.loads((OUT/'manifest.json').read_text());assert m['row_count']==len(pd.read_csv(OUT/'final_numerical_results.csv'))
 for r in m['component_references']:
  p=ROOT/r['path'];assert p.exists();assert sha(p)==r['sha256']
def test_final_checksums_match():
 for line in (OUT/'checksums.sha256').read_text().splitlines():
  digest,name=line.split('  ',1);assert sha(OUT/name)==digest
