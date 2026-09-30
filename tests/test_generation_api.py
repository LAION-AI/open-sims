import unittest
from fastapi.testclient import TestClient
from living_world.server import create_app
from living_world.generation.catalog import ROOMS, CATALOG
from living_world.generation import GENERATOR_VERSION


class GenerationApiTests(unittest.TestCase):
    def test_generation_navigation_and_main_world_isolation(self):
        with TestClient(create_app(database=":memory:")) as client:
            client.post('/api/control', json={'paused': True})
            before = client.get('/api/export').json()
            self.assertEqual(client.get('/atelier').status_code, 200)
            catalog = client.get('/api/generation/catalog').json()
            self.assertEqual(len(catalog['rooms']), len(ROOMS))
            self.assertEqual(len(catalog['objects']), len(CATALOG))
            self.assertEqual(catalog['generator_version'], GENERATOR_VERSION)
            for kind in ('nursery', 'gaming', 'music', 'gym', 'conservatory'):
                self.assertTrue(client.post('/api/generation/room', json={'kind':kind,'seed':42}).json()['validation']['valid'])
            self.assertTrue(client.post('/api/generation/room', json={'kind': 'living', 'seed': 42}).json()['validation']['valid'])
            self.assertEqual(client.post('/api/generation/room', json={'kind': 'living', 'width': 5}).status_code, 422)
            self.assertEqual(client.post('/api/generation/room', json={'kind': 'no-such-room'}).status_code, 422)
            self.assertEqual(client.post('/api/generation/room', json={'unexpected': True}).status_code, 422)
            self.assertEqual(client.post('/api/generation/house', json={'levels': 6}).status_code, 422)
            result = client.post('/api/generation/house', json={'seed': 42, 'levels': 3}).json()
            self.assertTrue(result['design']['validation']['valid'])
            endpoint = '/api/generation/demo/' + result['session_id']
            self.assertEqual(client.get(endpoint).json()['clock'], 0)
            response = client.post(endpoint + '/advance', json={'seconds': 300}).json()
            self.assertEqual(response['clock'], 300)
            self.assertEqual(response['invariant_errors'], [])
            self.assertGreater(response['metrics']['elevator_trips'], 0)
            self.assertGreater(response['metrics']['stairs_trips'], 0)
            self.assertEqual(client.post(endpoint + '/route', json={'actor_id':'missing', 'target_id':'missing'}).status_code, 409)
            self.assertEqual(client.post(endpoint + '/advance', json={'seconds':-1}).status_code, 422)
            self.assertEqual(client.get('/api/generation/demo/missing').status_code, 404)
            self.assertTrue(client.post('/api/generation/district', json={'count':8}).json()['validation']['valid'])
            self.assertEqual(client.get('/api/export').json(), before)
