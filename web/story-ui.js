// Read-only projections of authored and event-derived resident state.
import {drawPortrait,emotionGlyph} from './renderer.js';
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=value=>Math.round(Math.max(0,Math.min(1,Number(value)||0))*100);
const plain=value=>String(value??'').replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
const nameOf=(id,state)=>state?.actors?.find(actor=>actor.id===id)?.name||id;
export function portraitUrl(appearance,width=54,height=64){
  if(!appearance)return '';
  const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
  const context=canvas.getContext('2d');context.imageSmoothingEnabled=false;
  context.fillStyle='#e8eedc';context.fillRect(0,0,width,height);
  context.fillStyle='#d5e1cd';context.fillRect(0,height*.76,width,height*.24);
  drawPortrait(context,appearance,width/2,height+2,{scale:height/31});
  return canvas.toDataURL('image/png');
}
const posLabel=(item,world)=>{
  const place=item.location||{},id=place.id;
  if(place.type==='worn')return `Getragen · ${plain(place.slot||item.kind)}`;
  if(place.type==='carried')return 'Wird mitgetragen';
  if(place.type==='consumed')return 'Verbraucht';
  if(place.type==='container')return `Liegt in ${world?.objects?.find(o=>o.id===id)?.name||world?.buildings?.find(b=>b.id===id)?.name||id||'einem Behälter'}`;
  return plain(place.type||'Unbekannt');
};

export function affectMarkup(person,{compact=false}={}){
  const affect=person?.affect;
  const states=Array.isArray(affect?.states)?affect.states:[];
  if(!affect||!states.length){
    const legacy=person?.emotion;
    return `<section class="story-affect ${compact?'compact':''}" data-story="affect"><div class="section-heading">Gefühlslage <span class="subtle">MODELL</span></div><p class="story-muted">${legacy?.type?`Bisherige Anzeige: ${esc(legacy.type)}. Weitere belegte Gefühlszustände liegen in diesem Spielstand nicht vor.`:'Noch keine belegten Gefühlszustände.'}</p></section>`;
  }
  const cards=(compact?states.slice(0,3):states).map(s=>{
    const causes=(s.causes||[]).map(c=>`<li>${esc(c.text||c.kind||'Ereignis')}${c.evidence_id?` <small>· ${esc(c.evidence_id)}</small>`:''}</li>`).join('');
    return `<article class="affect-card" data-affect-id="${esc(s.id)}"><div class="affect-card-heading"><span class="affect-glyph" aria-hidden="true">${esc(emotionGlyph(s.id))}</span><strong>${esc(s.label_de||s.label||plain(s.id))}</strong><b>${pct(s.intensity)}%</b></div><div class="affect-meter" role="meter" aria-label="${esc(s.label_de||s.label||s.id)} Intensität" aria-valuenow="${pct(s.intensity)}" aria-valuemin="0" aria-valuemax="100"><span style="width:${pct(s.intensity)}%"></span></div>${!compact&&causes?`<ul class="affect-causes">${causes}</ul>`:''}</article>`;
  }).join('');
  const primary=states.find(s=>s.id===affect.primary)||states[0];
  return `<section class="story-affect ${compact?'compact':''}" data-story="affect"><div class="section-heading">Mehrere Gefühle zugleich <span class="subtle">${states.length} AKTIV</span></div><p class="story-primary">Im Vordergrund: <b>${esc(primary.label_de||primary.label||plain(primary.id))}</b></p><div class="affect-cards">${cards}</div>${compact&&states.length>3?`<p class="story-muted">+${states.length-3} weitere im Tab „Inner life“</p>`:''}${!compact?`<div class="narrative-pair"><div><span>Belegte Modelllage</span><p>${esc(affect.actual_narrative||'Keine belegte Modelllage.')}</p></div><div><span>Eigene Deutung</span><p>${esc(affect.self_narrative||'Keine Selbstdeutung hinterlegt.')}</p></div></div><p class="story-disclaimer">Fiktionale Spielzustände, keine Diagnose oder direkte Einsicht in ein Bewusstsein.</p>`:''}</section>`;
}

export function possessionsMarkup(person,world){
  const items=Array.isArray(person?.belongings)?person.belongings:[];
  if(!items.length)return `<section class="detail-block story-possessions" data-story="possessions"><h3>Konkrete Dinge & Kleidung</h3><p class="story-muted">Für diesen Spielstand sind noch keine Gegenstandsinstanzen hinterlegt.</p></section>`;
  const active=items.filter(i=>i.location?.type!=='consumed');
  const spent=items.filter(i=>i.location?.type==='consumed');
  const outfit=person.appearance?.outfit||{};
  const slots=['top','trousers','shoes','outerwear'];
  const slotLabels={top:'Oberteil',trousers:'Hose',shoes:'Schuhe',outerwear:'Jacke'};
  const clothing=slots.map(slot=>{
    const item=active.find(i=>i.kind===slot&&i.location?.type==='worn')||outfit[slot];
    return `<div class="outfit-piece"><i style="background:${esc(item?.state?.color||item?.color||'#d5d8ca')}"></i><span>${slotLabels[slot]}</span><strong>${esc(item?.label||'Nicht getragen')}</strong></div>`;
  }).join('');
  const itemRows=active.map(i=>`<li class="possession-row"><span class="possession-icon ${esc(i.kind)}" aria-hidden="true">${esc(itemGlyph(i.kind))}</span><div><strong>${esc(i.label||plain(i.kind))}</strong><small>${esc(posLabel(i,world))}${i.state?.stage?` · ${esc(plain(i.state.stage))}`:''}${i.state?.ready_at?` · Ofen bereit um ${esc(new Date(i.state.ready_at*1000).toISOString().slice(11,16))}`:''}</small></div><code>${esc(i.id)}</code></li>`).join('');
  return `<section class="detail-block story-possessions" data-story="possessions"><h3>Konkrete Dinge & Kleidung</h3><p class="story-muted">Jedes Stück hat eine eigene ID und einen Ort. Besitz und Tragen sind verschieden.</p>${person.last_meal?`<p>🍽️ Zuletzt gegessen: <strong>${esc(person.last_meal.label)}</strong></p>`:''}<div class="outfit-grid">${clothing}</div><ul class="possession-list">${itemRows}</ul>${spent.length?`<details><summary>${spent.length} verbrauchte Dinge im aktuellen Verlauf</summary><ul class="possession-list spent">${spent.slice(-12).reverse().map(i=>`<li class="possession-row"><span>${esc(itemGlyph(i.kind))}</span><div><strong>${esc(i.label)}</strong><small>${esc(i.id)}</small></div></li>`).join('')}</ul></details>`:''}</section>`;
}

function itemGlyph(kind){return ({pizza:'◉',pancake:'◍',egg:'●',tomato:'●',vegetable:'✿',dough:'◔',dirty_dish:'◯',top:'▣',trousers:'▥',shoes:'⌁',outerwear:'▣'})[kind]||'◇'}

const relationLabel={friendship:'Freundschaft',romance:'Romantik',romantic:'Romantik',family:'Familie',work:'Arbeit',coworker:'Kollegium',household:'Haushalt',acquaintance:'Bekanntschaft',partnership:'Partnerschaft',marriage:'Ehe'};
function typeText(type){return relationLabel[type]||plain(type)}
const roleLabel={spouse:'Ehepartner:in',partner:'Partner:in',romantic_interest:'Romantisches Interesse',parent:'Elternteil',child:'Kind',grandparent:'Großelternteil',grandchild:'Enkelkind',sibling:'Geschwister',cousin:'Cousin/Cousine',aunt_uncle:'Tante/Onkel',niece_nephew:'Nichte/Neffe',friend:'Freund:in',coworker:'Kolleg:in',housemate:'Mitbewohner:in',rival:'Rival:in',acquaintance:'Bekanntschaft'};
const feelingLabel={tense:'angespannt',competitive:'wetteifernd',attracted:'angezogen',close_and_trusting:'nah & vertrauensvoll',respectful:'respektvoll',warm:'zugewandt',reserved:'zurückhaltend'};
const roleText=e=>(e.roles||[]).map(role=>roleLabel[role]||plain(role)).join(' · ')||'Bekanntschaft';
const feelingText=key=>feelingLabel[key]||'nicht eingeordnet';
function relationColor(types=[]){
  if(types.some(t=>['romance','romantic','marriage','partnership'].includes(t)))return '#c8798f';
  if(types.includes('family'))return '#c3a264';
  if(types.includes('friendship'))return '#7199b2';
  if(types.some(t=>['coworker','work'].includes(t)))return '#79a586';
  if(types.includes('household'))return '#a59882';
  return '#9aa697';
}
function edgesFor(person){
  const graph=person?.social_graph||{};
  const viewer=graph.viewer_id||person?.id;
  const listed=new Set((graph.nodes||[]).map(n=>n.id));
  return (graph.edges||[]).filter(e=>e.source===viewer&&listed.has(e.target));
}
function graphSvg(person,state,edges){
  const cx=370,cy=255;
  const sorted=[...edges].sort((a,b)=>(b.importance||0)-(a.importance||0)||a.target.localeCompare(b.target));
  const n=sorted.length;
  const marks=sorted.map((edge,index)=>{
    const angle=-Math.PI/2+index*2*Math.PI/Math.max(1,n);
    const radius=n>12?(index%2?217:154):n>7?190:170;
    const x=cx+Math.cos(angle)*radius,y=cy+Math.sin(angle)*radius;
    const importance=pct(edge.importance);
    const color=relationColor(edge.relationship_types);
    const label=nameOf(edge.target,state).split(' ')[0];
    const appearance=state?.actors?.find(a=>a.id===edge.target)?.appearance;
    const photo=portraitUrl(appearance,48,48);
    const clip=`relation-clip-${edge.target}`;
    return `<g><line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" class="relation-edge" stroke="${color}" stroke-width="${(1.2+importance/42).toFixed(1)}"/><g class="relation-node" data-graph-person="${esc(edge.target)}" role="button" tabindex="0" aria-label="${esc(nameOf(edge.target,state))}: ${esc(roleText(edge))}; eigene Haltung ${esc(feelingText(edge.feeling))}; Gegenrichtung ${esc(edge.reciprocal?feelingText(edge.reciprocal.feeling):'nicht dokumentiert')}"><defs><clipPath id="${esc(clip)}"><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="21"/></clipPath></defs><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="25" fill="${color}"/>${photo?`<image href="${photo}" x="${(x-21).toFixed(1)}" y="${(y-21).toFixed(1)}" width="42" height="42" clip-path="url(#${esc(clip)})"/>`:`<text x="${x.toFixed(1)}" y="${(y+4).toFixed(1)}" class="relation-initial">${esc(label.slice(0,1))}</text>`}<text x="${x.toFixed(1)}" y="${(y+39).toFixed(1)}" class="relation-name">${esc(label.slice(0,13))}</text><text x="${x.toFixed(1)}" y="${(y+53).toFixed(1)}" class="relation-role">${esc((edge.roles||[]).map(r=>roleLabel[r]||plain(r)).slice(0,1).join('').slice(0,17))}</text></g></g>`;
  }).join('');
  const self=nameOf(person.id,state).split(' ')[0];
  const selfPhoto=portraitUrl(person.appearance,64,64);
  return `<svg class="relation-svg" viewBox="0 0 740 515" role="group" aria-label="Beziehungsnetz von ${esc(person.name)} mit ${edges.length} belegten eigenen Beziehungen"><title>Nur Beziehungen aus Sicht von ${esc(person.name)}</title>${marks}<defs><clipPath id="relation-ego-clip"><circle cx="${cx}" cy="${cy}" r="32"/></clipPath></defs><circle cx="${cx}" cy="${cy}" r="36" class="relation-ego"/>${selfPhoto?`<image href="${selfPhoto}" x="${cx-32}" y="${cy-32}" width="64" height="64" clip-path="url(#relation-ego-clip)"/>`:`<text x="${cx}" y="${cy+5}" class="relation-ego-text">${esc(self.slice(0,12))}</text>`}<text x="${cx}" y="${cy+53}" class="relation-name">${esc(self.slice(0,14))}</text></svg>`;
}
function relationRows(person,state,edges){
  if(!edges.length)return '<p class="story-muted">Keine passenden belegten Beziehungen.</p>';
  return edges.map(e=>{
    const q=e.qualities||{},reverse=e.reciprocal,other=nameOf(e.target,state).split(' ')[0];
    return `<article class="relation-list-row"><button data-graph-person="${esc(e.target)}"><span class="relation-avatar">${esc(nameOf(e.target,state).slice(0,1))}</span><span><strong>${esc(nameOf(e.target,state))}</strong><small>${esc(roleText(e))} · Bedeutung ${pct(e.importance)}%</small></span><span aria-hidden="true">↗</span></button><div class="relation-feelings"><div><b>${esc(person.name.split(' ')[0])} → ${esc(other)}</b><span>${esc(feelingText(e.feeling))}</span></div><div><b>${esc(other)} → ${esc(person.name.split(' ')[0])}</b><span>${esc(reverse?feelingText(reverse.feeling):'nicht dokumentiert')}</span></div></div><details class="relation-score-details"><summary>Beziehungswerte ansehen</summary><div class="relation-qualities">${[['Nähe','closeness'],['Vertrauen','trust'],['Respekt','respect'],['Anziehung','attraction'],['Spannung','tension'],['Rivalität','rivalry']].map(([label,key])=>`<span title="${esc(label)}: ${pct(q[key])}% / ${reverse?pct(reverse.qualities[key])+'%':'unbekannt'}">${label} <b>${pct(q[key])}% / ${reverse?pct(reverse.qualities[key])+'%':'–'}</b></span>`).join('')}</div><small>Werte: ${esc(person.name.split(' ')[0])} / ${esc(other)}. Dies sind längerfristige Beziehungswerte, keine augenblicklichen Emotionen.</small></details></article>`;
  }).join('');
}

let relationContext=null;
export function openRelationships(person,state,onSelect){
  const dialog=document.getElementById('relationships-dialog');
  if(!dialog||!person)return;
  relationContext={person,state,onSelect};
  const graph=person.social_graph||{};
  const edges=edgesFor(person);
  const types=[...new Set(edges.flatMap(e=>e.relationship_types||[]))].sort();
  dialog.innerHTML=`<div class="relationship-modal" role="document"><header><div><span class="eyebrow">SOZIALES NETZ · BEIDE RICHTUNGEN</span><h2>${esc(person.name)}s Beziehungen</h2><p>Rollen und längerfristige Beziehungswerte aus beiden Perspektiven. Aktuelle Emotionen und Gedanken anderer bleiben privat; fehlende Rückmeldungen werden nicht erfunden.</p></div><button class="relation-close" type="button" aria-label="Beziehungen schließen">×</button></header><div class="relation-tools"><label>Person suchen<input id="relation-search" type="search" placeholder="Name suchen…"></label><label>Art filtern<select id="relation-type"><option value="">Alle Beziehungen</option>${types.map(type=>`<option value="${esc(type)}">${esc(typeText(type))}</option>`).join('')}</select></label><span id="relation-count">${edges.length} Beziehungen</span></div><div class="relation-legend" aria-label="Beziehungsfarben"><span><i style="background:#c3a264"></i>Familie</span><span><i style="background:#c8798f"></i>Romantik</span><span><i style="background:#7199b2"></i>Freundschaft</span><span><i style="background:#79a586"></i>Kollegium</span><span><i style="background:#a59882"></i>Haushalt</span></div><div class="relation-layout"><div id="relation-graph">${graphSvg(person,state,edges)}</div><div class="relation-side"><h3>Rollen & Gefühle zueinander</h3><div id="relation-list">${relationRows(person,state,edges)}</div>${graph.observed_not_known?.length?`<details class="observed-only"><summary>${graph.observed_not_known.length} beobachtet, ohne belegte Beziehung</summary><p>${graph.observed_not_known.map(id=>esc(nameOf(id,state))).join(', ')}</p></details>`:''}</div></div></div>`;
  if(graph.heard_of_not_known?.length){
    const hearsay=graph.heard_of_not_known.map(h=>`<li>${esc(nameOf(h.id,state))} · erzählt von ${esc(nameOf(h.source_id,state))} · unsicher</li>`).join('');
    dialog.querySelector('.relation-side').insertAdjacentHTML('beforeend',`<details class="observed-only"><summary>Vom Hörensagen · keine persönliche Beziehung (${graph.heard_of_not_known.length})</summary><ul>${hearsay}</ul></details>`);
  }
  if(typeof dialog.showModal==='function')dialog.showModal();else dialog.setAttribute('open','');
  dialog.querySelector('.relation-close').onclick=()=>closeRelationships();
  dialog.onclick=event=>{if(event.target===dialog)closeRelationships()};
  const refresh=()=>{
    const search=dialog.querySelector('#relation-search').value.trim().toLocaleLowerCase();
    const type=dialog.querySelector('#relation-type').value;
    const filtered=edges.filter(e=>(!type||(e.relationship_types||[]).includes(type))&&
      (!search||nameOf(e.target,state).toLocaleLowerCase().includes(search)));
    dialog.querySelector('#relation-count').textContent=`${filtered.length} von ${edges.length} Beziehungen`;
    dialog.querySelector('#relation-graph').innerHTML=graphSvg(person,state,filtered);
    dialog.querySelector('#relation-list').innerHTML=relationRows(person,state,filtered);
  };
  dialog.querySelector('#relation-search').oninput=refresh;
  dialog.querySelector('#relation-type').onchange=refresh;
  dialog.addEventListener('click',onGraphClick);
  dialog.addEventListener('keydown',onGraphKey);
}
function onGraphClick(event){
  const target=event.target.closest('[data-graph-person]');
  if(target)selectRelated(target.getAttribute('data-graph-person'));
}
function onGraphKey(event){
  if((event.key==='Enter'||event.key===' ')&&event.target.closest('[data-graph-person]')){
    event.preventDefault();selectRelated(event.target.closest('[data-graph-person]').getAttribute('data-graph-person'));
  }
}
function selectRelated(id){const context=relationContext;closeRelationships();context?.onSelect?.(id)}
export function closeRelationships(){
  const dialog=document.getElementById('relationships-dialog');
  if(!dialog)return;
  dialog.removeEventListener('click',onGraphClick);
  dialog.removeEventListener('keydown',onGraphKey);
  if(dialog.open&&typeof dialog.close==='function')dialog.close();else dialog.removeAttribute('open');
  relationContext=null;
}
