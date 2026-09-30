from copy import deepcopy
import unittest

from living_world.affect import (
    EMOTIONS, adapt_legacy_emotion, appraise, initialize_affect, project_affect,
    social_graph_projection, taxonomy_projection,
)


def actor(identifier="a"):
    return {"id": identifier, "needs": {"bladder": .1, "fatigue": .1, "social": .1},
            "relations": {}, "psychology": {"theory_of_mind": {"known_people": {}}}}


class AffectTests(unittest.TestCase):
    def test_registry_is_exactly_forty_source_labels_with_no_active_defaults(self):
        registry = taxonomy_projection()
        self.assertEqual(len(registry["emotions"]), 40)
        self.assertEqual([row["label"] for row in registry["emotions"]], [
            "Amusement", "Elation", "Pleasure/Ecstasy", "Contentment", "Thankfulness/Gratitude", "Affection",
            "Infatuation", "Hope/Enthusiasm/Optimism", "Triumph", "Pride", "Interest", "Awe",
            "Astonishment/Surprise", "Concentration", "Contemplation", "Relief", "Longing", "Teasing",
            "Impatience and Irritability", "Sexual Lust", "Doubt", "Fear", "Distress", "Confusion",
            "Embarrassment", "Shame", "Disappointment", "Sadness", "Bitterness", "Contempt", "Disgust",
            "Anger", "Malevolence/Malice", "Sourness", "Pain", "Helplessness", "Fatigue/Exhaustion",
            "Emotional Numbness", "Intoxication/Altered States of Consciousness", "Jealousy & Envy",
        ])
        person = actor()
        patch = initialize_affect(person, 5)
        self.assertEqual(patch["affect"]["states"], [])
        self.assertNotIn("affect", person)

    def test_urgent_bladder_and_real_affection_can_be_simultaneous(self):
        person = actor()
        person["needs"]["bladder"] = .95
        result = appraise(person, person["needs"], 100,
                          {"kind": "romantic_affection", "category": "express_affection", "outcome": "positive",
                           "adult_relation": True, "text": "A mutually accepted affectionate interaction", "subject_id": "b"}, "beat_100")
        states = {state["id"]: state for state in result["states"]}
        self.assertIn("distress", states)
        self.assertIn("affection", states)
        self.assertEqual(states["affection"]["causes"][0]["evidence_id"], "beat_100")
        self.assertEqual(states["distress"]["causes"][0]["kind"], "modeled_need")
        self.assertIn("Modeled urgent bladder need", result["actual_narrative"])

    def test_self_rationalization_cannot_replace_evidence_bound_cause(self):
        person = actor()
        result = appraise(person, person["needs"], 100,
                          {"kind": "insult", "text": "Observed explicit insult", "subject_id": "b"}, "beat_101")
        actual = result["actual_narrative"]
        self.assertIn("Observed explicit insult", actual)
        self.assertNotEqual(actual, result["self_narrative"])
        self.assertIn("cannot be fully sure", result["self_narrative"])
        self.assertEqual(result["states"][0]["causes"][0]["evidence_id"], "beat_101")

    def test_trait_sensitive_self_story_acknowledges_evidenced_affection_without_inventing_events(self):
        outgoing, cautious = actor("outgoing"), actor("cautious")
        outgoing["psychology"]["big_five"] = {"extraversion": .9, "agreeableness": .4, "neuroticism": .2}
        cautious["psychology"]["big_five"] = {"extraversion": .2, "agreeableness": .4, "neuroticism": .9}
        cause = {"kind": "romantic_affection", "category": "express_affection", "outcome": "positive",
                 "adult_relation": True, "text": "Accepted affectionate interaction", "subject_id": "b"}
        outgoing_result = appraise(outgoing, outgoing["needs"], 100, cause, "beat_affection")
        cautious_result = appraise(cautious, cautious["needs"], 100, cause, "beat_affection")
        self.assertIn("open and connected", outgoing_result["self_narrative"])
        self.assertIn("only a friendly conversation", cautious_result["self_narrative"])
        self.assertNotEqual(outgoing_result["self_narrative"], cautious_result["self_narrative"])
        for result in (outgoing_result, cautious_result):
            self.assertIn("tentative gameplay interpretation", result["self_narrative"])
            self.assertIn("Accepted affectionate interaction", result["actual_narrative"])
            self.assertNotIn("new event", result["self_narrative"].lower())

    def test_mixed_social_and_need_appraisal_keeps_each_evidence_stream(self):
        person = actor()
        person["needs"]["bladder"] = .95
        result = appraise(person, person["needs"], 100,
                          {"kind": "romantic_affection", "category": "express_affection", "outcome": "positive",
                           "adult_relation": True, "text": "Accepted affectionate interaction", "subject_id": "b"}, "beat_mix")
        states = {state["id"]: state for state in result["states"]}
        self.assertEqual({cause["kind"] for cause in states["distress"]["causes"]}, {"modeled_need"})
        self.assertEqual({cause["kind"] for cause in states["affection"]["causes"]}, {"romantic_affection"})
        self.assertIn("connection and an immediate need", result["self_narrative"])

    def test_activity_baseline_interest_and_concentration_are_explicit_event_effects(self):
        person = actor()
        result = appraise(person, person["needs"], 100,
                          {"kind": "activity_started", "category": "read", "text": "Started reading"}, "beat_read")
        states = {state["id"] for state in result["states"]}
        self.assertTrue({"contentment", "interest", "concentration"}.issubset(states))
        self.assertFalse({"sexual_lust", "intoxication_altered_states_of_consciousness"} & states)

    def test_relief_requires_real_delta_and_physical_need_state_refreshes(self):
        person = actor()
        person["needs"]["bladder"] = .95
        first = appraise(person, person["needs"], 100, {"kind": "activity_started", "category": "wait", "text": "Started waiting"}, "beat_1")
        self.assertIn("distress", {state["id"] for state in first["states"]})
        person["affect"] = first
        person["needs"]["bladder"] = .10
        refreshed = appraise(person, person["needs"], 200,
                             {"kind": "need_relief", "category": "bladder", "relief": {"bladder": .85}, "text": "Bladder need reduced"}, "beat_2")
        self.assertNotIn("distress", {state["id"] for state in refreshed["states"]})
        self.assertIn("relief", {state["id"] for state in refreshed["states"]})
        no_delta = appraise(person, person["needs"], 201,
                            {"kind": "need_relief", "category": "bladder", "relief": {"bladder": 0}, "text": "No reduction"}, "beat_3")
        self.assertNotIn("relief", {state["id"] for state in no_delta["states"]})

    def test_infatuation_and_romantic_rejection_require_explicit_adult_relation_events(self):
        person = actor()
        successful = appraise(person, person["needs"], 100,
                               {"kind": "romantic_affection", "category": "flirt", "outcome": "positive", "adult_relation": True,
                                "text": "Accepted adult flirt", "subject_id": "b"}, "beat_romance")
        self.assertTrue({"affection", "infatuation"}.issubset({state["id"] for state in successful["states"]}))
        missing_gate = appraise(person, person["needs"], 100,
                                {"kind": "romantic_affection", "category": "flirt", "outcome": "positive", "text": "Ungated flirt"}, "beat_bad")
        self.assertNotIn("infatuation", {state["id"] for state in missing_gate["states"]})
        rejected = appraise(person, person["needs"], 100,
                            {"kind": "romantic_affection", "category": "flirt", "outcome": "declined", "adult_relation": True,
                             "text": "Explicit adult romantic rejection"}, "beat_declined")
        self.assertTrue({"sadness", "longing"}.issubset({state["id"] for state in rejected["states"]}))

    def test_projection_expires_states_without_mutating_canonical_affect(self):
        person = actor()
        person["affect"] = appraise(person, person["needs"], 100,
                                     {"kind": "dog_encounter", "text": "Observed dog nearby"}, "beat_102")
        before = deepcopy(person["affect"])
        visible = project_affect(person, 1301)
        self.assertEqual(visible["states"], [])
        self.assertEqual(person["affect"], before)

    def test_no_automatic_intoxication_or_lust_from_age_or_appearance(self):
        person = actor()
        person.update(age=19, appearance={"style": "anything"})
        result = appraise(person, person["needs"], 100,
                          {"kind": "appearance", "text": "Actor is wearing an outfit"}, "beat_103")
        self.assertFalse({"sexual_lust", "intoxication_altered_states_of_consciousness"} & {state["id"] for state in result["states"]})

    def test_legacy_adapter_has_stable_state_id_without_rewriting_history(self):
        person = actor()
        person["emotion"] = {"type": "Afraid", "intensity": .7, "cause": "older display text"}
        result = adapt_legacy_emotion(person, 50, "legacy_1")
        self.assertEqual(result["primary"], "fear")
        self.assertEqual(result["states"][0]["causes"][0]["evidence_id"], "legacy_1")
        self.assertIn("not reconstructed", result["actual_narrative"])

    def test_directed_graph_has_known_edges_not_merely_seen_people_or_target_minds(self):
        person, known, seen = actor("a"), actor("b"), actor("c")
        person["relations"]["b"] = {"closeness": .7, "trust": .8, "respect": .6, "attraction": .1, "tension": .0,
                                       "last_interaction": 20, "layers": {"friendship": {"status": "developing"}}}
        person["psychology"]["theory_of_mind"]["known_people"] = {"c": {"observations": [{"at": 1}], "inferences": {}}}
        known["affect"] = {"secret": "must not project"}
        graph = social_graph_projection(person, {"a": person, "b": known, "c": seen}, 100)
        self.assertEqual([node["id"] for node in graph["nodes"]], ["b"])
        self.assertEqual(graph["observed_not_known"], ["c"])
        self.assertNotIn("secret", str(graph))
        self.assertEqual(graph["edges"][0]["source"], "a")


if __name__ == "__main__":
    unittest.main()
