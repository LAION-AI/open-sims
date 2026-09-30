"""Verify a paused, migrated localhost world against its SQLite backup."""
import argparse
import json
from pathlib import Path
import sqlite3
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parent.parent


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--backup',required=True);args=parser.parse_args()
    base=f'http://127.0.0.1:{args.port}'
    def get(path):
        with urlopen(base+path,timeout=60) as response:return json.load(response)
    assert get('/api/state')['paused'],'Pause before verifying a stable canonical projection'
    path=Path(args.backup).resolve()
    connection=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    try:old=json.loads(connection.execute('SELECT payload FROM checkpoint WHERE id=1').fetchone()[0])
    finally:connection.close()
    current=get('/api/export');replay=get('/api/replay')['state'];health=get('/api/health')
    checks={
        'clock_not_reset':current['now']>=old['now'],
        'population_preserved':set(current['actors'])==set(old['actors']),
        'ages_preserved':all(current['actors'][key]['age']==a['age'] for key,a in old['actors'].items()),
        'households_preserved':all(current['actors'][key]['household_id']==a['household_id'] for key,a in old['actors'].items()),
        'unknown_kinship_not_invented':all(a['family']['relationship_status']=='unspecified' and not a['family']['parent_ids'] for a in current['actors'].values()),
        'old_object_geometry_preserved':all(all(current['objects'][key].get(field)==obj.get(field) for field in ('kind','x','y','w','h','anchors')) for key,obj in old['objects'].items()),
        'new_objects_added':len(current['objects'])==349,
        'new_schema':current['meta']['life_systems']['schema']=='everyday-life/2.0',
        'exact_replay':replay=={'actors':current['actors'],'objects':current['objects'],'world':current['meta']},
        'health':health['status']=='ok' and not health['invariants'],
        'model_disabled':not health['llm_enabled'],
    }
    result={'url':base,'backup':str(path),'backup_clock':old['now'],'current_clock':current['now'],
        'checks':checks,'passed':all(checks.values()),'rule_manifest':get('/api/rules')['manifest']}
    output=ROOT/'artifacts/life_systems/deployment.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
