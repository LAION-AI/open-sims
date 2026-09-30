"""Player object inspection does not mutate the world or grant action rights."""
from copy import deepcopy
import unittest
from fastapi.testclient import TestClient
from living_world.server import create_app
from living_world.object_inspection import inspect_object


class ObjectExplorerTests(unittest.TestCase):
    def test_object_projection_and_live_contents_are_read_only(self):
        with TestClient(create_app(':memory:',layout='neighborhood-v1',paused=True)) as client:
            w=client.app.state.world
            table=next(o for o in w.objects.values() if o['kind']=='table')
            actor=next(a for a in w.actors.values() if a['household_id']==table['household_id'])
            # Explicit fixture independent from the recipe planner.
            with w.transaction('test.object_contents',[actor['id']],'A test item in a real container.'):
                a=w.edit('actors',actor['id'])
                a['belongings'].append({'id':'test_portable_pizza','kind':'pizza','owner_id':a['id'],
                    'location':{'type':'container','id':table['id']},'state':{'stage':'served'}})
                w.edit('objects',table['id']).setdefault('daily',{})['served_meals']=1
            before=deepcopy(w.canonical_state()); queue=deepcopy(w.queue); seq=w.store.sequence
            self.assertEqual(w.invariants(),[])
            response=client.get('/api/objects/'+table['id'])
            self.assertEqual(response.status_code,200)
            data=response.json()
            self.assertEqual(data['object'],table)
            self.assertTrue(data['contents_complete'])
            self.assertEqual(data['contents'][0]['id'],'test_portable_pizza')
            self.assertEqual(data['contents'][0]['custodian_id'],actor['id'])
            self.assertIn('eat_recipe',[a['id'] for a in data['actions']])
            self.assertEqual(w.canonical_state(),before)
            self.assertEqual(w.queue,queue);self.assertEqual(w.store.sequence,seq)
            self.assertEqual(client.get('/api/objects/not-real').status_code,404)
            data['object']['condition']=0
            self.assertNotEqual(w.objects[table['id']]['condition'],0)
            fridge=next(o for o in w.objects.values() if o['kind']=='fridge')
            projected=inspect_object(w,fridge['id'])
            self.assertEqual(projected['effective_daily']['pantry_stock'],8)
            self.assertIn('pantry_stock',projected['default_daily_keys'])
            self.assertNotIn('daily',fridge)

    def test_direct_projection_is_detached_and_passive_chair_is_not_a_student(self):
        with TestClient(create_app(':memory:',layout='neighborhood-v1',paused=True)) as client:
            w=client.app.state.world
            chair=next(o for o in w.objects.values() if o['kind']=='school_student_chair')
            data=inspect_object(w,chair['id'])
            self.assertEqual(data['actions'],[])
            self.assertFalse(data['object']['blocking'])
            data['object']['anchors'].clear()
            self.assertTrue(chair['anchors'])

    def test_fast_speed_acceptance_preserves_pause_clock_and_rejects_out_of_range(self):
        with TestClient(create_app(':memory:',paused=True)) as client:
            before=client.get('/api/state').json()['clock']
            for speed in (1,10,60,120,300,600):
                response=client.post('/api/control',json={'speed':speed})
                self.assertEqual(response.status_code,200)
                self.assertTrue(response.json()['paused'])
                self.assertEqual(response.json()['speed'],speed)
                self.assertEqual(response.json()['clock'],before)
            for speed in (0,601):
                self.assertEqual(client.post('/api/control',json={'speed':speed}).status_code,422)


if __name__=='__main__':unittest.main()
