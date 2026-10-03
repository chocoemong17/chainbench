'use strict';
(() => {
  const $ = id => document.getElementById(id), root = document.documentElement, movie = $('movie');
  let record = null, frame = null;
  const methods = ['gd', 'momentum', 'adam'];
  const colors = {gd:'#3e68a3', momentum:'#8e651f', adam:'#b83e31'};
  const labels = {gd:'GD', momentum:'Momentum', adam:'Adam'};
  const ns = 'http://www.w3.org/2000/svg';
  const charts = {};
  const node = (tag, attrs, text) => {const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;};
  const timeAt = k => k <= 60 ? 6 + k/6 : 16+(k-60)*24/2340;
  const iterationAt = t => t<=6 ? 0 : t<=16 ? Math.min(60,Math.floor((t-6)*6+1e-8)) : t<40 ? Math.min(2400,60+Math.floor((t-16)*2340/24+1e-8)) : 2400;
  const fmt = x => x===0?'0':x.toExponential(2).replace('e-0','e-').replace('e+0','e+');
  let requested = new URL(location.href).searchParams.get('lang'), saved;
  try {saved=localStorage.getItem('chainbench-language');} catch (_) { /* Storage is optional. */ }
  root.lang=['en','ko'].includes(requested)?requested:['en','ko'].includes(saved)?saved:'en';
  function translate() {
    const ko=root.lang==='ko';
    $('language').textContent=ko?'English':'한국어';
    $('language').setAttribute('aria-label',ko?'Switch to English':'한국어로 전환');
    $('iteration').setAttribute('aria-label',ko?'영상 위치':'Video position');
    document.querySelector('.skip').textContent=ko?'영상으로 바로 가기':'Skip to the film';
    for(const track of movie.textTracks)track.mode=track.language===root.lang?'showing':'disabled';
  }
  $('language').addEventListener('click',()=>{root.lang=root.lang==='en'?'ko':'en';try{localStorage.setItem('chainbench-language',root.lang);}catch(_){}translate();});
  translate(); movie.addEventListener('loadedmetadata',translate);
  document.querySelector('.watch-link').addEventListener('click',()=>{movie.play().catch(()=>{});});
  function buildChart(metric) {
    const svg=$(metric+'-chart'), left=56, top=18, width=480, height=232;
    const high=Math.ceil(Math.log10(Math.max(...methods.flatMap(m=>record.traces[m].rows.map(r=>r[metric])))));
    const low=-12, px=k=>left+k/2400*width;
    const py=v=>top+(high-Math.log10(Math.max(1e-12,v)))/(high-low)*height;
    for(let power=high;power>=low;power-=2){const y=py(10**power);svg.append(node('line',{x1:left,x2:left+width,y1:y,y2:y,class:'grid'}),node('text',{x:left-10,y:y+4,'text-anchor':'end'},'10'+({'-12':'⁻¹²','-11':'⁻¹¹','-10':'⁻¹⁰','-9':'⁻⁹','-8':'⁻⁸','-7':'⁻⁷','-6':'⁻⁶','-5':'⁻⁵','-4':'⁻⁴','-3':'⁻³','-2':'⁻²','-1':'⁻¹','0':'⁰','1':'¹','2':'²','3':'³'}[power]??'^'+power)));}
    for(const k of [0,600,1200,1800,2400])svg.append(node('text',{x:px(k),y:278,'text-anchor':'middle'},k.toLocaleString('en')));
    for(const m of methods){svg.append(node('path',{d:record.traces[m].rows.map((r,k)=>(k?'L':'M')+px(k).toFixed(2)+','+py(r[metric]).toFixed(2)).join(''),stroke:colors[m],class:'trace','data-method':m}));}
    const cursor=node('line',{x1:left,x2:left,y1:top,y2:top+height,class:'cursor'});svg.append(cursor);
    const dots=Object.fromEntries(methods.map(m=>{const e=node('circle',{cx:left,cy:py(record.traces[m].rows[0][metric]),r:4,fill:colors[m],stroke:'#f7f6f2','stroke-width':2});svg.append(e);return [m,e];}));
    $(metric+'-values').replaceChildren();
    for(const m of methods){const span=document.createElement('span');span.className=m;span.append(labels[m]);const b=document.createElement('b');b.id=metric+'-'+m;span.append(b);$(metric+'-values').append(span);}
    charts[metric]={cursor,dots,px,py};
    let dragging=false;
    const seekEvent=e=>{const rect=svg.getBoundingClientRect();seek(Math.round(((e.clientX-rect.left)/rect.width*560-left)/width*2400));};
    svg.addEventListener('pointerdown',e=>{dragging=true;svg.setPointerCapture(e.pointerId);seekEvent(e);});
    svg.addEventListener('pointermove',e=>{if(dragging)seekEvent(e);});
    svg.addEventListener('pointerup',()=>{dragging=false;});svg.addEventListener('pointercancel',()=>{dragging=false;});
  }
  function draw(k) {
    if(!record)return;
    k=Math.max(0,Math.min(2400,k));$('iteration-value').textContent=k.toLocaleString('en');$('iteration').setAttribute('aria-valuetext','k = '+k);
    for(const metric of ['loss','distance']){const c=charts[metric];c.cursor.setAttribute('x1',c.px(k));c.cursor.setAttribute('x2',c.px(k));for(const m of methods){const v=record.traces[m].rows[k][metric];c.dots[m].setAttribute('cx',c.px(k));c.dots[m].setAttribute('cy',c.py(v));$(metric+'-'+m).textContent=fmt(v);}}
    window.adamLesson={source:record.source,k,record,timeAt,iterationAt};
  }
  function frameAt(t){return Math.max(0,Math.min(record.frame_iterations.length-1,Math.floor(t*record.fps+1e-6)));}
  function syncAt(t){if(!record)return;const f=frameAt(t);$('iteration').value=String(f);draw(record.frame_iterations[f]);}
  function seekFrame(f){if(!record)return;f=Math.max(0,Math.min(record.frame_iterations.length-1,f));movie.pause();movie.currentTime=f/record.fps;syncAt(movie.currentTime);}
  function seek(k){seekFrame(Math.round(timeAt(Math.max(0,Math.min(2400,k)))*record.fps));}
  $('iteration').addEventListener('input',e=>seekFrame(Number(e.target.value)));
  const sync=()=>{syncAt(movie.currentTime);if(!movie.paused&&!movie.ended)frame=requestAnimationFrame(sync);};
  movie.addEventListener('play',()=>{cancelAnimationFrame(frame);sync();});
  movie.addEventListener('pause',()=>{cancelAnimationFrame(frame);syncAt(movie.currentTime);});
  movie.addEventListener('timeupdate',()=>syncAt(movie.currentTime));
  movie.addEventListener('seeked',()=>syncAt(movie.currentTime));
  document.addEventListener('visibilitychange',()=>{if(document.hidden)movie.pause();});
  movie.addEventListener('error',()=>{$('load-status').hidden=false;$('load-status').textContent=root.lang==='ko'?'영상이 재생되지 않으면 아래 MP4 링크를 열어 주세요.':'Video unavailable. Open the MP4 link below.';$('load-status').setAttribute('role','alert');});
  fetch('experiment.json').then(r=>{if(!r.ok)throw Error('No data');return r.json();}).then(data=>{
    if(data.steps!==2400||data.duration!==48||methods.some(m=>data.traces[m].rows.length!==2401))throw Error('Invalid record');
    record=data;$('iteration').max=String(data.frame_iterations.length-1);buildChart('loss');buildChart('distance');syncAt(movie.currentTime);$('iteration').disabled=false;$('load-status').hidden=true;
  }).catch(()=>{$('load-status').hidden=false;$('load-status').textContent=root.lang==='ko'?'비교 데이터를 불러오지 못했습니다. 새로고침해 주세요.':'The comparison did not load. Please reload.';$('load-status').setAttribute('role','alert');});
})();
