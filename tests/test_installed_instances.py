"""Exercise the independent installed-output auditor against real and damaged records."""
import copy
import sys
from pathlib import Path

import pytest

from chainbench.instance_reporting import instance_html
from chainbench.instances import generate_instance, import_instance, run_instance

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from instance_evidence import CASES, require_stored_instances  # noqa: E402
from smoke_instances import audit_instance_result, raw_cases  # noqa: E402


@pytest.mark.parametrize('name,family,methods,rows', CASES)
def test_independent_scalar_audit_accepts_all_cases(name, family, methods, rows):
    manifest = (generate_instance(family, dimension=4, seed=int(name.rsplit('-', 1)[1]),
                                  run={'steps': 6, 'include_iterates': True})
                if name.startswith('generated-') else import_instance(raw_cases()[name]))
    record = run_instance(manifest)
    assert audit_instance_result(record, manifest, instance_html(record, 'ko')) == rows
    assert [r['method'] for r in record['runs']] == methods


@pytest.mark.parametrize('field', ['objective', 'gap', 'stationarity', 'distance_to_reference'])
def test_scalar_audit_rejects_plausible_but_wrong_metrics(field):
    manifest = import_instance(raw_cases()['imported-lasso'])
    record = run_instance(manifest)
    record['runs'][0]['rows'][1][field] += .001
    with pytest.raises(RuntimeError):
        audit_instance_result(record, manifest)


def test_audit_rejects_missing_plot_and_modified_byte_fingerprint():
    manifest = import_instance(raw_cases()['imported-quadratic'])
    record = run_instance(manifest)
    html = instance_html(record)
    with pytest.raises(RuntimeError):
        audit_instance_result(record, manifest, html.replace('<metadata>', '<removed>', 1))
    other = copy.deepcopy(manifest)
    other['input_sha256'] = '0'*64
    record['instance'] = other
    with pytest.raises(RuntimeError):
        audit_instance_result(record, other)


@pytest.mark.parametrize('value', [None, [], {}, [True]*10])
def test_missing_installed_scope_is_not_success(value):
    with pytest.raises(RuntimeError):
        require_stored_instances(value)
