"""Offline presentation shell shared by learning and controlled experiments."""
from __future__ import annotations

import json
from html import escape

from . import __version__

CSS = """
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif;background:#f3f1ec;
color:#172238;line-height:1.68;--ink:#172238;--muted:#64748b;--navy:#13233f;--blue:#2864d7;
--cream:#fbfaf7;--line:#ded9cf;--orange:#d97706;--green:#0f766e}*{box-sizing:border-box}
html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 8% 0,#fff 0,#f3f1ec 38%,#eef1f5 100%)}
a{color:#235bbd;text-underline-offset:3px}main{max-width:1320px;margin:auto;padding:30px 28px 80px}
header{position:relative;overflow:hidden;border-radius:28px;background:linear-gradient(135deg,#101f39,#1b355b 65%,#244c79);
color:#fff;padding:44px 48px;margin-bottom:28px;box-shadow:0 24px 60px #0f172a20}header:after{content:'';position:absolute;
width:360px;height:360px;border-radius:50%;right:-120px;top:-170px;background:#ffffff0d}h1,h2{font-family:Georgia,'Times New Roman',serif;
letter-spacing:-.018em}h1{font-size:clamp(34px,5vw,58px);line-height:1.06;margin:8px 0 18px;max-width:980px}
h2{font-size:30px;line-height:1.2;margin:0 0 14px}h3{font-size:17px;margin:0 0 8px}p{margin:8px 0 15px}.eyebrow{
font-size:11px;text-transform:uppercase;letter-spacing:.16em;font-weight:800;color:#8fa9cb}header a{color:#e7f0ff}
.controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:16px 0}button,input,select{font:inherit;padding:10px 14px;
border-radius:11px;border:1px solid #c6ceda;background:#fff;color:#18304f}button{cursor:pointer;font-weight:650}button:hover{background:#edf3fc}
button:focus-visible,a:focus-visible,summary:focus-visible,input:focus-visible{outline:3px solid #ef9f47;outline-offset:3px}
section,.panel{min-width:0;background:#fff;border:1px solid var(--line);border-radius:22px;padding:28px;margin:22px 0;scroll-margin-top:22px;
box-shadow:0 8px 32px #18253c0b}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px;margin:22px 0}
.card{position:relative;background:linear-gradient(180deg,#fff,#fbfcff);border:1px solid #dce2ea;border-radius:19px;padding:20px;text-decoration:none;color:var(--ink);
min-width:0;display:flex;flex-direction:column;gap:8px;box-shadow:0 7px 22px #1722380a}.card:before{content:'';height:4px;border-radius:8px;
background:linear-gradient(90deg,#245fc8,#7c3aed,#0f766e);position:absolute;left:18px;right:18px;top:0}.card img{width:100%;height:auto;margin-top:auto;border-radius:12px}
.card:hover{border-color:#82a8ea;box-shadow:0 13px 34px #17223816;transform:translateY(-1px)}.pairs,.deep-grid,.visual-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.deep-grid{grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}.deep-grid article{padding:17px;border-radius:15px;background:#f8fafc;border:1px solid #e6eaf0}
.visual-grid{align-items:start}.callout{padding:15px 18px;border-radius:14px;background:#edf4ff;border-left:5px solid #4b76c5}.caution{background:#fff5e5;border-left-color:#d99a35}
.badge{border-radius:999px;padding:4px 10px;background:#eef2fa;font-size:11px;font-weight:750;display:inline-block}.evidence-banner{padding:18px 20px;border-radius:17px;
background:linear-gradient(90deg,#ecfdf5,#eff6ff);border:1px solid #cfe8df;margin:18px 0}.evidence-tag{display:inline-block;margin-right:10px;padding:5px 10px;border-radius:999px;
font-size:11px;font-weight:800;letter-spacing:.08em;background:#0f766e;color:#fff}.evidence-ladder{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:18px 0}.evidence-step{
padding:14px;border-radius:14px;background:#fff;border:1px solid #d9e1ea}.evidence-step strong{display:block;font-size:13px}.evidence-step span{font-size:12px;color:#64748b}
.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}.metric{padding:16px;border-radius:15px;background:#172238;color:#fff}.metric span{display:block;
font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#aec1df}.metric strong{font-family:Georgia,serif;font-size:28px}.small{font-size:13px;color:#56657b}.formula{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:15px;padding:18px;background:#f0f3f7;border-radius:12px;overflow-wrap:anywhere;white-space:pre-wrap;border:1px solid #e1e6ed}
.plot{overflow-x:auto;margin:14px 0}.plot svg{width:100%;min-width:580px;height:auto;display:block;border-radius:14px}summary{font-weight:700;cursor:pointer;padding:10px 0}
pre{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f4f8;border-radius:12px;padding:16px}code{overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:10px;border-bottom:1px solid #e1e7ef;text-align:left;vertical-align:top}th{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:#637087}.scroll{overflow:auto}
nav a{display:inline-block;padding:6px 10px}footer{font-size:12px;color:#66768f;margin-top:34px}.pill{padding:5px 10px;border-radius:20px;background:#e6edfa;display:inline-block}.timeline{display:grid;
grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:18px 0}.timeline div{padding:12px 14px;border-radius:13px;background:#fff;border-top:3px solid #2864d7}.timeline strong{display:block;font-size:13px}.timeline span{font-size:12px;color:#667085}.trajectory-player{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:14px 16px;border-radius:16px;background:#101f39;color:white;margin:18px 0}.trajectory-player button{width:44px;height:40px;padding:0;border:0;background:#fff;color:#13233f;border-radius:999px}.trajectory-player input[type=range]{flex:1;min-width:220px;padding:0;border:0;background:transparent}.trajectory-player strong{min-width:56px;font-variant-numeric:tabular-nums}
html[lang='ko'] [lang='en'],html[lang='en'] [lang='ko']{display:none}[hidden]{display:none!important}@media(max-width:760px){main{padding:15px 12px 44px}header{padding:26px 22px}.pairs,.visual-grid{grid-template-columns:1fr}
section,.panel{padding:18px}.cards{grid-template-columns:1fr}h2{font-size:25px}.evidence-ladder{grid-template-columns:1fr 1fr}.plot svg{min-width:640px}}@media(max-width:480px){.evidence-ladder{grid-template-columns:1fr}}
@media print{button,input,nav,.controls{display:none}body{background:#fff}header{background:white;color:black;box-shadow:none;border:1px solid #ddd}.cards{display:none}section{break-inside:avoid}.plot svg{min-width:0}.evidence-ladder{grid-template-columns:repeat(2,1fr)}details>*{display:block}}
"""

SCRIPT = """
'use strict';
const root = document.documentElement;
document.querySelectorAll('[data-action="language"]').forEach(b => b.addEventListener('click', () => {
 root.lang = root.lang === 'ko' ? 'en' : 'ko';
}));
const filter = document.getElementById('lesson-filter');
if(filter) filter.addEventListener('input', () => {
 const query = filter.value.toLowerCase().trim();
 document.querySelectorAll('[data-search]').forEach(el => {
  el.hidden = !el.dataset.search.toLowerCase().includes(query);
 });
});
document.querySelectorAll('[data-download]').forEach(button => {
 button.addEventListener('click', () => {
  const pre = document.getElementById(button.dataset.download);
  if(!pre) return;
  const url = URL.createObjectURL(new Blob([pre.textContent], {type:'application/json'}));
  const a = document.createElement('a'); a.href = url; a.download = button.dataset.filename;
  a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
 });
});
document.querySelectorAll('[data-trajectory-player]').forEach(player => {
 const slider = player.querySelector('[data-trajectory-slider]');
 const label = player.querySelector('[data-trajectory-label]');
 const play = player.querySelector('[data-trajectory-play]');
 if(!slider || !label || !play) return;
 const lines = Array.from(document.querySelectorAll('[data-trajectory-line]'));
 const markers = Array.from(document.querySelectorAll('[data-trajectory-marker]'));
 const parse = el => el.dataset.trajectoryPoints.split('|').map(pair => pair.split(',').map(Number));
 const linePoints = new Map(lines.map(el => [el, parse(el)]));
 const markerPoints = new Map(markers.map(el => [el, parse(el)]));
 let timer = null;
 const update = () => {
  const step = Number(slider.value);
  label.textContent = `k = ${step}`;
  linePoints.forEach((points, el) => {
   const index = Math.min(step, points.length - 1);
   el.setAttribute('points', points.slice(0, index + 1).map(p => `${p[0]},${p[1]}`).join(' '));
  });
  markerPoints.forEach((points, el) => {
   const index = Math.min(step, points.length - 1);
   el.setAttribute('cx', points[index][0]); el.setAttribute('cy', points[index][1]);
  });
 };
 const stop = () => { if(timer) clearInterval(timer); timer = null; play.textContent = '▶'; };
 slider.addEventListener('input', () => { stop(); update(); });
 play.addEventListener('click', () => {
  if(timer){ stop(); return; }
  if(Number(slider.value) >= Number(slider.max)) slider.value = '0';
  play.textContent = '❚❚'; update();
  timer = setInterval(() => {
   const next = Number(slider.value) + 1;
   if(next > Number(slider.max)){ stop(); return; }
   slider.value = String(next); update();
  }, 520);
 });
 update();
});
"""


def bi(ko: str, en: str) -> str:
    """No HTML is accepted from copy or reports."""
    return f'<span lang="ko">{escape(ko)}</span><span lang="en">{escape(en)}</span>'


def evidence(data: dict, filename: str = "chainbench-evidence.json") -> str:
    text = escape(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False))
    return ('<details class="panel"><summary>' + bi('원본 수치·설정·환경 확인', 'Exact samples, settings and environment')
            + '</summary><button type="button" data-download="chainbench-evidence" data-filename="'
            + escape(filename, quote=True) + '">' + bi('JSON 저장', 'Save JSON')
            + '</button><pre id="chainbench-evidence">' + text + '</pre></details>')


def page(title: str, subtitle: str, body: str, *, lang: str = "en") -> str:
    if lang not in ("en", "ko"):
        raise ValueError("lang must be en or ko")
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="referrer" content="no-referrer">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            'img-src data:; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; '
            'connect-src \'none\'; base-uri \'none\'; form-action \'none\'">'
            f'<title>ChainBench · {escape(title)}</title><style>{CSS}</style></head><body><main>'
            '<header><div class="eyebrow">CHAINBENCH / LEARN · EXPERIMENT · AUDIT</div>'
            f'<h1>{escape(title)}</h1><p>{subtitle}</p>'
            f'<div class="controls"><span>v{__version__} · local &amp; offline</span>'
            '<button type="button" data-action="language">한국어 / English</button></div></header>'
            f'{body}<footer>{bi("실행 결과는 유한한 수치 관측입니다. 정리의 증명이나 실제 사용자 수를 뜻하지 않습니다.", "Finite numerical observations are not theorem proofs or evidence of adoption.")}'
            '</footer></main><script>' + SCRIPT + '</script></body></html>')
