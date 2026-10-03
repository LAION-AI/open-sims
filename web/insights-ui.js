const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const pct=value=>Math.round(Number(value||0)*100);
const stageNames={child:'Kinder',teen:'Teenager',adult:'Erwachsene',elder:'Senior:innen'};
const eventNames={drama:'⚡ Drama',intrigue:'🕵️ Intrige',romance:'💕 Liebe',event:'🎉 Veranstaltung',social:'💬 Sozial',career:'💼 Beruf',life:'🌿 Alltag'};
const actorButton=(id,name)=>`<button class="insights-person" data-insights-person="${escapeHtml(id)}">${escapeHtml(name)} ↗</button>`;
const bar=(label,count,max,sub='')=>`<div class="insights-bar"><span>${escapeHtml(label)}</span><div><i style="width:${Math.round(100*count/Math.max(max,1))}%"></i></div><b>${count}</b>${sub?`<small>${escapeHtml(sub)}</small>`:''}</div>`;
const empty=text=>`<p class="insights-empty">${escapeHtml(text)}</p>`;

function liveView(data){
  const featured=data.events.filter(event=>['drama','intrigue','romance','event','social'].includes(event.kind)).slice(0,9);
  return `<div class="insights-kpis"><article><strong>${data.population}</strong><span>Menschen</span></article><article><strong>${data.households}</strong><span>Wohneinheiten</span></article><article><strong>${pct(data.wellbeing)}%</strong><span>Wohlbefinden</span></article><article><strong>${data.active_social.length}</strong><span>soziale Aktionen jetzt</span></article></div>
    <div class="insights-grid"><section><h3>Jetzt zusammen</h3>${data.active_social.length?data.active_social.slice(0,12).map(item=>`<article class="insights-feed"><div><b>💬 ${escapeHtml(item.label)}</b><small>${escapeHtml(item.building)}</small></div><p>${actorButton(item.id,item.name)}${item.target_id?' mit '+actorButton(item.target_id,item.target_name):''}</p></article>`).join(''):empty('Gerade läuft keine soziale Aktion. Die Welt verändert sich weiter.')}</section>
    <section><h3>Interessante Wendungen</h3>${featured.length?featured.map(item=>`<article class="insights-feed"><div><b>${eventNames[item.kind]}</b><small>Tag ${Math.floor(item.at/86400)+1} · ${String(Math.floor(item.at/3600)%24).padStart(2,'0')}:${String(Math.floor(item.at/60)%60).padStart(2,'0')}</small></div><p>${escapeHtml(item.text)}</p><div class="insights-people">${item.participants.slice(0,3).map(person=>actorButton(person.id,person.name)).join('')}</div></article>`).join(''):empty('Noch kein soziales Ereignis im jüngsten Journal.')}</section></div>`;
}

function socialView(data){
  const keys=[['family','Familienbindungen'],['romance','romantische Bindungen'],['friendship','Freundschaften'],['coworker','Kolleg:innen'],['rivalry','Rivalitäten']];
  const max=Math.max(1,...keys.map(([key])=>data.relationship_counts[key]||0));
  const tense=data.relationships.filter(item=>item.tension>=.35).slice(0,8);
  const close=data.relationships.filter(item=>item.closeness>=.5).slice(0,8);
  const ties=items=>items.map(item=>`<article class="insights-tie"><p>${actorButton(item.a,item.a_name)} <span>↔</span> ${actorButton(item.b,item.b_name)}</p><small>${item.kinds.map(kind=>escapeHtml(kind)).join(' · ')} · Nähe ${pct(item.closeness)}% · Spannung ${pct(item.tension)}%</small></article>`).join('');
  return `<div class="insights-grid"><section><h3>Beziehungsnetz</h3>${keys.map(([key,label])=>bar(label,data.relationship_counts[key]||0,max)).join('')}<p class="insights-note">Bindungen können mehreren Kategorien zugleich angehören. Es sind bekannte, gespeicherte Beziehungen.</p></section><section><h3>Spannung & Nähe</h3><h4>Reibung</h4>${tense.length?ties(tense):empty('Zurzeit keine besonders angespannte bekannte Beziehung.')}<h4>Enge Verbindungen</h4>${close.length?ties(close):empty('Noch keine enge Verbindung erfasst.')}</section></div>`;
}

function peopleView(data){
  const stages=data.demographics;
  return `<div class="insights-grid"><section><h3>Generationen</h3>${stages.map(item=>bar(stageNames[item.stage],item.count,data.population,`Wohlbefinden ${pct(item.wellbeing)}% · häufigste Stimmung: ${item.moods[0]?.name||'–'}`)).join('')}<h3>Stimmungslage</h3>${data.moods.map(item=>bar(item.name,item.count,data.population)).join('')}</section><section><h3>Wer ist wo?</h3>${data.buildings.length?data.buildings.map(place=>`<details class="insights-place"><summary><strong>${escapeHtml(place.name)}</strong><span>${place.occupants.length} vor Ort</span></summary><div>${place.occupants.map(person=>actorButton(person.id,person.name)).join('')}</div></details>`).join(''):empty('Gerade ist niemand in einem Gebäude.')}<p class="insights-note">Anwesenheit basiert auf der aktuellen Kartenposition, nicht auf der Meldeadresse.</p></section></div>`;
}

function careersView(data){
  const max=Math.max(1,...data.professions.map(item=>item.count));
  return `<div class="insights-grid"><section><h3>Berufe</h3>${data.professions.map(item=>bar(item.name,item.count,max)).join('')}</section><section><h3>Persönliche Ambitionen</h3>${data.ambitions.map(item=>`<article class="insights-ambition"><p>${actorButton(item.id,item.name)}<span>${pct(item.progress)}%</span></p><strong>${escapeHtml(item.title)}</strong><div class="insights-progress"><i style="width:${pct(item.progress)}%"></i></div></article>`).join('')||empty('Noch keine offenen Ambitionen.')}</section></div>`;
}

export function createInsightsOverlay({onSelect}){
  const dialog=document.getElementById('insights-dialog');
  const body=document.getElementById('insights-body');
  let tab='live',data=null,request=0;
  function render(){if(!data)return;body.innerHTML=({live:liveView,social:socialView,people:peopleView,careers:careersView})[tab](data);body.querySelectorAll('[data-insights-person]').forEach(button=>button.addEventListener('click',()=>{dialog.close();onSelect(button.dataset.insightsPerson)}));}
  async function refresh(){const own=++request;try{const response=await fetch('/api/insights',{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);const value=await response.json();if(own!==request||!dialog.open)return;data=value;render();document.getElementById('insights-caption').textContent=`Tag ${Math.floor(data.clock/86400)+1} · ${String(Math.floor(data.clock/3600)%24).padStart(2,'0')}:${String(Math.floor(data.clock/60)%60).padStart(2,'0')} · Aus dem laufenden Spielstand`;}catch(error){if(dialog.open)body.innerHTML=empty(error.message==='HTTP 404'?'Der laufende Python-Server verwendet noch den alten API-Code. Bitte den Server beenden und neu starten; dann sind die Live-Einblicke verfügbar.':`Einblicke derzeit nicht erreichbar: ${error.message}`)}}
  function open(initialTab='live'){tab=initialTab;document.querySelectorAll('[data-insights-tab]').forEach(button=>button.classList.toggle('active',button.dataset.insightsTab===tab));if(!dialog.open)dialog.showModal();document.getElementById('insights-toggle').classList.add('active');body.innerHTML=empty('Die Nachbarschaft wird ausgewertet …');refresh()}
  document.getElementById('insights-toggle').addEventListener('click',()=>open());
  dialog.addEventListener('close',()=>document.getElementById('insights-toggle').classList.remove('active'));
  document.getElementById('insights-close').addEventListener('click',()=>dialog.close());
  document.getElementById('insights-refresh').addEventListener('click',refresh);
  document.querySelectorAll('[data-insights-tab]').forEach(button=>button.addEventListener('click',()=>{tab=button.dataset.insightsTab;document.querySelectorAll('[data-insights-tab]').forEach(item=>item.classList.toggle('active',item===button));render()}));
  setInterval(()=>{if(dialog.open)refresh()},5000);
  return {open,refresh};
}
