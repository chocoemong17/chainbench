"""Independent DOM audit of stored three-round blocks (no view imports)."""
import math
import re

CYCLE_SNAPSHOT = r"""()=>[...document.querySelectorAll('#cycle-inspector [data-adam-cycle-method]')].map(p=>({
 method:p.dataset.adamCycleMethod,
 summary:[...p.querySelectorAll('dl [data-cycle-value]')].map(n=>[n.dataset.cycleValue,n.textContent,n.dataset.raw]),
 rows:[...p.querySelectorAll('[data-cycle-row]')].filter(r=>!r.hidden).map(r=>({
  round:Number(r.querySelector('[data-cycle-round]').textContent),
  values:[...r.querySelectorAll('[data-cycle-value]')].map(n=>[n.dataset.cycleValue,n.textContent,n.dataset.raw])})),
 steps:[...p.querySelectorAll('[data-cycle-step]')].filter(g=>getComputedStyle(g).display!=='none').map(g=>({
  round:g.querySelector('[data-cycle-round]').textContent,
  move:g.querySelector('[data-cycle-move]').getAttribute('d'),clip:g.querySelector('[data-cycle-clip]').getAttribute('d'),
  markers:[...g.querySelectorAll('[data-cycle-marker]')].map(n=>[n.dataset.cycleMarker,n.getAttribute('cx'),n.getAttribute('cy')])}))
}))"""


def _near(value, expected, atol):
    if not math.isfinite(float(value)) or not math.isclose(float(value),expected,abs_tol=atol,rel_tol=0):
        raise RuntimeError('Adam cycle coordinate differs')


def _values(actual, expected):
    if [v[0] for v in actual]!=list(expected):
        raise RuntimeError('Adam cycle readout coverage differs')
    for key,text,raw in actual:
        value = expected[key]
        if value is None:
            if raw!='null' or text!='not applicable / 해당 없음':
                raise RuntimeError('Adam cycle invented a complete-block value')
        elif float(raw)!=value or not math.isfinite(float(text)) or not math.isclose(float(text),value,rel_tol=5.1e-9,abs_tol=0):
            raise RuntimeError('Adam cycle displayed value differs')


def validate_cycle(case, t, snapshot):
    start = ((t-1)//3)*3
    stop = min(start+3,case['inputs']['steps'])
    if [p['method'] for p in snapshot]!=['adam','amsgrad']:
        raise RuntimeError('Adam cycle method coverage differs')
    for panel in snapshot:
        method = panel['method']
        s = case['runs'][method]['series']
        # Independently aggregate raw per-round regrets; do not trust the
        # precomputed complete_cycles metadata or any rendering helper.
        complete = stop-start==3
        _values(panel['summary'],dict(start_x=s['x'][start],end_x=s['x'][stop],
            regret=math.fsum(s['regret_increment'][start:stop]) if complete else None,
            source_lower=2*case['inputs']['C']-4 if complete and method=='adam' else None))
        if [r['round'] for r in panel['rows']]!=list(range(start+1,stop+1)) or len(panel['steps'])!=stop-start:
            raise RuntimeError('Adam cycle invented or omitted a round')
        for offset,(row,stage) in enumerate(zip(panel['rows'],panel['steps'])):
            j = start+offset
            _values(row['values'],dict(gradient=case['gradients'][j],memory=s['denominator_memory'][j],
                effective_rate=s['effective_rate'][j],displacement=s['displacement'][j],
                projection=s['projection_correction'][j],regret_increment=s['regret_increment'][j]))
            if stage['round']!=f't={j+1}' or [m[0] for m in stage['markers']]!=['before','proposal','after']:
                raise RuntimeError('Adam cycle marker or round coverage differs')
            positions = dict(before=s['x'][j],proposal=s['proposal'][j],after=s['x'][j+1])
            y = 76+64*offset
            for (key,x,actual_y),dy in zip(stage['markers'],(-6,0,6)):
                _near(x,85+155*(positions[key]+2),.00000051)
                _near(actual_y,y+dy,0)
            for name,left,yy in (('move','before',y),('clip','proposal',y+12)):
                match = re.fullmatch(r'M([-\d.]+) (\d+) H([-\d.]+)',stage[name])
                if match is None:
                    raise RuntimeError('Adam cycle malformed segment')
                _near(match[1],85+155*(positions[left]+2),.00000051)
                _near(match[2],yy,0)
                _near(match[3],85+155*(positions['after']+2),.00000051)
