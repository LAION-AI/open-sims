"""Measured neighborhood workload, including paths, decisions, history and replay."""
import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from living_world.engine import World

parser=argparse.ArgumentParser()
parser.add_argument('--hours',type=int,default=168)
parser.add_argument('--seed',type=int,default=42)
parser.add_argument('--output',default='artifacts/benchmark.json')
args=parser.parse_args()
latencies=[];errors=[];max_queue=0;daily=[]
with tempfile.TemporaryDirectory() as directory:
    database=Path(directory)/'benchmark.sqlite3'
    w=World(seed=args.seed,database=database)
    started=time.perf_counter()
    for step in range(args.hours*12):
        before=time.perf_counter();w.advance(300);latencies.append((time.perf_counter()-before)*1000)
        errors.extend(w.invariants());max_queue=max(max_queue,len(w.queue))
        if (step+1)%288==0:
            w.save()
            day={'simulated_days':(step+1)//288,'beats':w.store.sequence,'queue':len(w.queue),'elapsed_seconds':round(time.perf_counter()-started,2),'wellbeing':w.snapshot()['wellbeing']}
            daily.append(day);print(json.dumps(day),flush=True)
    elapsed=time.perf_counter()-started
    replay_ok=w.store.replay()==w.canonical_state()
    action_counts=Counter();rule_counts=Counter()
    for (raw,) in w.store.connection.execute('SELECT payload FROM beats'):
        b=json.loads(raw);rule_counts[b['rule_id']]+=1
        if b['rule_id']=='decision.utility.v1':
            for change in b['changes']:
                if change['component_path']=='action' and change['new_value']:
                    action_counts[change['new_value']['kind']]+=1
    ordered=sorted(latencies)
    result={'platform':platform.platform(),'python':platform.python_version(),'processor':platform.processor(),'seed':args.seed,'population':44,'households':20,'objects':len(w.objects),'rule_manifest':w.rules.manifest(),'simulated_hours':args.hours,'elapsed_seconds':round(elapsed,3),
            'latency_ms_per_5_world_minutes':{'p50':round(statistics.median(ordered),3),'p95':round(ordered[int((len(ordered)-1)*.95)],3),'p99':round(ordered[int((len(ordered)-1)*.99)],3),'max':round(max(ordered),3)},
            'invariant_errors':errors,'replay_matches':replay_ok,'max_queue_size':max_queue,'metrics':w.snapshot()['metrics'],'action_counts':dict(action_counts),'rule_counts':dict(rule_counts),'daily':daily,'history_bytes':database.stat().st_size,
            'scope':'44 resident neighborhood only; no extrapolation to cities, animals or language-model costs'}
    w.close()
target=Path(args.output);target.parent.mkdir(exist_ok=True,parents=True);target.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('rule_manifest','daily')},indent=2))
raise SystemExit(1 if errors or not replay_ok else 0)
