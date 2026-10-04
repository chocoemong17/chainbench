'use strict';
(() => {
  const $=id=>document.getElementById(id), root=document.documentElement;
  let saved; try{saved=localStorage.getItem('chainbench-language');}catch(_){}
  const requested=new URL(location.href).searchParams.get('lang');
  root.lang=['en','ko'].includes(requested)?requested:['en','ko'].includes(saved)?saved:'en';
  const movie=$('movie'), cover=$('film-start'), slug=document.body.dataset.paper;
  let record=null, animation=null, current=0, pixel=16;
  const charts=[], ns='http://www.w3.org/2000/svg';
  const make=(tag,attrs,text)=>{const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;};
  function translate(){
    const ko=root.lang==='ko';$('language').textContent=ko?'English':'한국어';$('language').setAttribute('aria-label',ko?'Switch to English':'한국어로 전환');
    if(movie){$('iteration').setAttribute('aria-label',ko?'영상 위치':'Video position');cover.setAttribute('aria-label',ko?'48초 영상 재생':'Play the 48-second film');document.querySelector('.skip').textContent=ko?'영상으로 바로 가기':'Skip to the film';for(const t of movie.textTracks)t.mode=t.language===root.lang?'showing':'disabled';}
    if(record)draw(current);
  }
  $('language').addEventListener('click',()=>{root.lang=root.lang==='en'?'ko':'en';try{localStorage.setItem('chainbench-language',root.lang);}catch(_){}translate();});translate();
  if(!movie)return;
  cover.hidden=false;movie.addEventListener('loadedmetadata',translate);
  cover.addEventListener('click',()=>movie.play().catch(()=>{}));
  document.querySelector('.watch-link').addEventListener('click',()=>movie.play().catch(()=>{}));
  function chart(id,low,high,max,series,xlabel,spatial=false){
    const svg=$(id+'-chart'), px=x=>54+480*x/max, py=y=>18+228*(high-y)/(high-low);
    for(let i=0;i<=4;i++){
      const y=low+(high-low)*i/4,x=max*i/4;
      svg.append(make('line',{x1:54,x2:534,y1:py(y),y2:py(y),class:'grid'}),make('text',{x:45,y:py(y)+5,'text-anchor':'end'},Number(y.toFixed(2)).toString()),make('text',{x:px(x),y:277,'text-anchor':'middle'},xlabel(x)));
    }
    const lines=series.map(s=>{const p=make('path',{class:'curve',stroke:s.color,'data-series':s.key});svg.append(p);return p;});
    const cursor=make('line',{x1:54,x2:54,y1:18,y2:246,class:'cursor'});svg.append(cursor);
    const dots=series.map(s=>{const e=make('circle',{r:4,fill:s.color,stroke:'#f7f6f2','stroke-width':2,class:'probe'});svg.append(e);return e;});
    const c={id,svg,px,py,max,series,lines,cursor,dots,spatial};charts.push(c);
    let dragging=false;
    const action=e=>{const b=svg.getBoundingClientRect(),x=Math.max(0,Math.min(max,((e.clientX-b.left)/b.width*560-54)/480*max));if(spatial){pixel=Math.round(x);draw(current);}else seekStep(Math.round(x));};
    svg.addEventListener('pointerdown',e=>{dragging=true;svg.setPointerCapture(e.pointerId);action(e);});
    svg.addEventListener('pointermove',e=>{if(dragging)action(e);});
    svg.addEventListener('pointerup',()=>{dragging=false;});svg.addEventListener('pointercancel',()=>{dragging=false;});
  }
  function setup(){
    if(slug==='attention'){
      const weights=record.names.map((label,i)=>({key:'weight-'+i,label:[label,['빨강','초록','파랑','금색'][i]],color:record.colors[i],get:()=>record.rows.map(r=>r.weights[i])}));
      const channels=['R','G','B'].map((label,i)=>({key:'channel-'+i,label:[label,label],color:['#b83e31','#398c68','#4979bf'][i],get:()=>record.rows.map(r=>r.output[i])}));
      chart('first',0,1,180,weights,x=>Math.round(x)+'°');chart('second',0,1,180,channels,x=>Math.round(x)+'°');
    }else{
      const r=record.row_index;
      const profiles=[{key:'input',label:['Input','입력'],color:'#66766b',get:()=>record.input[r]},
        {key:'change',label:['Change','변화량'],color:'#b17827',get:k=>record.rows[k].delta[r]},
        {key:'output',label:['Output','출력'],color:'#b83e31',get:k=>record.rows[k].output[r]}];
      chart('first',-.25,1.05,31,profiles,x=>Math.round(x),true);
      chart('second',0,.21,100,[{key:'rmse',label:['Error','오차'],color:'#b83e31',get:()=>record.rows.map(r=>r.rmse)}],x=>(x/100).toFixed(2));
    }
  }
  function draw(k){
    if(!record)return;current=k;
    $('parameter-value').textContent=slug==='attention'?k+'°':(k/100).toFixed(2);
    $('iteration').setAttribute('aria-valuetext',slug==='attention'?k+'°':(k/100).toFixed(2));
    for(const c of charts){
      const position=c.spatial?pixel:k;c.cursor.setAttribute('x1',c.px(position));c.cursor.setAttribute('x2',c.px(position));
      const values=$(c.id+'-values');values.replaceChildren();
      for(let i=0;i<c.series.length;i++){
        const s=c.series[i], ys=s.get(k);
        c.lines[i].setAttribute('d',ys.map((y,x)=>(x?'L':'M')+c.px(x).toFixed(2)+','+c.py(y).toFixed(2)).join(''));
        c.dots[i].setAttribute('cx',c.px(position));c.dots[i].setAttribute('cy',c.py(ys[position]));
        const label=document.createElement('span');label.style.color=s.color;label.append(s.label[root.lang==='ko'?1:0]);const value=document.createElement('b');value.id=s.key;value.textContent=ys[position].toFixed(3);label.append(value);values.append(label);
      }
      if(c.spatial){const p=document.createElement('span');p.id='pixel-label';p.textContent=(root.lang==='ko'?'픽셀 ':'Pixel ')+pixel;values.append(p);}
    }
    window.paperLesson={record,k:current,pixel,slug};
  }
  function sync(){if(!record)return;const frame=Math.max(0,Math.min(1151,Math.floor(movie.currentTime*24+1e-6)));$('iteration').value=frame;draw(record.frame_steps[frame]);}
  function seekFrame(frame){if(!record)return;cover.hidden=true;movie.pause();movie.currentTime=(Math.max(0,Math.min(1151,frame))+.5)/24;sync();}
  function seekStep(k){const frame=record.frame_steps.findIndex(v=>v>=k);seekFrame(frame<0?1151:frame);}
  $('iteration').addEventListener('input',e=>seekFrame(Number(e.target.value)));
  const tick=()=>{sync();if(!movie.paused&&!movie.ended)animation=requestAnimationFrame(tick);};
  movie.addEventListener('play',()=>{cover.hidden=true;cancelAnimationFrame(animation);tick();});
  movie.addEventListener('pause',()=>{cancelAnimationFrame(animation);sync();});movie.addEventListener('timeupdate',sync);
  movie.addEventListener('seeked',()=>{if(movie.currentTime>0)cover.hidden=true;sync();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)movie.pause();});
  const fail=()=>{$('load-status').hidden=false;$('load-status').textContent=root.lang==='ko'?'계산 기록이나 영상을 불러오지 못했습니다. 새로고침하거나 아래 MP4 링크를 열어 주세요.':'The record or film could not load. Reload or open the MP4 below.';$('load-status').setAttribute('role','alert');};
  movie.addEventListener('error',fail);
  fetch('experiment.json').then(r=>{if(!r.ok)throw Error('Missing record');return r.json();}).then(data=>{
    const expected=slug==='attention'?180:100;
    if(data.kind!=='chainbench.visual-paper.v1'||data.slug!==slug||data.steps!==expected||data.rows.length!==expected+1||data.frame_steps.length!==1152||data.duration!==48||data.fps!==24||!data.frame_steps.every(k=>Number.isInteger(k)&&k>=0&&k<=expected))throw Error('Invalid record');
    record=data;setup();sync();$('iteration').disabled=false;$('load-status').hidden=true;
  }).catch(fail);
})();
