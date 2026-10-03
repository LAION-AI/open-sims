"""Pure leisure and social-drama decision helpers.

The coordinator owns state changes.  This module only describes weighted
actions and returns a proposed event; callers apply effects transactionally.
All chance is sampled through an explicitly supplied RNG.
"""
from __future__ import annotations

from copy import deepcopy


# id, display label, tags, extroversion pull, openness pull, conscientiousness pull
_ACTIVITIES = [
    ("host_party", "Host a party", ("social", "party"), .18, .04, -.05),
    ("attend_party", "Go to a party", ("social", "party"), .20, .06, -.08),
    ("ask_on_date", "Ask someone on a date", ("social", "romance"), .12, .08, .02),
    ("go_on_date", "Go on a date", ("social", "romance"), .15, .05, -.02),
    ("dance", "Dance", ("social", "music"), .18, .10, -.04),
    ("karaoke", "Sing karaoke", ("social", "music"), .16, .12, -.02),
    ("board_games", "Play board games", ("social", "games"), .06, .06, .02),
    ("video_games", "Play video games", ("games",), .02, .10, .01),
    ("read_for_fun", "Read for fun", ("quiet", "reading"), -.16, .14, .08),
    ("write_story", "Write a story", ("quiet", "creative"), -.10, .20, .08),
    ("paint", "Paint or sketch", ("creative",), -.08, .22, .04),
    ("play_instrument", "Play an instrument", ("creative", "music"), -.03, .20, .05),
    ("craft_project", "Make something by hand", ("creative", "craft"), -.05, .16, .12),
    ("garden", "Tend a garden", ("outdoors", "quiet"), -.04, .08, .12),
    ("cook_for_fun", "Try a new recipe", ("creative", "food"), .02, .10, .12),
    ("bake_treats", "Bake something nice", ("creative", "food"), .03, .08, .14),
    ("go_for_walk", "Take a long walk", ("outdoors", "quiet"), .01, .06, .03),
    ("hike", "Go hiking", ("outdoors", "fitness"), .01, .10, .02),
    ("jog", "Go jogging", ("fitness",), -.02, .03, .12),
    ("work_out", "Work out", ("fitness",), .00, .02, .15),
    ("play_team_sport", "Play a team sport", ("fitness", "social"), .12, .03, .06),
    ("swim", "Go swimming", ("fitness", "outdoors"), .03, .04, .02),
    ("visit_museum", "Visit a museum", ("culture", "quiet"), -.04, .18, .04),
    ("see_live_music", "See live music", ("culture", "social", "music"), .12, .14, -.03),
    ("watch_movie", "Watch a movie", ("quiet", "social"), .01, .07, -.02),
    ("volunteer", "Volunteer locally", ("social", "community"), .07, .07, .12),
    ("shop_for_fun", "Browse the shops", ("social", "outing"), .09, .07, -.05),
    ("relax_at_home", "Have a lazy day", ("quiet", "rest"), -.12, .01, -.16),
    ("meditate", "Take a quiet moment", ("quiet", "rest"), -.17, .05, .10),
    ("make_friends", "Meet someone new", ("social",), .20, .08, -.02),
]

LEISURE_ACTIVITIES = {
    row[0]: {"id": row[0], "label": row[1], "tags": list(row[2]),
             "trait_pull": {"extraversion": row[3], "openness": row[4],
                            "conscientiousness": row[5]},
             "duration_minutes": 90 if "party" not in row[2] else 180}
    for row in _ACTIVITIES
}

# Concrete micro-scenes share existing spatial affordances. They are chosen at
# action start, so a journal describes an action that actually reached its site.
ACTIVITY_SCENES = {
    'host_party': ('Hosting game night', 'Hosting a dinner gathering', 'Organizing a garden party'),
    'attend_party': ('Joining a dance party', 'Catching up at a party', 'Meeting people at a party'),
    'dance': ('Dancing to pop music', 'Trying a new dance', 'Dancing with the crowd'),
    'karaoke': ('Singing a duet', 'Trying karaoke', 'Cheering a karaoke set'),
    'board_games': ('Playing chess', 'Playing cards', 'Playing a strategy game'),
    'video_games': ('Playing a puzzle game', 'Playing a racing game', 'Trying a co-op game'),
    'read_for_fun': ('Reading a mystery', 'Reading a comic', 'Reading a novel'),
    'write_story': ('Writing a short story', 'Drafting a poem', 'Writing a travel tale'),
    'paint': ('Sketching a portrait', 'Painting a landscape', 'Drawing from memory'),
    'play_instrument': ('Practicing a melody', 'Improvising music', 'Playing an old favorite'),
    'craft_project': ('Making a small gift', 'Trying a craft project', 'Repairing a keepsake'),
    'garden': ('Tending flowers', 'Pruning herbs', 'Planting seedlings'),
    'cook_for_fun': ('Trying a new recipe', 'Testing a sauce', 'Cooking a favorite dish'),
    'bake_treats': ('Baking biscuits', 'Baking a cake', 'Trying a pastry recipe'),
    'go_for_walk': ('Walking around the block', 'Taking a park stroll', 'Exploring a side street'),
    'hike': ('Exploring the park trail', 'Taking a long nature walk', 'Following a woodland path'),
    'jog': ('Jogging a short loop', 'Running interval laps', 'Taking an easy run'),
    'work_out': ('Practicing stretches', 'Lifting weights', 'Training endurance'),
    'play_team_sport': ('Playing a ball game', 'Joining a pickup match', 'Practicing team drills'),
    'swim': ('Swimming laps', 'Playing in the pool', 'Practicing a stroke'),
    'see_live_music': ('Listening to a live set', 'Dancing at a concert', 'Meeting music fans'),
    'watch_movie': ('Watching a comedy', 'Watching a thriller', 'Watching a documentary'),
    'volunteer': ('Helping at a community event', 'Organizing donated supplies', 'Welcoming a newcomer'),
    'shop_for_fun': ('Browsing the book stalls', 'Window-shopping', 'Looking for a gift'),
    'relax_at_home': ('Taking a quiet break', 'Daydreaming on the sofa', 'Listening to music at home'),
    'meditate': ('Breathing mindfully', 'Practicing calm focus', 'Taking a peaceful pause'),
    'make_friends': ('Meeting a newcomer', 'Joining a friendly conversation', 'Introducing myself'),
}


def scene_for(activity: str, rng) -> str:
    """Select a concrete, reproducible version of an existing leisure action."""
    if activity not in LEISURE_ACTIVITIES:
        raise ValueError(f'unknown activity: {activity}')
    choices = ACTIVITY_SCENES.get(activity, (LEISURE_ACTIVITIES[activity]['label'],))
    return choices[rng.randrange(len(choices))]

EVENTS = {
    "good_time": {"weight": 1.0, "say": "Das tut gut 😊"},
    "new_friend": {"weight": .18, "say": "Du bist cool ✨"},
    "awkward_moment": {"weight": .14, "say": "Ähm ... ups 😅"},
    "minor_mishap": {"weight": .045, "say": "Na toll 🙈"},
    "argument": {"weight": .035, "say": "Das nervt echt 😤"},
    "shouting_match": {"weight": .009, "say": "Jetzt reicht's! 😡"},
    "fight": {"weight": .0015, "say": "Lass das! 😠"},
    "date_spark": {"weight": .10, "say": "Ich mag dich 💛"},
    "kiss": {"weight": .035, "say": "Komm näher 💋"},
    "bedroom_intimacy": {"weight": .012, "say": "Nur wir zwei 💕"},
    "family_planning": {"weight": .004, "say": "Bereit für mehr? 🏡"},
}


def _traits(sim: dict) -> dict:
    return (sim.get("psychology", {}).get("big_five")
            or sim.get("personality") or {})


def _trait(sim: dict, key: str, default: float = .5) -> float:
    try:
        return max(0.0, min(1.0, float(_traits(sim).get(key, default))))
    except (TypeError, ValueError):
        return default


def _draw(rng) -> float:
    if rng is None:
        raise ValueError("An injected RNG is required")
    if hasattr(rng, "random"):
        return float(rng.random())
    if hasattr(rng, "uniform"):
        return float(rng.uniform(0, 1))
    raise TypeError("rng must provide random() or uniform()")


def leisure_actions(sim: dict, context: dict | None = None) -> list[dict]:
    """Return feasible activity action records with personality-weighted scores.

    Context supports ``available_tags``, ``interests`` and ``with_sim``; the
    returned scores are positive weights, not probabilities.
    """
    context = context or {}
    interests = set(context.get("interests") or sim.get("profile", {}).get("interests", []))
    available = context.get("available_tags")
    friend = context.get("with_sim")
    rows = []
    for key, definition in LEISURE_ACTIVITIES.items():
        if available is not None and not (set(definition["tags"]) & set(available)):
            continue
        pull = definition["trait_pull"]
        score = 1.0 + sum((_trait(sim, trait) - .5) * amount * 3
                          for trait, amount in pull.items())
        if key in interests or set(definition["tags"]) & interests:
            score *= 1.55
        if "social" in definition["tags"] and friend:
            score *= .85 + _trait(sim, "extraversion") * .5
        if key == "relax_at_home":
            score *= 1 + (1 - _trait(sim, "conscientiousness")) * .35
        rows.append({"kind": "leisure", "activity": key,
                     "label": definition["label"], "duration_minutes": definition["duration_minutes"],
                     "weight": round(max(.05, score), 4), "tags": list(definition["tags"])})
    return rows


def choose_leisure_action(sim: dict, context: dict | None, rng) -> dict | None:
    """Sample an action using its personality and interest weight."""
    choices = leisure_actions(sim, context)
    if not choices:
        return None
    total = sum(item["weight"] for item in choices)
    point = _draw(rng) * total
    for item in choices:
        point -= item["weight"]
        if point <= 0:
            return deepcopy(item)
    return deepcopy(choices[-1])


def _romance_allowed(a: dict, b: dict, context: dict) -> bool:
    """Fail closed: explicit adult, non-kin, mutually consenting context required."""
    return (context.get("both_adults") is True
            and context.get("non_kin") is True
            and context.get("mutual_consent") is True)


def resolve_social_event(a: dict, b: dict | None, activity: str,
                         context: dict, rng) -> dict:
    """Return a sampled, safe event proposal without mutating either Sim.

    Context: ``tension`` (0..1), ``closeness`` (0..1), and explicit romance
    gates ``both_adults``, ``non_kin``, ``mutual_consent``. Optional
    ``romantic``/``committed``/``trying_for_child`` control adult outcomes.
    """
    _ = b  # reserve second actor for integrations; all inputs remain untouched
    if activity not in LEISURE_ACTIVITIES and activity not in {"work_chat", "date"}:
        raise ValueError(f"unknown activity: {activity}")
    tension = max(0.0, min(1.0, float(context.get("tension", 0))))
    closeness = max(0.0, min(1.0, float(context.get("closeness", 0))))
    ext = (_trait(a, "extraversion") + (_trait(b, "extraversion") if b else .5)) / (2 if b else 1)
    agreeable = (_trait(a, "agreeableness") + (_trait(b, "agreeableness") if b else .5)) / (2 if b else 1)
    neurotic = (_trait(a, "neuroticism") + (_trait(b, "neuroticism") if b else .5)) / (2 if b else 1)
    # Escalation chance rises with tension/neuroticism and falls with agreeableness.
    argument = .008 + tension * (.025 + neurotic * .045) + (1 - agreeable) * .012
    rows = ([("argument", argument),
            ("shouting_match", argument * (.08 + neurotic * .10)),
            ("fight", argument * (.006 + (1 - agreeable) * .012))] if b else []) + [
            ("minor_mishap", .018 + (1 - _trait(a, "conscientiousness")) * .035),
            ("new_friend", .025 + ext * .06 + closeness * .04),
            ("awkward_moment", .04 + neurotic * .055),
            ("good_time", .30 + ext * .20 + agreeable * .08)]
    romance_ok = bool(b and _romance_allowed(a, b, context))
    if romance_ok and (context.get("romantic") or activity in {"ask_on_date", "go_on_date", "date"}):
        rows.extend([("date_spark", .06 + closeness * .12),
                     ("kiss", .008 + closeness * .045)])
        if context.get('private_at_home') is True:
            rows.append(("bedroom_intimacy", .001 + closeness * .018))
        if context.get('private_at_home') is True and context.get("committed") and context.get("trying_for_child"):
            rows.append(("family_planning", .0005 + closeness * .007))
    # Events are mutually exclusive. Add unassigned probability as a quiet/no-event outcome.
    total = sum(weight for _, weight in rows)
    scale = min(1.0, .9 / total) if total else 1.0
    rows = [(name, weight * scale) for name, weight in rows]
    point = _draw(rng)
    for kind, weight in rows:
        if point < weight:
            return {"kind": kind, "activity": activity,
                    "participants": [x for x in (a.get("id"), b.get("id") if b else None) if x],
                    "say": EVENTS[kind]["say"], "probability": round(weight, 6),
                    "effects": _effect_contract(kind)}
        point -= weight
    return {"kind": "quiet", "activity": activity,
            "participants": [x for x in (a.get("id"), b.get("id") if b else None) if x],
            "say": "Ganz entspannt 😌", "probability": round(max(0, 1-sum(w for _,w in rows)), 6),
            "effects": _effect_contract("quiet")}


def _effect_contract(kind: str) -> dict:
    """Suggested scalar effect ranges; caller chooses concrete state fields."""
    effects = {
        "good_time": {"fun": (2, 12), "relationship": (0, 2)},
        "new_friend": {"relationship": (2, 8)},
        "awkward_moment": {"stress": (1, 5)},
        "minor_mishap": {"stress": (1, 4), "time_lost_minutes": (5, 30)},
        "argument": {"tension": (3, 10), "relationship": (-8, -2)},
        "shouting_match": {"tension": (8, 18), "relationship": (-15, -4)},
        "fight": {"tension": (12, 25), "relationship": (-20, -8)},
        "date_spark": {"romance": (2, 8), "relationship": (2, 6)},
        "kiss": {"romance": (4, 10), "relationship": (2, 5)},
        "bedroom_intimacy": {"romance": (5, 12), "relationship": (2, 6)},
        "family_planning": {"romance": (2, 6), "relationship": (2, 5)},
        "quiet": {},
    }
    return deepcopy(effects[kind])


def activity_definitions() -> dict:
    """Return an isolated copy of the public activity catalogue."""
    return deepcopy(LEISURE_ACTIVITIES)


def event_definitions() -> dict:
    """Return event metadata without exposing mutable module state."""
    return deepcopy(EVENTS)
