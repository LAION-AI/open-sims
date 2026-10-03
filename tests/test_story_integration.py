"""Acceptance tests for StoryLife's transaction, privacy, and migration seams."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import random

from living_world import affect
from living_world.engine import World
from living_world.ledger import BeatStore


class StoryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.world = World(seed=42)
        self.addCleanup(self.world.close)

    def _isolate_pair(self, aid="resident_001", bid="resident_002"):
        w = self.world
        with w.transaction("test.story.fixture", list(w.actors), "Explicit current-state fixture; no retrospective biography."):
            for identifier in w.actors:
                person = w.edit("actors", identifier)
                person["owner"] = "procedural" if identifier in (aid, bid) else "external"
                person["position"] = [56, 61]
                person["action"] = None
                person["cooldowns"]["chat"] = 0
                person["needs"] = {key: .02 for key in person["needs"]}
                person["needs_at"] = w.now
        return w.actors[aid], w.actors[bid]

    def test_perspective_exposes_only_self_story_not_actual_affect_causes(self):
        w = self.world
        with w.transaction("test.story.private_affect", ["resident_001"], "Private affect fixture."):
            person = w.edit("actors", "resident_001")
            person["affect"] = affect.appraise(person, person["needs"], w.now,
                                                 {"kind": "insult", "text": "PRIVATE_ACTUAL_MARKER", "subject_id": "resident_002"},
                                                 "beat_private")
        packet = w.perspective("resident_001")
        self.assertEqual(set(packet["self"]["affect"]), {"primary", "self_narrative", "updated_at"})
        self.assertNotIn("PRIVATE_ACTUAL_MARKER", str(packet))
        self.assertNotIn("actual_narrative", str(packet))
        self.assertNotIn("causes", str(packet))

    def test_begin_appraisal_and_expired_projection_are_consistent_and_nonmutating(self):
        w = self.world
        with w.transaction("test.story.begin", ["resident_003"], "Urgent present need fixture."):
            person = w.edit("actors", "resident_003")
            person["owner"] = "procedural"
            person["needs"]["bladder"] = .95
            person["needs_at"] = w.now
        w.decide("resident_003", {"action": "wait"})
        self.assertIn("distress", {state["id"] for state in w.actors["resident_003"]["affect"]["states"]})

        with w.transaction("test.story.expiry", ["resident_003"], "Expired affect projection fixture."):
            person = w.edit("actors", "resident_003")
            person["affect"] = affect.initialize_affect(person, w.now - 1300)["affect"]
            person["affect"] = affect.appraise(person, {key: .01 for key in person["needs"]}, w.now - 1300,
                                                 {"kind": "dog_encounter", "text": "Earlier direct dog encounter"}, "beat_old")
        canonical = deepcopy(w.actors["resident_003"]["affect"])
        inspected = w.inspect("resident_003")
        projected = next(row for row in w.snapshot()["actors"] if row["id"] == "resident_003")["affect"]
        self.assertEqual(inspected["affect"]["states"], [])
        self.assertEqual(projected["states"], [])
        self.assertEqual(w.actors["resident_003"]["affect"], canonical)

    def test_completed_affection_uses_structured_social_cause_for_runtime_multi_affect(self):
        """Completion must preserve social category/outcome for the affect appraiser."""
        w = self.world
        actor, other = self._isolate_pair()
        with w.transaction("test.story.affection", [actor["id"], other["id"]], "Recipient is currently available."):
            actor = w.edit("actors", actor["id"])
            other = w.edit("actors", other["id"])
            actor["relations"][other["id"]].update(closeness=.8, trust=.8)
            other["relations"][actor["id"]].update(closeness=.8, trust=.8)
            other["needs"]["social"] = .90
            other["psychology"]["big_five"]["agreeableness"] = 1.0
        original_rng=w.rng
        with patch.object(w,'rng',side_effect=lambda aid,decision,purpose:
                random.Random(1) if purpose=='chat_consent' else original_rng(aid,decision,purpose)):
            w.decide(actor["id"], {"action": "chat", "target_id": other["id"], "social_category": "express_affection"})
        action = w.actors[actor["id"]]["action"]
        self.assertIsNotNone(action)
        with patch('living_world.engine.leisure_drama.resolve_social_event',return_value={'kind':'quiet'}):
            w.advance(action["duration"])
        actor, other = w.actors[actor["id"]], w.actors[other["id"]]
        for person in (actor, other):
            states = {state["id"]: state for state in person["affect"]["states"]}
            self.assertIn("affection", states)
            self.assertIn("infatuation", states)
            self.assertTrue(any(cause["kind"] == "romantic_affection" and cause["adult_relation"] is True
                                for cause in states["affection"]["causes"]))

    def test_known_people_graph_has_directed_importance_and_is_not_in_perspective(self):
        w = self.world
        inspected = w.inspect("resident_001")
        graph = inspected["social_graph"]
        edge = next(edge for edge in graph["edges"] if edge["target"] == "resident_002")
        self.assertEqual(edge["source"], "resident_001")
        self.assertGreater(edge["importance"], 0)
        self.assertIn("household", edge["relationship_types"])
        self.assertNotIn("social_graph", w.perspective("resident_001")["self"])

    def test_v2_to_v3_migration_preserves_existing_records_and_replays_exactly(self):
        w = self.world
        legacy_actors = deepcopy(w.actors)
        for person in legacy_actors.values():
            person.pop("affect", None)
            person.pop("belongings", None)
        legacy_objects = {key: deepcopy(value) for key, value in w.objects.items() if int(key.split("_")[1]) <= 349}
        legacy_meta = deepcopy(w.meta)
        legacy_meta.pop("story_systems", None)
        payload = {"seed": w.seed, "rule_hash": w.rules.v2_hash, "now": w.now, "actors": legacy_actors,
                   "objects": legacy_objects, "meta": legacy_meta, "queue": deepcopy(w.queue),
                   "queue_serial": w.queue_serial, "epoch": w.epoch, "metrics": deepcopy(w.metrics)}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "v2.sqlite3"
            store = BeatStore(path)
            changes = []
            for collection, records in (("actors", payload["actors"]), ("objects", payload["objects"]), ("world", payload["meta"])):
                changes.extend({"collection": collection, "subject_id": key, "component_path": "$", "new_value": value}
                               for key, value in records.items())
            store.append(w._beat("v2.fixture", [], "Explicit v2 fixture.", changes))
            store.save_checkpoint(payload)
            store.close()
            resumed = World(database=path)
            try:
                backup = BeatStore(resumed.migration_backup)
                try:
                    self.assertEqual(backup.checkpoint()["rule_hash"], w.rules.v2_hash)
                finally:
                    backup.close()
                for key, before in legacy_objects.items():
                    self.assertEqual(resumed.objects[key], before, key)
                self.assertEqual(resumed.actors["resident_001"]["age"], legacy_actors["resident_001"]["age"])
                self.assertIn("affect", resumed.actors["resident_001"])
                self.assertIn("belongings", resumed.actors["resident_001"])
                self.assertEqual(resumed.store.replay(), resumed.canonical_state())
                self.assertEqual(resumed.invariants(), [])
            finally:
                resumed.close()


if __name__ == "__main__":
    unittest.main()
