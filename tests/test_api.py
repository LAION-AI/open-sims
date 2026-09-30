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
            self.assertEqual(len(person['social_categories']),20)
            self.assertIsNotNone(person['workplace']['target_id'])
            self.assertEqual(client.get('/not-a-document.md').status_code,404)


if __name__=='__main__':
    unittest.main()
