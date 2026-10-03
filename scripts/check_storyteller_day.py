"""Run a deterministic, save-free social/storyteller smoke simulation."""
import argparse
import json
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from living_world.engine import World


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--hours',type=float,default=6)
    parser.add_argument('--seed',type=int,default=73)
    args=parser.parse_args()
    world=World(args.seed,':memory:',layout='neighborhood-v1')
    try:
        world.advance(round(args.hours*3600))
        counts=Counter(json.loads(raw)['rule_id'] for (raw,) in
                       world.store.connection.execute('SELECT payload FROM beats'))
        report={'seed':args.seed,'hours':args.hours,'clock':world.now,
                'social_accepts':counts['social.accept.v2'],
                'social_declines':counts['social.decline.v1'],
                'material_incidents':counts['storyteller.activity.v1'],
                'social_incident_participants':sum(bool(a.get('last_social_incident')) for a in world.actors.values()),
                'invariants':world.invariants(),
                'replay_matches':world.store.replay()==world.canonical_state(),
                'events':world.metrics['events_processed']}
        print(json.dumps(report,indent=2))
        if report['invariants'] or not report['replay_matches']:
            raise SystemExit(1)
    finally:
        world.close()


if __name__=='__main__':
    main()
