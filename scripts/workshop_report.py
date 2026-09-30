"""Generate measured building/region evidence and a self-contained HTML appendix."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from living_world.generation import GENERATOR_VERSION
from living_world.generation.catalog import CATALOG, ROOMS, PUBLIC_BUILDING_BACKLOG, BUILDING_TEMPLATES
from living_world.generation.buildings import generate_building
from living_world.generation.regions import generate_region, route_to_room
from living_world.generation.demo import NavigationDemo
from living_world.workshop.library import Library
from living_world.workshop.providers import DemoProvider
from living_world.workshop.runner import Runner

OUT=ROOT/'artifacts'/'workshop'


def render(data):
    browser=OUT/'browser-verification.json'
    data['browser']=json.loads(browser.read_text(encoding='utf-8')) if browser.exists() else None
    if data['browser'] and data['browser'].get('generator_version')!=GENERATOR_VERSION:
        data['browser']=None
    unit_path=OUT/'unit-verification.json'
    data['unit_tests']=json.loads(unit_path.read_text(encoding='utf-8')) if unit_path.exists() else None
    drawings='\n'.join(re.sub(r'^import .*?;\s*$','',(ROOT/'web'/name).read_text(encoding='utf-8'),flags=re.M).replace('export ','') for name in ('bed-variants-drawing.js','civic-drawing.js','generation-drawing.js'))
    template=(ROOT/'docs'/'agent_workshop_template.html').read_text(encoding='utf-8')
    content=template.replace('/*__DRAWING__*/',drawings).replace('/*__DATA__*/',json.dumps(data,ensure_ascii=False).replace('</','<\\/'))
    (ROOT/'docs'/'agent_workshop.html').write_text(content,encoding='utf-8')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--render-only',action='store_true')
    parser.add_argument('--unit-tests',action='store_true',help='Run the complete unittest suite and save its measured result')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    if args.unit_tests:
        result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
        evidence={'passed':result.wasSuccessful(),'tests_run':result.testsRun,'failures':len(result.failures),
                  'errors':len(result.errors),'skipped':len(result.skipped),'generator_version':GENERATOR_VERSION,
                  'generated_at':datetime.now(timezone.utc).isoformat()}
        (OUT/'unit-verification.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
        if not result.wasSuccessful():
            raise SystemExit(1)
    if args.render_only:
        data=json.loads((OUT/'fixtures.json').read_text(encoding='utf-8'))
        if data['results']['generator_version']!=GENERATOR_VERSION:
            parser.error('Run a fresh batch for this version first')
        render(data);return
    started=time.perf_counter();buildings=[];building_valid=region_valid=route_checks=0
    for seed in range(24):
        residents={'adults':2,'children':seed%2,'teens':(seed+1)%2}
        request={'width':18,'depth':19,'room_count':6,'levels_above_ground':2,'basements':seed%2,
                 'residents':residents,'elevator':seed%3!=0,'terrace_exit':seed%4==0,'seed':seed}
        house=generate_building(request)
        assert house['validation']['valid']
        assert not NavigationDemo(house).advance(600)['invariant_errors']
        building_valid+=1
        if seed in (0,1):buildings.append(house)
    for kind,spec in BUILDING_TEMPLATES.items():
        program=spec['room_program']
        for seed in range(4):
            house=generate_building({'width':36 if kind=='school' else 29,'depth':30 if kind=='school' else 27,'room_count':len(program),'room_program':program,
                                     'levels_above_ground':1,'basements':0,'residents':{'adults':0,'children':0,'teens':0},'seed':seed})
            house['name']=spec['name'];assert house['validation']['valid'];building_valid+=1
            if seed==0:buildings.append(house)
    for seed in range(12):
        region=generate_region(seed)
        for plot in region['plots']:
            for floor in plot['design']['floors']:
                for room in floor['rooms']:
                    assert route_to_room(region,plot['id'],room['id'])['valid'];route_checks+=1
        assert region['validation']['valid'];region_valid+=1
    library=Library(':memory:')
    pack=Runner(library,DemoProvider()).run(['Neue kleine Leseplätze'])['jobs'][0]
    assert pack['state']=='awaiting_review' and pack['report']['valid'];library.close()
    results={'generator_version':GENERATOR_VERSION,'generated_at':datetime.now(timezone.utc).isoformat(),
             'room_types':len(ROOMS),'object_types':len(CATALOG),'building_valid':building_valid,'building_attempts':36,
             'region_valid':region_valid,'region_attempts':12,'public_to_room_routes':route_checks,
             'walker_seconds_per_residential_building':600,'walker_invariant_errors':[],
             'api_adapter_tests':'mocked only; no external generation called',
             'codex_development_agents':['gpt-6-luna/luna_beds','gpt-6-luna/luna_buildings','gpt-6-luna/luna_civic',
                                         'gpt-6-sol/spatial_plausibility'],
             'elapsed_seconds':round(time.perf_counter()-started,2),'failures':[]}
    data={'results':results,'buildings':buildings,'pack':pack,'taxonomy':PUBLIC_BUILDING_BACKLOG}
    (OUT/'fixtures.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    (OUT/'verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    render(data);print(json.dumps(results,indent=2))


if __name__=='__main__':main()
