// Presentation only: these components never change world or psychological state.
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=n=>Math.round((Number(n)||0)*100);
const name=k=>String(k).replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
const personName=(id,state)=>state.actors.find(a=>a.id===id)?.name||id;
const rows=items=>`<dl class="detail-list">${items.map(([k,v])=>`<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>`;

export function routineMarkup(p){
  if(!p.planned_steps?.length)return '';
  return `<section class="detail-block" data-life="routine"><h3>Ein Plan, mehrere Handgriffe</h3><p>${esc(name(p.routine.kind))} · ${esc(p.routine.status)} · ${Math.min(p.routine.index,p.planned_steps.length)} / ${p.planned_steps.length}</p><ol class="routine-steps">${p.planned_steps.map(s=>`<li class="${s.status}"><b>${s.status==='completed'?'✓ ':s.status==='next'?'→ ':''}${esc(s.label)}</b><small>${esc(s.target_name)} · ${esc(s.status)}</small></li>`).join('')}</ol><p class="coverage-note">Geplant ist nicht garantiert: Dringende Bedürfnisse können unterbrechen. Zutaten und Gegenstände bleiben dabei erhalten.</p></section>`;
}

export function psychologyMarkup(p,state){
  const ps=p.psychology;if(!ps)return '';
  const labels={openness:'Offenheit',conscientiousness:'Gewissenhaftigkeit',extraversion:'Extraversion',agreeableness:'Verträglichkeit',neuroticism:'Emotionale Reaktivität'};
  const known=Object.entries(ps.theory_of_mind?.known_people||{});
  return `<section class="detail-block" data-life="personality"><h3>Persönlichkeit · Big Five</h3><p>${(ps.traits||[]).map(esc).join(' · ')}</p>${Object.entries(ps.big_five).map(([k,v])=>`<div class="psych-trait"><label>${esc(labels[k]||k)} <b>${pct(v)}%</b></label><div class="progress-track"><span style="width:${pct(v)}%"></span></div></div>`).join('')}<p class="coverage-note">Spielparameter, keine psychologische Diagnose. Sie gewichten Entscheidungen, schreiben sie aber nicht vor.</p></section>
  <section class="detail-block" data-life="ambitions"><h3>Ambitionen & Hobbys</h3>${ps.ambitions.map(a=>`<div class="intent"><b>${esc(a.title)}</b><p>${pct(a.progress)}% · ${a.completed?'Erreicht':'Langfristiges Ziel'}</p><div class="progress-track"><span style="width:${pct(a.progress)}%"></span></div></div>`).join('')}${rows(ps.hobbies.map(h=>[name(h.kind),`${Math.round(h.practice_seconds/60)} min Praxis · ${pct(h.enjoyment)}% Vorliebe`]))}</section>
  <section class="detail-block" data-life="fears"><h3>Ängste & aktuelle Auslöser</h3>${ps.fears.map(f=>`<div class="belief"><p><b>${esc(name(f.kind))}</b> · ${pct(f.intensity)}%</p><small>${f.evidence_id?`Auslöser: ${esc(f.evidence_id)} · ${f.expires_at>p.clock?'aktiv':'abgeklungen'}`:'Disposition; noch kein beobachteter Auslöser'}</small></div>`).join('')}${ps.active_fear&&ps.active_fear.expires_at>p.clock?`<p class="thought-card">${esc(ps.active_fear.event)} · ${esc(ps.active_fear.source)}</p>`:''}</section>
  <section class="detail-block" data-life="tom"><h3>Was diese Person über andere vermutet</h3><p>Beobachtung und Deutung sind getrennt. Vermutungen können falsch sein.</p>${known.slice(-6).map(([id,k])=>`<div class="belief"><b>${esc(personName(id,state))}</b>${Object.values(k.inferences||{}).map(i=>`<p>${esc(i.value)} · ${esc(i.confidence)} confidence</p><small>${esc((i.evidence_ids||[]).join(', '))}</small>`).join('')}<details><summary>${k.observations.length} beobachtete Hinweise</summary>${k.observations.slice(-4).map(o=>`<p>${esc(o.observation)}<br><small>${esc(o.evidence_id)}</small></p>`).join('')}</details></div>`).join('')||'<p>Noch keine beobachteten sozialen Hinweise.</p>'}</section>`;
}

export function careerMarkup(p){
  const career=p.career;if(!career)return '';
  return `<section class="detail-block" data-life="career"><h3>Berufsweg · ${esc(career.job)}</h3>${rows([
    ['Aktuelle Aufgabe',career.task],['Stufe',career.level],
    ['Erfahrung',`${Number(career.experience_hours||0).toFixed(1)} Stunden · ${career.completed_shifts||0} abgeschlossene Einsätze`],
    ['Arbeitsqualität',`${pct(career.performance)}% · spielerischer Leistungswert`],
    ['Fachfertigkeit',`${name(career.skill)} · ${pct(p.skills?.[career.skill])}%`],
    ['Letzter Einsatz',career.last_shift==null?'Noch keiner':`Weltsekunde ${career.last_shift}`]
  ])}<p class="coverage-note">Fortschritt entsteht erst nach tatsächlich erreichter und abgeschlossener Arbeit am zugewiesenen Arbeitsplatz. Keine Berufsqualifikation in der realen Welt.</p></section>`;
}

export function relationshipsMarkup(p,state){
  const entries=Object.entries(p.relations||{});
  return `<section class="detail-block" data-life="relationships"><h3>Familie, Beziehungen & Bekanntschaften</h3>${rows([['Beziehungsstatus',name(p.family?.relationship_status||'unspecified')],['Partner',p.family?.partner_id?personName(p.family.partner_id,state):'Nicht hinterlegt'],['Eltern',(p.family?.parent_ids||[]).map(id=>personName(id,state)).join(', ')||'Nicht hinterlegt']])}<p class="coverage-note">Ein gemeinsamer Haushalt bedeutet nicht automatisch Verwandtschaft. Alte Spielstände behalten ihre Biografien; unbekannte Familienbeziehungen werden nicht erfunden.</p>${entries.map(([id,r])=>`<details class="relationship-detail"><summary>${esc(personName(id,state))} · ${esc(Object.entries(r.layers||{}).filter(([_,v])=>v.status!=='none').map(([k,v])=>`${name(k)}: ${name(v.status)}`).join(' · ')||r.kind)}</summary>${rows(['closeness','trust','respect','attraction','tension'].map(k=>[name(k),pct(r[k])+'%']))}<button class="small-button" data-related-person="${esc(id)}">Person ansehen</button></details>`).join('')}</section>`;
}

export function householdMarkup(p){
  return `<section class="detail-block" data-life="household"><h3>Haushalt · tatsächlicher Zustand</h3>${(p.household_objects||[]).map(o=>`<details><summary>${esc(o.name)}</summary>${rows(Object.entries(o.daily).map(([k,v])=>[name(k),v]))}</details>`).join('')}</section><section class="detail-block" data-life="social-categories"><h3>20 soziale Interaktionskategorien</h3><p>Verfügbarkeit hängt von Beziehung, Situation und Zustimmung ab.</p><div class="social-chips">${Object.entries(p.social_categories||{}).map(([k,v])=>`<span title="${esc(k)} · ${v.duration_seconds} s">${esc(v.label)}</span>`).join('')}</div></section>`;
}
