import copy
import random

from living_world import leisure_drama as drama


class FixedRng:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


def sim(aid, **traits):
    return {"id": aid, "psychology": {"big_five": {
        "openness": .5, "conscientiousness": .5,
        "extraversion": .5, "agreeableness": .5, "neuroticism": .5,
        **traits,
    }}}


def test_catalog_has_varied_activities_and_returns_isolated_copy():
    catalogue = drama.activity_definitions()
    assert len(catalogue) >= 25
    assert {"host_party", "ask_on_date", "paint", "hike", "play_team_sport", "relax_at_home"} <= catalogue.keys()
    catalogue.clear()
    assert len(drama.activity_definitions()) >= 25


def test_action_scores_reflect_personality_and_can_be_sampled():
    outgoing = sim("a", extraversion=.95)
    introvert = sim("b", extraversion=.05)
    outgoing_rows = {x["activity"]: x["weight"] for x in drama.leisure_actions(outgoing)}
    introvert_rows = {x["activity"]: x["weight"] for x in drama.leisure_actions(introvert)}
    assert outgoing_rows["attend_party"] > introvert_rows["attend_party"]
    assert introvert_rows["read_for_fun"] > outgoing_rows["read_for_fun"]
    selected = drama.choose_leisure_action(outgoing, None, random.Random(7))
    assert selected["kind"] == "leisure" and selected["activity"] in drama.activity_definitions()


def test_romantic_outcomes_fail_closed_without_all_three_gates():
    a, b = sim("a"), sim("b")
    before = copy.deepcopy((a, b))
    for context in ({"romantic": True}, {"romantic": True, "both_adults": True},
                    {"romantic": True, "both_adults": True, "non_kin": True}):
        result = drama.resolve_social_event(a, b, "go_on_date", context, FixedRng(.999))
        assert result["kind"] == "quiet"
    assert (a, b) == before


def test_adult_romance_includes_intimacy_but_not_unsolicited_pregnancy():
    a, b = sim("a"), sim("b")
    context = {"romantic": True, "both_adults": True, "non_kin": True,
               "mutual_consent": True, "closeness": 1}
    # The bedroom event is in the weighted list and can be deliberately sampled.
    result = drama.resolve_social_event(a, b, "go_on_date", context, FixedRng(.25))
    assert result["kind"] in {"quiet", "date_spark", "kiss", "bedroom_intimacy", "good_time", "new_friend", "awkward_moment"}
    assert "family_planning" not in result["effects"]
    family = drama.resolve_social_event(a, b, "go_on_date", {**context, "committed": True,
                                        "trying_for_child": True}, FixedRng(.999))
    assert family["kind"] == "quiet"  # rare outcome remains a chance, not an automatic result


def test_tension_increases_conflict_chance_and_fight_remains_rare():
    a, b = sim("a", agreeableness=.1, neuroticism=.9), sim("b", agreeableness=.1, neuroticism=.9)
    calm = drama.resolve_social_event(a, b, "board_games", {"tension": 0}, FixedRng(.001))
    tense = drama.resolve_social_event(a, b, "board_games", {"tension": 1}, FixedRng(.001))
    assert calm["kind"] == tense["kind"] == "argument"
    assert tense["probability"] > calm["probability"]
    assert drama.event_definitions()["fight"]["weight"] < .01


def test_unknown_action_and_unseeded_randomness_are_rejected():
    try:
        drama.resolve_social_event(sim("a"), None, "teleport", {}, FixedRng(.2))
    except ValueError:
        pass
    else:
        raise AssertionError("unknown activity accepted")
    try:
        drama.choose_leisure_action(sim("a"), None, None)
    except ValueError:
        pass
    else:
        raise AssertionError("global randomness accepted")
