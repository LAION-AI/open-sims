"""Create a separate inhabited save. Refuses to overwrite any existing database."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from living_world.engine import World


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--database',default='data/mosswood-lindenviertel-20260929.sqlite3')
    parser.add_argument('--seed',type=int,default=73)
    parser.add_argument('--opening-minutes',type=int,default=15)
    args=parser.parse_args()
    if not 0<=args.opening_minutes<=60:parser.error('Opening minutes must be 0–60')
    path=(ROOT/args.database).resolve()
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(f'Existing save left untouched: {path}')
    path.touch(exist_ok=False)
    world=World(seed=args.seed,database=path,layout='neighborhood-v1')
    try:
        world.advance(args.opening_minutes*60)
        world.paused=True
        world.speed=10
        errors=world.invariants()
        replay=world.store.replay()==world.canonical_state()
        if errors or not replay:raise RuntimeError({'invariants':errors,'replay_matches':replay})
        report={'created_at':datetime.now(timezone.utc).isoformat(),'database':str(path),
            'layout':world.layout,'seed':world.seed,'clock':world.now,'paused':world.paused,
            'population':len(world.actors),'households':len(world.spatial.households),
            'buildings':len(world.spatial.buildings),'fixtures':len(world.objects),
            'map_size_m':[world.spatial.width,world.spatial.height],
            'jobs':dict(Counter(a['profile']['job'] for a in world.actors.values())),
            'multi_emotion_residents':sum(len(world.inspect(aid)['affect']['states'])>1 for aid in world.actors),
            'invariants':errors,'replay_matches':replay,'beats':world.store.sequence,
            'planning':world.spatial.planning_metadata,'rules':world.rules.manifest()}
        world.save()
    finally:world.close()
    resumed=World(database=path)
    try:
        report['reload_invariants']=resumed.invariants()
        report['reload_replay_matches']=resumed.store.replay()==resumed.canonical_state()
        report['reload_paused']=resumed.paused
        if report['reload_invariants'] or not report['reload_replay_matches']:raise RuntimeError('Reload check failed')
    finally:resumed.close()
    out=ROOT/'artifacts'/'lindenviertel'
    out.mkdir(parents=True,exist_ok=True)
    (out/'creation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'planning','rules'}},indent=2,ensure_ascii=False))


if __name__=='__main__':main()
