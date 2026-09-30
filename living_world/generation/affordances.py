"""Authoring-time action contracts, deliberately separate from the live engine.

Objects offer affordances; actors supply capabilities; an executor owns effects,
reservations and time. These contracts are not claims of implemented simulation
actions. They can be consumed by procedural planners or future LWM agents alike.
"""
from copy import deepcopy


def action(name, seconds, capability=None, effect=None, *, requires=None, reservation="object_use_slot"):
    return {"name": name, "duration_seconds": seconds,
            "capability": capability, "effect_hint": effect,
            "requires": list(requires if requires is not None else ("reachable_anchor", "object_available")),
            "reservation": reservation, "execution": "authoring_contract_only"}


ACTIONS = {
    # Observation needs visibility, not a physical interaction anchor or slot.
    "inspect": action("Ansehen", 5, requires=("object_visible",), reservation=None),
    "clean": action("Reinigen", 60, "housekeeping", "hygiene"),
    "sleep": action("Schlafen", 3600, None, "energy"),
    "rest": action("Ausruhen", 300, None, "comfort"),
    "make_bed": action("Bett machen", 90, "housekeeping"),
    "climb_bunk": action("Obere Liege erreichen", 15, "climb"),
    "adjust_backrest": action("Rückenlehne einstellen", 10),
    "sit": action("Sitzen", 60, None, "comfort"),
    "read": action("Lesen", 600, "read", "fun"),
    "study": action("Lernen", 900, "read", "knowledge"),
    "work": action("Arbeiten", 900, "work", "progress"),
    "store": action("Einräumen", 30),
    "retrieve": action("Herausnehmen", 20),
    "wash": action("Waschen", 120, None, "hygiene"),
    "cook": action("Mahlzeit zubereiten", 600, "cooking", "meal"),
    "eat": action("Essen", 300, None, "hunger"),
    "drink": action("Trinken", 30, None, "thirst"),
    "play": action("Spielen", 600, None, "fun"),
    "exercise": action("Trainieren", 900, "exercise", "fitness"),
    "water": action("Gießen", 30, "gardening"),
    "feed_fish": action("Fische füttern", 30, "animal_care"),
    "perform": action("Musik spielen", 600, "music", "fun"),
    "repair": action("Reparieren", 600, "repair"),
    "teach": action("Unterrichten", 1800, "teaching", "lesson"),
    "observe_sample": action("Probe betrachten", 180, "lab_training", "knowledge"),
    "simulate_experiment": action("Abstrakten Versuch durchführen", 300, "lab_training"),
    "check_in": action("Anmelden", 60),
    "examine": action("Spielerische Untersuchung", 300, "medical_role"),
    "monitor": action("Anzeige prüfen", 30, "medical_role"),
    "equip": action("Ausrüstung anlegen", 90, "emergency_role"),
    "dispatch": action("Einsatz disponieren", 120, "emergency_role"),
    "relieve": action("Toilette benutzen", 90, None, "bladder"),
    "toggle_light": action("Licht schalten", 2, None, "lighting"),
    "change_baby": action("Baby wickeln", 180, "childcare", "care"),
    "soothe_baby": action("Baby beruhigen", 90, "childcare", "comfort"),
    "play_chess": action("Schach spielen", 1200, None, "fun"),
    "check_time": action("Uhrzeit ablesen", 5, None, "orientation", requires=("object_visible",), reservation=None),
    "groom": action("Sich pflegen", 180, None, "hygiene"),
    "wash_dishes": action("Geschirr spülen", 180, None, "cleanliness"),
    "dry_clothes": action("Wäsche trocknen", 60, None, "cleanliness"),
    "iron": action("Wäsche bügeln", 300, "housekeeping", "comfort"),
    "print": action("Dokument drucken", 30, "work", "work_product"),
    "create_art": action("Kunstwerk gestalten", 900, None, "fun"),
    "set_table": action("Tisch decken", 120, "housekeeping"),
    "serve": action("Mahlzeit servieren", 60, "cooking", "meal"),
    "observe_artifact": action("Ausstellungsstück betrachten", 60, None, "knowledge", requires=("object_visible",), reservation=None),
    "request_privacy": action("Privatsphäre erbitten", 15),
}


GROUPS = {
    ("sofa", "armchair", "bench", "rocking_chair", "civic_waiting_bench"): ["sit", "rest", "read"],
    ("bookshelf", "reading_table", "civic_archive_shelf"): ["read", "study", "store", "retrieve"],
    ("desk", "office_desk", "gaming_desk"): ["work", "study", "play"],
    ("school_teacher_desk", "civic_staff_desk"): ["work", "study", "store", "retrieve"],
    ("school_student_desk",): ["study", "read", "sit", "work"],
    ("dining_table", "large_dining_table", "reading_table", "civic_cafeteria_table"): ["eat", "sit", "set_table"],
    ("buffet", "civic_cafeteria_counter"): ["eat", "serve", "store", "retrieve"],
    ("counter", "stove", "kitchen_island", "microwave_cart"): ["cook"],
    ("school_physics_demo",): ["simulate_experiment", "observe_sample"],
    ("coffee_station", "bar"): ["drink"],
    ("sink", "basin", "shower", "bathtub", "utility_sink"): ["wash"],
    ("washing_machine", "dryer"): ["wash", "store", "retrieve"],
    ("plant", "planter_box", "plant_shelf", "potting_bench"): ["water"],
    ("aquarium",): ["feed_fish"],
    ("stereo", "piano", "synthesizer", "guitar_stand", "drum_kit"): ["perform", "play"],
    ("treadmill", "exercise_bike", "weight_bench", "punching_bag"): ["exercise"],
    ("dumbbell_rack",): ["retrieve", "exercise"],
    ("workbench", "sewing_table"): ["work", "repair"],
    ("easel",): ["create_art", "work"],
    ("tv", "arcade", "pool_table", "foosball_table", "pingpong_table", "toy_storage", "child_table"): ["play"],
    ("chess_table",): ["play_chess"],
    ("display_cabinet",): ["observe_artifact"],
    ("fridge", "freezer", "wardrobe", "cabinet", "sideboard", "dresser", "pantry_shelf", "storage_rack", "tool_cabinet", "filing_cabinet", "shoe_rack", "coat_rack", "baby_storage", "luggage_rack", "side_table", "coffee_table", "produce_crate", "laundry_basket", "towel_rack", "hospital_bedside_stand", "school_supply_cabinet", "civic_locker_bank", "clinic_cart", "fire_gear_rack"): ["store", "retrieve"],
    ("floor_lamp",): ["toggle_light"],
    ("toilet",): ["relieve"],
    ("changing_table",): ["change_baby"],
    ("crib",): ["sleep", "rest", "soothe_baby"],
    ("vanity",): ["groom"],
    ("dishwasher",): ["wash_dishes"],
    ("drying_rack",): ["dry_clothes", "store", "retrieve"],
    ("ironing_board",): ["iron"],
    ("printer_stand",): ["print", "work"],
    ("school_microscope", "school_lab_bench"): ["observe_sample", "study"],
    ("school_model_skeleton",): ["observe_artifact", "study"],
    ("school_chalkboard",): ["teach", "study", "read"],
    ("school_supply_cabinet",): ["store", "retrieve"],
    ("civic_safety_station",): ["read", "observe_sample"],
    ("clinic_exam_table",): ["check_in", "examine", "rest"],
    ("clinic_screen",): ["request_privacy"],
    ("hospital_bed",): ["sleep", "rest", "adjust_backrest", "monitor"],
    ("civic_reception_desk",): ["check_in", "work"],
    ("fire_dispatch_console",): ["dispatch", "work"],
    ("fire_engine_bay",): ["repair", "equip", "dispatch"],
    ("civic_service_kiosk",): ["check_in", "read", "work"],
}


# These capacities describe object design only; actor capabilities are
# declared independently on ACTIONS and runtime occupancy belongs to a caller.
OBJECT_CAPACITIES = {
    "single_bed": {"sleep_slots": 1}, "double_bed": {"sleep_slots": 2},
    "crib": {"sleep_slots": 1}, "hospital_bed": {"sleep_slots": 1},
    "sofa": {"seat_slots": 3}, "armchair": {"seat_slots": 1},
    "bench": {"seat_slots": 2}, "rocking_chair": {"seat_slots": 1},
    "dining_table": {"seat_slots": 4}, "large_dining_table": {"seat_slots": 6},
    "reading_table": {"seat_slots": 2}, "civic_cafeteria_table": {"seat_slots": 4},
    "civic_waiting_bench": {"seat_slots": 2},
    "pool_table": {"player_slots": 2}, "foosball_table": {"player_slots": 4},
    "pingpong_table": {"player_slots": 2}, "chess_table": {"player_slots": 2},
}


def object_actions(kind):
    from .bed_variants import BED_TRAITS
    from .civic_catalog import CIVIC_AFFORDANCES
    result = ["inspect", "clean"]
    if kind in ("single_bed", "double_bed", "crib") or kind in BED_TRAITS:
        result += ["sleep", "rest", "make_bed"]
        if "bunk" in kind or "loft" in kind:
            result += ["climb_bunk"]
        if "hospital" in kind:
            result += ["adjust_backrest"]
    for kinds, actions in GROUPS.items():
        if kind in kinds:
            result += actions
    # Clock objects are not in today's base catalog, but the contract is ready
    # for a future authoring spec without inventing one here.
    if kind in ("clock", "wall_clock"):
        result += ["check_time"]
    # Curated civic metadata is descriptive; only registered action IDs execute
    # through this contract. Unknown author labels remain visible as notes there.
    meta = CIVIC_AFFORDANCES.get(kind, {})
    civic = meta.get("actions", []) if isinstance(meta, dict) else meta
    result += [a for a in civic if a in ACTIONS]
    return list(dict.fromkeys(result))


def object_capacities(kind):
    """Return authoring-time physical capacity, independent of actor skills."""
    from .bed_variants import BED_CAPACITIES
    result = deepcopy(OBJECT_CAPACITIES.get(kind, {}))
    if kind in BED_CAPACITIES:
        result["sleep_slots"] = BED_CAPACITIES[kind]
    return result


def use_slot_capacity(kind, action_id):
    """Maximum simultaneous users suggested by static object capacity data."""
    capacity = object_capacities(kind)
    if action_id == "sleep":
        return capacity.get("sleep_slots", 1)
    if action_id in ("sit", "rest", "eat"):
        return capacity.get("seat_slots", 1)
    if action_id in ("play", "play_chess"):
        return capacity.get("player_slots", 1)
    return 1


def contracts(catalog):
    return {"execution": "authoring_contract_only", "actions": deepcopy(ACTIONS),
            "objects": {kind: object_actions(kind) for kind in catalog},
            "object_capacities": {kind: object_capacities(kind) for kind in catalog},
            "use_slot_capacities": {kind: {a: use_slot_capacity(kind, a) for a in object_actions(kind)}
                                    for kind in catalog},
            "ownership": {"object": "footprint, anchors, static capacity, affordance IDs",
                          "actor": "capabilities, role, needs, intention",
                          "executor": "reachability, use-slot occupancy, preconditions, time, effects"}}


def check_action(action_id, offered, actor, *, reachable=False, available=True,
                 visible=True, slots_in_use=0, slot_capacity=1):
    if action_id not in ACTIONS or action_id not in offered:
        return {"allowed": False, "reasons": ["not_offered"]}
    contract = ACTIONS[action_id]
    reasons = []
    if contract["capability"] and contract["capability"] not in actor.get("capabilities", []):
        reasons.append("capability_missing:" + contract["capability"])
    if "object_visible" in contract["requires"] and not visible:
        reasons.append("object_not_visible")
    if "reachable_anchor" in contract["requires"] and not reachable:
        reasons.append("no_reachable_anchor")
    if "object_available" in contract["requires"] and (not available or slots_in_use >= slot_capacity):
        reasons.append("use_slot_reserved")
    return {"allowed": not reasons, "reasons": reasons, "contract": deepcopy(contract)}
