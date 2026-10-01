"""Evidence-bound, multi-state affect for fictional life-simulation actors.

The EmoNet-Face taxonomy is a registry of labels, not a face reader, diagnosis,
or source of knowledge about another actor.  Every active state below comes from
the caller's supplied, inspectable event or the actor's modeled needs.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path


_DATA_PATH = Path(__file__).with_name("data") / "emotion_taxonomy.json"
with _DATA_PATH.open(encoding="utf-8") as _taxonomy_file:
    TAXONOMY = json.load(_taxonomy_file)
EMOTIONS = {row["id"]: row for row in TAXONOMY["emotions"]}
SCHEMA_VERSION = 2
DEFAULT_EXPIRY_SECONDS = 900
MAX_COMPONENTS = 6

# These registered labels have no game trigger in this implementation. In
# particular they are never inferred from age, appearance, clothing, or social
# attraction. Keeping them registered permits an honest complete UI taxonomy.
_NO_AUTOMATIC_TRIGGER = {"sexual_lust", "intoxication_altered_states_of_consciousness"}


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def _label(emotion_id: str) -> dict:
    record = EMOTIONS[emotion_id]
    return {"id": emotion_id, "label": record["label"], "label_de": record["label_de"]}


def taxonomy_projection() -> dict:
    """Return a copy of the imported 40-label registry for an attribution UI."""
    return deepcopy(TAXONOMY)


def _empty_affect(now: int) -> dict:
    return {"schema_version": SCHEMA_VERSION, "taxonomy_id": TAXONOMY["taxonomy_id"],
            "primary": None, "states": [], "actual_narrative": "No active, evidenced affect state.",
            "self_narrative": "I am not sure what I feel yet.", "updated_at": now,
            "active_subset_policy": "only modeled needs and explicit evidence-bound events activate labels"}


def initialize_affect(actor: dict, now: int = 0) -> dict:
    """Return the initial `{'affect': ...}` patch without altering the actor."""
    return {"affect": _empty_affect(now)}


def _cause_record(cause, evidence, now: int) -> dict:
    if isinstance(cause, str):
        source = {"kind": cause, "text": cause}
    else:
        source = dict(cause or {})
    if isinstance(evidence, str):
        evidence_id = evidence
    elif isinstance(evidence, dict):
        evidence_id = evidence.get("id") or evidence.get("evidence_id")
    else:
        evidence_id = None
    evidence_id = source.get("evidence_id", evidence_id)
    return {"kind": str(source.get("kind", "event"))[:80], "text": str(source.get("text", source.get("kind", "event")))[:240],
            "evidence_id": evidence_id, "subject_id": source.get("subject_id"),
            "at": int(source.get("at", now)), "expires_at": source.get("expires_at"),
            "category": source.get("category"), "outcome": source.get("outcome"),
            "relief": deepcopy(source.get("relief")) if isinstance(source.get("relief"), dict) else None,
            "adult_relation": source.get("adult_relation")}


def _effect_ids(cause: dict, needs: dict) -> list[tuple[str, float, int, str | None]]:
    """Map only explicit game events and modeled needs to safe active labels."""
    effects: list[tuple[str, float, int, str | None]] = []
    bladder = float(needs.get("bladder", 0))
    fatigue = float(needs.get("fatigue", 0))
    hunger = float(needs.get("hunger", 0))
    thirst = float(needs.get("thirst", 0))
    social = float(needs.get("social", 0))
    if bladder >= .68:
        effects.append(("distress", .28 + (bladder - .68) * 1.9, 300, "bladder"))
    if fatigue >= .68:
        effects.append(("fatigue_exhaustion", .28 + (fatigue - .68) * 1.9, 600, "fatigue"))
    if max(hunger, thirst) >= .82:
        effects.append(("distress", .32 + (max(hunger, thirst) - .82) * 2.0, 300, "hunger_or_thirst"))
    if social >= .78:
        effects.append(("longing", .24 + (social - .78) * 1.6, 600, "social"))

    kind = cause["kind"].lower().replace("-", "_")
    category = str(cause.get("category", "")).lower()
    outcome = str(cause.get("outcome", "")).lower()
    text = cause["text"].lower()
    if kind in {"dog_encounter", "unsafe_encounter"}:
        effects.append(("fear", .68, 1200, None))
    elif kind in {"work_warning", "work_failed_deadline", "job_warning"}:
        effects.extend((("distress", .54, 3600, None), ("doubt", .40, 1800, None)))
    elif kind in {"insult", "social_insult"}:
        effects.extend((("anger", .64, 900, None), ("embarrassment", .36, 900, None)))
    elif kind in {"social_rejection", "rejected"} or outcome == "declined":
        effects.extend((("disappointment", .48, 900, None), ("embarrassment", .24, 600, None)))
    elif kind == "goal_completed" or (kind == "activity_completed" and category in {
            "work", "creative_hobby", "craft", "bake_pizza", "cook_pancake"}):
        # Completing an arbitrary atomic action is not an achievement.  Pride
        # is reserved for explicit goals, work, a finished craft, or the point
        # at which a recipe has actually finished cooking.
        effects.append(("pride", .42, 900, None))
    elif kind == "need_relief":
        relief = cause.get("relief") if isinstance(cause.get("relief"), dict) else {}
        actual_reduction = max((float(value) for value in relief.values()), default=0.0)
        if actual_reduction > 0:
            effects.append(("relief", min(.72, .25 + actual_reduction * .8), 600, None))

    if kind in {"initialization", "activity_started"} and all(float(value) < .6 for value in needs.values()):
        effects.append(("contentment", .34, 600, None))
    if kind in {"activity_started", "activity_completed"}:
        activity = category
        if activity in {"read", "reading", "craft", "cooking", "prepare_meal", "garden", "gardening"}:
            effects.append(("interest", .42, 900, None))
        if activity in {"read", "reading", "craft", "cooking", "prepare_meal", "garden", "gardening", "work"}:
            effects.append(("concentration", .38, 900, None))

    if kind in {"social", "social_interaction", "social_complete"} or category:
        if category in {"check_in", "offer_help"} and outcome in {"positive", "accepted", "success"}:
            effects.append(("affection", .58, 1200, None))
        elif category in {"tell_joke", "play_together"} and outcome in {"positive", "accepted", "success"}:
            effects.append(("amusement", .50, 900, None))
        elif category in {"reconcile", "apologize"} and outcome in {"positive", "accepted", "success"}:
            effects.append(("relief", .48, 900, None))
        elif category in {"gossip", "set_boundary"} and outcome in {"negative", "boundary"}:
            effects.append(("anger", .42, 900, None))
    if kind == "romantic_affection" and category in {"flirt", "express_affection"}:
        if outcome in {"positive", "accepted", "success"} and cause.get("adult_relation") is True:
            effects.extend((("affection", .58, 1200, None), ("infatuation", .42, 1200, None)))
        elif outcome in {"declined", "rejected", "negative"}:
            effects.extend((("sadness", .42, 900, None), ("longing", .36, 900, None)))
    if "confus" in text:
        effects.append(("confusion", .40, 600, None))
    return [(emotion_id, _clamp(intensity), ttl, need_key) for emotion_id, intensity, ttl, need_key in effects
            if emotion_id not in _NO_AUTOMATIC_TRIGGER]


def _component_key(cause: dict, need_key: str | None) -> str:
    if need_key:
        return "need:" + need_key
    return "event:" + "|".join(str(cause.get(key) or "") for key in ("kind", "evidence_id", "subject_id", "category", "outcome"))


def _component(cause: dict, intensity: float, now: int, ttl: int, need_key: str | None = None) -> dict:
    """One independently expiring, evidence-bearing contribution to a state."""
    expiry = cause.get("expires_at")
    if not isinstance(expiry, (int, float)):
        expiry = now + ttl
    return {"key": _component_key(cause, need_key), "source": "need" if need_key else "event",
            "intensity": _clamp(intensity), "activated_at": now, "expires_at": int(expiry),
            "cause": deepcopy(cause)}


def _legacy_components(state: dict, now: int) -> list[dict]:
    """Normalize old aggregate states without inventing a missing history.

    V1 components had no cause or individual expiry.  Their recorded state
    expiry is the only defensible lifetime; if it too is absent, use the normal
    bounded default rather than making a legacy feeling permanent.
    """
    recorded_causes = list(state.get("causes", []))
    fallback_expiry = state.get("expires_at")
    if not isinstance(fallback_expiry, (int, float)):
        fallback_expiry = now + DEFAULT_EXPIRY_SECONDS
    rows = []
    raw_components = list(state.get("components", []))
    if not raw_components:
        raw_components = [{"key": f"legacy:{index}", "source": "event",
                           "intensity": state.get("intensity", 0), "cause": cause}
                          for index, cause in enumerate(recorded_causes[-MAX_COMPONENTS:])]
    if not raw_components and state.get("intensity", 0):
        raw_components = [{"key": "legacy:unattributed", "source": "event",
                           "intensity": state.get("intensity", 0),
                           "cause": {"kind": "legacy_affect_state",
                                     "text": "Legacy affect state; cause was not retained.",
                                     "evidence_id": None, "subject_id": None}}]
    for index, raw in enumerate(raw_components[-MAX_COMPONENTS:]):
        cause = raw.get("cause") if isinstance(raw.get("cause"), dict) else (
            recorded_causes[min(index, len(recorded_causes) - 1)] if recorded_causes else
            {"kind": "legacy_affect_state", "text": "Legacy affect state; cause was not retained.",
             "evidence_id": None, "subject_id": None})
        if not isinstance(cause, dict):
            cause = {"kind": "legacy_affect_state", "text": "Legacy affect state; cause was not retained.",
                     "evidence_id": None, "subject_id": None}
        expiry = raw.get("expires_at", cause.get("expires_at") if isinstance(cause, dict) else None)
        if not isinstance(expiry, (int, float)):
            expiry = fallback_expiry
        activated_at = raw.get("activated_at", state.get("activated_at", now))
        if not isinstance(activated_at, (int, float)):
            activated_at = now
        rows.append({"key": str(raw.get("key") or f"legacy:{index}"),
                     "source": raw.get("source") if raw.get("source") in {"need", "event"} else "event",
                     "intensity": _clamp(raw.get("intensity", state.get("intensity", 0))),
                     "activated_at": int(activated_at),
                     "expires_at": int(expiry), "cause": deepcopy(cause)})
    return rows


def _active_components(state: dict, now: int) -> list[dict]:
    return [component for component in _legacy_components(state, now)
            if component["intensity"] > 0 and component["expires_at"] > now]


def _causes_from_components(components: list[dict]) -> list[dict]:
    causes, keys = [], set()
    for component in components:
        cause = component["cause"]
        key = (cause.get("kind"), cause.get("evidence_id"), cause.get("subject_id"), cause.get("text"))
        if key not in keys:
            causes.append(deepcopy(cause))
            keys.add(key)
    return causes[-MAX_COMPONENTS:]


def _rebuild_state(state: dict, emotion_id: str, components: list[dict]) -> dict:
    result = deepcopy(state)
    result.update(_label(emotion_id))
    bounded = sorted(components, key=lambda item: (item["activated_at"], item["key"]))[-MAX_COMPONENTS:]
    result["components"] = bounded
    result["intensity"] = max((item["intensity"] for item in bounded), default=0.0)
    result["activated_at"] = min((item["activated_at"] for item in bounded), default=result.get("activated_at", 0))
    result["expires_at"] = max((item["expires_at"] for item in bounded), default=None)
    result["causes"] = _causes_from_components(bounded)
    return result


def _state(emotion_id: str, intensity: float, cause: dict, now: int, ttl: int, need_key: str | None = None) -> dict:
    return _rebuild_state({}, emotion_id, [_component(cause, intensity, now, ttl, need_key)])


def _merge_state(previous: dict, emotion_id: str, intensity: float, cause: dict, now: int, ttl: int, need_key: str | None = None) -> dict:
    component = _component(cause, intensity, now, ttl, need_key)
    components = [item for item in _active_components(previous, now) if item["key"] != component["key"]]
    return _rebuild_state(previous, emotion_id, components + [component])


def _refresh_physical_states(states: list[dict], now: int) -> dict[str, dict]:
    """Expire every component, then drop physical ones for recomputation."""
    refreshed = {}
    for state in states:
        if state.get("id") not in EMOTIONS:
            continue
        components = [part for part in _active_components(state, now) if part.get("source") != "need"]
        if not components:
            continue
        refreshed[state["id"]] = _rebuild_state(state, state["id"], components)
    return refreshed


def _actual_narrative(states: list[dict]) -> str:
    causes = []
    for state in states:
        for cause in state.get("causes", []):
            token = cause.get("text") or cause.get("kind")
            if token and token not in causes:
                causes.append(token)
    return "Evidence-bound appraisal: " + "; ".join(causes[:4]) if causes else "No active, evidenced affect state."


def _display_activity(value: str) -> str:
    """Small controlled vocabulary for self-stories; never reuse raw event text."""
    phrases = {"read": "reading", "creative_hobby": "a craft project", "craft": "a craft project",
               "bake_pizza": "baking the pizza", "cook_pancake": "cooking the pancakes",
               "prepare_meal": "preparing a meal", "eat_recipe": "the meal", "change_outfit": "changing clothes"}
    return phrases.get(value, value.replace("_", " "))


def _self_narrative(actor: dict, primary: str | None, states: list[dict], needs: dict) -> str:
    """Offer a bounded first-person interpretation, never an unobserved event."""
    traits = actor.get("psychology", {}).get("big_five", {})
    extraversion = float(traits.get("extraversion", .5))
    agreeableness = float(traits.get("agreeableness", .5))
    neuroticism = float(traits.get("neuroticism", .5))
    active = {state["id"] for state in states}
    suffix = " This is a tentative gameplay interpretation, not a hidden fact."
    primary_state = next((state for state in states if state["id"] == primary), {})
    primary_cause = (primary_state.get("causes") or [{}])[-1]
    category = _display_activity(str(primary_cause.get("category") or ""))
    kind = _display_activity(str(primary_cause.get("kind") or "event"))
    romantic_success = any(cause.get("kind") == "romantic_affection" and cause.get("category") in {"flirt", "express_affection"}
                           and cause.get("outcome") in {"positive", "accepted", "success"}
                           and cause.get("adult_relation") is True
                           for state in states for cause in state.get("causes", []))
    if romantic_success and extraversion < .45:
        return "Maybe that was only a friendly conversation; I am not certain what this interaction means to me." + suffix
    if "affection" in active and primary == "affection":
        if neuroticism >= .65:
            return "I notice warmth from this interaction, although I still feel uncertain." + suffix
        if extraversion >= .65:
            return "I feel more open and connected after this interaction." + suffix
        if agreeableness >= .65:
            return "I want to acknowledge the warmth in this interaction." + suffix
        return "I notice a warm connection after this interaction." + suffix
    if "affection" in active and primary in {"distress", "fatigue_exhaustion", "longing"}:
        if neuroticism >= .65:
            return "The connection matters to me, but it does not remove my current uncertainty or discomfort." + suffix
        if agreeableness >= .65:
            return "I value the connection, even while another immediate need has my attention." + suffix
        return "I notice both connection and an immediate need competing for my attention." + suffix
    if primary in {"distress", "doubt", "confusion", "embarrassment", "anger"}:
        if float(needs.get("fatigue", 0)) >= .45:
            return "Maybe fatigue is shaping how I read this moment; I cannot be fully sure." + suffix
        if neuroticism >= .65:
            return "I feel on edge about this moment, though that is only my current interpretation." + suffix
        return "I may be reacting strongly; I cannot be fully sure why." + suffix
    if primary == "pride":
        achievement = category or kind
        return f"I feel pleased that I completed {achievement}." + suffix
    if primary in {"interest", "concentration"}:
        activity = category or kind
        return f"I want to keep my attention on {activity}." + suffix
    if primary == "contentment":
        activity = category or kind
        return f"I feel fairly settled as I begin {activity}." + suffix
    if primary == "relief":
        need = category or "that need"
        return f"{need.capitalize()} feels less pressing after it eased." + suffix
    if primary == "fear" and primary_cause.get("kind") in {"dog_encounter", "unsafe_encounter"}:
        return "The observed encounter has made me cautious for now." + suffix
    if primary:
        detail = category or kind
        return f"I notice {primary.replace('_', ' ')} in response to {detail}." + suffix
    return "I am not sure what I feel yet." + suffix


def appraise(actor: dict, needs: dict, now: int, cause, evidence=None) -> dict:
    """Return an affect dictionary, not an actor wrapper.

    `cause` must be a real modeled need/event supplied by the coordinator. It
    neither reads another actor nor substitutes a self-story for actual causes.
    """
    existing = deepcopy(actor.get("affect", _empty_affect(now)))
    states_by_id = _refresh_physical_states(existing.get("states", []), now)
    source = _cause_record(cause, evidence, now)
    for emotion_id, intensity, ttl, need_key in _effect_ids(source, needs):
        effect_cause = ({**source, "kind": "modeled_need", "text": f"Modeled urgent {need_key} need"}
                        if need_key else source)
        old = states_by_id.get(emotion_id)
        states_by_id[emotion_id] = (_merge_state(old, emotion_id, intensity, effect_cause, now, ttl, need_key)
                                    if old else _state(emotion_id, intensity, effect_cause, now, ttl, need_key))
    states = sorted(states_by_id.values(), key=lambda row: (-row["intensity"], row["id"]))
    primary = states[0]["id"] if states else None
    return {"schema_version": SCHEMA_VERSION, "taxonomy_id": TAXONOMY["taxonomy_id"], "primary": primary,
            "states": states, "actual_narrative": _actual_narrative(states),
            "self_narrative": _self_narrative(actor, primary, states, needs), "updated_at": now,
            "active_subset_policy": "only modeled needs and explicit evidence-bound events activate labels"}


def project_affect(actor: dict, now: int) -> dict:
    """Return a privacy-safe, expiry-filtered affect projection for this actor."""
    affect = actor.get("affect", _empty_affect(now))
    # Projection has to filter individual causes too: a long-lived component
    # must not keep an older, expired component or its evidence visible.
    states = [_rebuild_state(state, state["id"], _active_components(state, now))
              for state in affect.get("states", []) if state.get("id") in EMOTIONS]
    states = [state for state in states if state["components"]]
    states.sort(key=lambda row: (-row["intensity"], row["id"]))
    return {"primary": states[0]["id"] if states else None, "states": states,
            "actual_narrative": _actual_narrative(states),
            "self_narrative": _self_narrative(actor, states[0]["id"] if states else None, states, actor.get("needs", {})),
            "updated_at": now}


def adapt_legacy_emotion(actor: dict, now: int, evidence_id: str = "legacy") -> dict:
    """Convert the previous single display band without claiming new history."""
    legacy = actor.get("emotion", {}) if isinstance(actor.get("emotion"), dict) else {}
    mapping = {"Afraid": "fear", "Worried": "distress", "Tense": "distress", "Disappointed": "disappointment",
               "Lonely": "longing", "Restless": "impatience_and_irritability", "Happy": "elation", "Content": "contentment"}
    emotion_id = mapping.get(legacy.get("type"))
    if not emotion_id:
        return _empty_affect(now)
    cause = {"kind": "legacy_display_adapter", "text": "Legacy display emotion; prior cause is not reconstructed.",
             "evidence_id": evidence_id, "subject_id": actor.get("id"), "expires_at": legacy.get("expires_at") or now + DEFAULT_EXPIRY_SECONDS}
    state = _state(emotion_id, legacy.get("intensity", .3), cause, now, DEFAULT_EXPIRY_SECONDS)
    return {"schema_version": SCHEMA_VERSION, "taxonomy_id": TAXONOMY["taxonomy_id"], "primary": emotion_id,
            "states": [state], "actual_narrative": "Legacy display value retained; prior history is not reconstructed.",
            "self_narrative": "I am not sure how this older feeling began.", "updated_at": now,
            "active_subset_policy": "legacy adapter; no new cause inferred"}


def _known_relation(relation: dict) -> bool:
    layers = relation.get("layers", {})
    if relation.get("last_interaction") is not None or relation.get("kind") not in (None, "Acquaintance"):
        return True
    return any(layer.get("status") not in (None, "none") for layer in layers.values() if isinstance(layer, dict))


def _relationship_roles(actor: dict, target: dict, relation: dict) -> list[str]:
    """Viewer-relative, structural roles; never infer kinship from age or home."""
    layers = relation.get('layers', {})
    family = actor.get('family', {})
    other_family = target.get('family', {})
    roles = []
    if family.get('partner_id') == target.get('id') and other_family.get('partner_id') == actor.get('id'):
        roles.append('spouse' if family.get('relationship_status') == other_family.get('relationship_status') == 'married' else 'partner')
    kin = layers.get('family', {}).get('status', 'none')
    if kin not in (None, 'none'):
        roles.append(kin)
    friendship = layers.get('friendship', {})
    if (friendship.get('status') == 'established'
            or float(friendship.get('score', 0)) >= .15):
        roles.append('friend')
    romance = layers.get('romance', {})
    if 'spouse' not in roles and 'partner' not in roles and float(romance.get('score', 0)) >= .15:
        roles.append('romantic_interest')
    if layers.get('coworker', {}).get('status') not in (None, 'none'):
        roles.append('coworker')
    if layers.get('household', {}).get('status') not in (None, 'none'):
        roles.append('housemate')
    return roles or ['acquaintance']


def _relationship_feeling(qualities: dict) -> str:
    """A readable appraisal of relation *scores*, not the target's current emotion."""
    if qualities['tension'] >= .55:
        return 'tense'
    if qualities['attraction'] >= .55 and qualities['closeness'] >= .35:
        return 'attracted'
    if qualities['closeness'] >= .65 and qualities['trust'] >= .6:
        return 'close_and_trusting'
    if qualities['respect'] >= .65:
        return 'respectful'
    if qualities['closeness'] >= .4:
        return 'warm'
    return 'reserved'


def social_graph_projection(actor: dict, actors, now: int) -> dict:
    """Project explicit pairwise relations; never expose needs, thoughts or affect."""
    by_id = actors if isinstance(actors, dict) else {row.get('id'): row for row in actors}
    actor_ids = set(by_id)
    nodes, edges = [], []
    for target_id, relation in actor.get("relations", {}).items():
        if target_id not in actor_ids or not _known_relation(relation):
            continue
        layers = relation.get("layers", {})
        types = sorted(key for key, value in layers.items() if isinstance(value, dict) and value.get("status") not in (None, "none"))
        qualities = {key: _clamp(relation.get(key, 0)) for key in ("closeness", "trust", "respect", "attraction", "tension")}
        importance = _clamp(.38 * qualities["closeness"] + .27 * qualities["trust"] + .20 * qualities["respect"] + .10 * qualities["attraction"] + (.05 if types else 0))
        target = by_id[target_id]
        reverse = target.get('relations', {}).get(actor.get('id'))
        reciprocal = None
        if reverse is not None and _known_relation(reverse):
            reverse_qualities = {key: _clamp(reverse.get(key, 0)) for key in qualities}
            reciprocal = {'qualities': reverse_qualities,
                          'feeling': _relationship_feeling(reverse_qualities),
                          'roles': _relationship_roles(target, actor, reverse)}
        nodes.append({"id": target_id, "known": True, "importance": importance})
        edges.append({"source": actor.get("id"), "target": target_id, "directed": True,
                      "relationship_types": types, "qualities": qualities, "importance": importance,
                      "roles": _relationship_roles(actor, target, relation),
                      "feeling": _relationship_feeling(qualities), 'reciprocal': reciprocal})
    known_ids = {node["id"] for node in nodes}
    observed = actor.get("psychology", {}).get("theory_of_mind", {}).get("known_people", {})
    observed_not_known = sorted(target_id for target_id in observed if target_id in actor_ids and target_id not in known_ids)
    return {"viewer_id": actor.get("id"), "generated_at": now,
            "nodes": sorted(nodes, key=lambda row: (-row["importance"], row["id"])),
            "edges": sorted(edges, key=lambda row: (-row["importance"], row["target"])),
            "observed_not_known": observed_not_known,
            "privacy": "explicit directional relation scores from both participants; current affect, needs, thoughts and beliefs are excluded"}
