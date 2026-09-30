"""Repeatable full acceptance report. Never opens the user's live database."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from living_world.engine import World


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--hours',type=int,default=24)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--skip-tests',action='store_true')
    parser.add_argument('--layout',choices=['legacy','neighborhood-v1'],default='legacy')
    parser.add_argument('--output',default='artifacts/story/verification.json')
    args=parser.parse_args()
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'seed':args.seed,'layout':args.layout,
            'live_database_touched':False,'test_results':None}
    success=True
    if not args.skip_tests:
        print('Running the complete unittest suite...',flush=True)
        log=io.StringIO(); started=time.perf_counter()
        suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
        result=unittest.TextTestRunner(stream=log,verbosity=1).run(suite)
        report['test_results']={'count':result.testsRun,'failures':len(result.failures),
            'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful(),
            'elapsed_seconds':round(time.perf_counter()-started,3),'log':log.getvalue()}
        success=result.wasSuccessful()
        print(log.getvalue(),flush=True)
    world=World(seed=args.seed,layout=args.layout)
    started=time.perf_counter()
    try:
        invariant_errors=[]
        hourly=[]
        for hour in range(args.hours):
            before=dict(world.metrics)
            world.advance(3600)
            invariant_errors.extend({'hour':hour+1,'error':e} for e in world.invariants())
            hourly.append({'hour':hour+1,'completed':world.metrics['completed_actions']-before['completed_actions'],
                'interrupted':world.metrics['interrupted_actions']-before['interrupted_actions'],
                'decisions':world.metrics['decisions']-before['decisions'],
                'beat_count':world.store.sequence})
            if (hour+1)%6==0:print(f'{hour+1} world hours: {world.store.sequence} Beats; invariant errors {len(invariant_errors)}',flush=True)
        replay_ok=world.store.replay()==world.canonical_state()
        meals=Counter(i['kind'] for a in world.actors.values() for i in a['belongings']
                      if i['kind'] in {'pizza','pancake'} and i['location']['type']=='consumed')
        # Reachability and replay alone cannot detect repeated action cancellation.
        # This is a coarse regression alarm, not a scientific behavioural metric.
        ratio=world.metrics['interrupted_actions']/max(1,world.metrics['completed_actions'])
        quality={'interruption_to_completion_ratio':round(ratio,4),'maximum_ratio':2.0,
            'passed':ratio<=2.0,'scope':'Heuristic cancellation-loop alarm; not a realism certificate'}
        report['simulation']={'hours':args.hours,'elapsed_seconds':round(time.perf_counter()-started,3),
            'invariants':invariant_errors,'replay_matches':replay_ok,'rules':world.rules.manifest(),
            'hourly_activity':hourly,'quality_checks':quality,
            'population':len(world.actors),'fixtures':len(world.objects),'metrics':world.snapshot()['metrics'],
            'consumed_meals_in_retained_state':dict(meals),
            'outfits_changed':sum(a.get('outfit_last_day') is not None for a in world.actors.values()),
            'workplace_buildings':sorted({a['workplace']['building_id'] for a in world.actors.values() if a.get('workplace')})}
        success=success and not invariant_errors and replay_ok and quality['passed']
    finally:world.close()
    report['passed']=success
    target=ROOT/args.output
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='test_results'},ensure_ascii=False,indent=2),flush=True)
    print('Report: '+str(target),flush=True)
    return 0 if success else 1


if __name__=='__main__':raise SystemExit(main())
