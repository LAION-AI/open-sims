"""Acceptance checks for denser homes, careers, relations and safe suggestions."""
from collections import Counter
from copy import deepcopy
import unittest

from living_world.engine import RejectedProposal, World
from living_world.neighborhood import LivingNeighborhood
from living_world.plausibility import audit


class ExpandedLifeTests(unittest.TestCase):
    def test_generator_adds_reachable_storage_and_seating_across_seeds(self):
        for seed in (0, 1, 7, 73):
            map_ = LivingNeighborhood(seed)
            kinds = Counter(obj['kind'] for obj in map_.objects.values())
            self.assertEqual(kinds['wardrobe'], 20)
            self.assertEqual(kinds['dining_chair'], 60)
            self.assertGreaterEqual(len(map_.objects), 500)
            for home in map_.households:
                building = next(b for b in map_.buildings if b['id'] == home['building_id'])
                wardrobe = map_.objects[building['wardrobe_id']]
                self.assertEqual(wardrobe['household_id'], home['id'])
                self.assertIsNotNone(map_.path(building['door'], wardrobe['anchors'][0]))

    def test_new_world_careers_possessions_audit_and_old_hashes(self):
        world = World(seed=73, layout='neighborhood-v1')
        try:
            self.assertEqual(world.invariants(), [])
            self.assertEqual(world.rules.v2_hash, 'd833aaed1a19bc03e5609dd51625c6badbdcdc77dbb58970f5db589137f9dde0')
            self.assertEqual(world.rules.v3_hash, '8f1820507751980f9bee364318271c54a18213ee6f89ff715c344767199a5e12')
            before = deepcopy(world.canonical_state())
            path_queries = world.spatial.path_queries
            report = audit(world)
            self.assertEqual(world.spatial.path_queries, path_queries)
            self.assertEqual(report['objects'], 522)
            self.assertEqual({row['code'] for row in report['findings']}, {'school_population_not_modelled'})
            for actor in world.actors.values():
                self.assertEqual(actor['career']['job'], actor['profile']['job'])
                self.assertTrue(any(a['kind'] == 'career' for a in actor['psychology']['ambitions']))
                wardrobe = next(o for o in world.objects.values() if o.get('household_id') == actor['household_id'] and o['kind'] == 'wardrobe')
                self.assertTrue(any(item['location'].get('id') == wardrobe['id'] for item in actor['belongings']))
            self.assertEqual(world.canonical_state(), before)
        finally:
            world.close()

    def test_work_completion_advances_career_and_ambition(self):
        world = World(seed=73, layout='neighborhood-v1')
        try:
            aid = 'resident_004'
            with world.transaction('test.work_isolation', list(world.actors), 'Isolate one real shift.'):
                for key in world.actors:
                    actor = world.edit('actors', key)
                    actor['owner'] = 'external'
                    actor['needs'] = {need: .02 for need in actor['needs']}
                    actor['needs_at'] = world.now
            world.decide(aid, {'action': 'work'})
            end = world.actors[aid]['action']['ends_at']
            world.advance(end - world.now)
            actor = world.actors[aid]
            self.assertEqual(actor['career']['completed_shifts'], 1)
            self.assertGreater(actor['career']['experience_hours'], 0)
            self.assertGreater(actor['skills'][actor['career']['skill']], .15)
            self.assertGreater(next(a['progress'] for a in actor['psychology']['ambitions'] if a['kind'] == 'career'), 0)
            self.assertEqual(world.invariants(), [])
            self.assertEqual(world.store.replay(), world.canonical_state())
        finally:
            world.close()

    def test_relationships_show_explicit_role_and_both_directions(self):
        world = World(seed=73, layout='neighborhood-v1')
        try:
            person = world.inspect('resident_001')
            edge = next(e for e in person['social_graph']['edges'] if e['target'] == 'resident_002')
            self.assertIn('spouse', edge['roles'])
            self.assertIn('feeling', edge)
            self.assertIsNotNone(edge['reciprocal'])
            reverse = world.actors['resident_002']['relations']['resident_001']
            self.assertEqual(edge['reciprocal']['qualities']['trust'], reverse['trust'])
            self.assertNotIn('affect', edge['reciprocal'])
            child = next(e for e in person['social_graph']['edges'] if 'child' in e['roles'])
            self.assertGreaterEqual(child['qualities']['closeness'], .6)
            friends = [e for a in world.actors.values()
                       for e in a['relations'].values() if e.get('origin') == 'authored_new_world_friendship']
            self.assertGreaterEqual(len(friends), 4)
        finally:
            world.close()

    def test_recommendation_is_journaled_advisory_and_versioned(self):
        world = World(seed=73, layout='neighborhood-v1')
        try:
            aid = 'resident_001'
            actor = world.actors[aid]
            option = world.inspect(aid)['recommendation_options'][0]
            payload = {'expected_version': actor['version'], **option}
            with self.assertRaises(RejectedProposal):
                world.recommend(aid, {**payload, 'expected_version': -1})
            recommendation = world.recommend(aid, payload)
            self.assertEqual(recommendation['status'], 'pending')
            with self.assertRaises(RejectedProposal):
                world.cancel_recommendation(aid, payload['expected_version'])
            world.decide(aid)
            self.assertIn(world.actors[aid]['player_recommendation']['status'],
                          {'followed', 'considered', 'unavailable'})
            self.assertEqual(world.invariants(), [])
            self.assertEqual(world.store.replay(), world.canonical_state())
        finally:
            world.close()


if __name__ == '__main__':
    unittest.main()
