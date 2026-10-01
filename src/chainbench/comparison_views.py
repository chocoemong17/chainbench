"""Offline reading of supplied experiment records and their differences."""
from __future__ import annotations

import json
from html import escape

from ._pages import bi, evidence, page
from .comparison import compare_experiments
from .experiments import canonical_json
from .visuals import ChartSpec, LineSeries, render_line_chart


def comparison_html(result: dict, lang: str = "en") -> str:
    expected = compare_experiments([r["experiment"] for r in result["records"]], metric=result["metric"])
    if canonical_json(result) != canonical_json(expected):
        raise ValueError("comparison diagnostics or charts disagree with supplied records")
    def pretty(value):
        return '<pre>' + escape(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)) + '</pre>'
    def yes(value):
        return bi('같음', 'same') if value else bi('다름', 'different')
    def plot(item):
        raw = item["chart"]
        chart = ChartSpec(raw["title"], raw["x_label"], raw["y_label"],
                          tuple(LineSeries(**s) for s in raw["series"]), raw["y_scale"])
        return ('<p class="comparison-scroll-hint small">' + bi('그래프를 가로로 스크롤하면 끝까지 볼 수 있습니다. 키보드로 영역을 선택한 뒤 방향키도 사용할 수 있습니다.', 'Scroll the chart horizontally to inspect its full width, or focus it and use the arrow keys.')
                + '</p><div class="plot" tabindex="0" role="region" aria-label="'
                + escape(raw['title'], quote=True) + '" data-comparison-chart="' + item["id"] + '">'
                + render_line_chart(chart) + '</div>')
    intro = bi('실제로 저장한 실험 2–4개를 나란히 읽습니다. 먼저 문제·입력·예산의 차이를 확인한 뒤 곡선을 비교하세요.',
               'Read two to four saved experiments together. Inspect problem, input and budget differences before comparing curves.')
    body = ('<style>.comparison-table{min-width:640px}.comparison-table th,.comparison-table td{white-space:nowrap}'
            '.comparison-scroll-hint{display:none}@media(max-width:760px){.comparison-scroll-hint{display:block}}'
            '@media print{.comparison-scroll-hint{display:none}}</style>'
            '<nav class="panel"><a href="#comparison-context">' + bi('무엇이 달라졌나', 'What changed?') + '</a>')
    for record in result["records"]:
        body += f'<a href="#record-{record["id"]}">' + bi('기록 ', 'Record ') + record["id"] + '</a>'
    body += '</nav><section id="comparison-context"><h2>' + bi('같은 문제를 비교하고 있나요?', 'Are these the same recorded problem?') + '</h2>'
    body += '<p class="callout caution">' + bi(
        '저장된 관측을 읽는 기능입니다. 알고리즘을 다시 실행하거나 입력 배열·작성자를 인증하지 않습니다. 같은 해시도 독립적인 재현을 입증하지 않으며, 같은 기록을 두 번 넣어도 새 증거가 되지 않습니다.',
        'These are supplied observations. No solver is rerun and no input arrays or authors are authenticated. Matching hashes do not establish independent reproduction; duplicate records add no evidence.') + '</p>'
    headings = [bi('기록 쌍', 'Pair'), bi('전체 설정', 'Full config'), bi('입력 해시', 'Input digest'),
                bi('문제·시작점', 'Problem and start'), bi('환경', 'Environment'), bi('원본 기록', 'Whole record')]
    body += '<p class="comparison-scroll-hint small">' + bi('표를 가로로 스크롤해 환경과 원본 기록의 차이까지 확인하세요. 영역을 선택한 뒤 방향키로도 이동할 수 있습니다.', 'Scroll the table horizontally to reach environment and whole-record differences. Focus the region to use the arrow keys.') + '</p>'
    body += '<div class="scroll" tabindex="0" role="region" aria-label="Record diagnostics"><table class="comparison-table"><thead><tr>'
    body += ''.join('<th scope="col">'+h+'</th>' for h in headings) + '</tr></thead><tbody>'
    for pair in result["pairs"]:
        body += f'<tr data-pair="{pair["left"]}-{pair["right"]}"><th scope="row">{pair["left"]} / {pair["right"]}</th>'
        body += ''.join('<td>'+yes(pair[key])+'</td>' for key in
                        ('same_config', 'same_input_digest', 'same_recorded_problem', 'same_environment', 'identical_record')) + '</tr>'
    body += '</tbody></table></div><details><summary>' + bi('차이가 나는 실제 필드 보기', 'Inspect the actual differing fields') + '</summary>' + pretty(result["pairs"]) + '</details></section>'
    body += '<section><h2>' + bi('공통 축에서 읽기', 'Read on shared axes') + '</h2>'
    body += '<p>' + bi('입력 해시·문제 설정·시작점·측정 정의가 모두 같은 경우에만 같은 방법의 기록을 겹쳐 보여 줍니다. 설정이나 종료 기준의 차이는 위 표와 각 기록에 남습니다.',
                      'Overlay the same method only when every record agrees on its input digest, problem setup, start and measurement definitions. Settings and stopping differences remain visible above and below.') + '</p>'
    shared = [item for item in result["charts"] if item["id"].startswith('shared-')]
    body += ''.join(plot(item) for item in shared) if shared else '<p class="callout">' + bi('겹쳐 그리지 않았습니다. 모든 기록의 문제 정보가 같지 않거나, 둘 이상의 기록에 공통으로 들어 있는 방법이 없습니다. 아래 패널에서 축 눈금을 확인하세요.', 'No overlay: recorded problems differ, or no method appears in at least two records. Read the separate panels and their tick values below.') + '</p>'
    body += '<p class="small">' + bi('종료 이후의 점을 늘리거나 보간하지 않습니다. k는 계산 시간이 아닌 기록된 반복 번호입니다. 0은 로그축 바닥의 삼각형으로 표시합니다.', 'No samples are extended or interpolated after termination. k is recorded iteration, not elapsed time. Zero values appear as triangles at the log-axis baseline.') + '</p></section>'
    body += '<p class="callout caution">' + bi('아래 패널의 y축 범위는 각각 다릅니다. 문제·목적함수의 척도가 다르면 마지막 값이나 선의 기울기만으로 우열을 정할 수 없습니다.', 'The panels below have independent y ranges. When problems or objective scales differ, final values and apparent slopes cannot determine a ranking.') + '</p>'
    for record in result["records"]:
        ident, exp = record["id"], record["experiment"]
        f, config = exp["fixture"], exp["config"]
        body += f'<section id="record-{ident}" data-record="{ident}"><h2>' + bi('기록 ', 'Record ') + ident + '</h2>'
        body += f'<p>{escape(f["kind"])} · dimension {f["dimension"]} · budget {config["steps"]} · start {escape(f["start"])}</p>'
        body += '<p class="small">' + bi('기록 SHA-256', 'Record SHA-256') + ': <code>' + record["record_sha256"] + '</code></p>'
        body += plot(next(c for c in result["charts"] if c["id"] == 'record-'+ident))
        body += '<div class="scroll" tabindex="0" role="region" aria-label="Recorded method endpoints"><table><thead><tr><th scope="col">Method</th><th scope="col">Updates</th><th scope="col">Termination</th><th scope="col">' + escape(result["metric"]) + '</th></tr></thead><tbody>'
        for run in exp["runs"]:
            body += f'<tr><th scope="row">{escape(run["method"])}</th><td>{run["updates"]}</td><td>{escape(run["termination"])}</td><td>{run["rows"][-1][result["metric"]]:.8g}</td></tr>'
        body += '</tbody></table></div><p class="small">' + bi('budget_complete는 요청한 갱신을 마쳤다는 뜻이며 수렴 인증이 아닙니다.', 'budget_complete means the requested updates ran; it does not certify convergence.') + '</p>'
        body += '<details><summary>' + bi('문제·설정·환경·방법 매개변수', 'Problem, settings, environment and method parameters') + '</summary>'
        body += pretty({"fixture": f, "config": config, "environment": exp["environment"],
                        "parameters": {r["method"]: r["parameters"] for r in exp["runs"]}}) + '</details></section>'
    body += evidence(result, 'comparison.json')
    return page('Saved experiments · compare the context', intro, body, lang=lang)
