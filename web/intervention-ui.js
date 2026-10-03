const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels={small_talk:'Plaudern',phone_call:'Anrufen',deep_talk:'Tiefes Gespräch',comfort:'Trösten',ask_favor:'Um Hilfe bitten',offer_help:'Hilfe anbieten',collaborate_project:'Gemeinsam arbeiten',persuade:'Überzeugen',make_plans:'Pläne schmieden',invite_to_dinner:'Zum Essen einladen',tell_story:'Geschichte erzählen',tease:'Necken',debate:'Diskutieren',provoke:'Provozieren',argue:'Streit anfangen',flirt:'Flirten',joke:'Scherzen',gossip:'Tratschen',play:'Zusammen spielen',compliment:'Kompliment',apologize:'Entschuldigen',ask_on_date:'Date vorschlagen',kiss:'Küssen'};
const name=key=>labels[key]||key.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());

export function createInterventions({getPerson,onSubmitted,toast}){
  const dialog=document.getElementById('intervention-dialog');
  let data=null,tab='contacts',contact=null,query='',submitting=false;
  async function request(path,body){const response=await fetch(path,body===undefined?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!response.ok){let error=`HTTP ${response.status}`;try{error=(await response.json()).detail||error}catch{}throw new Error(error)}return response.json()}
  function render(){
    if(!data)return;
    const person=getPerson();
    const available=data.owner==='procedural'&&!data.fault;
    const notice=data.fault?`Die Simulation ist angehalten: ${data.fault}. Bitte Speicherplatz und Serverstatus prüfen.`:data.owner==='procedural'?'Der Vorschlag gilt für die nächste freie Entscheidung. Der andere Sim kann ablehnen.':'Externe KI-Steuerung ist aktiv. Wechsle im Sim-Profil zur prozeduralen Steuerung, um Empfehlungen zu geben.';
    const contacts=data.contacts.filter(row=>row.name.toLowerCase().includes(query.toLowerCase()));
    const selected=contacts.find(row=>row.id===contact);
    const contactList=`<div class="intervention-contact-list">${contacts.map(row=>`<button type="button" data-contact="${escapeHtml(row.id)}" class="${row.id===contact?'active':''}"><b>${escapeHtml(row.name)}</b><small>${row.nearby?'In der Nähe':'Per Telefon erreichbar'} · ${escapeHtml(row.relationship)}</small></button>`).join('')||'<p>Gerade ist niemand erreichbar. Versuche es später erneut.</p>'}</div>`;
    const conversation=selected?`<section class="intervention-choice"><h3>Mit ${escapeHtml(selected.name)} …</h3><p>${selected.nearby?'Eine Begegnung in Sichtweite.':'Ein Telefonat kann die Entfernung überbrücken.'}</p><div class="intervention-options">${selected.categories.map(category=>`<button type="button" data-conversation="${escapeHtml(category)}" ${available?'':'disabled'}>${escapeHtml(name(category))}</button>`).join('')}</div></section>`:'<section class="intervention-choice"><p>Wähle eine Person. Die verfügbaren Gesprächsarten hängen von Ort, Beziehung, Alter und Situation ab.</p></section>';
    const places=data.places.filter(row=>`${row.label} ${row.object}`.toLowerCase().includes(query.toLowerCase()));
    const placeList=`<div class="intervention-places">${places.map(row=>`<button type="button" data-place-action="${escapeHtml(row.action)}" data-place-target="${escapeHtml(row.target_id)}" ${available?'':'disabled'}><strong>${escapeHtml(row.label)}</strong><small>${escapeHtml(row.object)}</small></button>`).join('')||'<p>Gerade kein passender Ort erreichbar oder geöffnet.</p>'}</div>`;
    dialog.innerHTML=`<div class="intervention-shell"><header><div><span class="eyebrow">SPIELER-EINFLUSS · ${escapeHtml(person?.name||'SIM')}</span><h2>Was soll als Nächstes passieren?</h2><p>${escapeHtml(notice)}</p></div><button type="button" data-intervention-close aria-label="Schließen">×</button></header><nav><button type="button" data-intervention-tab="contacts" class="${tab==='contacts'?'active':''}">💬 Kontakt & Gespräch</button><button type="button" data-intervention-tab="places" class="${tab==='places'?'active':''}">📍 Wohin gehen?</button></nav><label class="intervention-search">${tab==='contacts'?'Person suchen':'Ort oder Aktivität suchen'}<input type="search" id="intervention-search" value="${escapeHtml(query)}" placeholder="Suchen …"></label><div class="intervention-body">${tab==='contacts'?`<div class="intervention-columns">${contactList}${conversation}</div>`:placeList}</div><p id="intervention-status" role="status"></p></div>`;
    dialog.querySelector('[data-intervention-close]').onclick=()=>dialog.close();
    dialog.querySelectorAll('[data-intervention-tab]').forEach(button=>button.onclick=()=>{tab=button.dataset.interventionTab;query='';render()});
    dialog.querySelector('#intervention-search').oninput=event=>{const cursor=event.target.selectionStart;query=event.target.value;render();const input=dialog.querySelector('#intervention-search');input.focus();input.setSelectionRange(cursor,cursor)};
    dialog.querySelectorAll('[data-contact]').forEach(button=>button.onclick=()=>{contact=button.dataset.contact;render()});
    dialog.querySelectorAll('[data-conversation]').forEach(button=>button.onclick=()=>submit('chat',contact,button.dataset.conversation));
    dialog.querySelectorAll('[data-place-action]').forEach(button=>button.onclick=()=>submit(button.dataset.placeAction,button.dataset.placeTarget));
  }
  async function submit(action,target_id,social_category=null){
    if(submitting)return;
    submitting=true;
    const status=dialog.querySelector('#intervention-status');
    status.textContent='Vorschlag wird geprüft …';
    const waiting=setTimeout(()=>{if(dialog.open&&submitting)status.textContent='Die Simulation ist beschäftigt; dein Vorschlag wird noch geprüft …'},2500);
    try{
      await request('/api/player/recommendations',{actor_id:data.actor_id,action,target_id,social_category,ttl_seconds:3600});
      dialog.close();toast('Vorgemerkt: '+name(social_category||action)+' · beim nächsten freien Moment.');
      Promise.resolve(onSubmitted()).catch(error=>toast(error.message));
    }catch(error){status.innerHTML=`${escapeHtml(error.message)} <button type="button" data-intervention-refresh>Liste aktualisieren</button>`;status.querySelector('[data-intervention-refresh]').onclick=refresh}
    finally{clearTimeout(waiting);submitting=false}
  }
  async function refresh(){
    if(!dialog.open)return;
    try{data=await request(`/api/actors/${getPerson().id}/interventions`);if(!dialog.open)return;render()}
    catch(error){dialog.innerHTML=`<div class="intervention-shell"><button type="button" data-intervention-close>Schließen</button><p>Menü derzeit nicht erreichbar: ${escapeHtml(error.message)}</p><p>Bei HTTP 404 bitte den lokalen Python-Server neu starten, damit die aktuelle API geladen wird.</p></div>`;dialog.querySelector('[data-intervention-close]').onclick=()=>dialog.close()}
  }
  function open(){data=null;contact=null;query='';tab='contacts';if(!dialog.open)dialog.showModal();dialog.innerHTML='<div class="intervention-shell"><p>Erreichbare Kontakte und Orte werden gesucht …</p></div>';refresh()}
  return {open,refresh,close:()=>dialog.close()};
}
