import copy
import importlib.util
import json
from pathlib import Path

import pytest

from chainbench.learning import learning_html


def validator():
    spec = importlib.util.spec_from_file_location('paths_smoke',
        Path(__file__).resolve().parents[1]/'scripts/smoke_learning_paths.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.validate_learning_paths


@pytest.mark.parametrize('topic,count', [
    ('gd-baseline', 3), ('nesterov-1983', 3), ('polyak-1964', 3),
    ('hestenes-stiefel-1952', 3), ('jaggi-2013', 3), ('rockafellar-1976', 2),
    ('beck-teboulle-2009', 4), ('ista-vs-fista', 4),
])
def test_focused_pages_have_executable_workflows_and_no_missing_local_links(topic, count):
    html = learning_html(topic, 'en')
    assert validator()(html) == count
    assert 'data-workflow-link=' not in html


def test_link_context_does_not_change_computed_learning_evidence(monkeypatch):
    from test_learning_workflows import Evidence

    import chainbench.learning as module

    # A presentation-only change must preserve one computed record exactly.
    # Independent recomputation has a separate numerical comparison contract.
    result = module.run_check('jaggi-2013')
    chart = module.build_check_chart('jaggi-2013')
    monkeypatch.setattr(module, 'run_check', lambda _: copy.deepcopy(result))
    monkeypatch.setattr(module, 'build_check_chart', lambda _: copy.deepcopy(chart))
    raw = learning_html('jaggi-2013', 'ko')
    linked = learning_html('jaggi-2013', 'ko', report_links=['simplex.html', 'fw-sparsity.html'])
    assert json.loads(Evidence(raw).text) == json.loads(Evidence(linked).text)


@pytest.mark.parametrize('bad', ['missing.html', '../simplex.html', 'https://example.com/x'])
def test_unknown_report_link_rejected_before_computation(bad, monkeypatch):
    import chainbench.learning as module
    monkeypatch.setattr(module, 'run_check', lambda _: pytest.fail('link preflight must run first'))
    with pytest.raises(ValueError, match='linked learning report'):
        learning_html(report_links=[bad])


def test_independent_validator_binds_cards_to_actual_artifact_commands():
    html = learning_html('jaggi-2013', report_links=['simplex.html'])
    artifacts = [{'path':'simplex.html', 'command':['geometry','frank-wolfe','--steps','18','--lang','en']}]
    assert validator()(html, artifacts) == 3
    artifacts[0]['command'][3] = '17'
    with pytest.raises(RuntimeError, match='workflow'):
        validator()(html, artifacts)


@pytest.mark.parametrize('fault', ['missing-file', 'wrong-command', 'wrong-target'])
def test_independent_validator_rejects_broken_reading_paths(fault):
    html = learning_html('jaggi-2013', report_links=['simplex.html'])
    artifacts = [{'path':'simplex.html', 'command':['geometry','frank-wolfe','--steps','18','--lang','en']}]
    if fault == 'missing-file':
        artifacts = []
    elif fault == 'wrong-command':
        html = html.replace('python -m chainbench geometry frank-wolfe --steps 18',
                            'python -m chainbench geometry frank-wolfe --steps 19')
    else:
        html = html.replace('href="simplex.html"', 'href="fw-sparsity.html"')
    with pytest.raises(RuntimeError, match='workflow'):
        validator()(html, artifacts)
