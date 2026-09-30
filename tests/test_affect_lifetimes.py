"""Regression tests for evidence-level affect lifetimes and achievement gates."""

from copy import deepcopy
import unittest

from living_world.affect import appraise, project_affect


def actor():
    return {"id": "resident_test", "needs": {"bladder": .1, "fatigue": .1, "social": .1},
            "relations": {}, "psychology": {"theory_of_mind": {"known_people": {}}}}


class AffectLifetimeTests(unittest.TestCase):
    def test_pride_requires_a_goal_work_craft_or_finished_recipe(self):
        ordinary = actor()
        result = appraise(ordinary, ordinary["needs"], 100,
                          {"kind": "activity_completed", "category": "wait", "text": "Completed waiting"}, "beat_wait")
        self.assertNotIn("pride", {state["id"] for state in result["states"]})

        for category in ("work", "creative_hobby", "bake_pizza", "cook_pancake"):
            person = actor()
            achieved = appraise(person, person["needs"], 100,
                                {"kind": "activity_completed", "category": category,
                                 "text": f"Completed {category}"}, f"beat_{category}")
            pride = next(state for state in achieved["states"] if state["id"] == "pride")
            self.assertEqual(pride["components"][0]["cause"]["evidence_id"], f"beat_{category}")
            self.assertEqual(pride["components"][0]["expires_at"], 1000)

        person = actor()
        goal = appraise(person, person["needs"], 100,
                        {"kind": "goal_completed", "category": "community", "text": "Goal completed"}, "beat_goal")
        self.assertIn("pride", {state["id"] for state in goal["states"]})

    def test_expired_component_and_its_cause_are_filtered_while_later_component_remains(self):
        person = actor()
        first = appraise(person, person["needs"], 100,
                         {"kind": "insult", "text": "First explicit insult"}, "beat_first")
        person["affect"] = first
        second = appraise(person, person["needs"], 300,
                          {"kind": "insult", "text": "Second explicit insult"}, "beat_second")
        person["affect"] = second
        canonical = deepcopy(second)

        visible = project_affect(person, 1000)
        anger = next(state for state in visible["states"] if state["id"] == "anger")
        self.assertEqual([part["cause"]["evidence_id"] for part in anger["components"]], ["beat_second"])
        self.assertEqual([cause["evidence_id"] for cause in anger["causes"]], ["beat_second"])
        self.assertNotIn("First explicit insult", visible["actual_narrative"])
        self.assertEqual(person["affect"], canonical)

    def test_components_and_causes_are_bounded_to_six_latest_evidence_records(self):
        person = actor()
        for index in range(8):
            person["affect"] = appraise(person, person["needs"], 100 + index,
                                         {"kind": "insult", "text": f"Explicit insult {index}"}, f"beat_{index}")
        anger = next(state for state in person["affect"]["states"] if state["id"] == "anger")
        self.assertEqual(len(anger["components"]), 6)
        self.assertEqual(len(anger["causes"]), 6)
        self.assertEqual([part["cause"]["evidence_id"] for part in anger["components"]],
                         [f"beat_{index}" for index in range(2, 8)])

    def test_legacy_state_without_components_uses_recorded_expiry_not_permanent_fallback(self):
        person = actor()
        person["affect"] = {"states": [{"id": "fear", "intensity": .7, "expires_at": 200,
                                       "causes": [{"kind": "legacy_display_adapter", "text": "Retained legacy display",
                                                   "evidence_id": "legacy_1", "subject_id": "resident_test"}]}]}
        visible = project_affect(person, 150)
        self.assertEqual(visible["states"][0]["components"][0]["cause"]["evidence_id"], "legacy_1")
        self.assertEqual(project_affect(person, 200)["states"], [])

    def test_normal_self_story_names_a_recorded_activity_or_achievement(self):
        person = actor()
        started = appraise(person, person["needs"], 100,
                           {"kind": "activity_started", "category": "read", "text": "Started reading"}, "beat_read")
        self.assertIn("reading", started["self_narrative"])
        achiever = actor()
        completed = appraise(achiever, achiever["needs"], 200,
                             {"kind": "activity_completed", "category": "creative_hobby", "text": "Completed craft"}, "beat_craft")
        self.assertIn("completed a craft project", completed["self_narrative"])
        self.assertNotIn("new event", completed["self_narrative"].lower())


if __name__ == "__main__":
    unittest.main()
