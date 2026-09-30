import {paintRoom,paintHouseFloor,paintDistrict,furnitureSprite} from './generation-drawing.js';
import {drawPerson} from './renderer.js';

const $=id=>document.getElementById(id), esc=v=>String(v??'').replace(/[&<>"']/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
const state={ready:false,mode:'room',design:null,demo:null,session:null,floor:0,selected:null,person:'walker-0',playing:false,busy:false,advancing:false,variants:[],camera:{unit:35,x:0,y:0}};
window.atelier=state;
let catalog,toastTimer,requestNumber=0;
const canvas=$('design-canvas'),ctx=canvas.getContext('2d');
const floorName=n=>n===0?'EG':`${n}. OG`;
const clock=t=>`${Math.floor(t/60).toString().padStart(2,'0')}:${(t%60).toString().padStart(2,'0')}`;
function toast(message){$('atelier-toast').textContent=message;$('atelier-toast').classList.remove('hidden');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('atelier-toast').classList.add('hidden'),5500)}
async function api(path,body){const r=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));return data}
function pause(){state.playing=false;$('demo-play').textContent='NPC-Rundgang starten ▷'}
function resize(){const r=canvas.getBoundingClientRect();state.width=r.width;state.height=r.height;state.dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(r.width*state.dpr);canvas.height=Math.round(r.height*state.dpr);draw()}
function fit(){if(!state.design)return;const d=state.design;state.camera={unit:Math.min((state.width-65)/(d.width+1),(state.height-90)/(d.height+1)),x:0,y:state.mode==='house'?10:0};draw()}
function origin(){return {x:(state.width-state.design.width*state.camera.unit)/2+state.camera.x,y:(state.height-state.design.height*state.camera.unit)/2+state.camera.y}}
function zoom(factor,px=state.width/2,py=state.height/2){if(!state.design)return;const old=state.camera.unit,next=Math.max(1,Math.min(160,old*factor)),ratio=next/old;state.camera.x=(state.camera.x-(px-state.width/2))*ratio+(px-state.width/2);state.camera.y=(state.camera.y-(py-state.height/2))*ratio+(py-state.height/2);state.camera.unit=next;draw()}
function draw(){
  ctx.setTransform(state.dpr,0,0,state.dpr,0,0);ctx.clearRect(0,0,state.width,state.height);ctx.imageSmoothingEnabled=false;
  if(!state.design)return;const d=state.design,{x,y}=origin(),u=state.camera.unit,opts={overlay:$('overlay').checked,labels:$('room-labels').checked,selected:state.selected};
  if(state.mode==='room')paintRoom(ctx,d,x,y,u,opts);
  else if(state.mode==='district')paintDistrict(ctx,d,x,y,u);
  else{
    paintHouseFloor(ctx,d,state.floor,x,y,u,opts);
    const actor=state.demo?.actors.find(a=>a.id===state.person);
    if(actor?.route&&$('overlay').checked){ctx.strokeStyle='#547e8480';ctx.lineWidth=Math.max(1.5,u*.12);ctx.setLineDash([u*.22,u*.2]);for(const step of actor.route.steps.slice(actor.index)){if(step.kind==='walk'&&step.from[0]===state.floor){ctx.beginPath();ctx.moveTo(x+(step.from[1]+.5)*u,y+(step.from[2]+.5)*u);ctx.lineTo(x+(step.to[1]+.5)*u,y+(step.to[2]+.5)*u);ctx.stroke()}}ctx.setLineDash([])}
    for(const person of state.demo?.actors||[]){
      if(person.position&&person.position[0]===state.floor){const [,px,py]=person.position;drawPerson(ctx,person.appearance,x+(px+.5)*u,y+(py+.85)*u,{scale:u/32,walking:false});if(person.id===state.person){ctx.strokeStyle='#446e52';ctx.lineWidth=1.5;ctx.strokeRect(x+px*u,y+py*u,u,u)}}
      else if(person.location.kind==='portal'&&person.location.from[0]===state.floor){const loc=person.location,px=x+(loc.from[1]+.5)*u,py=y+(loc.from[2]+.5)*u;ctx.fillStyle='#f9f3dd';ctx.fillRect(px-22,py-10,44,20);ctx.fillStyle='#63866d';ctx.fillRect(px-20,py+7,40*loc.progress,2);ctx.font='9px Segoe UI';ctx.textAlign='center';ctx.fillText(`${person.name} ↕`,px,py+2)}
    }
  }
}
function checks(items){return items.map(s=>`<div class="check-item"><b>✓</b><span>${esc(s)}</span></div>`).join('')}
function metrics(pairs){return '<div class="metric-pair">'+pairs.map(([n,s])=>`<div><strong>${esc(n)}</strong><span>${esc(s)}</span></div>`).join('')+'</div>'}
function details(){
  const d=state.design;if(!d)return;const v=d.validation;
  $('valid-badge').textContent=v.valid?'✓ Regeln erfüllt':'Prüfung fehlgeschlagen';$('valid-badge').classList.toggle('bad',!v.valid);
  $('design-name').textContent=state.mode==='room'?`${d.name}. Mit eigenem Charakter.`:d.name;
  $('design-kicker').textContent={room:'RAUMSTUDIE / 01',house:'HAUSSTUDIE / 02',district:'BLOCKSTUDIE / 03'}[state.mode];
  $('drawing-note').textContent=state.mode==='district'?'Straße → Gehweg → Haustür':`1 Quadrat = 1 m²${state.mode==='house'?' · '+floorName(state.floor):''}`;
  let summary='',detail='';
  if(state.mode==='room'){
    $('design-caption').textContent=`${d.family} · ${d.width} × ${d.height} m · ${d.palette.name} · Seed ${d.seed}`;
    summary=checks(['Keine überlappenden Möbel','Tür und Eintritt bleiben frei','Alle Bedienflächen erreichbar','Zusammenhängende freie Bodenfläche','Hohe Möbel verdecken keine Fenster'])+metrics([[d.objects.length,'MÖBEL'],[Math.round(v.free_fraction*100)+'%','FREIER BODEN']]);
    detail=`<h3>Entscheidungen des Generators</h3><ul class="reason-list">${d.trace.map(t=>`<li>${esc(t)}</li>`).join('')}</ul><h3>Bewusst weggelassen</h3>${d.omitted.map(o=>`<div class="omitted-item">${esc(catalog.objects[o.kind].name)}<br>${esc(o.reason)}</div>`).join('')||'<p class="muted-note">Alle gewählten Ergänzungen passen.</p>'}<p class="muted-note">${d.search.nodes} Suchschritte · Signatur ${esc(d.signature)}<br>Gleicher Seed + gleiche Version = gleicher Entwurf.</p>`;
  }else if(state.mode==='house'){
    $('design-caption').textContent=`${d.levels} Etagen · ${d.width} × ${d.height} m · ${d.elevator?'Treppe & Aufzug':'Treppe'} · Seed ${d.seed}`;
    summary=checks(['Alle Räume von der Haustür erreichbar','Etagenzugänge übereinander ausgerichtet','Möbelziele über Etagen erreichbar','Gemeinsame Aufzugskapazität: eine Person'])+metrics([[d.floors.reduce((n,f)=>n+f.rooms.length,0),'RÄUME'],[d.levels,'ETAGEN']]);
    if(!d.elevator||d.levels===1)summary=summary.replace('<div class="check-item"><b>✓</b><span>Gemeinsame Aufzugskapazität: eine Person</span></div>','');
    detail=`<h3>${esc(d.floors[state.floor].name)}</h3><ul class="reason-list">${d.floors[state.floor].rooms.map(r=>`<li>${esc(r.name)} · ${r.width} × ${r.height} m</li>`).join('')}</ul><p class="muted-note">Testpersonen ohne Bedürfnisse. Sie prüfen Laufwege, Wartezeiten und Etagenwechsel; die Hauptsimulation bleibt unverändert.</p>`;
  }else{
    $('design-caption').textContent=`${d.plots.length} Grundstücke · ${d.width} × ${d.height} m · Seed ${d.seed}`;
    summary=checks(['Straßennetz als verbundener Graph','Keine überlappenden Grundstücke','Jede Haustür besitzt einen Fußweg zum Gehweg'])+metrics([[d.plots.length,'GRUNDSTÜCKE'],[d.edges.length,'STRASSENABSCHNITTE']]);
    detail='<h3>Der nächste Maßstab</h3><p class="muted-note">Diese Blockstudie trennt zunächst Parzellen und Anbindung von den Hausinnenräumen. Für eine vollständige Stadt werden Hausabmessungen, Eingänge und Straßenkoordinaten anschließend gemeinsam validiert.</p><p class="muted-note">Grundstücke anklicken, um Seed und Etagenzahl zu untersuchen.</p>';
  }
  let library=[];
  if(state.mode==='room'){
    const spec=catalog.rooms[d.kind];library=[...new Set([...spec.required,...Object.values(spec.programs||{}).flat(),...spec.optional])];
    detail=`<details class="furniture-library"><summary>${library.length} mögliche Gegenstände</summary><p class="muted-note">Passend zum Raumtyp. Der Generator wählt die Ausstattung; markierte Objekte stehen in diesem Entwurf.</p><div class="furniture-cards">${library.map(k=>{const o=catalog.objects[k];return `<article class="${d.objects.some(o=>o.kind===k)?'present':''}"><canvas width="120" height="82" aria-label="${esc(o.name)}"></canvas><strong>${esc(o.name)}</strong><span>${o.w} × ${o.h} m</span></article>`}).join('')}</div></details>`+detail;
  }
  $('validation-summary').innerHTML=summary;$('design-details').innerHTML=detail;objectDetails();
  document.querySelectorAll('.furniture-cards canvas').forEach((cv,i)=>{const k=library[i],o=catalog.objects[k],c=cv.getContext('2d'),s=Math.min(1.3,95/(o.w*24),62/(o.h*24));c.save();c.translate((cv.width-o.w*24*s)/2,(cv.height-o.h*24*s)/2);c.scale(s,s);furnitureSprite(c,{kind:k,base_w:o.w,base_h:o.h},d.palette);c.restore()});
}
function objectDetails(){
  const d=state.design;let o;if(state.mode==='room')o=d?.objects.find(o=>o.id===state.selected);else if(state.mode==='house')o=d?.floors[state.floor].objects.find(o=>o.id===state.selected);else o=d?.plots.find(o=>o.id===state.selected);
  if(!o){$('object-inspector').innerHTML=`<p class="muted-note">${state.mode==='district'?'Ein Grundstück anklicken, um Abmessungen, Eingang und Anbindung zu untersuchen.':'Ein Möbelstück anklicken, um seine belegte Fläche und die freigehaltenen Bedienbereiche zu sehen.'}</p>`;return}
  const pairs=state.mode==='district'?[['Haus-Seed',o.house_seed],['Etagen',o.levels],['Grundstück',`${o.bounds[2]} × ${o.bounds[3]} m`],['Eingang',o.door.join(', ')],['Anbindung',`${o.footpath_width_m} m Fußweg`]]:[['Belegte Fläche',`${o.w} × ${o.h} m`],['Position',`${o.x}, ${o.y}`],['Drehung',`${o.orientation*90}°`],['Bedienflächen',`${o.clearance.length} m²`],['Rolle',o.required?'Funktionsmöbel':'Optionale Ergänzung']];
  $('object-inspector').innerHTML=`<div class="object-card"><div class="eyebrow">${state.mode==='district'?'GRUNDSTÜCK':'OBJEKTVERTRAG'}</div><h3>${esc(o.name||o.id)}</h3><dl class="key-values">${pairs.map(([k,v])=>`<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl><p>${esc(o.reason||'Fassadenstudie; Innenraum noch nicht instanziiert.')}</p></div>`;
}
function setFloor(level){state.floor=Math.max(0,Math.min(state.design.levels-1,level));state.selected=null;for(const b of $('floor-controls').children)b.classList.toggle('active',+b.dataset.floor===state.floor);details();draw()}
state.setFloor=setFloor;
function showDemo(){
  const demo=state.demo;if(!demo)return;$('demo-clock').textContent=`Testzeit ${clock(demo.clock)} · ${demo.metrics.elevator_trips} Aufzugfahrten`;
  $('walkers').innerHTML=demo.actors.map(a=>`<button class="walker ${a.id===state.person?'active':''}" data-person="${a.id}"><b>${esc(a.name)} · ${a.position?floorName(a.position[0]):floorName(a.location.from[0])+' → '+floorName(a.location.to[0])}</b><span>${esc(a.status)}</span><small>Ziel: ${esc(a.target?.name)} · ${floorName(a.target?.floor??0)}</small></button>`).join('');
  $('walkers').querySelectorAll('button').forEach(b=>b.onclick=()=>{state.person=b.dataset.person;$('route-person').value=state.person;showDemo();draw()});
  const person=demo.actors.find(a=>a.id===state.person);if($('follow-floor').checked&&person?.position&&person.position[0]!==state.floor)setFloor(person.position[0]);
  $('navigation-log').innerHTML=`<h3>Wegeprotokoll</h3>${demo.events.filter(e=>e.actor_id===state.person).slice(-9).reverse().map(e=>`<div class="log-entry"><time>${clock(e.time)}</time><p>${esc(e.text)}</p></div>`).join('')}`;
}
async function advance(seconds=1){if(state.advancing||!state.session)return;state.advancing=true;const sid=state.session;try{const demo=await api(`/api/generation/demo/${sid}/advance`,{seconds});if(state.session===sid){state.demo=demo;showDemo();draw()}}catch(e){pause();toast(e.message)}finally{state.advancing=false}}
state.advance=advance;
function useRoom(room){pause();state.design=room;state.selected=null;$('seed').value=room.seed;details();fit();document.querySelectorAll('.variant').forEach(b=>b.classList.toggle('active',+b.dataset.seed===room.seed))}
function showVariants(rooms){
  state.variants=rooms;$('variants').innerHTML=rooms.map(r=>`<button class="variant ${r.seed===state.design.seed?'active':''}" data-seed="${r.seed}"><canvas width="320" height="200" aria-label="${esc(r.family)}"></canvas><strong>${esc(r.family)}</strong><span>Seed ${r.seed} · ${r.objects.length} Möbel</span></button>`).join('');
  [...$('variants').children].forEach((b,i)=>{const r=rooms[i],cv=b.querySelector('canvas'),c=cv.getContext('2d'),u=Math.min(270/(r.width+1),174/(r.height+1));c.imageSmoothingEnabled=false;paintRoom(c,r,(320-r.width*u)/2,(200-r.height*u)/2,u);b.onclick=()=>useRoom(r)});
}
async function generate(){
  if(state.busy)return;state.busy=true;state.ready=false;pause();$('generate').disabled=true;const token=++requestNumber;
  try{
    const seed=Number($('seed').value);if(!Number.isInteger(seed)||seed<0||seed>2000000000)throw Error('Bitte einen ganzzahligen Seed zwischen 0 und 2.000.000.000 wählen.');
    let d;
    if(state.mode==='room'){
      const body={seed,kind:$('room-kind').value,width:Number($('room-width').value),height:Number($('room-height').value),style:$('style').value||null};
      d=await api('/api/generation/room',body);state.design=d;state.session=null;state.demo=null;
      const variants=await Promise.allSettled([0,1,2,3].map(i=>i?api('/api/generation/room',{...body,seed:(seed+i*17)%2000000001}):Promise.resolve(d)));
      if(token!==requestNumber)return;showVariants(variants.filter(r=>r.status==='fulfilled').map(r=>r.value));
    }else if(state.mode==='house'){
      const result=await api('/api/generation/house',{seed,levels:+$('levels').value,elevator:$('elevator').checked});d=result.design;state.design=d;state.demo=result.demo;state.session=result.session_id;state.floor=0;
      $('floor-controls').innerHTML=d.floors.map(f=>`<button data-floor="${f.level}" class="${f.level===0?'active':''}">${floorName(f.level)}</button>`).join('');
      for(const b of $('floor-controls').children)b.onclick=()=>setFloor(+b.dataset.floor);
      $('route-person').innerHTML=state.demo.actors.map(a=>`<option value="${a.id}">${esc(a.name)}</option>`).join('');$('route-person').value=state.person;
      $('route-target').innerHTML=state.demo.targets.map(t=>`<option value="${esc(t.id)}">${floorName(t.floor)} · ${esc(t.name)}</option>`).join('');showDemo();
    }else{d=await api('/api/generation/district',{seed,count:+$('plots').value});state.design=d;state.demo=null;state.session=null}
    state.selected=null;details();fit();state.ready=true;
  }catch(e){toast(e.message);$('valid-badge').textContent='Entwurf abgelehnt';$('valid-badge').classList.add('bad');state.ready=!!state.design}
  finally{state.busy=false;$('generate').disabled=false}
}
state.generate=generate;
async function mode(next){if(state.busy||next===state.mode)return;pause();state.mode=next;state.design=null;state.session=null;state.demo=null;state.selected=null;state.floor=0;
  clearTimeout(toastTimer);$('atelier-toast').classList.add('hidden');
  for(const id of ['overlay','room-labels'])$(id).closest('label').classList.toggle('hidden',next==='district');
  document.querySelector('.legend').classList.toggle('hidden',next==='district');
  document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('active',b.dataset.mode===next));
  for(const name of ['room','house','district'])$(`${name}-settings`).classList.toggle('hidden',name!==next);
  for(const [id,yes] of [['variant-section',next==='room'],['demo-section',next==='house'],['route-panel',next==='house'],['floor-controls',next==='house'],['district-note',next==='district']])$(id).classList.toggle('hidden',!yes);
  await generate();
}
state.modeSwitch=mode;
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>mode(b.dataset.mode));
$('generate').onclick=generate;$('next-seed').onclick=()=>{$('seed').value=(+$('seed').value+1)%2000000001;generate()};
$('room-kind').onchange=()=>{const spec=catalog.rooms[$('room-kind').value];['width','height'].forEach((k,i)=>{$(`room-${k}`).value=spec.size[i];$(`room-${k}`).min=spec.minimum[i]});generate()};
$('overlay').onchange=draw;$('room-labels').onchange=draw;$('zoom-in').onclick=()=>zoom(1.25);$('zoom-out').onclick=()=>zoom(.8);$('fit').onclick=fit;
$('demo-play').onclick=()=>{state.playing=!state.playing;$('demo-play').textContent=state.playing?'Rundgang pausieren Ⅱ':'NPC-Rundgang starten ▷'};
$('demo-step').onclick=()=>{pause();advance(10)};
$('route-person').onchange=()=>{state.person=$('route-person').value;showDemo();draw()};
$('send-walker').onclick=async()=>{if(!state.session)return;try{state.demo=await api(`/api/generation/demo/${state.session}/route`,{actor_id:$('route-person').value,target_id:$('route-target').value,transport:$('route-transport').value});showDemo();draw();toast('Weg geplant. Rundgang starten oder zehn Sekunden vorspulen.')}catch(e){toast(e.message)}};
$('export-design').onclick=()=>{if(!state.design)return;const blob=new Blob([JSON.stringify(state.design,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`mosswood-${state.mode}-${state.design.seed}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
let drag=null;
canvas.onpointerdown=e=>{canvas.setPointerCapture(e.pointerId);drag={x:e.offsetX,y:e.offsetY,sx:e.offsetX,sy:e.offsetY,moved:false}};
canvas.onpointermove=e=>{if(!drag)return;state.camera.x+=e.offsetX-drag.x;state.camera.y+=e.offsetY-drag.y;drag.x=e.offsetX;drag.y=e.offsetY;if(Math.hypot(e.offsetX-drag.sx,e.offsetY-drag.sy)>4)drag.moved=true;draw()};
canvas.onpointerup=e=>{if(drag&&!drag.moved&&state.design){const {x,y}=origin(),px=(e.offsetX-x)/state.camera.unit,py=(e.offsetY-y)/state.camera.unit;const objects=state.mode==='room'?state.design.objects:state.mode==='house'?state.design.floors[state.floor].objects:state.design.plots.map(p=>({...p,x:p.bounds[0],y:p.bounds[1],w:p.bounds[2],h:p.bounds[3]}));state.selected=objects.find(o=>px>=o.x&&px<o.x+o.w&&py>=o.y&&py<o.y+o.h)?.id||null;objectDetails();draw()}drag=null};canvas.onpointercancel=()=>drag=null;
canvas.addEventListener('wheel',e=>{e.preventDefault();zoom(Math.exp(-e.deltaY*.0015),e.offsetX,e.offsetY)},{passive:false});
window.addEventListener('keydown',e=>{if(['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName))return;if(state.mode==='house'&&['PageUp','PageDown'].includes(e.key)){e.preventDefault();setFloor(state.floor+(e.key==='PageUp'?1:-1))}if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();state.camera.x+=e.key==='ArrowLeft'?30:e.key==='ArrowRight'?-30:0;state.camera.y+=e.key==='ArrowUp'?30:e.key==='ArrowDown'?-30:0;draw()}});
new ResizeObserver(()=>{resize();if(state.design)fit()}).observe(canvas.parentElement);
setInterval(()=>{if(state.playing&&!document.hidden)advance(1)},250);
try{catalog=await api('/api/generation/catalog');state.catalog=catalog;$('room-kind').innerHTML=Object.entries(catalog.rooms).map(([k,v])=>`<option value="${k}">${esc(v.name)}</option>`).join('');document.querySelector('.intro').insertAdjacentHTML('afterend',`<p class="catalog-summary">${Object.keys(catalog.rooms).length} Raumtypen · ${Object.keys(catalog.objects).length} Gegenstände</p>`);$('style').insertAdjacentHTML('beforeend',Object.entries(catalog.styles).map(([k,v])=>`<option value="${k}">${esc(v.name)}</option>`).join(''));resize();await generate()}catch(e){toast(e.message)}
