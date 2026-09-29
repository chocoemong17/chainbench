"""Offline presentation shell shared by learning and controlled experiments."""
from __future__ import annotations

import json
from html import escape

from . import __version__

CSS = """
:root{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:#f4f6fa;color:#172238;
line-height:1.65}*{box-sizing:border-box}body{margin:0}a{color:#215ac5;text-underline-offset:3px}
main{max-width:1260px;margin:auto;padding:26px 24px 60px}header{border-radius:22px;background:#162844;
color:#fff;padding:32px;margin-bottom:22px}h1{font-size:clamp(28px,4vw,44px);line-height:1.2;margin:8px 0 16px}
h2{font-size:24px;line-height:1.3;margin:0 0 14px}h3{font-size:17px;margin:0 0 8px}
p{margin:8px 0 14px}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.12em}
header a{color:#d8e9ff}.controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:14px 0}
button,input,select{font:inherit;padding:9px 13px;border-radius:9px;border:1px solid #bbc7d8;
background:#fff;color:#1a3359}button{cursor:pointer}button:hover{background:#eaf1fb}button:focus-visible,
a:focus-visible,summary:focus-visible{outline:3px solid #ef8d32;outline-offset:3px}
section,.panel{min-width:0;background:#fff;border:1px solid #dfe5ef;border-radius:18px;padding:23px;
margin:18px 0;scroll-margin-top:20px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
gap:15px;margin:20px 0}.card{background:#fff;border:1px solid #dfe5ef;border-radius:15px;padding:17px;
text-decoration:none;color:#172238;min-width:0;display:flex;flex-direction:column;gap:6px}
.card img{width:100%;height:auto;margin-top:auto}.card:hover{border-color:#6596e9;box-shadow:0 6px 24px #17223816}
.pairs{display:grid;grid-template-columns:1fr 1fr;gap:18px}.callout{padding:13px 17px;border-radius:12px;
background:#f0f5ff;border-left:4px solid #5380c9}.caution{background:#fff5e5;border-left-color:#d99a35}
.badge{border-radius:7px;padding:3px 9px;background:#eef2fa;font-size:12px;display:inline-block}
.small{font-size:13px;color:#56657b}.formula{font-family:ui-monospace,monospace;font-size:16px;padding:17px;
background:#eef3fa;border-radius:10px;overflow-wrap:anywhere;white-space:pre-wrap}
.plot{overflow-x:auto;margin:12px 0}.plot svg{width:100%;min-width:580px;height:auto;display:block}
summary{font-weight:600;cursor:pointer;padding:9px 0}pre{font-size:12px;white-space:pre-wrap;
overflow-wrap:anywhere;background:#f1f4f8;border-radius:10px;padding:15px}code{overflow-wrap:anywhere}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:9px;border-bottom:1px solid #e1e7ef;
text-align:left}.scroll{overflow:auto}nav a{display:inline-block;padding:6px 10px}footer{font-size:12px;
color:#66768f;margin-top:30px}.pill{padding:5px 10px;border-radius:20px;background:#e6edfa;display:inline-block}
html[lang='ko'] [lang='en'],html[lang='en'] [lang='ko']{display:none}[hidden]{display:none!important}
@media(max-width:650px){main{padding:14px 12px 40px}header{padding:22px}.pairs{grid-template-columns:1fr}
section,.panel{padding:17px}.cards{grid-template-columns:1fr}h2{font-size:21px}}
@media print{button,input,nav,.controls{display:none}header{background:white;color:black}.cards{display:none}
section{break-inside:avoid}.plot svg{min-width:0}details> *{display:block}}
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
    # Inline scripts are project-owned; all report data are escaped text, never executable.
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
