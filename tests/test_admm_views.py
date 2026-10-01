import copy
import json
from html.parser import HTMLParser

import pytest

from chainbench.admm_geometry import run_admm_geometry
from chainbench.admm_views import admm_html
from chainbench.cli import main


class Record(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.text = ''
        self.cases = []
        self.native = []
        self.outcomes = []
        self.overview_links = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if 'data-admm-outcome' in attrs:
            self.outcomes.append(attrs['data-admm-outcome'])
        if 'data-admm-overview-link' in attrs:
            self.overview_links.append((attrs['data-admm-overview-link'],attrs['href']))
        if tag=='pre' and attrs.get('id')=='chainbench-evidence':
            self.active = True
        if 'data-admm-case' in attrs:
            self.cases.append(attrs['data-admm-case'])
        if 'data-admm-native' in attrs:
            self.native.append(int(attrs['data-admm-native']))

    def handle_endtag(self, tag):
        if tag=='pre':
            self.active = False

    def handle_data(self, text):
        if self.active:
            self.text += text


@pytest.mark.parametrize('steps',[1,60,160])
def test_html_retains_all_cases_exact_records_and_native_initial_states(steps):
    result = run_admm_geometry(steps)
    before = copy.deepcopy(result)
    html = admm_html(result,'ko')
    parsed = Record()
    parsed.feed(html)
    assert json.loads(parsed.text)==result==before
    assert parsed.cases==[c['id'] for c in result['cases']]
    assert parsed.native==[k for c in result['cases'] for k in c['native_iterations']]
    assert len(parsed.outcomes)==len(set(parsed.outcomes))==36
    assert set(parsed.outcomes)==set(parsed.cases)
    assert len(parsed.overview_links)==36
    for case_id,target in parsed.overview_links:
        assert target==f'#admm-{case_id}-k{steps}'
        assert parsed.ids.count(target[1:])==1
    assert html.count('data-admm-primal="surface"')==36
    assert html.count('data-admm-native="0"><td>0</td><td>—</td>')==36
    assert 'not reproductions of the source' in html
    assert 'f(x)+g(z)' in html and 'not a measurement-residual certificate' in html
    assert 'no outcome filtering' in html


@pytest.mark.parametrize('fault',['missing','duplicate'])
def test_overview_cannot_claim_full_coverage_with_a_missing_or_duplicate_case(fault):
    record = run_admm_geometry(1)
    if fault=='missing':
        record['cases'].pop()
    else:
        record['cases'][-1]=record['cases'][0]
    with pytest.raises(ValueError,match='each declared case exactly once'):
        admm_html(record)


@pytest.mark.parametrize('family,default',[('frank-wolfe',18),('ista-fista',18),('admm-lasso',60)])
def test_geometry_cli_preserves_existing_defaults_and_declares_admm_default(capsys,family,default):
    assert main(['geometry',family,'--format','json'])==0
    data = json.loads(capsys.readouterr().out)
    assert data['parameters']['steps']==default


@pytest.mark.parametrize('steps',['0','161'])
def test_cli_rejects_invalid_admm_budget(capsys,steps):
    with pytest.raises(SystemExit) as error:
        main(['geometry','admm-lasso','--steps',steps,'--format','json'])
    assert error.value.code==2
    assert 'steps' in capsys.readouterr().err


def test_invalid_identity_nonfinite_record_and_language_cannot_render():
    with pytest.raises(ValueError,match='ADMM'):
        admm_html({'kind':'another experiment'})
    record = run_admm_geometry(1)
    with pytest.raises(ValueError,match='lang'):
        admm_html(record,'xx')
    record['cases'][0]['rows'][1]['x'][0] = float('nan')
    with pytest.raises(ValueError):
        admm_html(record)
