const esc=value=>String(value??'–').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pretty=value=>String(value??'').replaceAll('_',' ');
const rows=values=>`<dl class="object-values">${values.map(([key,value])=>`<div><dt>${esc(key)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl>`;

// This projection deliberately uses a freshly fetched world, never a stale
// geometry cache: old /api/state packets omit idle furniture conditions.
export function legacyObjectProjection(world,state,rules,id){
  const object=world.objects.find(o=>o.id===id);if(!object)throw new Error('Objekt nicht mehr vorhanden');
  return {object,building:world.buildings.find(b=>b.id===object.building_id),clock:state.clock,
    contents:[],contents_complete:false,users:state.actors.filter(a=>a.action?.target_id===id).map(a=>({actor_id:a.id,name:a.name,...a.action})),
    actions:Object.entries(rules.definitions.actions).filter(([,a])=>a.object_kinds?.includes(object.kind)).map(([id,a])=>({id,...a,duration_seconds:a.duration}))};
}

export function createObjectExplorer({world,getState,rules,renderer,onActor}){
  const panel=document.getElementById('object-explorer'),body=document.getElementById('object-explorer-body');
  let selected=null,mode='list',request=null,ticket=0,apiSupported=null,lastData=null;
  const fetchJSON=async(url,signal)=>{const response=await fetch(url,{signal});if(!response.ok)throw new Error(`Objektdaten nicht verfügbar (${response.status})`);return response.json()};
  function stop(){ticket++;request?.abort();request=null;}
  function close(){stop();panel.classList.add('hidden');renderer.selectedObject=null;}
  function show(){panel.classList.remove('hidden');document.querySelectorAll('.drawer').forEach(d=>d.classList.add('hidden'));}
  function renderList(){
    const query=document.getElementById('object-search').value.trim().toLocaleLowerCase();
    const matches=world.objects.filter(o=>`${o.name} ${o.kind} ${o.id} ${world.buildings.find(b=>b.id===o.building_id)?.name||''}`.toLocaleLowerCase().includes(query));
    body.innerHTML=`<p class="object-note">${matches.length} feste Objekte. Innenräume öffnen oder hier auswählen. Lose Gegenstände erscheinen als Containerinhalt.</p><div class="object-list">${matches.map(o=>`<button data-inspect-object="${esc(o.id)}"><strong>${esc(o.name)}</strong><span>${esc(world.buildings.find(b=>b.id===o.building_id)?.name||'Außenbereich')} · ${o.w} × ${o.h} m</span></button>`).join('')||'<p>Keine passenden Objekte.</p>'}</div>`;
  }
  function renderDetail(data){
    const o=data.object,oldScroll=body.scrollTop,rawOpen=body.querySelector('details')?.open;
    const daily=data.effective_daily||o.daily||{};
    const reservations=Object.entries(o.reservations||{}),available=Math.max(0,o.capacity-reservations.length);
    body.innerHTML=`<button class="object-back" data-object-list>← Alle Objekte</button><div class="object-title"><span class="eyebrow">${esc(data.building?.name||'Außenbereich')}</span><h2>${esc(o.name)}</h2><span>${esc(pretty(o.kind))} · ${esc(o.id)}</span></div>
      <div class="object-status"><b>Zustand ${Math.round(o.condition*100)}%</b><progress max="1" value="${o.condition}" aria-label="Objektzustand"></progress><span>${available} von ${o.capacity} Interaktionsplätzen unreserviert</span></div>
      ${rows([['Grundfläche',`${o.w} × ${o.h} m`],['Position',`${o.x}, ${o.y} · Ebene ${o.floor??0}`],['Bewegung',o.blocking===false?'Begehbar / Sitzplatz':'Blockierte Stellfläche'],['Interaktionsanker',(o.anchors||[]).map(a=>a.join(', ')).join(' · ')],['Objektversion',o.version??0]])}
      <h3>Nutzung & Reservierungen</h3>${data.users.map(a=>`<button class="object-person" data-object-person="${esc(a.actor_id)}">${esc(a.name)} ↗ <small>${esc(a.label)} · ${a.phase==='travel'?'unterwegs':'am Objekt'}</small></button>`).join('')||'<p class="object-note">Gerade keine aktive Nutzung.</p>'}
      ${reservations.map(([id,r])=>`<p class="object-note">${esc(getState().actors.find(a=>a.id===r.actor_id)?.name||r.actor_id)}: Anker ${esc(r.anchor?.join(', '))}, bis Weltsekunde ${esc(r.end)} <small>(${esc(id)})</small></p>`).join('')}
      <h3>Objektzustände</h3>${Object.keys(daily).length?rows(Object.entries(daily).map(([k,v])=>[pretty(k)+(data.default_daily_keys?.includes(k)?' (Regelstandard)':''),typeof v==='object'?JSON.stringify(v):v])):`<p class="object-note">${data.contents_complete?'Keine zusätzlichen Alltagszustände modelliert.':'Keine gespeicherten Alltagswerte. Regelstandardwerte sind über diese ältere Schnittstelle nicht vollständig verfügbar.'}</p>`}
      <h3>Konkreter Containerinhalt</h3>${!data.contents_complete?'<p class="object-note">Dieser laufende Server unterstützt noch keine vollständige Inhaltsprojektion. Objektzustände oben sind frisch geladen; Inhaltsdetails folgen nach Server-Neustart.</p>':data.contents.length?data.contents.map(i=>`<div class="object-item"><b>${esc(i.name||pretty(i.kind))}</b><small>${esc(i.id)} · ${esc(i.state?.stage||'')} · Verwahrung: ${esc(i.custodian_name)}</small></div>`).join(''):'<p class="object-note">Keine konkreten tragbaren Instanzen enthalten. Vorratszähler sind separat oben aufgeführt.</p>'}
      <h3>Implementierte Aktionsarten</h3><p class="object-note">Fähigkeiten dieses Objekttyps, keine Handlungsfreigabe für einen bestimmten Sim.</p>${data.actions.map(a=>`<div class="object-item"><b>${esc(a.label)}</b><small>${a.duration_seconds} Weltsekunden · ${esc(a.id)}</small></div>`).join('')||'<p class="object-note">Räumliches Objekt ohne zugeordnete Laufzeitaktion. Eine Katalogfunktion allein aktiviert noch kein Verhalten.</p>'}
      <details ${rawOpen?'open':''}><summary>Vollständiger Objektzustand</summary><pre>${esc(JSON.stringify(o,null,2))}</pre></details><p class="object-note">Nur Beobachtung · geladen bei Weltsekunde ${esc(data.clock)} · keine Veränderung durch Inspektion</p>`;
    body.scrollTop=oldScroll;
  }
  async function refresh(){
    if(mode!=='detail'||panel.classList.contains('hidden')||request)return;
    const id=selected,current=++ticket,controller=new AbortController();request=controller;
    try{
      if(apiSupported===null){const schema=await fetchJSON('/openapi.json',controller.signal);apiSupported=!!schema.paths?.['/api/objects/{oid}'];}
      const data=apiSupported?await fetchJSON('/api/objects/'+encodeURIComponent(id),controller.signal):legacyObjectProjection(await fetchJSON('/api/world',controller.signal),getState(),rules,id);
      if(current===ticket&&selected===id){const changed=JSON.stringify(lastData)!==JSON.stringify(data);lastData=data;if(changed)renderDetail(data);}
    }catch(error){if(error.name!=='AbortError'&&current===ticket)body.innerHTML=`<p role="alert">${esc(error.message)}. Die Welt wurde nicht verändert.</p><button data-object-list>Zur Liste</button>`;}
    finally{if(request===controller)request=null;}
  }
  function openObject(id,focus=false){
    const obj=world.objects.find(o=>o.id===id);if(!obj)return;
    stop();selected=id;mode='detail';lastData=null;show();panel.dataset.objectId=id;renderer.selectedObject=id;renderer.follow=false;
    document.getElementById('hover-label').classList.add('hidden');
    if(focus){if(obj.building_id){renderer.focusHome(obj.building_id);if(renderer.roofs==='closed'){renderer.roofs='auto';const toggle=document.getElementById('roof-toggle');toggle.querySelector('span').textContent='Auto roofs';toggle.classList.add('active')}}else{renderer.camera.x=(obj.x+obj.w/2)*24;renderer.camera.y=(obj.y+obj.h/2)*24;renderer.camera.zoom=1.4}}
    document.getElementById('object-search-wrap').classList.add('hidden');body.scrollTop=0;body.innerHTML='<p role="status">Objektzustand wird geladen …</p>';refresh();
  }
  function openList(){stop();mode='list';show();document.getElementById('object-search-wrap').classList.remove('hidden');renderList();document.getElementById('object-search').focus();}
  panel.addEventListener('click',event=>{const target=event.target.closest('button');if(!target)return;
    if(target.hasAttribute('data-object-close'))close();
    else if(target.hasAttribute('data-object-list'))openList();
    else if(target.dataset.inspectObject)openObject(target.dataset.inspectObject,true);
    else if(target.dataset.objectPerson){close();onActor(target.dataset.objectPerson)}
  });
  panel.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();close();document.getElementById('objects-toggle').focus()}});
  window.addEventListener('keydown',event=>{if(!event.defaultPrevented&&event.key==='Escape'&&!document.querySelector('dialog[open]'))close()});
  document.getElementById('object-search').addEventListener('input',renderList);
  setInterval(refresh,2000);
  return {openObject,openList,close,get selected(){return selected},get data(){return lastData}};
}
