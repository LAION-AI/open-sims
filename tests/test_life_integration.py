"""Acceptance tests of executed, logged mechanics, not just template metadata."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from living_world.engine import World
from living_world.ledger import BeatStore
from living_world.daily_life import daily_state, plan_meal
from living_world import psychology


class LifeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.world=World()
        self.addCleanup(self.world.close)

    def isolate(self, aid='resident_005'):
        w=self.world
        with w.transaction('test.fixture',list(w.actors),'Explicit test fixture, not simulated history.'):
            for key in w.actors:
                a=w.edit('actors',key)
                a['owner']='external' if key!=aid else 'procedural'
                a['schedule'].update(start=0,end=1)
                a['needs']={k:.02 for k in a['needs']}
                a['needs_at']=w.now
        return w.actors[aid]

    def test_authored_family_and_coworkers_are_separate_from_household(self):
        w=self.world
        self.assertEqual(w.actors['resident_001']['family']['relationship_status'],'married')
        self.assertEqual(w.actors['resident_005']['family']['relationship_status'],'partnered')
        self.assertEqual(w.actors['resident_005']['relations']['resident_010']['layers']['family']['status'],'cousin')
        self.assertNotEqual(w.actors['resident_005']['household_id'],w.actors['resident_010']['household_id'])
        self.assertTrue(any(r['layers']['coworker']['status']=='shared_workplace' for a in w.actors.values() for r in a['relations'].values()))
        self.assertTrue(all(not c['allowed'] for c in psychology.social_candidates(w.actors['resident_005'],w.actors['resident_010'],w.now) if c['requires_consent']))

    def test_meal_chain_executes_food_and_cleanup_once(self):
        w=self.world;a=self.isolate()
        with w.transaction('test.hunger',[a['id']],'Hungry test resident.'):
            current=w.edit('actors',a['id'])
            current['needs']['hunger']=.9
            # Persisted v2 plans remain executable after the v3 recipe upgrade.
            current['routine']={'id':'legacy-meal','kind':'meal','status':'active','index':0,
                'steps':plan_meal(current,w.objects),'started_at':w.now}
        fridge=next(o for o in w.objects.values() if o['kind']=='fridge' and o['household_id']==a['household_id'])
        self.assertFalse(any(c['kind']=='eat' and c['target_id']==fridge['id'] for c in w.candidates(a)[0]))
        w.decide(a['id'],{'action':'fetch_ingredients'})
        observed=set(); consumed_at=None
        for _ in range(450):
            a=w.actors[a['id']]
            if a['action']:observed.add(a['action']['kind'])
            w.advance(10)
            if a.get('routine',{}).get('status')=='completed':
                consumed_at=w.now;break
        self.assertIsNotNone(consumed_at)
        self.assertTrue({'fetch_ingredients','prepare_meal','serve_meal','eat_meal','clear_dishes','wash_dishes','bin_trash','empty_trash','wipe_counter'}.issubset(observed),observed)
        self.assertEqual(daily_state(fridge)['pantry_stock'],7)
        self.assertFalse(set(a['inventory']) & {'ingredients','prepared_meal','dirty_dish','food_scraps'})
        self.assertLess(w.needs_at(a)['hunger'],.35)
        home={o['kind']:o for o in w.objects.values() if o['household_id']==a['household_id']}
        self.assertEqual(daily_state(home['sink'])['washed_total'],1)
        self.assertEqual(daily_state(home['table'])['dirty_dishes'],0)
        self.assertEqual(daily_state(home['bin'])['disposed_total'],1)
        self.assertEqual(daily_state(home['counter'])['mess'],0)
        self.assertEqual(w.invariants(),[])
        self.assertEqual(w.store.replay(),w.canonical_state())

    def test_real_dog_visibility_triggers_evidenced_fear_once_per_cooldown(self):
        w=self.world;a=self.isolate('resident_001')
        with w.transaction('test.fear',[a['id']],'Authored fear fixture.'):
            a=w.edit('actors',a['id']);a['position']=[56,61]
            a['schedule']['end']=17*3600
            next(f for f in a['psychology']['fears'] if f['kind']=='dogs')['intensity']=.6
        w._check_fears(a['id'])
        first=w.store.sequence
        self.assertEqual(a['emotion']['type'],'Afraid')
        self.assertLess(a['emotion']['valence'],0)
        self.assertEqual(a['psychology']['active_fear']['source'],'dog_clover')
        w._check_fears(a['id'])
        self.assertEqual(w.store.sequence,first)
        self.assertEqual(w.store.replay(),w.canonical_state())

    def test_commute_uses_assigned_external_station(self):
        w=self.world;a=self.isolate('resident_004')
        with w.transaction('test.work',[a['id']],'Working hours fixture.'):
            a=w.edit('actors',a['id']);a['schedule'].update(start=8*3600,end=17*3600)
        w.decide(a['id'],{'action':'work'})
        self.assertEqual(a['workplace']['building_id'],'school')
        self.assertEqual(a['action']['target_id'],a['workplace']['target_id'])
        self.assertGreater(len(a['action']['path']),20)
        w.advance(a['action']['arrives_at']-w.now)
        self.assertEqual(a['action']['phase'],'using')
        self.assertIn('school',[r['id'] for r in w.spatial.regions_at(a['position'])])
        self.assertEqual(w.invariants(),[])

    def test_snapshot_inspection_does_not_change_minds(self):
        w=self.world;w.advance(90);before=deepcopy(w.canonical_state());seq=w.store.sequence
        for _ in range(3):
            w.snapshot();w.inspect('resident_001');w.perspective('resident_001')
        self.assertEqual(w.canonical_state(),before)
        self.assertEqual(w.store.sequence,seq)

    def test_already_clean_final_chore_finishes_the_plan(self):
        w=self.world;a=self.isolate()
        counter=next(o for o in w.objects.values() if o['kind']=='counter' and o['household_id']==a['household_id'])
        with w.transaction('test.chore',[a['id']],'A housemate already cleaned the counter.'):
            a=w.edit('actors',a['id'])
            a['routine']={'id':'test_plan','kind':'cleaning','status':'active','index':0,
                'steps':[{'kind':'wipe_counter','target_id':counter['id']}]}
        self.assertEqual(daily_state(counter)['mess'],0)
        w._repair_routine(a['id'])
        self.assertEqual(a['routine']['index'],1)
        self.assertEqual(a['routine']['status'],'completed')
        self.assertEqual(w.store.replay(),w.canonical_state())

    def test_v1_migration_preserves_biography_active_action_and_replay(self):
        w=self.world
        w.decide('resident_001',{'action':'eat'})
        payload={'seed':w.seed,'rule_hash':w.rules.legacy_hash,'now':w.now,
            'actors':deepcopy(w.actors),'objects':{k:deepcopy(v) for k,v in w.objects.items() if int(k.split('_')[1])<=320},
            'meta':{k:deepcopy(v) for k,v in w.meta.items() if k in {'environment','economy'}},
            'queue':[e for e in w.queue if e[2]!='animal_tick'],'queue_serial':w.queue_serial,'epoch':w.epoch,'metrics':deepcopy(w.metrics)}
        for a in payload['actors'].values():
            for key in ('psychology','family','routine','workplace','workplace_id'):a.pop(key,None)
            for rel in a['relations'].values():
                for key in ('layers','respect','attraction','tension'):rel.pop(key,None)
        before=deepcopy(payload['actors']['resident_001'])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'legacy.sqlite3';store=BeatStore(path)
            changes=[]
            for collection, records in (('actors',payload['actors']),('objects',payload['objects']),('world',payload['meta'])):
                changes.extend({'collection':collection,'subject_id':key,'component_path':'$','new_value':value} for key,value in records.items())
            store.append(w._beat('legacy.fixture',[],'Explicit v1 test fixture.',changes));store.save_checkpoint(payload);store.close()
            resumed=World(database=path)
            try:
                after=resumed.actors['resident_001']
                for key in ('age','position','money','needs','action'):
                    self.assertEqual(after[key],before[key],key)
                self.assertEqual(after['family']['relationship_status'],'unspecified')
                backup=BeatStore(resumed.migration_backup)
                try:
                    self.assertEqual(backup.checkpoint()['rule_hash'],w.rules.legacy_hash)
                    self.assertEqual(backup.checkpoint()['actors']['resident_001'],before)
                finally:backup.close()
                self.assertEqual(len(resumed.objects),365)
                self.assertEqual(resumed.store.replay(),resumed.canonical_state())
                resumed.advance(90)
                self.assertEqual(resumed.invariants(),[])
            finally:resumed.close()


if __name__=='__main__':unittest.main()
