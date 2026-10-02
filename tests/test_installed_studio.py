"""Independent audits for the installed live service's exact numeric outputs."""
import copy
import sys
from pathlib import Path

import pytest

from chainbench.studio_worker import calculate

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from smoke_studio import audit_response  # noqa: E402
from studio_evidence import FAMILIES, case_request  # noqa: E402


@pytest.mark.parametrize('family', FAMILIES)
@pytest.mark.parametrize('seed', [0, 7])
def test_actual_studio_cases_have_independently_audited_arrays_metrics_and_plots(family, seed):
    request = case_request(family, seed)
    value = calculate(request)
    result = audit_response(value, request)
    assert result['rows'] == 3*len(FAMILIES[family])


@pytest.mark.parametrize('damage', ['request', 'metric', 'html', 'start', 'digest', 'input-json', 'result-json'])
def test_studio_auditor_rejects_changed_outputs(damage):
    request = case_request('diagonal-lasso', 0)
    value = copy.deepcopy(calculate(request))
    if damage == 'request':
        value['request']['seed'] = 7
    elif damage == 'metric':
        value['result']['runs'][0]['rows'][1]['gap'] += .01
    elif damage == 'html':
        value['html'] = value['html'].replace('<metadata>', '<removed>', 1)
    elif damage == 'start':
        value['result']['instance']['x0'][0] += .01
    elif damage == 'input-json':
        value['input_json'] += ' '
    elif damage == 'result-json':
        value['result_json'] += ' '
    else:
        value['result']['instance']['input_sha256'] = '0'*64
    with pytest.raises(RuntimeError):
        audit_response(value, request)
