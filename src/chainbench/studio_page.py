"""Small bilingual controls; results are the existing standalone numeric reports."""
from __future__ import annotations

from ._pages import CSS, SCRIPT, bi
from .experiments import METHODS

CSP = ("default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
       "img-src data:; connect-src 'self'; frame-src 'self' blob:; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

STUDIO_SCRIPT = """
(() => {
 'use strict';
 const $=id=>document.getElementById(id),form=$('studio-form'),result=$('studio-result');
 const token=location.hash.slice(1);history.replaceState(null,'',location.pathname);
 let urls=[],busy=false,stopped=false;
 const say=(ko,en)=>{$('studio-status').textContent=document.documentElement.lang==='ko'?ko:en;};
 const clear=()=>{urls.forEach(URL.revokeObjectURL);urls=[];result.hidden=true;$('studio-frame').removeAttribute('srcdoc');};
 function controls(){
   const family=$('family').value;
   document.querySelectorAll('[data-family]').forEach(el=>{
     el.hidden=el.dataset.family!==family;
     el.querySelectorAll('input').forEach(input=>{input.disabled=el.hidden;});
   });
   clear();
 }
 const request=()=>{
   const family=$('family').value;
   const value={family,dimension:Number($('dimension').value),seed:Number($('seed').value),
     steps:Number($('steps').value),lang:document.documentElement.lang,
     methods:Array.from(form.querySelectorAll('input[name="method"]:checked:not(:disabled)')).map(el=>el.value)};
   if(family==='quadratic'){value.L=Number($('L').value);value.condition_number=Number($('condition-number').value);}
   if(family==='diagonal-lasso')value.lam=Number($('lam').value);
   return value;
 };
 async function post(path,value){
   const response=await fetch(path,{method:'POST',credentials:'omit',redirect:'error',cache:'no-store',
      headers:{'Content-Type':'application/json','X-ChainBench-Token':token},body:JSON.stringify(value)});
   const data=await response.json();if(!response.ok)throw new Error(data.error||'Request failed');return data;
 }
 function download(id,name,text,type){
   const url=URL.createObjectURL(new Blob([text],{type}));urls.push(url);
   $(id).href=url;$(id).download=name;
 }
 form.addEventListener('input',clear);$('family').addEventListener('change',controls);
 form.addEventListener('submit',async event=>{
   event.preventDefault();if(busy||stopped||!token)return;
   const value=request();if(!value.methods.length){say('방법을 하나 이상 선택하세요.','Select at least one method.');return;}
   busy=true;clear();$('run').disabled=true;$('stop').disabled=true;
   form.querySelectorAll('input,select').forEach(el=>{el.disabled=true;});
   form.setAttribute('aria-busy','true');say('선택한 조건으로 계산하고 있습니다…','Computing the selected experiment…');
   try{
     const data=await post('/api/run',value),record=data.result;
     $('studio-settings').textContent=JSON.stringify(data.request,null,2);
     $('studio-summary').textContent=record.fixture.kind+' · d='+record.fixture.dimension+' · '
       +record.runs.map(r=>r.method+': '+r.updates).join(' / ');
     $('studio-hash').textContent=record.instance.input_sha256;
     download('download-input','studio-input.json',JSON.stringify(record.instance,null,2),'application/json');
     download('download-result','studio-result.json',JSON.stringify(record,null,2),'application/json');
     download('download-html','studio-report.html',data.html,'text/html');
     $('studio-frame').srcdoc=data.html;result.hidden=false;
     say('계산 완료. 아래 결과는 표시된 입력과 설정에서 나온 실제 기록입니다.',
         'Complete. The report contains actual observations for the displayed inputs and settings.');
   }catch(error){say('계산하지 못했습니다: '+error.message,'Calculation failed: '+error.message);}
   finally{busy=false;$('run').disabled=stopped;$('stop').disabled=stopped;form.setAttribute('aria-busy','false');
     form.querySelectorAll('input,select').forEach(el=>{const group=el.closest('[data-family]');el.disabled=!!group&&group.hidden;});}
 });
 $('stop').addEventListener('click',async()=>{
   if(busy||stopped||!token)return;
   try{await post('/api/shutdown',{});stopped=true;$('run').disabled=true;$('stop').disabled=true;
       say('서버를 종료했습니다. 지금 표시된 결과는 계속 읽거나 내려받을 수 있습니다.',
           'The server is stopped. You can still read and download the current result.');}
   catch(error){say('연결할 수 없습니다. 터미널에서 종료 상태를 확인하세요.',
                   'Cannot reach the server. Check its status in your terminal.');}
 });
 controls();
 if(!token){$('run').disabled=true;$('stop').disabled=true;
   say('터미널에 표시된 전체 주소를 다시 여세요. 새로고침하면 세션 키가 사라집니다.',
       'Open the full URL printed in your terminal. Refreshing clears the session key.');}
 else{$('run').disabled=false;$('stop').disabled=false;
   say('조건을 고른 다음 계산하기를 누르세요.','Choose the settings, then run the experiment.');}
})();
"""


def studio_html(lang='en'):
    def label(id, ko, en, control):
        return '<label for="'+id+'">'+bi(ko,en)+control+'</label>'
    def number(id, default, lower, upper, step='1'):
        return f'<input id="{id}" type="number" value="{default}" min="{lower}" max="{upper}" step="{step}" required>'
    body = '<section><h2>'+bi('1. 실험 조건 고르기','1. Choose an experiment')+'</h2>'
    body += '<form id="studio-form"><div class="studio-grid">'
    body += label('family','문제군','Problem family','<select id="family"><option value="quadratic">Quadratic · 이차함수</option>'
                  '<option value="diagonal-lasso">Diagonal LASSO · 희소성</option><option value="simplex">Simplex · 확률 단체</option></select>')
    body += label('dimension','차원','Dimension',number('dimension',6,2,16))
    body += label('seed','입력 시드','Input seed',number('seed',0,0,2**32-1))
    body += label('steps','업데이트 수','Updates',number('steps',30,0,200))+'</div>'
    body += '<div class="studio-grid" data-family="quadratic">'
    body += label('L','최대 고유값 L','Largest eigenvalue L',number('L',1,.001,1000,'any'))
    body += label('condition-number','조건수 L/μ','Condition number L/μ',number('condition-number',10,1,10000,'any'))+'</div>'
    body += '<div class="studio-grid" data-family="diagonal-lasso" hidden>'
    body += label('lam','희소성 가중치 λ','Sparsity weight λ',number('lam',.12,0,10,'any'))+'</div>'
    for family, methods in METHODS.items():
        body += '<fieldset data-family="'+family+'"'+(' hidden' if family!='quadratic' else '')+'><legend>'+bi('계산할 방법','Methods to run')+'</legend>'
        body += ''.join('<label class="method"><input type="checkbox" name="method" value="'+m+'" checked> '+m+'</label>' for m in methods)+'</fieldset>'
    body += '<p class="small">'+bi('시드를 바꾸면 행렬·벡터·시작점이 달라집니다. 시드를 고정하고 조건수 또는 λ를 바꾸어 결과를 관찰하세요. 동일한 업데이트 수가 동일한 연산량을 뜻하지는 않습니다.',
        'Changing the seed changes the arrays and starting point. Keep it fixed while varying the condition number or λ. Equal update counts are not equal computational work.')+'</p>'
    body += '<div class="controls"><button id="run" type="submit" disabled>'+bi('새로 계산하기','Run a new experiment')+'</button>'
    body += '<button id="stop" type="button" disabled>'+bi('서버 종료','Stop server')+'</button></div></form>'
    body += '<p id="studio-status" role="status" aria-live="polite">'+bi('JavaScript를 켜면 새 실험을 계산할 수 있습니다. 저장한 HTML은 서버 없이 읽을 수 있습니다.',
        'Enable JavaScript to compute a new experiment. Downloaded HTML can be read without this server.')+'</p></section>'
    body += '<section id="studio-result" hidden><h2>'+bi('2. 실제 결과 읽고 저장하기','2. Read and save the result')+'</h2>'
    body += '<p id="studio-summary"></p><p class="small">input SHA-256: <code id="studio-hash"></code></p>'
    body += '<div class="controls"><a id="download-input">'+bi('입력 JSON','Input JSON')+'</a><a id="download-result">'+bi('결과 JSON','Result JSON')+'</a>'
    body += '<a id="download-html">'+bi('독립 HTML 보고서','Standalone HTML report')+'</a></div>'
    body += '<details><summary>'+bi('이 결과의 계산 조건','Settings used for this result')+'</summary><pre id="studio-settings"></pre></details>'
    body += '<p class="small">'+bi('아래 보고서에서 방법과 업데이트를 선택하세요. 전체 화면으로 읽으려면 HTML을 저장해 여세요.',
        'Choose a method and update inside the report. Save the HTML and open it to read at full size.')+'</p>'
    body += '<iframe id="studio-frame" title="Computed numeric experiment / 계산된 수치 실험" sandbox="allow-scripts allow-downloads"></iframe></section>'
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>ChainBench · Experiment studio</title>'
        '<style>'+CSS+'''
        .studio-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px;margin:18px 0}
        .studio-grid label{display:grid;gap:6px}.studio-grid input,.studio-grid select{width:100%;min-width:0}
        fieldset{border:1px solid #dce2ea;border-radius:14px;padding:16px}.method{display:inline-flex;align-items:center;gap:7px;margin:5px 16px 5px 0}
        #run{background:#235bbd;color:white}button:disabled{opacity:.55;cursor:default}
        #studio-frame{width:100%;height:900px;border:1px solid #dce2ea;border-radius:14px;background:white}
        select:focus-visible,iframe:focus-visible{outline:3px solid #ef9f47;outline-offset:3px}
        @media(max-width:480px){.studio-grid{grid-template-columns:1fr}#studio-frame{height:1050px}}
        </style></head><body><main><header><div class="eyebrow">CHAINBENCH / CHOOSE · COMPUTE · UNDERSTAND</div>
        <h1>Experiment studio</h1><p>'''+bi('조건을 바꾸고, 직접 계산하고, 알고리즘의 움직임을 읽으세요.',
        'Change the conditions, compute the result and read how the algorithms move.')+'</p>'
        '<div class="controls"><button type="button" data-action="language">한국어 / English</button></div></header>'
        +body+'<footer>'+bi('이 컴퓨터에서만 실행하는 실험입니다. 결과는 내려받을 때 저장됩니다. 유한한 수치 관측은 정리의 증명이나 보편적인 방법 순위가 아닙니다.',
        'This experiment runs on this computer. Results are saved when you download them. Finite observations are not theorem proofs or a universal ranking.')
        +'</footer></main><script>'+SCRIPT+STUDIO_SCRIPT+'</script></body></html>')
