"""A generated map is the actual inhabited world, not just a preview image."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from living_world.engine import World


class NeighborhoodIntegrationTests(unittest.TestCase):
    def test_all_residents_have_usable_homes_jobs_and_story_state(self):
        world=World(seed=73,layout='neighborhood-v1')
        try:
            self.assertEqual(len(world.actors),54)
            self.assertEqual(len(world.spatial.households),21)
            self.assertEqual(world.invariants(),[])
            self.assertEqual(world.meta['map']['layout'],'neighborhood-v1')
            for actor in world.actors.values():
                self.assertTrue(world.spatial.walkable(tuple(actor['position'])))
                self.assertTrue(actor['belongings'])
                self.assertIn('affect',actor)
                if actor['profile']['job'] in {'Pupil','Kindergarten child','Retired','Student'}:
                    self.assertIsNone(actor['workplace'])
                else:
                    self.assertIsNotNone(actor['workplace'],actor['profile']['job'])
                    station=world.objects[actor['workplace']['target_id']]
                    self.assertIsNotNone(world.spatial.path(actor['position'],station['anchors'][0]))
            world.advance(1800)
            self.assertEqual(world.invariants(),[])
            self.assertEqual(world.store.replay(),world.canonical_state())
        finally:world.close()

    def test_resume_uses_frozen_geometry_not_a_new_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            database=Path(directory)/'new-neighborhood.sqlite3'
            world=World(seed=73,database=database,layout='neighborhood-v1')
            world.advance(120)
            world.paused=True
            world.speed=60
            before=deepcopy(world.canonical_state())
            geometry=deepcopy(world.spatial.public_data())
            queue=deepcopy(world.queue)
            world.close()
            with patch('living_world.neighborhood.LivingNeighborhood',side_effect=AssertionError('Must not regenerate a save')):
                resumed=World(seed=123,database=database,layout='legacy')
            try:
                self.assertEqual(resumed.layout,'neighborhood-v1')
                self.assertEqual(resumed.seed,73)
                self.assertTrue(resumed.paused)
                self.assertEqual(resumed.speed,60)
                self.assertEqual(resumed.canonical_state(),before)
                self.assertEqual(resumed.spatial.public_data(),geometry)
                self.assertEqual(resumed.queue,queue)
                self.assertEqual(resumed.store.replay(),before)
                resumed.advance(300)
                self.assertEqual(resumed.invariants(),[])
            finally:resumed.close()

    def test_teacher_commutes_to_the_actual_school_interior(self):
        world=World(seed=73,layout='neighborhood-v1')
        try:
            aid='resident_004'
            with world.transaction('test.new_neighborhood_commute',list(world.actors),'Isolated real workplace route.'):
                for key in world.actors:
                    actor=world.edit('actors',key)
                    actor['owner']='external'
                    actor['needs']={k:.02 for k in actor['needs']}
                    actor['needs_at']=world.now
            actor=world.actors[aid]
            target=world.objects[actor['workplace']['target_id']]
            self.assertEqual(target['building_id'],'school')
            world.decide(aid,{'action':'work'})
            action=world.actors[aid]['action']
            self.assertEqual(action['target_id'],target['id'])
            self.assertTrue(all(world.spatial.walkable(tuple(cell)) for cell in action['path']))
            self.assertGreater(len(action['path']),1)
            world.advance(action['ends_at']-world.now)
            self.assertIn(world.actors[aid]['position'],target['anchors'])
            self.assertGreater(world.actors[aid]['schedule']['work_seconds'],0)
            self.assertEqual(world.invariants(),[])
            self.assertEqual(world.store.replay(),world.canonical_state())
        finally:world.close()


if __name__=='__main__':unittest.main()
