'use strict';
(() => {
  const $=id=>document.getElementById(id), root=document.documentElement;
  let saved; try{saved=localStorage.getItem('chainbench-language');}catch(_){}
  const requested=new URL(location.href).searchParams.get('lang');
  root.lang=['en','ko'].includes(requested)?requested:['en','ko'].includes(saved)?saved:'en';
  const movie=$('movie'), cover=$('film-start'), slug=document.body.dataset.paper;
  const ns='http://www.w3.org/2000/svg', blue='#3466a0', green='#237c67', red='#b7573d', ink='#242927', muted='#666d68', track='#dce1d8';
  let record=null, parameter=100, selected=2, depth=8, direction='forward', mediaLanguage='en', mediaSwitch=0;
  const tr=(en,ko)=>root.lang==='ko'?ko:en;
  const make=(tag,attrs={},text)=>{const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;};
  const label=(svg,x,y,text,color=ink,size=21,anchor='start')=>{const e=make('text',{x,y,'text-anchor':anchor},text);e.style.fill=color;e.style.fontSize=size+'px';svg.append(e);};
  const rect=(svg,x,y,w,h,fill,id)=>{const a={x,y,width:Math.max(0,w),height:h,fill,rx:5};if(id)a.id=id;const el=make('rect',a);svg.append(el);return el;};
  const line=(svg,points,color,width=3,marker=false)=>svg.append(make('polyline',{points:points.map(p=>p.join(',')).join(' '),fill:'none',stroke:color,'stroke-width':width,...(marker?{'marker-end':'url(#arrow)'}:{})}));
  function readout(id,items){
    const box=$(id);box.replaceChildren();
    for(const [name,value,text] of items){const b=document.createElement('span');b.id=name;b.dataset.value=value;b.textContent=text;box.append(b);}
  }
  function draw(){
    if(!record)return;
    const a=$('first-chart'),b=$('second-chart');a.replaceChildren();b.replaceChildren();
    $('parameter-value').textContent=slug==='attention'?(parameter/25).toFixed(2):(parameter/100).toFixed(2);
    $('parameter').setAttribute('aria-valuetext',tr('Strength ','크기 ')+$('parameter-value').textContent);
    if(slug==='attention'){
      const row=record.cases[selected][parameter],places=record.places[root.lang];
      a.setAttribute('aria-label',tr(`Where is ${record.names[selected]}? Attention shares`,`질문: ${record.names[selected]}의 위치는? 참고 비중`));
      b.setAttribute('aria-label',tr('Weighted location information','비중대로 모인 위치 정보'));
      label(a,22,30,tr(`Q: Where is ${record.names[selected]}?`,`Q: ${record.names[selected]}의 위치는?`),blue,24);
      label(a,22,66,tr('K · name tag → V · location','K · 이름표 → V · 위치'),muted,18);
      for(let i=0;i<3;i++){
        const y=106+i*82,w=row.weights[i];
        label(a,22,y,record.names[i],ink,22);label(a,115,y,'→ '+places[i],muted,20);
        rect(a,22,y+13,432,15,track);rect(a,22,y+13,432*w,15,blue,'weight-bar-'+i);
        label(a,535,y+26,Math.round(w*100)+'%',blue,23,'end');
      }
      label(b,22,36,tr('Every value contributes its share.','각 내용은 비중만큼 담깁니다.'),green,22);
      let left=22;
      const colors=[blue,'#aa7a32',green];
      for(let i=0;i<3;i++){
        const w=row.output[i]*516;
        // Square edges keep the segment areas proportional, including tiny shares.
        const bar=rect(b,left,72,w,62,colors[i],'output-bar-'+i);bar.setAttribute('rx',0);left+=w;
        rect(b,22,172+i*47,12,12,colors[i]);label(b,46,184+i*47,places[i],ink,22);
        label(b,535,184+i*47,Math.round(100*row.output[i])+'%',colors[i],23,'end');
      }
      label(b,22,330,tr('Drag here to change the question.','여기를 끌어 질문을 바꿔 보세요.'),muted,17);
      readout('first-values',row.weights.map((v,i)=>['weight-'+i,v,record.names[i]+' '+(100*v).toFixed(1)+'%']));
      const biggest=row.output.indexOf(Math.max(...row.output));
      readout('second-values',[['result',row.output[biggest],parameter===0?tr('Equal shares','같은 비중'):tr('Mostly '+places[biggest]+' information',places[biggest]+' 정보가 주로 담김')]]);
      document.querySelectorAll('[data-query]').forEach(e=>e.setAttribute('aria-pressed',String(Number(e.dataset.query)===selected)));
    }else{
      const row=record.blocks[parameter],back=direction==='backward';
      a.setAttribute('aria-label',tr(back?'Backward learning signal through branch and shortcut':'Forward input plus correction',back?'가지와 지름길로 돌아오는 학습 신호':'원래 정보와 수정분의 순전파'));
      b.setAttribute('aria-label',tr(`Signal magnitudes after ${depth} blocks`,`${depth}개 블록을 지난 신호 크기`));
      const defs=make('defs'),marker=make('marker',{id:'arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:6,markerHeight:6,orient:'auto-start-reverse'});
      marker.append(make('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:back?red:green}));defs.append(marker);a.append(defs);
      const paths=[[[72,167],[135,167],[135,83],[196,83]],[[354,83],[420,83],[420,152]],[[437,167],[508,167]]];
      for(const points of paths)line(a,back?[...points].reverse():points,back?red:green,3,true);
      line(a,back?[[420,184],[420,287],[135,287],[135,167]]:[[135,167],[135,287],[420,287],[420,184]],blue,4);
      rect(a,196,44,158,80,'#e7ede4');label(a,275,73,tr('Branch','학습하는 가지'),green,22,'middle');
      label(a,275,106,back?tr('Find adjustment','수정 방향 계산'):'+'+row.correction.toFixed(2),ink,19,'middle');
      a.append(make('circle',{cx:420,cy:167,r:18,fill:'#f7f6f2',stroke:ink,'stroke-width':2}));label(a,420,174,'+',ink,24,'middle');
      label(a,42,148,tr(back?'Earlier':'Input',back?'앞쪽 층':'입력'),ink,19,'middle');
      label(a,42,205,back?tr('Both paths','두 신호'):row.x.toFixed(1),blue,back?16:24,'middle');
      label(a,520,148,tr(back?'Error':'Output',back?'오차':'출력'),ink,19,'middle');
      label(a,520,205,back?tr('Signal','신호'):row.y.toFixed(2),back?red:ink,back?19:24,'middle');
      label(a,275,256,tr(back?'Shortcut: direct signal':'Shortcut: original 2.0',back?'지름길: 신호를 직접 전달':'지름길: 원래 값 2.0'),blue,19,'middle');
      label(a,275,329,tr(back?'Gradients guide an optimizer’s update.':'Target 2.2 · chosen weights, not training',back?'기울기를 이용해 최적화 알고리즘이 갱신합니다.':'정답 2.2 · 학습 아닌 가중치 조절'),muted,17,'middle');
      readout('first-values',back?[['input-gradient',row.dx,tr('Both contributions add; the branch still learns.','두 기여가 합쳐지며, 가지도 학습합니다.')]]:[['prediction',row.y,tr('Prediction ','예측 ')+row.y.toFixed(2)],['correction',row.correction,tr('Correction +','수정분 +')+row.correction.toFixed(2)]]);
      const vals=[Math.abs(record.plain[depth]),Math.abs(record.residual[depth])];
      label(b,22,36,tr(`${depth} blocks backward`,`${depth}개 블록을 거슬러`),ink,23);
      for(let i=0;i<16;i++)rect(b,22+i*32.25,62,26,9,i<depth?blue:track);
      for(let i=0;i<2;i++){
        const y=123+i*110,color=i?blue:red;
        label(b,22,y,tr(i?'With shortcuts':'Plain mappings only',i?'지름길 있음':'직접 매핑만'),color,22);
        label(b,536,y,vals[i]*100<1?tr('< 1','1 미만'):Math.round(vals[i]*100).toString(),color,25,'end');
        rect(b,22,y+17,516,33,track);rect(b,22,y+17,516*vals[i],33,color,(i?'residual':'plain')+'-bar');
      }
      label(b,22,330,tr('Same starting magnitude: 100','두 경우 모두 출발 크기: 100'),muted,18);
      readout('second-values',vals.map((v,i)=>[(i?'residual':'plain')+'-signal',v*100,tr(i?'With shortcut':'Plain',i?'지름길 있음':'직접 매핑만')+': '+(v*100<1?tr('< 1','1 미만'):Math.round(v*100))]));
      $('depth-value').textContent=depth;$('depth').setAttribute('aria-valuetext',depth+tr(' blocks','개 블록'));
      document.querySelectorAll('[data-direction]').forEach(e=>e.setAttribute('aria-pressed',String(e.dataset.direction===direction)));
    }
    window.paperLesson={record,parameter,selected,depth,direction,slug};
  }
  function captions(){for(const t of movie.textTracks)t.mode=t.language===root.lang?'showing':'disabled';}
  function translate(){
    $('language').textContent=tr('한국어','English');$('language').setAttribute('aria-label',tr('Switch to Korean','Switch to English'));
    if(!movie){
      for(const paper of ['attention','resnet']){
        const img=document.querySelector('img[src^="'+paper+'/poster"]');
        if(img)img.src=paper+'/poster'+(root.lang==='ko'?'.ko':'')+'.jpg';
      }
      return;
    }
    $('iteration').setAttribute('aria-label',tr('Video position','영상 위치'));cover.setAttribute('aria-label',tr('Play the 48-second film','48초 영상 재생'));
    document.querySelector('.skip').textContent=tr('Skip to the film','영상으로 바로 가기');
    document.querySelector('.chapters').setAttribute('aria-label',tr('Film chapters','영상 장면'));
    document.querySelector('.choices').setAttribute('aria-label',slug==='attention'?tr('Query','질문'):tr('Direction','전달 방향'));
    captions();draw();
    if(mediaLanguage!==root.lang){
      const time=movie.currentTime||0,playing=!movie.paused,token=++mediaSwitch;
      mediaLanguage=root.lang;
      const suffix=mediaLanguage==='ko'?'.ko':'';
      movie.poster='poster'+suffix+'.jpg';cover.querySelector('img').src=movie.poster;$('mp4-link').href='film'+suffix+'.mp4';
      movie.querySelectorAll('source').forEach(s=>{s.src='film'+suffix+(s.type==='video/webm'?'.webm':'.mp4');});
      movie.addEventListener('loadedmetadata',()=>{if(token!==mediaSwitch)return;movie.currentTime=time;captions();if(playing)movie.play().catch(()=>{});},{once:true});
      movie.load();
    }
  }
  $('language').addEventListener('click',()=>{root.lang=root.lang==='en'?'ko':'en';try{localStorage.setItem('chainbench-language',root.lang);}catch(_){}translate();});
  if(!movie){translate();return;}
  function sync(){
    const frame=Math.max(0,Math.min(1151,Math.floor(movie.currentTime*24+1e-6))),scene=Math.min(3,Math.floor(frame/288));
    $('iteration').value=frame;$('film-time').textContent='00:'+String(Math.floor(frame/24)).padStart(2,'0');
    document.querySelectorAll('[data-chapter]').forEach(e=>{e.setAttribute('aria-current',String(Number(e.dataset.chapter)===scene));});
    document.querySelectorAll('[data-note]').forEach(e=>{e.hidden=Number(e.dataset.note)!==scene;});
  }
  function seek(frame){if(!record||movie.readyState<1)return;cover.hidden=true;movie.pause();movie.currentTime=(Math.max(0,Math.min(1151,frame))+.5)/24;sync();}
  cover.hidden=false;
  cover.addEventListener('click',()=>movie.play().catch(fail));
  document.querySelector('.watch-link').addEventListener('click',()=>movie.play().catch(fail));
  movie.addEventListener('play',()=>{cover.hidden=true;});
  movie.addEventListener('loadedmetadata',()=>{captions();sync();});
  movie.addEventListener('timeupdate',sync);
  movie.addEventListener('seeked',()=>{if(movie.currentTime>0)cover.hidden=true;sync();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)movie.pause();});
  $('iteration').addEventListener('input',e=>seek(Number(e.target.value)));
  document.querySelectorAll('[data-chapter]').forEach(e=>e.addEventListener('click',()=>seek(Number(e.dataset.chapter)*288)));
  $('parameter').addEventListener('input',e=>{parameter=Number(e.target.value);draw();});
  if($('depth'))$('depth').addEventListener('input',e=>{depth=Number(e.target.value);draw();});
  document.querySelectorAll('[data-query]').forEach(e=>e.addEventListener('click',()=>{selected=Number(e.dataset.query);draw();}));
  document.querySelectorAll('[data-direction]').forEach(e=>e.addEventListener('click',()=>{direction=e.dataset.direction;draw();}));
  for(const [i,svg] of [...document.querySelectorAll('.chart-svg')].entries()){
    let dragging=false;
    const action=e=>{if(!record)return;const box=svg.getBoundingClientRect(),u=Math.max(0,Math.min(1,(e.clientX-box.left)/box.width));if(i===0){parameter=Math.round(u*100);$('parameter').value=parameter;}else if(slug==='attention'){selected=Math.min(2,Math.floor(u*3));}else{depth=Math.round(u*16);$('depth').value=depth;}draw();};
    svg.addEventListener('pointerdown',e=>{dragging=true;svg.setPointerCapture(e.pointerId);action(e);});
    svg.addEventListener('pointermove',e=>{if(dragging)action(e);});
    svg.addEventListener('pointerup',()=>{dragging=false;});svg.addEventListener('pointercancel',()=>{dragging=false;});
  }
  function fail(){
    $('load-status').hidden=false;$('load-status').textContent=tr('The record or film could not load. Reload or open the MP4 below.','계산 기록이나 영상을 불러오지 못했습니다. 새로고침하거나 아래 MP4 링크를 열어 주세요.');$('load-status').setAttribute('role','alert');
  }
  movie.addEventListener('error',fail);translate();
  const finite=v=>Array.isArray(v)?v.every(finite):v&&typeof v==='object'?Object.values(v).every(finite):typeof v!=='number'||Number.isFinite(v);
  fetch('experiment.json').then(r=>{if(!r.ok)throw Error('Missing record');return r.json();}).then(data=>{
    if(data.kind!=='chainbench.visual-paper.v2'||data.slug!==slug||data.duration!==48||data.fps!==24||!finite(data)||!/^[a-f0-9]{40}$/.test(data.source))throw Error('Invalid record');
    if(slug==='attention'&&(!Array.isArray(data.cases)||data.cases.length!==3||!data.cases.every(rows=>rows.length===101&&rows.every(r=>r.weights.length===3&&r.output.length===3&&Math.abs(r.weights.reduce((a,b)=>a+b,0)-1)<1e-8))))throw Error('Invalid attention');
    if(slug==='resnet'&&(data.blocks?.length!==101||data.plain?.length!==17||data.residual?.length!==17))throw Error('Invalid residual');
    record=data;draw();sync();document.querySelectorAll('input,button[data-chapter],button[data-query],button[data-direction]').forEach(e=>e.disabled=false);$('load-status').hidden=true;
  }).catch(fail);
})();
