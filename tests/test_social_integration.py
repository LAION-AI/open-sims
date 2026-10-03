"""Executed social-system acceptance tests; no engine fixtures fabricate history."""
from copy import deepcopy
import unittest
from unittest.mock import patch
import random

from living_world.engine import RejectedProposal, World


class SocialIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.world = World(seed=42)
        self.addCleanup(self.world.close)

    def _isolate_pair(self, aid, bid, *, position=(56, 61)):
        """Make exactly two residents available, with an authored present-time setup."""
        w = self.world
        with w.transaction("test.social.fixture", list(w.actors), "Explicit present-time social test fixture."):
            for identifier in w.actors:
                actor = w.edit("actors", identifier)
                actor["owner"] = "procedural" if identifier in (aid, bid) else "external"
                actor["action"] = None
                actor["position"] = list(position)
                actor["cooldowns"]["chat"] = 0
                actor["needs"] = {key: .02 for key in actor["needs"]}
                actor["needs_at"] = w.now
        return w.actors[aid], w.actors[bid]

    def _request(self, aid, bid, category):
        return self.world.decide(aid, {"action": "chat", "target_id": bid, "social_category": category})

    def test_accepted_contact_changes_each_direction_once_and_records_evidence(self):
        w = self.world
        actor, other = self._isolate_pair("resident_001", "resident_002")
        # This is a present-time willingness fixture, not an invented relationship.
        with w.transaction("test.social.acceptance", [actor["id"], other["id"]], "Recipient is currently socially available."):
            other = w.edit("actors", other["id"])
            other["needs"]["social"] = .90
            other["psychology"]["big_five"]["agreeableness"] = 1.0
            actor = w.edit("actors", actor["id"])
            actor["relations"][other["id"]].update(closeness=.80, trust=.80)
            other["relations"][actor["id"]].update(closeness=.80, trust=.80)
        before_a = deepcopy(actor["relations"][other["id"]])
        before_b = deepcopy(other["relations"][actor["id"]])
        original_rng=w.rng
        with patch.object(w,'rng',side_effect=lambda aid,decision,purpose:
                random.Random(1) if purpose=='chat_consent' else original_rng(aid,decision,purpose)):
            self._request(actor["id"], other["id"], "small_talk")
        action = w.actors[actor["id"]]["action"]
        self.assertEqual(action["social_category"], "small_talk")
        self.assertEqual(action["partner_id"], other["id"])
        with patch('living_world.engine.leisure_drama.resolve_social_event',return_value={'kind':'quiet'}):
            w.advance(action["duration"])

        actor, other = w.actors[actor["id"]], w.actors[other["id"]]
        relation_a, relation_b = actor["relations"][other["id"]], other["relations"][actor["id"]]
        self.assertEqual(relation_a["closeness"], round(before_a["closeness"] + .045, 4))
        self.assertEqual(relation_b["closeness"], round(before_b["closeness"] + .045, 4))
        self.assertEqual(relation_a["trust"], round(before_a["trust"] + .025, 4))
        self.assertEqual(relation_b["trust"], round(before_b["trust"] + .025, 4))
        evidence = relation_a["last_evidence_id"]
        self.assertEqual(evidence, relation_b["last_evidence_id"])
        for person, subject in ((actor, other["id"]), (other, actor["id"])):
            observations = person["psychology"]["theory_of_mind"]["known_people"][subject]["observations"]
            self.assertTrue(any(row["observation"] == "social:small_talk:positive" and row["evidence_id"] == evidence for row in observations))
            self.assertEqual(person["psychology"]["social_appraisal"]["category"], "small_talk")
        self.assertEqual(w.invariants(), [])
        self.assertEqual(w.store.replay(), w.canonical_state())

    def test_external_intent_cannot_bypass_kin_age_or_commitment_romance_guards(self):
        w = self.world
        actor, kin = self._isolate_pair("resident_005", "resident_010")
        with self.assertRaises(RejectedProposal):
            self._request(actor["id"], kin["id"], "flirt")

        adult, underage = self._isolate_pair("resident_012", "resident_013")
        with w.transaction("test.social.age", [underage["id"]], "Explicit eligibility boundary fixture."):
            w.edit("actors", underage["id"])["age"] = 17
        with self.assertRaises(RejectedProposal):
            self._request(adult["id"], underage["id"], "ask_date")

        committed, stranger = self._isolate_pair("resident_001", "resident_012")
        self.assertNotEqual(committed["family"]["partner_id"], stranger["id"])
        with self.assertRaises(RejectedProposal):
            self._request(committed["id"], stranger["id"], "express_affection")

    def test_story_argument_requires_completed_mutual_chat_and_reaches_both_journals(self):
        w=self.world
        actor,other=self._isolate_pair('resident_001','resident_002')
        with w.transaction('test.story.accept',[actor['id'],other['id']],
                           'Both participants are presently open to a conversation.'):
            w.edit('actors',other['id'])['psychology']['big_five']['agreeableness']=1.0
        before=deepcopy(w.actors[actor['id']]['relations'][other['id']])
        original_rng=w.rng
        with patch.object(w,'rng',side_effect=lambda aid,decision,purpose:
                random.Random(1) if purpose=='chat_consent' else original_rng(aid,decision,purpose)):
            self._request(actor['id'],other['id'],'small_talk')
        action=w.actors[actor['id']]['action']
        self.assertIsNotNone(action)
        self.assertEqual(w.actors[actor['id']]['relations'][other['id']]['closeness'],before['closeness'])
        story={'kind':'argument','text':'A small disagreement became an argument.'}
        with (patch('living_world.engine.storyteller.social_turn',return_value=story),
              patch('living_world.engine.leisure_drama.resolve_social_event',return_value={'kind':'quiet'})):
            w.advance(action['duration'])
        a,b=w.actors[actor['id']],w.actors[other['id']]
        self.assertLess(a['relations'][b['id']]['closeness'],before['closeness'])
        self.assertGreater(a['relations'][b['id']]['rivalry'],0)
        self.assertEqual(a['last_social_incident']['kind'],'argument')
        self.assertEqual(b['last_social_incident']['kind'],'argument')
        self.assertIn(a['emotion']['type'],{'Tense','Disappointed','Afraid'})
        for person in (a,b):
            self.assertTrue(any(story['text'] in beat['narration']
                                for beat in w.store.recent(person['id'],limit=8)))
        self.assertEqual(w.invariants(),[])
        self.assertEqual(w.store.replay(),w.canonical_state())

    def test_declined_flirt_does_not_force_partnership_or_shared_action(self):
        w = self.world
        actor, other = self._isolate_pair("resident_012", "resident_013")
        with w.transaction("test.social.decline", [actor["id"], other["id"]], "Recipient is currently unavailable."):
            actor = w.edit("actors", actor["id"])
            other = w.edit("actors", other["id"])
            actor["family"].update(partner_id=None, relationship_status="single")
            other["family"].update(partner_id=None, relationship_status="single")
            # Acceptance is impossible when any recipient need is critical.
            other["needs"]["hunger"] = .99
        before = deepcopy(actor["relations"].get(other["id"], {}))
        self._request(actor["id"], other["id"], "flirt")

        actor, other = w.actors[actor["id"]], w.actors[other["id"]]
        self.assertIsNone(actor["action"])
        self.assertIsNone(other["action"])
        self.assertIsNone(actor["family"]["partner_id"])
        self.assertIsNone(other["family"]["partner_id"])
        romance = actor["relations"][other["id"]]["layers"]["romance"]
        self.assertNotEqual(romance["status"], "established")
        self.assertEqual(romance["score"], before.get("layers", {}).get("romance", {}).get("score", 0.0))
        self.assertEqual(actor["last_decision"]["policy"], "recipient declined; no shared action executed")
        self.assertEqual(w.invariants(), [])


if __name__ == "__main__":
    unittest.main()
