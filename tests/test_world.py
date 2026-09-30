import json
from pathlib import Path
import tempfile
import unittest
from collections import deque

from living_world.engine import World, RejectedProposal


class WorldTests(unittest.TestCase):
    def setUp(self):
        self.world=World()

    def tearDown(self):
        self.world.close()

    def test_households_and_every_interaction_anchor_reachable(self):
        w=self.world
        self.assertEqual(len(w.spatial.households),20)
        self.assertEqual(len(w.actors),44)
        self.assertEqual(len(w.objects),365)
        visited={(2,2)};queue=deque(visited)
        while queue:
            x,y=queue.popleft()
            for p in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if p not in visited and w.spatial.walkable(p):
                    visited.add(p);queue.append(p)
        for obj in w.objects.values():
            for anchor in obj['anchors']:
                self.assertIn(tuple(anchor),visited,obj['id'])
        sofa=next(o for o in w.objects.values() if o['kind']=='sofa')
        self.assertEqual((sofa['w'],sofa['h']),(3,1))

    def test_step_partition_does_not_change_decisions_or_history(self):
        other=World()
        try:
            self.world.advance(3600)
            for _ in range(60):
                other.advance(60)
            self.assertEqual(self.world.canonical_state(),other.canonical_state())
            self.assertEqual(self.world.store.sequence,other.store.sequence)
            self.assertEqual(self.world.queue,other.queue)
        finally:
            other.close()

    def test_accepted_changes_replay_exactly(self):
        self.world.advance(4*3600)
        self.assertEqual(self.world.store.replay(),self.world.canonical_state())
        self.assertEqual(self.world.invariants(),[])

    def test_two_residents_cannot_reserve_same_toilet(self):
        w=self.world
        ids=list(w.actors)[:2]
        # Exclude a newly seeded nearby chat from this resource-reservation test:
        # it is not the property under test and its consent draw is intentionally
        # probabilistic.  Both selected residents still use the real scheduler.
        with w.transaction('test.scenario',list(w.actors),'Both housemates urgently need the bathroom.'):
            for key in w.actors:
                actor=w.edit('actors',key)
                actor['owner']='procedural' if key in ids else 'external'
                actor['cooldowns']['chat']=w.now+3600
            for aid in ids:
                actor=w.edit('actors',aid)
                actor['needs']={k:.05 for k in actor['needs']}
                actor['needs']['bladder']=.99 if aid==ids[0] else .93
                # Once the first resident has reserved the toilet, only the
                # second gets a real, long-running shower alternative instead
                # of a short fallback wait that may finish before the assertion.
                if aid==ids[1]:actor['needs']['hygiene']=.99
                actor['needs_at']=w.now
        # The first intent is an explicit valid request.  The second resident's
        # scheduled decision then observes the live reservation, rather than a
        # stochastic choice deciding whether this test exercises the toilet.
        w.decide(ids[0],{'action':'toilet'})
        w.advance(20)
        toilets=[o for o in w.objects.values() if o['kind']=='toilet' and o['household_id']=='household_01']
        self.assertEqual(len(toilets[0]['reservations']),1)
        self.assertNotEqual(w.actors[ids[0]]['action']['kind'],w.actors[ids[1]]['action']['kind'])
        w.advance(600)
        self.assertEqual(w.invariants(),[])

    def test_ownership_handoff_preserves_actions_and_rejects_stale_intent(self):
        w=self.world;aid='resident_001'
        w.advance(5)
        old=json.loads(json.dumps(w.actors[aid]['action']))
        packet=w.transfer(aid,'external',1)
        self.assertEqual(w.actors[aid]['action'],old)
        self.assertEqual(packet['authority_scope']['owner_epoch'],2)
        with self.assertRaises(RejectedProposal):
            w.submit_intent({'actor_id':aid,'owner_epoch':1,'expected_version':w.actors[aid]['version'],'action':'wait'})
        w.advance(3600)
        self.assertIsNone(w.actors[aid]['action'])
        w.transfer(aid,'procedural',2)
        w.advance(2)
        self.assertIsNotNone(w.actors[aid]['action'])
        self.assertEqual(w.invariants(),[])

    def test_perspective_excludes_other_minds(self):
        w=self.world;w.advance(1800)
        packet=w.perspective('resident_001')
        for visible in packet['visible_people']:
            self.assertEqual(set(visible),{'id','name','position'})
        self.assertNotIn('actors',packet)
        self.assertTrue(all(b['evidence'] for b in packet['self']['beliefs']))

    def test_interruption_preserves_travel_and_releases_resources(self):
        w=self.world;w.advance(3)
        actor=next(a for a in w.actors.values() if a['action'] and a['action']['reservation_id'])
        aid=actor['id'];position=list(w.position_at(actor));money=actor['money']
        w.interrupt(aid,'Test interruption')
        self.assertEqual(w.actors[aid]['position'],position)
        self.assertEqual(w.actors[aid]['money'],money)
        self.assertEqual(w.invariants(),[])

    def test_checkpoint_resume_matches_uninterrupted_world(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'world.sqlite3'
            persisted=World(database=path)
            persisted.advance(1200);persisted.close()
            resumed=World(database=path)
            try:
                resumed.advance(1200)
                self.world.advance(2400)
                self.assertEqual(resumed.canonical_state(),self.world.canonical_state())
                self.assertEqual(resumed.store.replay(),resumed.canonical_state())
            finally:
                resumed.close()


if __name__=='__main__':
    unittest.main()
