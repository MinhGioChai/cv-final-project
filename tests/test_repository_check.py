import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('repository_check',Path(__file__).resolve().parents[1]/'scripts/check_repository.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)


def test_credentials_report_only_rule_and_line():
    value='hf_'+'a'*30
    result=checker.findings('safe\n'+value)
    assert result==[{'rule':'hf_token','line':2}]
    assert value not in str(result)


def test_git_candidate_audit_rejects_tracked_local_cache(tmp_path):
    path=tmp_path/'data/raw/receipt.json';path.parent.mkdir(parents=True);path.write_text('{}')
    report=checker.audit(tmp_path,['data/raw/receipt.json'])
    assert not report['ready'] and report['issues'][0]['rule']=='local_artifact_in_git'


def test_clean_small_candidates_pass(tmp_path):
    (tmp_path/'README.md').write_text('synthetic_test_only')
    assert checker.audit(tmp_path,['README.md'])['ready']


def test_signed_url_is_flagged_without_contents():
    result=checker.findings('https://example.invalid/a?'+'X-Amz-Signature=synthetic_test_only')
    assert result==[{'rule':'signed_asset_url','line':1}]
