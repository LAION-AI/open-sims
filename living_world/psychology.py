"""Deterministic gameplay psychology helpers.

This module deliberately has no access to ``World`` and never mutates an actor
dictionary.  Callers apply returned patches inside their coordinator transaction.
It models fictional characters, not clinical assessment or real people.
"""
from __future__ import annotations

from copy import deepcopy
from math import exp


SCHEMA_VERSION = 1
ADULT_AGE = 18
MAX_OBSERVATIONS = 12

# A category is a mechanical interaction family, rather than generated dialogue.
# Romantic categories are guarded by consent, adulthood, and non-kinship.
SOCIAL_CATEGORIES = {
    "greet": {"label": "Greet", "duration_seconds": 45, "tone": "warm", "base": .35},
    "small_talk": {"label": "Small talk", "duration_seconds": 180, "tone": "warm", "base": .42},
    "share_interest": {"label": "Share interest", "duration_seconds": 300, "tone": "warm", "base": .46},
    "offer_help": {"label": "Offer help", "duration_seconds": 240, "tone": "warm", "base": .40},
    "ask_advice": {"label": "Ask advice", "duration_seconds": 300, "tone": "warm", "base": .36},
    "tell_joke": {"label": "Tell joke", "duration_seconds": 90, "tone": "play", "base": .40},
    "compliment": {"label": "Compliment", "duration_seconds": 75, "tone": "warm", "base": .40},
    "apologize": {"label": "Apologize", "duration_seconds": 150, "tone": "repair", "base": .32},
    "check_in": {"label": "Check in", "duration_seconds": 180, "tone": "care", "base": .41},
    "confide": {"label": "Confide", "duration_seconds": 360, "tone": "care", "base": .26},
    "invite_activity": {"label": "Invite to activity", "duration_seconds": 90, "tone": "warm", "base": .37},
    "celebrate": {"label": "Celebrate", "duration_seconds": 240, "tone": "warm", "base": .43},
    "play_together": {"label": "Play together", "duration_seconds": 300, "tone": "play", "base": .42},
    "coordinate_work": {"label": "Coordinate work", "duration_seconds": 240, "tone": "task", "base": .38},
    "set_boundary": {"label": "Set boundary", "duration_seconds": 120, "tone": "boundary", "base": .28},
    "gossip": {"label": "Gossip", "duration_seconds": 180, "tone": "tension", "base": .24},
    "reconcile": {"label": "Reconcile", "duration_seconds": 300, "tone": "repair", "base": .27},
    "flirt": {"label": "Flirt", "duration_seconds": 120, "tone": "romance", "base": .24, "romantic": True},
    "ask_date": {"label": "Ask for date", "duration_seconds": 90, "tone": "romance", "base": .20, "romantic": True},
    "express_affection": {"label": "Express affection", "duration_seconds": 120, "tone": "romance", "base": .25, "romantic": True},
    "ask_help": {"label": "Ask for help", "duration_seconds": 210, "tone": "care", "base": .30},
    "undermine": {"label": "Discuss work performance", "duration_seconds": 150, "tone": "conflict", "base": .08},
    "share_news": {"label": "Share news", "duration_seconds": 150, "tone": "warm", "base": .30},
    "challenge": {"label": "Friendly challenge", "duration_seconds": 240, "tone": "play", "base": .24},
    "phone_call": {"label": "Phone call", "duration_seconds": 240, "tone": "warm", "base": .39},
    "deep_talk": {"label": "Deep conversation", "duration_seconds": 420, "tone": "care", "base": .30},
    "comfort": {"label": "Comfort", "duration_seconds": 240, "tone": "care", "base": .35},
    "ask_favor": {"label": "Ask a favor", "duration_seconds": 180, "tone": "care", "base": .26},
    "collaborate_project": {"label": "Work on a project together", "duration_seconds": 480, "tone": "task", "base": .30},
    "persuade": {"label": "Try to persuade", "duration_seconds": 240, "tone": "task", "base": .25},
    "make_plans": {"label": "Make plans", "duration_seconds": 210, "tone": "warm", "base": .35},
    "invite_to_dinner": {"label": "Invite to dinner", "duration_seconds": 150, "tone": "warm", "base": .32},
    "tell_story": {"label": "Tell a story", "duration_seconds": 240, "tone": "play", "base": .33},
    "tease": {"label": "Playful teasing", "duration_seconds": 90, "tone": "play", "base": .30},
    "debate": {"label": "Debate an idea", "duration_seconds": 300, "tone": "task", "base": .28},
    "provoke": {"label": "Provoke", "duration_seconds": 100, "tone": "conflict", "base": .13},
    "argue": {"label": "Start an argument", "duration_seconds": 240, "tone": "conflict", "base": .12},
}

_ACTION_FACTORS = {
    "chat": ("extraversion", "agreeableness", "socializing"),
    "socialize": ("extraversion", "agreeableness", "socializing"),
    "read": ("openness", "conscientiousness", "reading"),
    "work": ("conscientiousness", "openness", None),
    "craft": ("openness", "conscientiousness", "craft"),
    "garden": ("openness", "agreeableness", "gardening"),
    "walk": ("openness", "extraversion", "walking"),
    "relax": ("neuroticism", "openness", "relaxing"),
    "cooking": ("conscientiousness", "openness", "cooking"),
}
_ACTION_ALIASES = {
    "creative_hobby": "craft", "stroll": "walk", "eat_meal": "cooking",
    "prepare_meal": "cooking",
}
_HOBBY_FOR_ACTION = {"read": "reading", "chat": "socializing", "socialize": "socializing"}
_OUTCOME_EFFECTS = {
    "positive": (.045, .025, .018), "accepted": (.030, .015, .010),
    "neutral": (.004, .002, .001), "declined": (-.010, -.004, 0),
    "negative": (-.050, -.035, -.020), "boundary": (-.018, -.008, -.004),
}
_OUTCOME_ALIASES = {"success": "positive", "failure": "negative"}


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def _unit(value: float) -> float:
    return _clamp(value)


def _rng_value(rng, low=.0, high=1.0) -> float:
    """Accept Random-compatible injected RNGs only; never use global randomness."""
    if rng is None:
        raise ValueError("A seeded, injected RNG is required")
    if hasattr(rng, "uniform"):
        return float(rng.uniform(low, high))
    if hasattr(rng, "random"):
        return low + (high - low) * float(rng.random())
    raise TypeError("rng must provide uniform() or random()")


def _trait_labels(big_five: dict[str, float]) -> list[str]:
    labels = []
    if big_five["openness"] >= .62: labels.append("Curious")
    if big_five["conscientiousness"] >= .62: labels.append("Organized")
    if big_five["extraversion"] >= .62: labels.append("Outgoing")
    if big_five["agreeableness"] >= .62: labels.append("Considerate")
    if big_five["neuroticism"] >= .62: labels.append("Cautious")
    return labels or ["Practical"]


def social_category_definitions() -> dict:
    """Return a copy of the public category contracts for UI and planners."""
    return deepcopy(SOCIAL_CATEGORIES)


def _hobby_names(actor: dict) -> list[str]:
    interests = list(actor.get("profile", {}).get("interests", []))
    preferences = actor.get("preferences", {})
    ranked = sorted(preferences, key=lambda key: (-float(preferences[key]), key))
    return (interests + [name for name in ranked if name not in interests])[:3] or ["relaxing"]


def _action_kind(kind: str) -> str:
    """Normalize engine action aliases without changing the externally logged kind."""
    return _ACTION_ALIASES.get(kind, kind)


def _hobby_kind(kind: str) -> str:
    kind = _action_kind(kind)
    return _HOBBY_FOR_ACTION.get(kind, kind)


def _career_title(actor: dict) -> str:
    job = actor.get('profile', {}).get('job', 'worker')
    article = 'an' if job[:1].lower() in 'aeiou' else 'a'
    return f'Grow as {article} {job}'


def initialize_psychology(actor: dict, rng, now: int = 0) -> dict:
    """Return a new psychology component for a fictional actor.

    ``rng`` is deliberately supplied by the world seed/actor identity.  The
    component is presentation-neutral and does not overwrite legacy fields.
    """
    big_five = {key: round(_rng_value(rng, .25, .78), 3) for key in
                ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")}
    hobbies = _hobby_names(actor)
    strongest = max(big_five, key=big_five.get)
    ambition_by_trait = {
        "openness": ("create", "Develop a creative practice"),
        "conscientiousness": ("mastery", "Build reliable mastery"),
        "extraversion": ("community", "Strengthen community ties"),
        "agreeableness": ("care", "Support people I value"),
        "neuroticism": ("stability", "Create a comfortable routine"),
    }
    ambition_kind, ambition_title = ambition_by_trait[strongest]
    fears = [
        {"id": "fear_rejection", "kind": "social_rejection", "intensity": _clamp(.12 + big_five["neuroticism"] * .25), "last_updated": now},
        {"id": "fear_stagnation", "kind": "stagnation", "intensity": _clamp(.10 + big_five["openness"] * .20), "last_updated": now},
        {"id": "fear_conflict", "kind": "conflict", "intensity": _clamp(.08 + big_five["agreeableness"] * .20), "last_updated": now},
        {"id": "fear_dogs", "kind": "dogs", "intensity": _clamp(.04 + _rng_value(rng, 0, .45)), "last_updated": now},
        {"id": "fear_job_loss", "kind": "job_loss", "intensity": _clamp(.04 + _rng_value(rng, 0, .45)), "last_updated": now},
    ]
    if actor.get('age',30)<18:
        fears=[fear for fear in fears if fear['kind']!='job_loss']
        development={'kind':'learning','title':'Learn and make friends'}
    elif actor.get('age',30)>=66 and actor.get('profile',{}).get('job')=='Retired':
        fears=[fear for fear in fears if fear['kind']!='job_loss']
        development={'kind':'community','title':'Share experience with neighbors'}
    else:
        development={'kind':'career','title':_career_title(actor)}
    social_style = {"drive": _clamp(_rng_value(rng, .12, .93)),
                    "competitiveness": _clamp(_rng_value(rng, .1, .9)),
                    "ruthlessness": _clamp(_rng_value(rng, .03, .55)),
                    "compassion": _clamp(_rng_value(rng, .3, .95)),
                    "presentation": _clamp(_rng_value(rng, .2, .9)),
                    "preferences": {key: _clamp(_rng_value(rng, .1, .9)) for key in
                                    ("kindness", "status", "presentation", "shared_interests")}}
    return {"schema_version": SCHEMA_VERSION, "big_five": big_five, "social_style": social_style,
            "traits": _trait_labels(big_five),
            "ambitions": [{"id": "ambition_primary", "kind": ambition_kind, "title": ambition_title,
                           "progress": 0.0, "completed": False, "updated_at": now},
                          {"id": "ambition_career", "kind": development['kind'],
                           "title": development['title'],
                           "progress": 0.0, "completed": False, "updated_at": now},
                          {"id": "ambition_hobby", "kind": "hobby",
                           "activity": hobbies[0], "title": "Practice " + hobbies[0],
                           "progress": 0.0, "completed": False, "updated_at": now}],
            "hobbies": [{"id": "hobby_" + name, "kind": name, "enjoyment": _clamp(actor.get("preferences", {}).get(name, .5)),
                         "practice_seconds": 0, "last_practiced": None} for name in hobbies],
            "fears": fears,
            "theory_of_mind": {"known_people": {}, "max_observations_per_person": MAX_OBSERVATIONS,
                                 "policy": "direct_observations_only"},
            "action_model": {"policy": "seeded_if_then_weighted", "last_choice": None}}


def migrate_existing_actor(actor: dict, rng, now: int = 0) -> dict:
    """Return only missing conservative additions for an existing save."""
    patch = {}
    if not isinstance(actor.get("psychology"), dict):
        patch["psychology"] = initialize_psychology(actor, rng, now)
    else:
        psychology = deepcopy(actor["psychology"])
        psychology.setdefault("schema_version", SCHEMA_VERSION)
        style=psychology.setdefault('social_style',{})
        for key,value in initialize_psychology(actor, rng, now)['social_style'].items():
            style.setdefault(key,value)
        psychology.setdefault("theory_of_mind", {"known_people": {}, "max_observations_per_person": MAX_OBSERVATIONS, "policy": "direct_observations_only"})
        patch["psychology"] = psychology
    return patch


def add_missing_ambitions(actor: dict, now: int) -> dict:
    """Add future goals to a v3 save without inventing earlier progress."""
    psychology = deepcopy(actor.get('psychology', {}))
    ambitions = psychology.setdefault('ambitions', [])
    known = {item.get('id') for item in ambitions}
    if 'ambition_career' not in known:
        ambitions.append({'id': 'ambition_career', 'kind': 'career',
                          'title': _career_title(actor),
                          'progress': 0.0, 'completed': False, 'updated_at': now})
    if 'ambition_hobby' not in known:
        hobby = next(iter(psychology.get('hobbies', [])), {}).get('kind', 'relaxing')
        ambitions.append({'id': 'ambition_hobby', 'kind': 'hobby', 'activity': hobby,
                          'title': 'Practice ' + hobby, 'progress': 0.0,
                          'completed': False, 'updated_at': now})
    return {'psychology': psychology}


def _layers(relation: dict | None, household_id: str | None, other_household_id: str | None,
            family_status: str = "none", partnered: bool = False) -> dict:
    existing = deepcopy((relation or {}).get("layers", {}))
    for key in ("family", "romance", "friendship", "coworker", "household"):
        existing.setdefault(key, {"score": 0.0, "status": "none"})
    if household_id and household_id == other_household_id:
        existing["household"] = {"score": max(.5, _unit(existing["household"].get("score", 0))), "status": "co_resident"}
    if family_status != "none":
        existing["family"] = {"score": max(.7, _unit(existing["family"].get("score", 0))), "status": family_status}
    if partnered:
        romance = existing["romance"]
        romance["score"] = max(.65, _unit(romance.get("score", 0)))
        if romance.get("status") in (None, "none"):
            romance["status"] = "established"
    return existing


def _relation(actor: dict, other: dict, family_status: str = "none", partnered: bool = False) -> dict:
    relation = deepcopy(actor.get("relations", {}).get(other.get("id"), {}))
    relation.setdefault("closeness", .0)
    relation.setdefault("trust", .35)
    relation.setdefault("respect", .35)
    relation.setdefault("attraction", .0)
    relation.setdefault("tension", .0)
    relation.setdefault("last_interaction", None)
    relation.setdefault("kind", "Acquaintance")
    relation["layers"] = _layers(relation, actor.get("household_id"), other.get("household_id"), family_status, partnered)
    return relation


def _family(actor: dict) -> dict:
    """Structural family data only; no life history is inferred from it."""
    return actor.get("family", {}) if isinstance(actor.get("family"), dict) else {}


def _workplace_id(actor: dict):
    """Support the current scalar integration field and its earlier object shape."""
    direct = actor.get("workplace_id")
    if direct:
        return direct
    workplace = actor.get("workplace")
    return workplace.get("workplace_id") if isinstance(workplace, dict) else None


def _kinship(actor: dict, other: dict, by_id: dict[str, dict]) -> str:
    """Derive a label from explicit parent ids only--never age or co-residence."""
    actor_parents = set(_family(actor).get("parent_ids", []))
    other_parents = set(_family(other).get("parent_ids", []))
    if other.get("id") in actor_parents:
        return "parent"
    if actor.get("id") in other_parents:
        return "child"
    if actor_parents and actor_parents & other_parents:
        return "sibling"
    actor_grandparents = {parent for parent_id in actor_parents for parent in _family(by_id.get(parent_id, {})).get("parent_ids", [])}
    other_grandparents = {parent for parent_id in other_parents for parent in _family(by_id.get(parent_id, {})).get("parent_ids", [])}
    if other.get("id") in actor_grandparents:
        return "grandparent"
    if actor.get("id") in other_grandparents:
        return "grandchild"
    if actor_parents & other_grandparents:
        return "niece_nephew"
    if other_parents & actor_grandparents:
        return "aunt_uncle"
    if actor_grandparents and actor_grandparents & other_grandparents:
        return "cousin"
    return "none"


def initial_family_profiles(actors, include_minors=False) -> dict:
    """Return an authored *new-world-only* adult family fixture.

    Apply this before :func:`initialize_social_graph`.  It supplies explicit
    ages, parent IDs, partners and statuses for a small cross-household family
    network; all entries are adults and it makes no claim about child physiology
    or unseen shared events. Existing saves must use ``migrate_existing_actor``
    instead and retain their own age and relationship records.
    """
    people = list(actors.values()) if isinstance(actors, dict) else list(actors)
    if len(people) < 11:
        raise ValueError("initial_family_profiles requires at least 11 actors for its authored multigenerational fixture")
    ids = [person["id"] for person in people]
    # The first eleven residents form: grandparents -> adult children -> adult
    # grandchildren, plus two cousins. Remaining residents are explicitly single
    # adults with no invented kin links.
    authored = {
        0: (73, [], 1, "married"), 1: (71, [], 0, "married"),
        2: (49, [0, 1], 3, "married"), 3: (48, [], 2, "married"),
        4: (27, [2, 3], 5, "partnered"), 5: (29, [], 4, "partnered"),
        6: (24, [2, 3], None, "single"),
        7: (47, [0, 1], 8, "partnered"), 8: (48, [], 7, "partnered"),
        9: (25, [7, 8], None, "single"), 10: (31, [], None, "single"),
    }
    patch = {}
    household_members = {}
    for person in people:
        household_members.setdefault(person.get('household_id'), []).append(person['id'])
    household_order = {identifier:index for index,identifier in enumerate(household_members)}
    for index, person in enumerate(people):
        age, parent_indexes, partner_index, status = authored.get(index, (22 + (index * 7) % 39, [], None, "single"))
        if include_minors and index >= 11:
            members=household_members[person.get('household_id')]
            house_index=household_order[person.get('household_id')]
            if len(members)==3 and person['id']==members[-1]:
                age=5 if house_index%2==0 else 9
            elif len(members)==2 and person['id']==members[-1] and house_index in {9,14,19}:
                age=15
            if age<18:
                parent_indexes=[ids.index(members[0])]
                if len(members)==3 and members[1]!=person['id']:
                    parent_indexes.append(ids.index(members[1]))
                status='child' if age<13 else 'teen'
        patch[person["id"]] = {"age": age, "family": {"parent_ids": [ids[p] for p in parent_indexes],
                                                           "partner_id": ids[partner_index] if partner_index is not None else None,
                                                           "relationship_status": status}}
    structural = {identifier: {"id": identifier, "family": row["family"]} for identifier, row in patch.items()}
    for identifier, row in patch.items():
        row["family"]["known_kin_ids"] = sorted(other_id for other_id, other in structural.items()
                                                   if other_id != identifier and _kinship(structural[identifier], other, structural) != "none")
    return patch


def initialize_social_graph(actors, now: int = 0) -> dict:
    """Return `actor_id -> {'relations': ...}` patches; retain all legacy relation data."""
    records = actors.values() if isinstance(actors, dict) else actors
    # Inputs are read-only here; copies are made only for returned relation patches.
    people = list(records)
    by_id = {person["id"]: person for person in people}
    patches = {}
    for actor in people:
        relations = deepcopy(actor.get("relations", {}))
        for other in people:
            if other.get("id") == actor.get("id"):
                continue
            prior = relations.get(other["id"])
            family_status = _kinship(actor, other, by_id)
            partnered = _family(actor).get("partner_id") == other["id"] and _family(other).get("partner_id") == actor["id"]
            same_home = bool(actor.get("household_id")) and actor.get("household_id") == other.get("household_id")
            workplace_id, other_workplace_id = _workplace_id(actor), _workplace_id(other)
            shared_workplace = bool(workplace_id) and workplace_id == other_workplace_id
            if prior is None and not (same_home or family_status != "none" or partnered or shared_workplace):
                continue
            relation = _relation(actor, other, family_status, partnered)
            if prior is None and family_status != 'none':
                # New-world authored kin should not all appear emotionally
                # indifferent merely because no interaction beat has fired yet.
                closeness = .62 if family_status in {'parent', 'child'} else .54 if family_status in {'sibling', 'grandparent', 'grandchild'} else .43
                relation['closeness'] = closeness
                relation['trust'] = .66 if family_status in {'parent', 'child'} else .57
                relation['respect'] = .58
            if shared_workplace and relation["layers"]["coworker"].get("status") in (None, "none"):
                relation["layers"]["coworker"] = {"score": .5, "status": "shared_workplace"}
                if prior is None:
                    relation['respect'] = max(relation['respect'], .52)
            if prior is None:
                relation["introduced_at"] = now
            relations[other["id"]] = relation
        patches[actor["id"]] = {"relations": relations}
    return patches


def authored_friendships(actors, now: int = 0) -> dict:
    """Seed a few reciprocal cross-home friendships for *new* worlds only.

    Candidates share an interest when possible and live within a few homes;
    no relationship is inferred for an old save from mere proximity.
    """
    people = list(actors.values()) if isinstance(actors, dict) else list(actors)
    by_id = {person['id']: person for person in people}
    patches = {}
    for index in range(11, len(people), 5):
        actor = people[index]
        options = []
        for distance in range(2, 9):
            for neighbor_index in (index + distance, index - distance):
                if not 11 <= neighbor_index < len(people):
                    continue
                other = people[neighbor_index]
                if (other['household_id'] == actor['household_id']
                        or _kinship(actor, other, by_id) != 'none'):
                    continue
                shared = set(actor.get('profile', {}).get('interests', [])) & set(other.get('profile', {}).get('interests', []))
                options.append((-len(shared), distance, other['id']))
        if not options:
            continue
        _, _, other_id = min(options)
        other = by_id[other_id]
        for viewer, target, offset in ((actor, other, .0), (other, actor, .045)):
            relation = _relation(viewer, target)
            relation['kind'] = 'Friend'
            relation['closeness'] = max(float(relation['closeness']), .57 + offset)
            relation['trust'] = max(float(relation['trust']), .53 + offset)
            relation['respect'] = max(float(relation['respect']), .54)
            relation['layers']['friendship'] = {'score': .62, 'status': 'established'}
            relation['introduced_at'] = now
            relation['origin'] = 'authored_new_world_friendship'
            patches.setdefault(viewer['id'], {'relations': {}})['relations'][target['id']] = relation
    return patches


def _big_five(actor: dict) -> dict:
    return actor.get("psychology", {}).get("big_five", {})


def action_bias(actor: dict, kind: str, now: int | None = None) -> float:
    """Return a bounded [-1, 1] stable tendency; it is not a forced action."""
    action_kind = _action_kind(kind)
    trait_a, trait_b, preference = _ACTION_FACTORS.get(action_kind, ("openness", "conscientiousness", None))
    five = _big_five(actor)
    score = (float(five.get(trait_a, .5)) - .5) * .75 + (float(five.get(trait_b, .5)) - .5) * .25
    if preference:
        score += (float(actor.get("preferences", {}).get(preference, .5)) - .5) * .65
    if action_kind in ("chat", "socialize"):
        score -= (float(five.get("neuroticism", .5)) - .5) * .15
    drive=float(actor.get('psychology',{}).get('social_style',{}).get('drive',.5))
    if action_kind in {'work','read','craft'}:
        score+=(drive-.5)*.26
    elif action_kind in {'relax','walk'}:
        score-=(drive-.5)*.12
    psychology = actor.get("psychology", {})
    hobby_kind = _hobby_kind(action_kind)
    for hobby in psychology.get("hobbies", []):
        if hobby.get("kind") == hobby_kind:
            score += (float(hobby.get("enjoyment", .5)) - .5) * .30
    ambition_actions = {"community": {"chat", "socialize"}, "mastery": {"read", "work", "craft"},
                        "create": {"craft"}, "care": {"garden", "socialize"}, "stability": {"relax"}}
    for ambition in psychology.get("ambitions", []):
        if not ambition.get("completed") and action_kind in ambition_actions.get(ambition.get("kind"), set()):
            score += .12 * (1 - float(ambition.get("progress", 0)))
    for fear in psychology.get("fears", []):
        if now is not None and fear.get("expires_at") is not None and fear["expires_at"] <= now:
            continue
        intensity = float(fear.get("intensity", 0))
        if fear.get("kind") == "social_rejection" and action_kind in ("chat", "socialize"):
            score -= intensity * .18
        elif fear.get("kind") == "job_loss" and action_kind == "work":
            score += intensity * .25
        elif fear.get("kind") == "dogs" and action_kind == "walk":
            score -= intensity * .20
    return round(max(-1.0, min(1.0, score)), 4)


def conditional_action_probability(actor: dict, kind: str, now: int | None = None) -> float:
    """Stable if-then probability before availability, cost, and consent checks."""
    return round(1 / (1 + exp(-2.7 * action_bias(actor, kind, now))), 4)


def choose_if_then_action(actor: dict, candidates: list[dict], rng) -> dict | None:
    """Choose from feasible candidate actions with injected seeded randomness."""
    feasible = [candidate for candidate in candidates if candidate.get("allowed", True)]
    if not feasible:
        return None
    weights = [max(.0001, conditional_action_probability(actor, item["kind"])) * max(.0001, item.get("score", 1)) for item in feasible]
    threshold = _rng_value(rng) * sum(weights)
    cumulative = 0.0
    for item, weight in zip(feasible, weights):
        cumulative += weight
        if threshold <= cumulative:
            return deepcopy(item)
    return deepcopy(feasible[-1])


def _romance_allowed(actor: dict, other: dict, relation: dict) -> tuple[bool, str]:
    if int(actor.get("age", ADULT_AGE)) < ADULT_AGE or int(other.get("age", ADULT_AGE)) < ADULT_AGE:
        return False, "romance requires adult participants in this world"
    family = relation["layers"]["family"]
    if family.get("status") not in (None, "none", "unknown") or float(family.get("score", 0)) > 0:
        return False, "romance is blocked for known kin"
    if other.get("id") in _family(actor).get("known_kin_ids", []) or actor.get("id") in _family(other).get("known_kin_ids", []):
        return False, "romance is blocked for explicit kin"
    own_family, other_family = _family(actor), _family(other)
    own_preferences = actor.get("relationship_preferences", {})
    other_preferences = other.get("relationship_preferences", {})
    def rare_boundary_risk(person, counterpart):
        style = person.get("psychology", {}).get("social_style", {})
        edge = person.get("relations", {}).get(counterpart.get("id"), {})
        return (float(person.get("needs", {}).get("fun", 0)) > .75
                and float(style.get("ruthlessness", 0)) > .35
                and float(edge.get("attraction", 0)) > .35)
    if (own_family.get("partner_id") not in (None, other.get("id"))
            and own_preferences.get("nonmonogamous") is not True and not rare_boundary_risk(actor, other)):
        return False, "actor is committed to another partner"
    if (other_family.get("partner_id") not in (None, actor.get("id"))
            and other_preferences.get("nonmonogamous") is not True and not rare_boundary_risk(other, actor)):
        return False, "recipient is committed to another partner"
    if other_preferences.get("romance_opt_in") is False:
        return False, "recipient has not opted in to romance"
    return True, "romantic consent must be checked at execution"


def _social_context(actor: dict, other: dict, relation: dict, category: str) -> tuple[bool, str]:
    """Check relationship context, never spatial availability or recipient consent."""
    if category == "coordinate_work":
        coworker = relation["layers"]["coworker"]
        shared_workplace = bool(_workplace_id(actor)) and _workplace_id(actor) == _workplace_id(other)
        if coworker.get("status") in (None, "none") and not shared_workplace:
            return False, "coordinate work requires a shared workplace or coworker link"
    if category == "undermine":
        if int(actor.get('age', ADULT_AGE)) < ADULT_AGE or int(other.get('age', ADULT_AGE)) < ADULT_AGE:
            return False, "workplace rivalry requires adult coworkers"
        if not _workplace_id(actor) or _workplace_id(actor) != _workplace_id(other):
            return False, "undermining requires a shared workplace"
    if category in ("apologize", "reconcile") and float(relation.get("tension", 0)) < .035:
        return False, f"{category} requires an existing tension"
    if category == 'confide' and float(relation.get('trust', 0)) < .30:
        return False, 'confiding requires a minimum of trust'
    if category == 'deep_talk' and float(relation.get('trust', 0)) < .18:
        return False, 'a deep conversation requires some trust'
    if category == 'collaborate_project' and (float(relation.get('trust', 0)) < .10
            and relation['layers']['coworker'].get('status') in (None, 'none')):
        return False, 'a joint project requires rapport or a coworker link'
    if category == 'phone_call' and other.get('id') not in actor.get('relations', {}) \
            and other.get('household_id') != actor.get('household_id'):
        return False, 'a phone call requires a known contact'
    if category == 'express_affection' and float(relation['layers']['romance'].get('score', 0)) < .08:
        return False, 'affection requires an existing romantic connection'
    if category == 'ask_date' and (float(relation.get('attraction', 0)) < .04
                                    and float(relation.get('closeness', 0)) < .15):
        return False, 'a date invitation requires some rapport'
    return True, "available if both people are present and free"


def shared_topics(actor: dict, other: dict) -> list[str]:
    """Use only explicit interests, never inferred private thoughts."""
    own = set(actor.get('profile', {}).get('interests', []))
    theirs = set(other.get('profile', {}).get('interests', []))
    return sorted(own & theirs)


def partner_priority(actor: dict, other: dict, distance: int, now: int) -> float:
    """Prefer meaningful or novel encounters, with a short reunion cooldown."""
    relation = actor.get('relations', {}).get(other.get('id'))
    closeness = float((relation or {}).get('closeness', 0))
    last = (relation or {}).get('last_interaction')
    recently_met = last is not None and now - last < 2 * 3600
    household = actor.get('household_id') == other.get('household_id')
    score = .23 * closeness + .06 * bool(shared_topics(actor, other))
    score += .035 if relation is None else 0
    score += .045 if household else 0
    score -= .18 if recently_met else 0
    score -= min(.12, max(0, distance) * .025)
    style = actor.get("psychology", {}).get("social_style", {})
    score += float(style.get("compassion", .5)) * max(0, max(other.get("needs", {}).values(), default=0) - .65) * .15
    score += float(style.get("competitiveness", .5)) * float(other.get("social_status", .5)) * .04
    return round(score, 4)


def _tom_social_modifier(actor: dict, subject_id: str, category: str, now: int) -> float:
    """First-order adjustment from the actor's own recent, explicit observations."""
    known = actor.get("psychology", {}).get("theory_of_mind", {}).get("known_people", {}).get(subject_id, {})
    inferences = known.get("inferences", {})
    modifier = 0.0
    availability = inferences.get("availability", {})
    if availability.get("updated_at", -10**12) >= now - 6 * 3600 and category in ("confide", "flirt", "ask_date", "express_affection"):
        modifier -= .18
    rapport = inferences.get("rapport", {})
    if rapport.get("updated_at", -10**12) >= now - 12 * 3600 and category not in ("gossip", "set_boundary"):
        modifier += .055
    return modifier


def social_candidates(actor: dict, other: dict, now: int) -> list[dict]:
    """Score all social categories from actor-local data; never presume acceptance."""
    relation = _relation(actor, other)
    five = _big_five(actor)
    other_five = _big_five(other)
    social_need = float(actor.get("needs", {}).get("social", .5))
    connection = (float(relation["closeness"]) + float(relation["trust"])) / 2
    topics = shared_topics(actor, other)
    style = actor.get("psychology", {}).get("social_style", {})
    other_style = other.get("psychology", {}).get("social_style", {})
    prefs = style.get("preferences", {})
    appeal = (float(prefs.get("kindness", .5)) * float(other_style.get("compassion", .5))
              + float(prefs.get("status", .5)) * float(other.get("social_status", .5))
              + float(prefs.get("presentation", .5)) * float(other_style.get("presentation", .5))
              + float(prefs.get("shared_interests", .5)) * bool(topics)) / max(.001, sum(float(v) for v in prefs.values()) or 2)
    results = []
    for category, definition in SOCIAL_CATEGORIES.items():
        allowed, reason = _social_context(actor, other, relation, category)
        if definition.get("romantic"):
            romantic_allowed, romantic_reason = _romance_allowed(actor, other, relation)
            if not romantic_allowed:
                allowed, reason = False, romantic_reason
        tone = definition["tone"]
        affinity = (five.get("extraversion", .5) + five.get("agreeableness", .5)) / 2
        willingness = definition["base"] + (other_five.get("agreeableness", .5) - .5) * .25 + connection * .25
        if tone == "conflict":
            willingness -= other_five.get("agreeableness", .5) * .20
        if tone == "romance":
            willingness += relation["layers"]["romance"].get("score", 0) * .20
            willingness += (appeal - .5) * .25
        if tone == "care":
            willingness += connection * .12
        score = definition["base"] + affinity * .28 + social_need * .24 + connection * .30
        score += _tom_social_modifier(actor, other.get("id"), category, now)
        if category in {'share_interest', 'invite_activity', 'play_together'}:
            score += .13 if topics else -.11
            willingness += .08 if topics else -.04
        if category == 'coordinate_work' and _workplace_id(actor) == _workplace_id(other):
            score += .09
            score += (float(style.get('drive',.5))-.5)*.18
        if category == 'check_in' and relation['layers']['family'].get('status') not in (None, 'none'):
            score += .08
        if tone == "conflict": score -= five.get("agreeableness", .5) * .22
        if tone == "romance": score += relation["layers"]["romance"].get("score", 0) * .26
        if tone == "romance": score += (appeal - .5) * .30
        if tone == "romance" and actor.get("family", {}).get("partner_id") not in (None, other.get("id")):
            score -= .55
            willingness -= .25
        if category == "offer_help":
            score += float(style.get("compassion", .5)) * max(0, max(other.get("needs", {}).values(), default=0) - .55) * .3
        if category == "ask_help":
            score += max(0, max(actor.get("needs", {}).values(), default=0) - .55) * .25
            willingness += float(other_style.get("compassion", .5)) * .20
        if category in {"challenge", "undermine", "debate", "persuade", "argue", "provoke"}:
            score += (float(style.get("competitiveness", .5)) - .5) * .30
        if category in {'provoke', 'argue'}:
            score += float(relation.get('tension', 0)) * .28 + (float(style.get('ruthlessness', .5))-.5)*.20 - .26
            willingness -= .18
        if category == 'comfort':
            score += float(style.get('compassion', .5)) * max(0, max(other.get('needs', {}).values(), default=0)-.4) * .25
        if category == "undermine":
            score += (float(style.get("ruthlessness", .5)) - .5) * .25 - .30
            willingness -= .35
        if not allowed: score = -1.0
        results.append({"category": category, "score": round(max(-1., min(1., score)), 4),
                        "probability": round(max(0., min(1., score if allowed else 0.)), 4),
                        "willingness": round(max(0., min(1., willingness)), 4),
                        "duration_seconds": definition["duration_seconds"], "allowed": allowed, "reason": reason,
                        "requires_consent": bool(definition.get("romantic")),
                        "topic": topics[0] if topics and category in {'share_interest', 'invite_activity', 'play_together'} else None})
    return sorted(results, key=lambda row: (-row["score"], row["category"]))


def _category_delta(category: str, outcome: str) -> tuple[float, float, float]:
    closeness, trust, layer = _OUTCOME_EFFECTS.get(outcome, _OUTCOME_EFFECTS["neutral"])
    tone = SOCIAL_CATEGORIES[category]["tone"]
    if tone == "conflict": closeness, trust, layer = -abs(closeness or .01), -abs(trust or .01), -abs(layer)
    if tone == "repair" and outcome in ("positive", "accepted"): trust += .015
    return closeness, trust, layer


def apply_social(actor: dict, other: dict, category: str, outcome: str, now: int, evidence_id: str) -> dict:
    """Return bilateral relation patches after a resolved, consent-checked event.

    The coordinator owns authorization, presence, and the draw.  Passing a
    romantic category that fails a structural safety check raises ValueError.
    """
    outcome = _OUTCOME_ALIASES.get(outcome, outcome)
    if category not in SOCIAL_CATEGORIES: raise ValueError("unknown social category")
    if outcome not in _OUTCOME_EFFECTS: raise ValueError("unknown social outcome")
    forward, reverse = _relation(actor, other), _relation(other, actor)
    context_allowed, context_reason = _social_context(actor, other, forward, category)
    if not context_allowed:
        raise ValueError(context_reason)
    if SOCIAL_CATEGORIES[category].get("romantic"):
        allowed, reason = _romance_allowed(actor, other, forward)
        if not allowed: raise ValueError(reason)
    dc, dt, dl = _category_delta(category, outcome)
    layer_name = "romance" if SOCIAL_CATEGORIES[category].get("romantic") else "friendship"
    for relation in (forward, reverse):
        relation["closeness"] = _unit(float(relation["closeness"]) + dc)
        relation["trust"] = _unit(float(relation["trust"]) + dt)
        relation["last_interaction"] = now
        relation["last_evidence_id"] = evidence_id
        layer = relation["layers"][layer_name]
        layer["score"] = _unit(float(layer.get("score", 0)) + dl)
        if layer["score"] > 0 and layer.get("status") not in {"established", "married", "partnered"}:
            layer["status"] = "developing"
        tone = SOCIAL_CATEGORIES[category]["tone"]
        if tone == "romance":
            relation["attraction"] = _unit(float(relation.get("attraction", 0)) + (dc if outcome in ("positive", "accepted") else dc / 2))
        if tone == "conflict":
            relation["tension"] = _unit(float(relation.get("tension", 0)) + (.09 if outcome in ("positive", "accepted") else .035))
            relation["respect"] = _unit(float(relation.get("respect", .35)) - .04)
        elif tone == "tension":
            relation["tension"] = _unit(float(relation.get("tension", 0)) + (.045 if outcome in ("positive", "accepted") else .015))
            relation["respect"] = _unit(float(relation.get("respect", .35)) - (.025 if outcome in ("positive", "accepted") else 0))
        elif tone == "boundary":
            relation["tension"] = _unit(float(relation.get("tension", 0)) + (.015 if outcome == "negative" else -.020))
            relation["respect"] = _unit(float(relation.get("respect", .35)) + (.025 if outcome in ("positive", "accepted", "boundary") else -.02))
        elif tone in ("care", "task", "repair"):
            relation["respect"] = _unit(float(relation.get("respect", .35)) + (.025 if outcome in ("positive", "accepted") else -.01 if outcome == "negative" else 0))
            if tone == "repair" and outcome in ("positive", "accepted"):
                relation["tension"] = _unit(float(relation.get("tension", 0)) - .04)
    return {actor["id"]: {"relations": {other["id"]: forward}}, other["id"]: {"relations": {actor["id"]: reverse}}}


def observe(actor: dict, subject_id: str, observation: str, now: int, evidence_id: str, modality: str = "direct") -> dict:
    """Store an observed fact and low-confidence, explicitly sourced inference only."""
    patch = deepcopy(actor.get("psychology", {}))
    tom = patch.setdefault("theory_of_mind", {"known_people": {}, "max_observations_per_person": MAX_OBSERVATIONS, "policy": "direct_observations_only"})
    known = tom.setdefault("known_people", {}).setdefault(subject_id, {"observations": [], "inferences": {}})
    entry = {"at": now, "observation": str(observation)[:240], "evidence_id": evidence_id, "modality": modality}
    known["observations"] = (known.get("observations", []) + [entry])[-int(tom.get("max_observations_per_person", MAX_OBSERVATIONS)):]
    lower = str(observation).lower()
    if any(word in lower for word in ("declined", "left", "busy", "boundary")):
        known["inferences"]["availability"] = {"value": "may prefer space", "confidence": "low", "evidence_ids": [evidence_id], "updated_at": now}
    elif any(word in lower for word in ("accepted", "agreed", "helped", "smiled", "celebrated")):
        known["inferences"]["rapport"] = {"value": "interaction was receptive", "confidence": "low", "evidence_ids": [evidence_id], "updated_at": now}
    return {"psychology": patch}


def update_fears(actor: dict, event: str, now: int, evidence_id: str) -> dict:
    """Update game concerns from an event label; it is not mental-health diagnosis."""
    patch = deepcopy(actor.get("psychology", {}))
    fears = patch.setdefault("fears", [])
    mapping = {"dog_encounter": "dogs", "work_failed_deadline": "job_loss", "work_warning": "job_loss",
               "rejected": "social_rejection", "conflict": "conflict", "failed": "stagnation", "unsafe": "unpreparedness"}
    kind = next((value for key, value in mapping.items() if key in event.lower()), None)
    if not kind: return {"psychology": patch}
    fear = next((row for row in fears if row.get("kind") == kind), None)
    if fear is None:
        fear = {"id": "fear_" + kind, "kind": kind, "intensity": .10, "last_updated": now}; fears.append(fear)
    fear["intensity"] = _unit(float(fear.get("intensity", 0)) + .08)
    fear["last_updated"] = now; fear["evidence_id"] = evidence_id; fear["expires_at"] = now + 4 * 3600
    return {"psychology": patch}


def complete_activity(actor: dict, activity: str, now: int, evidence_id: str, duration_seconds: int = 0) -> dict:
    """Advance a matching hobby and compatible ambition; returns a psychology patch."""
    patch = deepcopy(actor.get("psychology", {}))
    activity = _hobby_kind(activity)
    duration = max(0, int(duration_seconds))
    for hobby in patch.get("hobbies", []):
        if hobby.get("kind") == activity:
            hobby["practice_seconds"] = int(hobby.get("practice_seconds", 0)) + duration
            hobby["last_practiced"] = now; hobby["last_evidence_id"] = evidence_id
    kind_map = {"reading": "mastery", "craft": "create", "gardening": "care", "socializing": "community", "relaxing": "stability", "cooking": "mastery", "work": "career"}
    for ambition in patch.get("ambitions", []):
        if ambition.get("kind") == kind_map.get(activity):
            ambition["progress"] = _unit(float(ambition.get("progress", 0)) + max(.02, duration / 36000))
            ambition["completed"] = ambition["progress"] >= 1.0; ambition["updated_at"] = now; ambition["evidence_id"] = evidence_id
        elif ambition.get('kind') == 'hobby' and ambition.get('activity') == activity:
            ambition['progress'] = _unit(float(ambition.get('progress', 0)) + duration / 72000)
            ambition['completed'] = ambition['progress'] >= 1.0
            ambition['updated_at'] = now; ambition['evidence_id'] = evidence_id
    return {"psychology": patch}
