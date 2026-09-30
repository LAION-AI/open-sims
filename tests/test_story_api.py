"""Public observation contracts and isolated planning, without external services."""
from fastapi.testclient import TestClient
import unittest
from living_world.server import create_app


class StoryApiTests(unittest.TestCase):
    def test_story_projections_and_documents_are_read_only(self):
        with TestClient(create_app(':memory:')) as client:
            client.post('/api/control',json={'paused':True})
            before=client.get('/api/export').json()
            for path in ('/story-supplement','/static/story-ui.js','/static/story-ui.css','/city',
                         '/affect_design.md','/possessions_design.md','/city_design.md'):
                self.assertEqual(client.get(path).status_code,200,path)
            taxonomy=client.get('/api/emotions/taxonomy').json()
            self.assertEqual(len(taxonomy['emotions']),40)
            self.assertIn('eat_recipe',client.get('/api/items/actions').json()['actions'])
            graph=client.get('/api/actors/resident_001/relationships').json()
            self.assertEqual(graph['viewer_id'],'resident_001')
            self.assertTrue(graph['edges'])
            self.assertTrue(all(e['source']=='resident_001' for e in graph['edges']))
            self.assertEqual(client.get('/api/actors/not-real/relationships').status_code,404)
            self.assertEqual(client.get('/api/export').json(),before)
            self.assertEqual(client.post('/api/capture',json={'overlay':'not-supported'}).status_code,422)
            self.assertEqual(client.post('/api/capture',json={'building_id':'not-a-building'}).status_code,404)

    def test_city_routes_do_not_mutate_the_main_world(self):
        with TestClient(create_app(':memory:')) as client:
            client.post('/api/control',json={'paused':True})
            before=client.get('/api/export').json()
            reply=client.post('/api/generation/city',json={'seed':42,'columns':4,'rows':4})
            self.assertEqual(reply.status_code,200)
            plan=reply.json(); city=plan['design']
            self.assertTrue(city['validation']['valid'])
            self.assertEqual(len(city['validation']['services']),9)
            plot=next(p for p in city['plots'] if p['service']=='school')
            room=next(r for f in plot['design']['floors'] for r in f['rooms'] if r['kind']=='school_classroom')
            route=client.post('/api/generation/city/'+plan['session_id']+'/route',
                json={'plot_id':plot['id'],'room_id':room['id']})
            self.assertEqual(route.status_code,200)
            self.assertTrue(route.json()['valid'])
            self.assertEqual(client.post('/api/generation/city',json={'seed':True}).status_code,422)
            self.assertEqual(client.post('/api/generation/city',json={'extra':'no'}).status_code,422)
            self.assertEqual(client.get('/api/export').json(),before)


if __name__=='__main__':unittest.main()
