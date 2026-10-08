'use strict';
(() => {
  const $=id=>document.getElementById(id),root=document.documentElement,slug=document.body.dataset.paper;
  const ns='http://www.w3.org/2000/svg',blue='#3466a0',red='#b7573d',green='#237c67',ink='#242927',gray='#68756d',line='#d6ddd3';
  const tr=(a,b)=>root.lang==='ko'?b:a;
  let saved;try{saved=localStorage.getItem('chainbench-language');}catch(_){}
  const requested=new URL(location.href).searchParams.get('lang');
  root.lang=['en','ko'].includes(requested)?requested:['en','ko'].includes(saved)?saved:'en';
  const movie=$('movie'),cover=$('film-start'),slider=$('parameter');
  let record=null,parameter=Number(slider.value),mode=slug==='dropout'?'training':'forward',filter=0,stride=1,depth=0,mediaLanguage='en',generation=0;
  const make=(tag,attrs={},text)=>{const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;};
  const text=(s,x,y,t,color=ink,size=18,anchor='start')=>{const e=make('text',{x,y,'text-anchor':anchor},t);e.style.fill=color;e.style.fontSize=size+'px';s.append(e);return e;};
  const rect=(s,x,y,w,h,fill,stroke='none',attrs={})=>{const e=make('rect',{x,y,width:w,height:h,rx:4,fill,stroke,...attrs});s.append(e);return e;};
  const path=(s,points,color=blue,width=2,attrs={})=>s.append(make('polyline',{points:points.map(p=>p.join(',')).join(' '),fill:'none',stroke:color,'stroke-width':width,...attrs}));
  function arrow(s,a,b,color){path(s,[a,b],color,2);const theta=Math.atan2(b[1]-a[1],b[0]-a[0]);s.append(make('polygon',{points:[b,...[-1,1].map(k=>[b[0]-9*Math.cos(theta+k*.5),b[1]-9*Math.sin(theta+k*.5)])].map(p=>p.join(',')).join(' '),fill:color}));}
  function readout(id,entries){$(id).replaceChildren();for(const [key,value,label] of entries){const e=document.createElement('span');e.id=key;e.dataset.value=String(value);e.textContent=label;$(id).append(e);}}
  function grid(s,data,x,y,cell,max=1,active=null,until=Infinity,kind='cell'){
    for(let r=0;r<data.length;r++)for(let c=0;c<data[r].length;c++){
      const v=data[r][c],known=r*data[r].length+c<=until;
      const strength=Math.min(1,Math.abs(v)/max),fill=!known?'#d4dbd3':v===0?'#fafbf8':v<0?red:blue;
      rect(s,x+c*cell,y+r*cell,cell-1,cell-1,fill,'none',{'data-kind':kind,'data-row':r,'data-col':c,'data-value':known?v:'unknown','fill-opacity':known&&v!==0?.35+.65*strength:1,rx:2});
      if(known&&v!==0&&cell>=20)text(s,x+(c+.5)*cell,y+(r+.69)*cell,Number.isInteger(v)?v.toString():v.toFixed(1),strength>.4?'white':ink,Math.min(16,cell*.62),'middle');
    }
    if(active)rect(s,x+active[1]*cell,y+active[0]*cell,cell*active[2],cell*active[2],'none',red,{'stroke-width':3,rx:0});
  }
  function backprop(a,b){
    const row=record.trace[parameter],back=mode==='backward';
    text(a,20,30,back?tr('Backward · how does the loss change?','역방향 · 오차는 얼마나 변할까요?'):tr('Forward · y = AB + CDE','순방향 · y = AB + CDE'),back?red:blue,21);
    const positions={A:[52,90],B:[52,159],C:[52,240],D:[52,309],E:[52,382],AB:[205,128],CD:[205,270],CDE:[337,319],y:[440,208],L:[509,107]};
    const edges=[['A','AB'],['B','AB'],['C','CD'],['D','CD'],['CD','CDE'],['E','CDE'],['AB','y'],['CDE','y'],['y','L']];
    for(const [x,z] of edges){const p=positions[x],q=positions[z],start=[p[0]+28,p[1]],end=[q[0]-29,q[1]];arrow(a,back?end:start,back?start:end,back?red:blue);}
    const g=row.y-4,gv={A:row.gradients[0],B:row.gradients[1],C:row.gradients[2],D:row.gradients[3],E:row.gradients[4],AB:g,CD:g*row.values[4],CDE:g,y:g,L:1};
    for(const [key,[x,y]] of Object.entries(positions)){
      const v=key.length===1&&'ABCDE'.includes(key)?row.values['ABCDE'.indexOf(key)]:key==='L'?row.loss:row[key];
      rect(a,x-31,y-27,62,48,'#fafbf8',back?red:blue,{'data-node':key,'data-value':v});
      text(a,x,y-9,key,gray,14,'middle');text(a,x,y+11,v.toFixed(key==='L'?3:2),ink,15,'middle');
      if(back)text(a,x,y+40,'g '+gv[key].toFixed(3),red,13,'middle').setAttribute('data-gradient',key);
    }
    text(b,24,32,tr('Prediction after each update','갱신마다 달라지는 예측'),ink,22);
    const x=k=>48+k*76,y=v=>326-(v-2)*120;
    for(const value of [2,3,4]){path(b,[[43,y(value)],[526,y(value)]],value===4?green:line,1);text(b,29,y(value)+5,String(value),value===4?green:gray,17,'end');}
    text(b,525,66,tr('Target 4','목표 4'),green,18,'end');
    path(b,record.trace.map(v=>[x(v.step),y(v.y)]),line,3);
    path(b,record.trace.slice(0,parameter+1).map(v=>[x(v.step),y(v.y)]),blue,3);
    for(const v of record.trace){b.append(make('circle',{cx:x(v.step),cy:y(v.y),r:v.step===parameter?8:4,fill:v.step<=parameter?blue:line,'data-step':v.step,'data-y':v.y}));text(b,x(v.step),356,String(v.step),gray,17,'middle');}
    text(b,280,392,tr('Completed updates','완료한 갱신 횟수'),gray,18,'middle');
    readout('first-values',[['output',row.y,'y = '+row.y.toFixed(4)],['loss',row.loss,tr('Loss ','오차 ')+row.loss.toFixed(6)]]);
    readout('second-values',[['distance',row.distance_to_target,tr('Distance to target: ','목표까지 거리: ')+row.distance_to_target.toFixed(6)]]);
    a.setAttribute('aria-label',tr(`${mode}, update ${parameter}, prediction ${row.y.toFixed(4)}`,`${back?'역방향':'순방향'}, ${parameter}회 갱신, 예측 ${row.y.toFixed(4)}`));
  }
  function volume(s,maps,x,y,cell,selected){
    const max=Math.max(1,...maps.flat(2).map(Math.abs)),h=maps[0].length,w=maps[0][0].length;
    for(let z=maps.length-1;z>=0;z--){grid(s,maps[z],x+z*14,y-z*15,cell,max,null,Infinity,'volume');rect(s,x+z*14,y-z*15,w*cell,h*cell,'none',selected?green:gray,{'stroke-width':selected?2.5:1,rx:0});}
    if(maps.length>1)for(const [dx,dy] of [[0,0],[w*cell,0],[w*cell,h*cell]])path(s,[[x+dx,y+dy],[x+dx+14,y+dy-15]],gray,1);
  }
  function cnn(a,b){
    const kernel=record.kernels[filter],maps=stride===1?record.one:record.stride2,output=maps[filter],h=output.length,w=output[0].length;
    const r=Math.floor(parameter/w)*stride,c=(parameter%w)*stride;
    const patch=record.input.slice(r,r+3).map(row=>row.slice(c,c+3));
    const sums=patch.map((row,i)=>row.reduce((acc,v,j)=>acc+v*kernel[i][j],0)),raw=sums.reduce((a,b)=>a+b,0),value=Math.max(0,raw);
    text(a,18,30,tr('Input · 7 × 9','입력 · 7 × 9'),ink,20);text(a,302,30,tr('Write one output','출력 한 칸 채우기'),ink,20);
    grid(a,record.input,18,53,26,1,[r,c,3],Infinity,'input');grid(a,output,302,53,30,6,[r/stride,c/stride,1],parameter,'output');
    arrow(a,[261,134],[291,134],blue);
    text(a,18,267,tr('Patch × filter','선택한 창 × 필터'),ink,19);
    grid(a,patch,18,282,25,1);text(a,103,329,'×',gray,26);grid(a,kernel,135,282,25,2);
    text(a,237,298,tr('Multiply, then add','같은 칸끼리 곱하고 합하기'),gray,17);
    text(a,237,327,sums.map(v=>'('+v+')').join(' + '),blue,20);
    text(a,237,359,`ReLU(${raw}) = ${value}`,green,24);
    text(a,18,400,tr(`Position ${parameter+1}/${h*w} · stride ${stride}`,`위치 ${parameter+1}/${h*w} · 스트라이드 ${stride}`),gray,18);
    text(b,18,30,tr('Two layers · stride 1','여러 층 · 스트라이드 1'),ink,21);
    const all=[[record.input],record.one,record.two],xs=[18,226,424],cells=[15,17,20],dims=['7×9×1','5×7×2','3×5×2'];
    for(let i=0;i<3;i++){volume(b,all[i],xs[i],98,cells[i],i===depth);text(b,xs[i],67,tr(i===0?'Input':'Layer '+i,i===0?'입력':i+'층'),i===depth?green:gray,18);text(b,xs[i],233,dims[i],i===depth?green:gray,19);}
    arrow(b,[169,151],[207,151],gray);arrow(b,[363,151],[405,151],gray);
    path(b,[[18,260],[541,260]],line,1);
    text(b,18,291,tr(`First layer · stride ${stride}`,`첫 층 · 스트라이드 ${stride}`),gray,18);
    text(b,18,330,'CNN',blue,22);text(b,235,330,'18',blue,36,'end');
    text(b,305,330,'Dense',red,22);text(b,542,330,(63*h*w*2).toLocaleString('en-US'),red,36,'end');
    text(b,18,367,tr('Shared weights','공유 가중치'),blue,18);text(b,305,367,tr('Independent weights','독립 가중치'),red,18);
    text(b,18,404,tr('Same I/O sizes; not an accuracy comparison.','같은 입출력 크기이며 정확도 비교는 아닙니다.'),gray,16);
    readout('first-values',[['raw',raw,tr('Sum ','곱의 합 ')+raw],['cell-value',value,tr('Output ','출력 ')+value]]);
    readout('second-values',[['shared',18,tr('CNN: 18','CNN: 18개')],['dense',63*h*w*2,'Dense: '+(63*h*w*2).toLocaleString('en-US')]]);
    $('depth-value').textContent=depth;$('stride').textContent=tr('Stride ','스트라이드 ')+stride;
    document.querySelectorAll('[data-filter]').forEach(e=>e.setAttribute('aria-pressed',String(Number(e.dataset.filter)===filter)));
    a.setAttribute('aria-label',tr(`Filter ${filter+1}, stride ${stride}, position ${parameter+1}, output ${value}`,`필터 ${filter+1}, 스트라이드 ${stride}, 위치 ${parameter+1}, 출력 ${value}`));
  }
  function dropout(a,b){
    const row=mode==='prediction'?record.prediction:record.cases[parameter];
    const masks=[[1,1,1],row.mask1,row.mask2,[1,1]],xs=[39,198,357,515];
    const positions=record.widths.map((n,k)=>Array.from({length:n},(_,i)=>[xs[k],82+i*260/(n-1)]));
    text(a,18,29,tr(mode==='prediction'?'Prediction · everyone returns':'Mask '+(parameter+1)+' · participating paths',mode==='prediction'?'예측 · 모든 노드 복귀':'조합 '+(parameter+1)+' · 이번에 참여하는 연결'),ink,20);
    for(let layer=0;layer<3;layer++)for(let i=0;i<positions[layer].length;i++)for(let j=0;j<positions[layer+1].length;j++){
      const on=masks[layer][i]&&masks[layer+1][j];path(a,[positions[layer][i],positions[layer+1][j]],on?blue:line,on?1.5:.8,{'data-inactive':String(!on),'data-edge':`${layer}-${i}-${j}`});
    }
    for(let k=0;k<4;k++)for(let i=0;i<positions[k].length;i++){
      const [x,y]=positions[k][i],active=masks[k][i];
      a.append(make('circle',{cx:x,cy:y,r:15,fill:'#fafbf8',stroke:active?blue:red,'stroke-width':2,'data-active':String(Boolean(active)),'data-layer':k,'data-node':i,'data-activation':row.layers[k][i]}));
      if(active)text(a,x,y+5,String(i+1),blue,16,'middle');else{path(a,[[x-7,y-7],[x+7,y+7]],red,2);path(a,[[x-7,y+7],[x+7,y-7]],red,2);}
    }
    for(let i=0;i<4;i++)text(a,xs[i],376,tr(['Input','Hidden 1','Hidden 2','Scores'][i],['입력','중간층 1','중간층 2','점수'][i]),gray,16,'middle');
    const off=mode!=='prediction'&&(!row.mask1.some(Boolean)||!row.mask2.some(Boolean));
    text(a,18,411,off?tr('A whole hidden layer is omitted → both scores 0','중간층 하나가 전부 쉬어 → 두 점수 모두 0'):tr('× omitted for this calculation · numbers are node indices','× 이번 계산에서 제외 · 숫자는 노드 번호'),off?red:gray,16);
    text(b,18,30,tr('Two computed output scores','실제로 계산한 출력 점수 두 개'),ink,22);
    const curr=row.layers[3],predict=record.prediction.layers[3],max=.2,zero=282,scale=1070;
    path(b,[[zero,78],[zero,312]],gray,1);
    for(let i=0;i<2;i++){
      const y=116+i*112;
      text(b,18,y-31,tr('Score ','점수 ')+(i+1),gray,18);
      for(const [offset,v,color,id] of [[0,curr[i],blue,'current'],[28,predict[i],green,'prediction']]){
        rect(b,zero+Math.min(0,v)*scale,y+offset,Math.abs(v)*scale,18,color,'none',{'data-series':id,'data-score':i,'data-value':v,rx:2});
        text(b,538,y+offset+15,v.toFixed(4),color,17,'end');
      }
    }
    text(b,zero-max*scale,332,'−0.2',gray,15,'middle');text(b,zero,332,'0',gray,15,'middle');text(b,zero+max*scale,332,'+0.2',gray,15,'middle');
    text(b,18,370,tr('Blue: selected calculation','파랑: 선택한 계산'),blue,18);text(b,18,399,tr('Green: all units, prediction scaling','초록: 모두 복귀한 예측 계산'),green,18);
    readout('first-values',[['kept1',row.mask1.reduce((a,b)=>a+b,0),tr('Hidden 1: ','중간층 1: ')+row.mask1.reduce((a,b)=>a+b,0)+'/5'],['kept2',row.mask2.reduce((a,b)=>a+b,0),tr('Hidden 2: ','중간층 2: ')+row.mask2.reduce((a,b)=>a+b,0)+'/5']]);
    readout('second-values',curr.map((v,i)=>['score-'+i,v,tr('Score ','점수 ')+(i+1)+': '+v.toFixed(4)]));
    a.setAttribute('aria-label',tr(`${mode}, mask ${parameter+1}, ${row.mask1.reduce((a,b)=>a+b,0)} and ${row.mask2.reduce((a,b)=>a+b,0)} hidden units participating`,`${mode==='prediction'?'예측':'참여 조합'}, ${parameter+1}번 조합, 중간층 ${row.mask1.reduce((a,b)=>a+b,0)}개와 ${row.mask2.reduce((a,b)=>a+b,0)}개 참여`));
  }
  function draw(){
    if(!record)return;
    const a=$('first-chart'),b=$('second-chart');a.replaceChildren();b.replaceChildren();
    ({backprop,cnn,dropout})[slug](a,b);
    $('parameter-value').textContent=slug==='backprop'?parameter:parameter+1;
    slider.setAttribute('aria-valuetext',tr('Selected ','선택 ')+$('parameter-value').textContent);
    document.querySelectorAll('[data-mode]').forEach(e=>e.setAttribute('aria-pressed',String(e.dataset.mode===mode)));
    window.foundationLesson={record,parameter,mode,filter,stride,depth};
  }
  function captions(){for(const t of movie.textTracks)t.mode=t.language===root.lang?'showing':'disabled';}
  function translate(){
    $('language').textContent=tr('한국어','English');$('language').setAttribute('aria-label',tr('Switch to Korean','Switch to English'));
    document.querySelector('.skip').textContent=tr('Skip to the film','영상으로 바로 가기');
    $('iteration').setAttribute('aria-label',tr('Video position','영상 위치'));cover.setAttribute('aria-label',tr('Play film','영상 재생'));
    captions();draw();
    if(mediaLanguage!==root.lang){
      const time=movie.currentTime||0,playing=!movie.paused,token=++generation;
      mediaLanguage=root.lang;const suffix=mediaLanguage==='ko'?'.ko':'';
      movie.poster='poster'+suffix+'.jpg';cover.querySelector('img').src=movie.poster;$('mp4-link').href='film'+suffix+'.mp4';
      movie.querySelectorAll('source').forEach(s=>s.src='film'+suffix+(s.type==='video/webm'?'.webm':'.mp4'));
      movie.addEventListener('loadedmetadata',()=>{if(token!==generation)return;movie.currentTime=time;captions();if(playing)movie.play().catch(fail);},{once:true});movie.load();
    }
  }
  function sync(){if(!record)return;const frame=Math.min(record.duration*record.fps-1,Math.floor(movie.currentTime*record.fps));$('iteration').value=frame;$('film-time').textContent='00:'+String(Math.floor(movie.currentTime)).padStart(2,'0');let active=0;const buttons=[...document.querySelectorAll('[data-time]')];buttons.forEach((e,i)=>{if(Number(e.dataset.time)<=movie.currentTime+.02)active=i;});buttons.forEach((e,i)=>e.setAttribute('aria-current',String(i===active)));}
  function seek(time){if(!record||movie.readyState<1)return;cover.hidden=true;movie.pause();movie.currentTime=Math.min(record.duration-.04,Math.max(0,time));sync();}
  function fail(){ $('load-status').hidden=false;$('load-status').textContent=tr('The record or film could not load. Reload or open the MP4 below.','계산 기록이나 영상을 불러오지 못했습니다. 새로고침하거나 아래 MP4를 열어 주세요.');$('load-status').setAttribute('role','alert'); }
  $('language').addEventListener('click',()=>{root.lang=root.lang==='en'?'ko':'en';try{localStorage.setItem('chainbench-language',root.lang);}catch(_){}translate();});
  cover.hidden=false;cover.addEventListener('click',()=>movie.play().catch(fail));
  document.querySelector('.watch-link').addEventListener('click',()=>movie.play().catch(fail));
  movie.addEventListener('play',()=>{cover.hidden=true;});movie.addEventListener('timeupdate',sync);movie.addEventListener('loadedmetadata',()=>{captions();sync();});movie.addEventListener('error',fail);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)movie.pause();});
  $('iteration').addEventListener('input',e=>seek(Number(e.target.value)/record.fps));
  document.querySelectorAll('[data-time]').forEach(e=>e.addEventListener('click',()=>seek(Number(e.dataset.time))));
  function select(value){parameter=Math.max(0,Math.min(Number(slider.max),Math.round(value)));slider.value=parameter;if(slug==='dropout')mode='training';draw();}
  slider.addEventListener('input',e=>select(Number(e.target.value)));
  document.querySelectorAll('[data-mode]').forEach(e=>e.addEventListener('click',()=>{mode=e.dataset.mode;draw();}));
  document.querySelectorAll('[data-filter]').forEach(e=>e.addEventListener('click',()=>{filter=Number(e.dataset.filter);draw();}));
  if($('stride'))$('stride').addEventListener('click',()=>{stride=stride===1?2:1;slider.max=stride===1?34:11;select(Math.min(parameter,Number(slider.max)));});
  if($('depth'))$('depth').addEventListener('input',e=>{depth=Number(e.target.value);draw();});
  for(const [i,svg] of [...document.querySelectorAll('.chart-svg')].entries()){
    let dragging=false;
    const action=e=>{if(!record)return;const box=svg.getBoundingClientRect(),u=Math.max(0,Math.min(1,(e.clientX-box.left)/box.width));if(slug==='cnn'&&i===1){depth=Math.round(u*2);$('depth').value=depth;draw();}else select(u*Number(slider.max));};
    svg.addEventListener('pointerdown',e=>{dragging=true;svg.setPointerCapture(e.pointerId);action(e);});svg.addEventListener('pointermove',e=>{if(dragging)action(e);});svg.addEventListener('pointerup',()=>{dragging=false;});svg.addEventListener('pointercancel',()=>{dragging=false;});
  }
  const finite=v=>Array.isArray(v)?v.every(finite):v&&typeof v==='object'?Object.values(v).every(finite):typeof v!=='number'||Number.isFinite(v);
  function valid(d){
    if(d.kind!=='chainbench.foundation.v1'||d.slug!==slug||!finite(d)||!/^[a-f0-9]{40}$/.test(d.source)||d.fps!==25||!Array.isArray(d.chapters)||!d.chapters.length||d.duration<=0||d.duration>=60)return false;
    if(slug==='backprop')return d.duration===59&&d.trace?.length===7&&d.trace.every(v=>v.values?.length===5&&v.gradients?.length===5&&typeof v.loss==='number'&&typeof v.y==='number');
    if(slug==='cnn')return d.input?.length===7&&d.input.every(v=>v.length===9)&&d.kernels?.length===2&&d.one?.length===2&&d.two?.length===2&&d.stride2?.length===2&&d.matrix?.length===70;
    return d.widths?.join(',')==='3,5,5,2'&&d.cases?.length===5&&[...d.cases,d.prediction].every(v=>v?.layers?.length===4&&v.layers.every((r,i)=>r.length===d.widths[i])&&v.mask1?.length===5&&v.mask2?.length===5);
  }
  translate();fetch('experiment.json').then(r=>{if(!r.ok)throw Error('Missing record');return r.json();}).then(d=>{if(!valid(d))throw Error('Invalid record');record=d;$('iteration').max=d.duration*d.fps-1;draw();sync();document.querySelectorAll('input,button[data-time],button[data-mode],button[data-filter],#stride').forEach(e=>e.disabled=false);$('load-status').hidden=true;}).catch(fail);
})();
