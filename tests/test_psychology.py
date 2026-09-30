from copy import deepcopy
import random
import unittest

from living_world.psychology import (
    SOCIAL_CATEGORIES, action_bias, apply_social, complete_activity,
    initialize_psychology, initialize_social_graph, initial_family_profiles,
    observe, social_candidates, update_fears,
)


def actor(identifier, age=30, household="home_a"):
    return {"id": identifier, "name": identifier, "age": age, "household_id": household,
            "preferences": {"reading": .8, "socializing": .6, "craft": .4},
            "profile": {"interests": ["reading"]}, "needs": {"social": .7}, "relations": {}}


class PsychologyTests(unittest.TestCase):
    def test_initialization_is_seeded_and_does_not_mutate_actor(self):
        person = actor("a")
        before = deepcopy(person)
        one = initialize_psychology(person, random.Random(7), 10)
        two = initialize_psychology(person, random.Random(7), 10)
        self.assertEqual(one, two)
        self.assertEqual(person, before)
        self.assertEqual(set(one["big_five"]), {"openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"})
        self.assertTrue({"dogs", "job_loss"}.issubset({fear["kind"] for fear in one["fears"]}))

    def test_new_world_fixture_makes_adult_multigenerational_explicit_links(self):
        people = {f"p{i}": actor(f"p{i}", household=f"home_{i}") for i in range(11)}
        fixture = initial_family_profiles(people)
        self.assertTrue(all(row["age"] >= 18 for row in fixture.values()))
        for identifier, patch in fixture.items():
            people[identifier].update(patch)
        graph = initialize_social_graph(people, 100)
        self.assertEqual(graph["p0"]["relations"]["p4"]["layers"]["family"]["status"], "grandchild")
        self.assertEqual(graph["p4"]["relations"]["p9"]["layers"]["family"]["status"], "cousin")
        self.assertEqual(graph["p2"]["relations"]["p3"]["layers"]["romance"]["status"], "established")
        self.assertNotIn("p10", graph["p0"]["relations"])

    def test_social_categories_include_twenty_and_block_known_kin_romance(self):
        self.assertEqual(len(SOCIAL_CATEGORIES), 20)
        parent, child = actor("parent", 50), actor("child", 25, "home_b")
        child["family"] = {"parent_ids": ["parent"], "partner_id": None, "relationship_status": "single"}
        graph = initialize_social_graph({"parent": parent, "child": child})
        parent.update(graph["parent"]); child.update(graph["child"])
        parent["psychology"] = initialize_psychology(parent, random.Random(1))
        child["psychology"] = initialize_psychology(child, random.Random(2))
        flirt = next(row for row in social_candidates(parent, child, 20) if row["category"] == "flirt")
        self.assertFalse(flirt["allowed"])
        with self.assertRaises(ValueError):
            apply_social(parent, child, "flirt", "success", 20, "beat_1")
        adult, minor = actor("adult", 30), actor("minor", 17, "home_c")
        adult["psychology"] = initialize_psychology(adult, random.Random(3))
        minor["psychology"] = initialize_psychology(minor, random.Random(4))
        self.assertFalse(next(row for row in social_candidates(adult, minor, 20) if row["category"] == "ask_date")["allowed"])

    def test_social_resolution_is_bilateral_patch_and_accepts_success_alias(self):
        first, second = actor("a"), actor("b", household="home_b")
        graph = initialize_social_graph({"a": first, "b": second})
        first.update(graph["a"]); second.update(graph["b"])
        before = deepcopy(first)
        patch = apply_social(first, second, "small_talk", "success", 42, "beat_42")
        self.assertEqual(first, before)
        self.assertGreater(patch["a"]["relations"]["b"]["closeness"], 0)
        self.assertEqual(patch["b"]["relations"]["a"]["last_evidence_id"], "beat_42")

    def test_tom_is_observation_bounded_and_fears_have_expiry(self):
        person = actor("a")
        person["psychology"] = initialize_psychology(person, random.Random(4))
        patch = observe(person, "b", "social:small_talk:declined", 99, "beat_99")
        known = patch["psychology"]["theory_of_mind"]["known_people"]["b"]
        self.assertEqual(known["observations"][0]["evidence_id"], "beat_99")
        self.assertEqual(known["inferences"]["availability"]["confidence"], "low")
        fear_patch = update_fears(person, "dog_encounter", 100, "beat_100")
        dog = next(row for row in fear_patch["psychology"]["fears"] if row["kind"] == "dogs")
        self.assertEqual(dog["expires_at"], 100 + 4 * 3600)

    def test_activity_and_bias_are_bounded(self):
        person = actor("a")
        person["preferences"].update({"cooking": .9, "walking": .8})
        person["psychology"] = initialize_psychology(person, random.Random(8))
        patch = complete_activity(person, "read", 200, "beat_200", 600)
        hobby = next(row for row in patch["psychology"]["hobbies"] if row["kind"] == "reading")
        self.assertEqual(hobby["practice_seconds"], 600)
        self.assertEqual(action_bias(person, "creative_hobby"), action_bias(person, "craft"))
        self.assertEqual(action_bias(person, "stroll"), action_bias(person, "walk"))
        meal_patch = complete_activity(person, "prepare_meal", 201, "beat_201", 300)
        cooking = next(row for row in meal_patch["psychology"]["hobbies"] if row["kind"] == "cooking")
        self.assertEqual(cooking["practice_seconds"], 300)
        self.assertGreaterEqual(action_bias(person, "chat"), -1)
        self.assertLessEqual(action_bias(person, "chat"), 1)

    def test_tom_context_and_committed_partner_gate_social_candidates(self):
        first, second = actor("a"), actor("b", household="home_b")
        first["psychology"] = initialize_psychology(first, random.Random(9))
        second["psychology"] = initialize_psychology(second, random.Random(10))
        baseline = {row["category"]: row for row in social_candidates(first, second, 100)}
        first.update(observe(first, "b", "social:small_talk:declined", 100, "beat_decline"))
        after_decline = {row["category"]: row for row in social_candidates(first, second, 101)}
        self.assertLess(after_decline["confide"]["score"], baseline["confide"]["score"])
        first.update(observe(first, "b", "social:small_talk:accepted", 102, "beat_accept"))
        after_rapport = {row["category"]: row for row in social_candidates(first, second, 103)}
        self.assertGreater(after_rapport["tell_joke"]["score"], baseline["tell_joke"]["score"])
        self.assertFalse(after_rapport["coordinate_work"]["allowed"])
        self.assertFalse(after_rapport["apologize"]["allowed"])
        first["workplace"] = {"workplace_id": "studio"}
        second["workplace_id"] = "studio"
        with_workplace = {row["category"]: row for row in social_candidates(first, second, 103)}
        self.assertTrue(with_workplace["coordinate_work"]["allowed"])
        first["family"] = {"partner_id": "c", "parent_ids": [], "relationship_status": "married"}
        committed = {row["category"]: row for row in social_candidates(first, second, 104)}
        self.assertFalse(committed["flirt"]["allowed"])
        first["relationship_preferences"] = {"nonmonogamous": True}
        opted_in = {row["category"]: row for row in social_candidates(first, second, 104)}
        self.assertTrue(opted_in["flirt"]["allowed"])

    def test_fixture_requires_its_authored_population(self):
        with self.assertRaises(ValueError):
            initial_family_profiles({"only": actor("only")})


if __name__ == "__main__":
    unittest.main()
