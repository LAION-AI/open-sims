"""Regression coverage for arbitration between simultaneous critical needs."""

import unittest

from living_world.engine import World


class UrgentNeedsTests(unittest.TestCase):
    def setUp(self):
        self.world = World(seed=73, layout="neighborhood-v1")
        self.addCleanup(self.world.close)

    def critical_fixture(self, anchor_kind, bladder=.97, fatigue=.97):
        w, aid = self.world, "resident_001"
        with w.transaction("test.urgent_fixture", list(w.actors),
                           "Explicit simultaneous-critical-needs fixture."):
            for identifier in w.actors:
                person = w.edit("actors", identifier)
                person["owner"] = "procedural" if identifier == aid else "external"
                person["action"] = None
                person["routine"] = None
                person["cooldowns"] = {}
            actor = w.edit("actors", aid)
            target = next(obj for obj in w.objects.values()
                          if obj["kind"] == anchor_kind and obj["household_id"] == actor["household_id"])
            actor["position"] = list(target["anchors"][0])
            actor["needs"] = {key: .02 for key in actor["needs"]}
            actor["needs"].update(bladder=bladder, fatigue=fatigue)
            actor["needs_at"] = w.now
        return aid

    def test_critical_toilet_finishes_once_when_fatigue_is_also_critical(self):
        w = self.world
        aid = self.critical_fixture("toilet")
        w.decide(aid, {"action": "toilet"})
        action = w.actors[aid]["action"]
        self.assertEqual(action["kind"], "toilet")

        # Previously the fatigue urgent timer fired one second later and
        # cancelled this bladder-relieving action, then the inverse happened.
        w.advance(2)
        self.assertEqual(w.actors[aid]["action"]["kind"], "toilet")
        self.assertEqual(w.metrics["interrupted_actions"], 0)

        w.advance(w.actors[aid]["action"]["ends_at"] - w.now)
        self.assertIsNone(w.actors[aid]["action"])
        self.assertEqual(w.metrics["completed_actions"], 1)
        self.assertEqual(w.metrics["interrupted_actions"], 0)
        self.assertLess(w.needs_at(w.actors[aid])["bladder"], .1)
        self.assertGreater(w.needs_at(w.actors[aid])["fatigue"], .94)
        self.assertEqual(w.invariants(), [])

    def test_unrelated_action_is_still_preempted_by_simultaneous_critical_needs(self):
        w = self.world
        aid = self.critical_fixture("toilet")
        w.decide(aid, {"action": "wait"})
        self.assertEqual(w.actors[aid]["action"]["kind"], "wait")
        w.advance(1)
        self.assertIsNone(w.actors[aid]["action"])
        self.assertEqual(w.metrics["interrupted_actions"], 1)
        self.assertEqual(w.invariants(), [])

    def test_long_sleep_rechecks_after_fatigue_recovers_then_yields_to_critical_bladder(self):
        w = self.world
        aid = self.critical_fixture("bed")
        w.decide(aid, {"action": "sleep"})
        sleep = w.actors[aid]["action"]
        self.assertEqual(sleep["kind"], "sleep")
        rechecks = [event for event in w.queue if event[2] == "urgent" and event[3] == aid
                    and event[4] == sleep["id"]]
        self.assertEqual(len(rechecks), 1)
        recheck_at = rechecks[0][0]
        self.assertGreater(recheck_at, w.now + 1, "sleep is not interrupted instantly")
        self.assertLess(recheck_at, sleep["ends_at"], "sleep does not suppress bladder urgency all night")

        w.advance(recheck_at - w.now - 1)
        self.assertEqual(w.actors[aid]["action"]["kind"], "sleep")
        self.assertEqual(w.metrics["interrupted_actions"], 0)
        w.advance(1)
        self.assertIsNone(w.actors[aid]["action"])
        self.assertEqual(w.metrics["interrupted_actions"], 1)
        current = w.needs_at(w.actors[aid])
        self.assertLess(current["fatigue"], .91)
        self.assertGreaterEqual(current["bladder"], .939)
        self.assertEqual(w.invariants(), [])

    def test_long_sleep_rechecks_when_other_need_becomes_critical_after_start(self):
        w = self.world
        aid = self.critical_fixture("bed", bladder=.90, fatigue=.97)
        w.decide(aid, {"action": "sleep"})
        sleep = w.actors[aid]["action"]
        recheck = next(event for event in w.queue if event[2] == "urgent" and event[3] == aid
                       and event[4] == sleep["id"])
        self.assertLess(recheck[0], sleep["ends_at"])

        w.advance(recheck[0] - w.now)
        self.assertIsNone(w.actors[aid]["action"])
        self.assertEqual(w.metrics["interrupted_actions"], 1)
        current = w.needs_at(w.actors[aid])
        self.assertLess(current["fatigue"], .91)
        self.assertGreaterEqual(current["bladder"], .939)
        self.assertEqual(w.invariants(), [])

    def test_recovery_ping_without_interrupt_schedules_later_bladder_threshold(self):
        w = self.world
        aid = self.critical_fixture("bed", bladder=.80, fatigue=.97)
        w.decide(aid, {"action": "sleep"})
        sleep = w.actors[aid]["action"]
        first = next(event for event in w.queue if event[2] == "urgent" and event[3] == aid
                     and event[4] == sleep["id"])
        w.advance(first[0] - w.now)
        self.assertEqual(w.actors[aid]["action"]["kind"], "sleep")
        second = next(event for event in w.queue if event[2] == "urgent" and event[3] == aid
                      and event[4] == sleep["id"] and event[0] > first[0])
        self.assertLess(second[0], sleep["ends_at"])
        w.advance(second[0] - w.now)
        self.assertIsNone(w.actors[aid]["action"])
        self.assertEqual(w.metrics["interrupted_actions"], 1)


if __name__ == "__main__":
    unittest.main()
