"""Measure the executed life system and render its standalone HTML supplement."""
import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import platform
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from living_world.engine import World
from living_world.psychology import social_category_definitions


def measure(hours,seed):
    with tempfile.TemporaryDirectory() as directory:
        world=World(seed=seed,database=Path(directory)/'evaluation.sqlite3')
        try:
            started=time.perf_counter();errors=[];max_queue=0
            for step in range(hours*12):
                world.advance(300)
                errors.extend(world.invariants());max_queue=max(max_queue,len(world.queue))
                if (step+1)%72==0:
                    world.save()
                    print(json.dumps({'hours':(step+1)/12,'elapsed_seconds':round(time.perf_counter()-started,2),'beats':world.store.sequence}),flush=True)
            elapsed=time.perf_counter()-started
            current_actions={};completed=Counter();accepted=Counter();declined=Counter();rules=Counter();examples=[]
            for (raw,) in world.store.connection.execute('SELECT payload FROM beats ORDER BY sequence'):
                beat=json.loads(raw);rule=beat['rule_id'];rules[rule]+=1
                if rule=='action.complete.v1':
                    for change in beat['changes']:
                        if change['collection']=='actors' and change['component_path']=='action' and change['new_value'] is None:
                            action=current_actions.get(change['subject_id'])
                            if action:completed[action['kind']]+=1
                for change in beat['changes']:
                    if change['collection']!='actors':continue
                    key=change['subject_id'];value=change['new_value'];path=change['component_path']
                    if path=='$':current_actions[key]=value.get('action')
                    elif path=='action':current_actions[key]=value
                    elif path=='last_decision' and value and rule.startswith('social.'):
                        (declined if 'decline' in rule else accepted)[value.get('social_category','small_talk')]+=1
                if rule in {'psychology.fear.v2','social.accept.v2','routine.replan.v2'} and len(examples)<12:
                    examples.append({'id':beat['id'],'at':beat['interval'][1],'rule':rule,'text':beat['narration']})
            world.save()
            return {'generated_at':datetime.now(timezone.utc).isoformat(),'seed':seed,'simulated_hours':hours,
                'population':len(world.actors),'households':20,'objects':len(world.objects),
                'rules':world.rules.manifest(),'python':platform.python_version(),'platform':platform.platform(),
                'elapsed_seconds':round(elapsed,3),'max_queue':max_queue,'beats':world.store.sequence,
                'invariant_errors':errors,'replay_matches':world.store.replay()==world.canonical_state(),
                'completed_actions':dict(sorted(completed.items())),'accepted_social_categories':dict(sorted(accepted.items())),
                'declined_social_categories':dict(sorted(declined.items())),'rule_counts':dict(rules),
                'examples':examples,'snapshots':[world.inspect(aid) for aid in ('resident_001','resident_004','resident_005')],
                'scope':'Seeded new world; 44 adults, not a city benchmark. Counts measure executed completions; chat counts per participant, accepted categories per encounter.'}
        finally:world.close()


def render(report):
    target=ROOT/'docs/life_systems.html'
    template=(ROOT/'docs/life_systems_template.html').read_text(encoding='utf-8')
    metrics={k:v for k,v in report.items() if k not in {'snapshots','examples','rules'}}
    rows=''.join(f'<tr><td>{escape(key)}</td><td>{escape(value["label"])}</td><td>{value["duration_seconds"]} s</td></tr>' for key,value in social_category_definitions().items())
    examples=''.join(f'<li><code>{escape(item["id"])}</code> {escape(item["text"])}</li>' for item in report['examples'])
    gallery=[]
    screenshots=[('spatial_plausibility/family-default.png','Generatorlabor: typbezogene Familienräume; verbleibende unzugewiesene Flächen sind sichtbar.'),
        ('spatial_plausibility/school-24-seats.png','Generatorlabor: Schulplan mit tatsächlich platzierten Schülerplätzen.'),
        ('life_systems/03-psychology-personality.png','Browserprüfung: Persönlichkeitswerte und Ambitionen im Inspektor.'),
        ('life_systems/09a-served-table-closeup.png','Hauptsimulation: Mahlzeit, Geschirr und Aufräumplan in einem bestehenden Haushalt.'),
        ('life_systems/08-mobile-inspector.png','Browserprüfung: tatsächliche Haushaltszustände bei 390 Pixeln Breite.')]
    for path,caption in screenshots:
        source=ROOT/'artifacts'/path
        if source.exists():
            data=base64.b64encode(source.read_bytes()).decode('ascii')
            gallery.append(f'<figure class="card" style="margin:0"><img loading="lazy" style="width:100%;max-height:480px;object-fit:contain" src="data:image/png;base64,{data}" alt="{escape(caption)}"><figcaption>{escape(caption)}</figcaption></figure>')
    browser_path=ROOT/'artifacts/life_systems/browser-report.json'
    if browser_path.exists():
        browser=json.loads(browser_path.read_text(encoding='utf-8'))
        metrics['browser_verification']={'passed':browser['passed'],'checks':len(browser['checks']),'issues':browser['issues']}
    for name, filename, keys in (
            ('room_generation','generation/verification.json',('generator_version','room_attempts','room_valid')),
            ('building_generation','workshop/verification.json',('generator_version','building_attempts','building_valid','region_valid','public_to_room_routes','failures')),
            ('workshop_browser','workshop/browser-verification.json',('generator_version','passed','errors')),
            ('atelier_browser','generation/browser-verification.json',('generator_version','passed'))):
        source=ROOT/'artifacts'/filename
        if source.exists():
            data=json.loads(source.read_text(encoding='utf-8'))
            metrics[name]={key:data[key] for key in keys if key in data}
    html=template.replace('{{METRICS}}',escape(json.dumps(metrics,ensure_ascii=False,indent=2))).replace('{{CATEGORIES}}',rows).replace('{{EXAMPLES}}',examples).replace('{{GALLERY}}',''.join(gallery))
    target.write_text(html,encoding='utf-8')
    print(str(target))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--hours',type=int,default=24);parser.add_argument('--seed',type=int,default=42);parser.add_argument('--render-only',action='store_true')
    args=parser.parse_args();path=ROOT/'artifacts/life_systems/report.json';path.parent.mkdir(parents=True,exist_ok=True)
    if args.render_only:report=json.loads(path.read_text(encoding='utf-8'))
    else:
        if args.hours<1:parser.error('--hours must be positive')
        report=measure(args.hours,args.seed);path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    render(report)
    print(json.dumps({k:report[k] for k in ('simulated_hours','elapsed_seconds','invariant_errors','replay_matches','completed_actions','accepted_social_categories')},indent=2))
    raise SystemExit(1 if report['invariant_errors'] or not report['replay_matches'] else 0)


if __name__=='__main__':main()
