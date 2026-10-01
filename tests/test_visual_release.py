"""Release regressions: a rendered picture must retain its actual numerical evidence."""
import copy
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict, replace
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import pytest

from chainbench._plot_audit import chart_metric
from chainbench.checks import run_all
from chainbench.cli import main
from chainbench.experiment_reporting import render_experiment
from chainbench.experiments import preset_config, run_experiment
from chainbench.reporting import render_html
from chainbench.visuals import ChartSpec, LineSeries, build_check_chart, render_line_chart


class Evidence(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.text = ''
    def handle_starttag(self, tag, attrs):
        if tag == 'pre' and dict(attrs).get('id') == 'chainbench-evidence':
            self.active = True
    def handle_endtag(self, tag):
        if tag == 'pre':
            self.active = False
    def handle_data(self, data):
        if self.active:
            self.text += data


def evidence(text):
    parser = Evidence()
    parser.feed(text)
    return json.loads(parser.text)


def test_plotted_samples_reproduce_every_checked_metric():
    for result in run_all():
        chart = build_check_chart(result.slug)
        assert chart_metric(result.slug, chart) == pytest.approx(result.observed, rel=1e-10)


def test_fixed_html_retains_exact_chart_samples_and_environment(monkeypatch):
    captured = {}

    def capture_chart(slug):
        chart = build_check_chart(slug)
        captured[slug] = asdict(chart)
        return chart

    monkeypatch.setattr('chainbench.reporting.build_check_chart', capture_chart)
    results = run_all()
    record = evidence(render_html(results))
    assert len(record['charts']) == len(results)
    assert record['environment']['numpy'] == np.__version__
    assert record['results'][0]['observed'] == results[0].observed
    # Compare every serialized chart with its actual input, not another rerun.
    assert record['charts'] == json.loads(json.dumps(captured))


@pytest.mark.parametrize('change', [{'observed': 42.}, {'consistent': False}, {'threshold': 7.}])
def test_summary_cannot_silently_disagree_with_picture(change):
    results = run_all()
    results[0] = replace(results[0], **change)
    with pytest.raises(ValueError, match='visual'):
        render_html(results)


def test_duplicate_paper_cards_are_rejected():
    result = run_all()[0]
    with pytest.raises(ValueError, match='duplicate'):
        render_html([result, result])


@pytest.mark.parametrize('family', ['quadratic', 'diagonal-lasso', 'simplex'])
def test_experiment_html_retains_all_rows_parameters_and_config(family):
    result = run_experiment(preset_config(family))
    before = copy.deepcopy(result)
    assert evidence(render_experiment(result, 'html')) == result == before


def test_zero_lasso_is_a_valid_visual_result(tmp_path):
    path = tmp_path / 'zero.html'
    assert main(['experiment', '--preset', 'diagonal-lasso', '--lam', '100',
                 '--format', 'html', '--output', str(path)]) == 0
    text = path.read_text(encoding='utf-8')
    assert 'All recorded values are zero' in text
    assert evidence(text)['runs'][0]['rows'][-1]['gap'] == 0


@pytest.mark.parametrize('values', [(0., 0., 0.), (1., 0., .1), (1., 0., 0.), (1e-300, 1e-200, 1e200)])
def test_svg_zeros_and_extreme_finite_data_preserve_samples(values):
    spec = ChartSpec('Exact <samples>', 'iteration', 'error',
                     (LineSeries('A&B', (0., 1., 2.), values),))
    xml = ET.fromstring(render_line_chart(spec))
    metadata = xml.find('{http://www.w3.org/2000/svg}metadata')
    assert json.loads(metadata.text)['series'][0]['y'] == list(values)
    assert '<samples>' not in render_line_chart(spec)
    assert all('nan' not in str(value).lower() and 'inf' not in str(value).lower()
               for el in xml.iter() for key, value in el.attrib.items()
               if key in ('points', 'd', 'cx', 'cy'))
    if any(v == 0 for v in values) and any(v > 0 for v in values):
        assert 'zero samples shown as triangles' in render_line_chart(spec)


def test_five_series_legend_labels_stay_inside_viewbox():
    spec = ChartSpec('Five methods', 'iteration', 'error', tuple(
        LineSeries(name, (0., 1.), (1., .1))
        for name in ['gd', 'smooth-fista', 'heavy-ball', 'cg', 'proximal-point']))
    xml = ET.fromstring(render_line_chart(spec))
    found = []
    for el in xml.iter():
        if el.tag.endswith('text') and el.text in [s.label for s in spec.series]:
            assert 0 <= float(el.attrib['x']) < 690
            found.append(el.text)
    assert len(found) == 5


@pytest.mark.parametrize('series', [(), (LineSeries('bad', (0., 1.), (1.,)),),
    (LineSeries('bad', (0., 0.), (1., .5)),), (LineSeries('bad', (0.,), (float('nan'),)),),
    (LineSeries('bad', (0.,), (-1.,)),)])
def test_malformed_chart_data_is_rejected(series):
    with pytest.raises(ValueError):
        render_line_chart(ChartSpec('bad', 'k', 'gap', series))


def test_html_escapes_external_text_in_the_exact_record():
    result = run_experiment(preset_config('simplex'))
    result['notice'] = '</pre><script>alert(1)</script>'
    text = render_experiment(result, 'html')
    assert '<script>' not in text
    assert evidence(text)['notice'] == result['notice']


def test_markdown_requires_explicit_format_after_v030_default_change(tmp_path):
    dest = tmp_path / 'report.html'
    assert main(['report', '--output', str(dest)]) == 0
    assert Path(dest).read_text(encoding='utf-8').startswith('<!doctype html>')


def test_independent_install_validator_accepts_actual_visual_reports():
    import importlib.util

    from chainbench.reporting import result_to_dict
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'smoke_install.py'
    spec = importlib.util.spec_from_file_location('smoke', path)
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    results = run_all()
    text = render_html(results)
    smoke.validate_html(text, [result_to_dict(r) for r in results])
    with pytest.raises(RuntimeError):
        smoke.validate_html('<svg/>', [result_to_dict(r) for r in results])
    for name in ('quadratic', 'diagonal-lasso', 'simplex'):
        result = run_experiment(preset_config(name))
        text = render_experiment(result, 'html')
        smoke.validate_html(text, result, experiment=True)
        result['runs'][0]['rows'][-1]['gap'] += 1
        with pytest.raises(RuntimeError):
            smoke.validate_html(text, result, experiment=True)
