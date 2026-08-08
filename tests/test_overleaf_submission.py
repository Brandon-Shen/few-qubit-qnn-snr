import hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def test_imported_artifact_identity_and_hashes():
    p=json.loads((ROOT/'verification/overleaf_import_provenance.json').read_text())
    for a in p['artifacts']:
        path=ROOT/a['assigned_filename']; assert path.exists(); assert sha(path)==a['sha256']
    audit=json.loads((ROOT/'verification/pdf_automated_audit.json').read_text())
    assert audit['main']['pages']==20 and audit['esm1']['pages']==7
    assert all(audit['main']['identity_checks'].values()) and all(audit['esm1']['identity_checks'].values())

def test_source_pdf_consistency_has_no_substantive_mismatch():
    d=json.loads((ROOT/'verification/overleaf_source_pdf_consistency.json').read_text())
    assert d['substantive_source_pdf_mismatches']==[]
    assert d['frozen_content']['primary_family'] and d['frozen_content']['conditional_j']

def test_staging_package_sources_and_references():
    package=ROOT/'submission_package'
    assert sha(package/'main.tex')==sha(ROOT/'paper/sn-article.tex')
    assert sha(package/'ESM_1.tex')==sha(ROOT/'paper/supplemental.tex')
    final=json.loads((ROOT/'verification/final_release_artifacts.json').read_text())
    assert final['status']=='final_compiled_artifacts_frozen'
    for artifact in final['artifacts']:
        path=ROOT/artifact['path']
        assert path.exists()
        assert path.stat().st_size==artifact['bytes']
        assert sha(path)==artifact['sha256']
    for tex in [package/'main.tex',package/'ESM_1.tex']:
        text=tex.read_text(encoding='utf-8')
        for ref in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',text): assert (package/ref).exists(),ref
    dep=json.loads((ROOT/'verification/source_dependency_inventory.json').read_text())
    assert dep['missing_required_official_files']==['sn-jnl.cls','sn-basic.bst']

def test_current_pdf_is_explicitly_final_for_release():
    stage=json.loads((ROOT/'verification/submission_package_staging.json').read_text())
    assert stage['status']=='final_release_package_prepared'
    assert stage['pdfs_outdated_relative_to_current_source'] is False
    assert stage['new_overleaf_compile_required'] is False
    assert stage['historical_imports_retained'] is True
    assert stage['zip_created'] is False
