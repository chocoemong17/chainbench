'use strict';
(() => {
  const root = document.documentElement;
  const $ = id => document.getElementById(id);
  let cases = [], current = null, traces = {}, k = 0, timer = null;
  const copy = {
    en: { play: 'Watch 30 seconds', pause: 'Pause', start: '01 / SAME START', move: '02 / FOLLOW THE STEP', memory: '03 / ADD MEMORY', compare: '04 / COMPARE THE GAP',
      captions: ['Both methods start at the same point. Press Play or drag the iteration slider.', 'The gradient points uphill. Each method subtracts a scaled gradient; the curves trace their computed points.', 'Smooth FISTA uses an extrapolated point that remembers the previous move. Watch how its path differs.', 'Compare the actual objective gaps below the plot. A smaller gap here is an observation, not a promise for every problem.'],
      contour: 'Each contour joins points with the same objective.', cases: ['Gentle valley', 'Narrow valley', 'Rotated valley'], error: 'The experiment could not load. Reload the page or open a paper report below.' },
    ko: { play: '30초로 살펴보기', pause: '일시정지', start: '01 / 같은 출발점', move: '02 / 이동 따라가기', memory: '03 / 이전 이동 활용', compare: '04 / 오차 비교',
      captions: ['두 방법은 같은 점에서 출발합니다. 재생하거나 반복 횟수 슬라이더를 끌어 보세요.', '기울기는 올라가는 방향입니다. 각 방법은 보폭을 곱한 기울기를 빼며, 선은 실제로 계산한 점들을 잇습니다.', 'Smooth FISTA는 이전 이동을 활용한 외삽점에서 시작합니다. 두 경로가 어떻게 달라지는지 보세요.', '그림 아래 실제 목적함수 오차를 비교하세요. 여기서 더 작은 오차가 모든 문제에서의 우위를 보장하지는 않습니다.'],
      contour: '각 등고선은 목적함숫값이 같은 점들을 잇습니다.', cases: ['완만한 골짜기', '좁은 골짜기', '회전한 골짜기'], error: '실험을 불러오지 못했습니다. 새로고침하거나 아래 논문 보고서를 열어 주세요.' }
  };
  const language = () => copy[root.lang] || copy.en;
  try {
    const requested = new URL(location.href).searchParams.get('lang');
    const saved = localStorage.getItem('chainbench-language');
    root.lang = ['en', 'ko'].includes(requested) ? requested : ['en', 'ko'].includes(saved) ? saved : 'en';
  } catch (_) { root.lang = 'en'; }
  function translate() {
    const c = language();
    $('language').textContent = root.lang === 'en' ? '한국어' : 'English';
    $('language').setAttribute('aria-label', root.lang === 'en' ? 'Switch language to Korean' : '영어로 전환');
    $('play-label').textContent = timer ? c.pause : c.play;
    $('plot-caption').textContent = c.contour;
    [...$('case').options].forEach((option, i) => { option.textContent = c.cases[i]; });
    $('iteration').setAttribute('aria-label', root.lang === 'en' ? 'Iteration k' : '반복 횟수 k');
    document.querySelector('.skip').textContent = root.lang === 'en' ? 'Skip to the experiment' : '실험으로 바로 가기';
    $('landscape').setAttribute('aria-label', root.lang === 'en' ? 'Contour plot with gradient descent and accelerated paths' : '경사하강법과 가속 경로를 나타낸 등고선');
    if (current) draw();
  }
  $('language').addEventListener('click', () => {
    root.lang = root.lang === 'en' ? 'ko' : 'en';
    try { localStorage.setItem('chainbench-language', root.lang); } catch (_) { /* Optional. */ }
    translate();
  });
  // Each update uses the declared quadratic, with no interpolation of solver steps.
  function solve(problem, steps) {
    const Q = problem.Q, star = problem.x_star, L = problem.L;
    const grad = x => Q.map(row => row[0] * (x[0] - star[0]) + row[1] * (x[1] - star[1]));
    const gap = x => { const g = grad(x); return .5 * ((x[0] - star[0]) * g[0] + (x[1] - star[1]) * g[1]); };
    const result = {};
    for (const method of ['gd', 'smooth-fista']) {
      let x = [...problem.start], y = [...x], t = 1;
      const points = [[...x]], gaps = [gap(x)];
      for (let i = 0; i < steps; i++) {
        const base = method === 'gd' ? x : y, g = grad(base);
        const next = base.map((v, j) => v - g[j] / L);
        const nextT = (1 + Math.sqrt(1 + 4 * t * t)) / 2;
        y = next.map((v, j) => v + (t - 1) / nextT * (v - x[j]));
        x = next; t = nextT; points.push([...x]); gaps.push(gap(x));
      }
      result[method] = { points, gaps };
    }
    return result;
  }
  const xy = p => [310 + p[0] * 82, 224 - p[1] * 70];
  function contours() {
    const group = $('contours'), p = current.problem;
    group.replaceChildren();
    const theta = p.angle_degrees * Math.PI / 180, c = Math.cos(theta), s = Math.sin(theta);
    for (const level of [.006, .024, .075, .18, .38, .7, 1.2, 1.9, 2.8, 4.2]) {
      const points = [];
      for (let j = 0; j <= 160; j++) {
        const angle = 2 * Math.PI * j / 160;
        const a = Math.sqrt(2 * level * p.condition_number) * Math.cos(angle), b = Math.sqrt(2 * level) * Math.sin(angle);
        points.push(xy([p.x_star[0] + c * a - s * b, p.x_star[1] + s * a + c * b]));
      }
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', 'M' + points.map(v => v.join(',')).join('L') + 'Z');
      path.setAttribute('fill', 'none'); path.setAttribute('stroke', '#4d7b75'); path.setAttribute('stroke-opacity', '.65'); path.setAttribute('stroke-width', '1');
      group.append(path);
    }
    const optimum = xy(p.x_star), start = xy(p.start);
    $('optimum').setAttribute('transform', `translate(${optimum[0]} ${optimum[1]})`);
    $('start-point').setAttribute('cx', start[0]); $('start-point').setAttribute('cy', start[1]);
  }
  function draw() {
    for (const [method, prefix] of [['gd', 'gd'], ['smooth-fista', 'fista']]) {
      const run = traces[method], points = run.points.slice(0, k + 1).map(xy), last = points[points.length - 1];
      $(prefix + '-path').setAttribute('d', 'M' + points.map(v => v.join(',')).join('L'));
      $(prefix + '-dot').setAttribute('cx', last[0]); $(prefix + '-dot').setAttribute('cy', last[1]);
      $(prefix + '-gap').textContent = run.gaps[k].toExponential(3);
    }
    $('iteration').value = String(k); $('iteration-label').textContent = `${k} / ${current.steps}`;
    const chapter = k === 0 ? 0 : k <= 12 ? 1 : k <= 40 ? 2 : 3, c = language();
    $('chapter').textContent = [c.start, c.move, c.memory, c.compare][chapter];
    $('narration').textContent = c.captions[chapter];
    // Read-only evidence interface used by the independent browser comparison.
    window.chainbenchExplorer = { caseIndex: Number($('case').value), k, traces, problem: current.problem };
  }
  function stop() {
    clearInterval(timer); timer = null; $('play').setAttribute('aria-pressed', 'false');
    $('play-icon').textContent = '▶'; $('play-label').textContent = language().play;
  }
  function selectCase() {
    stop(); current = cases[Number($('case').value)]; k = 0;
    traces = solve(current.problem, current.steps); $('iteration').max = String(current.steps);
    contours(); draw();
  }
  $('case').addEventListener('change', selectCase);
  $('reset').addEventListener('click', selectCase);
  $('iteration').addEventListener('input', event => { stop(); k = Number(event.target.value); draw(); });
  $('play').addEventListener('click', () => {
    if (timer) { stop(); return; }
    if (k >= current.steps) { k = 0; draw(); }
    $('play').setAttribute('aria-pressed', 'true'); $('play-icon').textContent = 'Ⅱ'; $('play-label').textContent = language().pause;
    timer = setInterval(() => { k += 1; draw(); if (k >= current.steps) stop(); }, 500);
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
  window.addEventListener('pagehide', stop);
  translate();
  fetch('explorer-data.json').then(response => { if (!response.ok) throw new Error('Reference data unavailable'); return response.json(); }).then(data => {
    cases = data.cases;
    if (cases.length !== 3 || cases.some(c => c.steps !== 60)) throw new Error('Invalid example inventory');
    selectCase(); $('load-status').hidden = true;
    for (const id of ['case', 'reset', 'iteration', 'play']) $(id).disabled = false;
  }).catch(() => { $('load-status').textContent = language().error; $('load-status').setAttribute('role', 'alert'); });
})();
