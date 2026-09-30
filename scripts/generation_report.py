"""Reproduce the batch experiment and build the self-contained HTML supplement.

No dependencies beyond Python; no server, network, or language model required.
"""
import argparse
from datetime import datetime, timezone
import json
import re
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from living_world.generation import GENERATOR_VERSION
from living_world.generation.catalog import ROOMS, CATALOG, catalog_data
from living_world.generation.rooms import generate_room, validate_room, GenerationError
from living_world.generation.houses import generate_house, generate_district
from living_world.generation.demo import NavigationDemo


def write_report(data):
    browser_path=ROOT/'artifacts'/'generation'/'browser-verification.json'
    browser_result=json.loads(browser_path.read_text(encoding='utf-8')) if browser_path.exists() else None
    if browser_result and browser_result.get('generator_version') != data['results']['generator_version']:
        browser_result=None
    data['browser_result']=browser_result
    template=(ROOT/'docs'/'housing_supplement_template.html').read_text(encoding='utf-8')
    drawings='\n'.join(re.sub(r'^import .*?;\s*$', '', (ROOT/'web'/name).read_text(encoding='utf-8'), flags=re.M).replace('export ', '')
                       for name in ('bed-variants-drawing.js','civic-drawing.js','generation-drawing.js'))
    output=template.replace('/*__DRAWING__*/',drawings).replace('/*__DATA__*/',json.dumps(data,ensure_ascii=False).replace('</','<\\/'))
    target=ROOT/'docs'/'procedural_housing_supplement.html'
    target.write_text(output,encoding='utf-8')
    print('Report: '+str(target))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seeds', type=int, default=64)
    parser.add_argument('--render-only', action='store_true', help='Reuse the recorded experiment; only refresh HTML, drawings and browser evidence')
    args = parser.parse_args()
    out=ROOT/'artifacts'/'generation'
    out.mkdir(exist_ok=True,parents=True)
    if args.render_only:
        data=json.loads((out/'design-fixtures.json').read_text(encoding='utf-8'))
        if data['results']['generator_version'] != GENERATOR_VERSION:
            parser.error('Recorded fixtures belong to another generator version; run a fresh batch first')
        write_report(data)
        return
    if not 4 <= args.seeds <= 1000:
        parser.error('--seeds must be between 4 and 1000')
    failures, times, rows, gallery = [], [], [], []
    total = 0
    observed = set()
    started = time.perf_counter()
    for kind, spec in ROOMS.items():
        signatures, rotations, families, omissions = set(), set(), set(), 0
        valid = 0
        for seed in range(args.seeds):
            # Rotate entrance side and include minimum/default/expanded sizes.
            dims = spec['minimum'] if seed % 4 == 0 else [min(14, v+1) for v in spec['size']] if seed % 4 == 1 else spec['size']
            begin = time.perf_counter()
            try:
                room = generate_room(kind, seed, *dims, door_side=('north','east','south','west')[seed%4])
                if not validate_room(room)['valid']:
                    raise GenerationError(str(room['validation']['errors']))
                valid += 1
                observed.update(o['kind'] for o in room['objects'])
                signatures.add(room['signature'])
                families.add(room['family'])
                rotations.add(room['objects'][0]['orientation'])
                omissions += len(room['omitted'])
            except GenerationError as exc:
                failures.append({'kind': kind, 'seed': seed, 'size': dims, 'error': str(exc)})
            times.append((time.perf_counter()-begin)*1000)
            total += 1
        gallery.extend(generate_room(kind, seed) for seed in (42,59,76,93))
        rows.append({'kind':kind,'name':spec['name'],'attempts':args.seeds,'valid':valid,'unique_geometry':len(signatures),'families':len(families),'orientations':len(rotations),'optional_omissions':omissions})
        print(f'{kind}: {valid}/{args.seeds} valid', flush=True)
    # Fixed dimensions/palette/door side: geometry diversity cannot be faked by
    # varying the room area, colors, labels, IDs or the entrance side.
    fixed = [generate_room('living', seed, 8, 7, style='sage') for seed in range(args.seeds)]
    houses = []
    house_count = 32
    house_valid = 0
    for seed in range(house_count):
        try:
            house = generate_house(seed, 1+seed%5, seed%3!=0)
            if not house['validation']['valid']:
                raise GenerationError(str(house['validation']['errors']))
            house_valid += 1
        except GenerationError as exc:
            failures.append({'kind':'house','seed':seed,'error':str(exc)})
    houses = [generate_house(42,3,True), generate_house(7,2,False), generate_house(19,5,True)]
    blocks = [generate_district(seed, 2+seed%11) for seed in range(100)]
    block_valid = sum(b['validation']['valid'] for b in blocks)
    for b in blocks:
        if not b['validation']['valid']:
            failures.append({'kind':'district','seed':b['seed'],'error':b['validation']['errors']})
    demo = NavigationDemo(houses[0])
    portal_sample = None
    for _ in range(1800):
        snap = demo.advance(1)
        if snap['invariant_errors']:
            raise RuntimeError(snap['invariant_errors'])
        if portal_sample is None and any(a['ride'] for a in snap['actors']):
            portal_sample = snap
    result = {'generator_version':GENERATOR_VERSION,'generated_at':datetime.now(timezone.utc).isoformat(),
              'scope':'Batch verification of the isolated housing laboratory, not a city-scale performance claim',
              'room_type_count':len(ROOMS),'catalog_object_count':len(CATALOG),'observed_object_types':len(observed),
              'unobserved_object_types':sorted(set(CATALOG)-observed),
              'room_attempts':total,'room_valid':sum(r['valid'] for r in rows),'room_results':rows,
              'room_ms_median':round(statistics.median(times),2),'room_ms_p95':round(sorted(times)[int(.95*(len(times)-1))],2),
              'house_attempts':house_count,'house_valid':house_valid,'block_attempts':len(blocks),'block_valid':block_valid,
              'fixed_living_attempts':len(fixed),'fixed_living_unique_geometry':len({r['signature'] for r in fixed}),
              'fixed_living_families':sorted({r['family'] for r in fixed}),
              'navigation_seconds':demo.now,'navigation_metrics':demo.metrics,'navigation_invariant_errors':demo.invariants(),
              'failures':failures,'elapsed_seconds':round(time.perf_counter()-started,2)}
    data={'results':result,'catalog':catalog_data(),'rooms':gallery,'houses':houses,'district':generate_district(42,8),'portal_sample':portal_sample}
    (out/'design-fixtures.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    write_report(data)
    (out/'verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('room_results','fixed_living_families')},indent=2))
    raise SystemExit(1 if failures else 0)


if __name__=='__main__':
    main()
