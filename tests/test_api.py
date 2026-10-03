import unittest
from fastapi.testclient import TestClient

from living_world.server import create_app


class ApiTests(unittest.TestCase):
    def test_controls_validation_and_agent_bridge(self):
        with TestClient(create_app(database=":memory:")) as client:
            self.assertEqual(client.post('/api/control',json={'paused':True}).status_code,200)
            initial=client.get('/api/state').json()['clock']
            stepped=client.post('/api/control',json={'step_seconds':60}).json()
            self.assertEqual(stepped['clock'],initial+60)
            self.assertEqual(client.post('/api/control',json={'speed':-1}).status_code,422)
            self.assertEqual(client.post('/api/control',json={'unexpected':'value'}).status_code,422)
            self.assertEqual(client.get('/api/actors/missing').status_code,404)
            self.assertEqual(client.get('/api/health').json()['invariants'],[])
            self.assertEqual(len(client.get('/api/world').json()['households']),20)
            packet=client.get('/api/bridge/resident_001/context').json()
            transferred=client.post('/api/bridge/resident_001/ownership',json={'owner':'external','expected_epoch':packet['self']['owner_epoch']})
            self.assertEqual(transferred.status_code,200)
            stale=client.post('/api/bridge/intent',json={'actor_id':'resident_001','owner_epoch':1,'expected_version':packet['self']['version'],'action':'wait'})
            self.assertEqual(stale.status_code,409)
            self.assertIn('Stale',stale.json()['detail'])
            self.assertEqual(client.post('/api/save',json={}).json()['saved'],True)
            exported=client.get('/api/export').json()
            replay=client.get('/api/replay').json()['state']
            self.assertEqual(replay['actors'],exported['actors'])
            self.assertEqual(replay['objects'],exported['objects'])

    def test_life_documentation_and_inspection_are_available(self):
        with TestClient(create_app(database=":memory:")) as client:
            client.post('/api/control',json={'paused':True})
            for path in ('/life-supplement','/psychology_design.md','/daily_life_design.md','/spatial_plausibility_notes.md','/plausibility-plan'):
                self.assertEqual(client.get(path).status_code,200,path)
            person=client.get('/api/actors/resident_001').json()
            self.assertEqual(len(person['psychology']['big_five']),5)
            self.assertGreaterEqual(len(person['social_categories']),24)
            if person['profile']['job']!='Retired':
                self.assertIsNotNone(person['workplace']['target_id'])
            else:
                self.assertIsNone(person['workplace'])
            self.assertEqual(client.get('/not-a-document.md').status_code,404)

    def test_campus_save_exposes_students_floors_and_inspection(self):
        with TestClient(create_app(database=':memory:',seed=73,layout='neighborhood-v1',paused=True)) as client:
            health=client.get('/api/health').json()
            self.assertEqual(health['population'],54)
            self.assertEqual(health['households'],20)
            self.assertEqual(health['residential_units'],21)
            world=client.get('/api/world').json()
            self.assertEqual(world['planning_metadata']['runtime_floors'],[0,1,2])
            self.assertEqual(len(world['planning_metadata']['portals']),2)
            state=client.get('/api/state').json()
            self.assertTrue(state['paused'])
            self.assertEqual(sum(a['household_id']=='student_residence' for a in state['actors']),10)
            person=client.get('/api/actors/resident_045').json()
            self.assertEqual(person['profile']['job'],'Student')
            self.assertEqual(person['household_id'],'student_residence')
            for path in ('/campus-social-w100','/static/campus-ui.css','/static/app.js'):
                self.assertEqual(client.get(path).status_code,200,path)


if __name__=='__main__':
    unittest.main()
