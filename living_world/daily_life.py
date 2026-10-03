"""Deterministic plans and completion effects for ordinary household life.

These functions only read canonical records. The event engine owns travel,
reservations, elapsed time and committing returned patches in a transaction.
"""

from copy import deepcopy


class StepUnavailable(ValueError):
    """A planned step is no longer valid against current canonical state."""


def _action(label, kinds, duration, relief=None, preference=None, thought="", cost=0):
    return {"label": label, "object_kinds": kinds, "duration": duration,
            "relief": relief or {}, "cost": cost, "preference": preference,
            "thought": thought}


DAILY_ACTIONS = {
    "buy_groceries": _action("Buying groceries", ["shop_counter"], 360,
                            thought="The pantry needs supplies.", cost=20),
    "stock_fridge": _action("Putting groceries away", ["fridge"], 180,
                            thought="I should put the groceries away."),
    "fetch_ingredients": _action("Getting ingredients", ["fridge"], 120,
                                 thought="I'll take what I need from the fridge."),
    "prepare_meal": _action("Preparing a meal", ["counter"], 600,
                            preference="cooking", thought="I can make something nourishing."),
    "serve_meal": _action("Carrying dinner to the table", ["table"], 90,
                          thought="The meal is ready for the table."),
    "eat_meal": _action("Eating a meal", ["table"], 600,
                        relief={"hunger": .8, "comfort": .1}, preference="cooking",
                        thought="I can sit down and enjoy this meal."),
    "clear_dishes": _action("Clearing dirty dishes", ["table"], 90,
                            thought="The dishes need to go to the sink."),
    "wash_dishes": _action("Washing dishes", ["sink"], 240,
                           thought="I'll wash up after eating."),
    "bin_trash": _action("Putting scraps in the bin", ["bin"], 90,
                         thought="The food scraps belong in the bin."),
    "empty_trash": _action("Taking out the trash", ["bin"], 180,
                           thought="The bin should be emptied."),
    "wipe_counter": _action("Wiping the kitchen counter", ["counter"], 180,
                            thought="A clean worktop makes the kitchen nicer."),
    "creative_hobby": _action("Making a craft project", ["desk"], 1200,
                              relief={"fun": .58, "comfort": .12}, preference="craft",
                              thought="I want to make something of my own."),
}


JOB_STATIONS = {
    "Teacher": ("teacher_station", "school"),
    "Illustrator": ("illustrator_station", "studio"),
    "Designer": ("designer_station", "studio"),
    "Carpenter": ("carpenter_station", "workshop"),
    "Tailor": ("tailor_station", "workshop"),
    "Gardener": ("gardener_station", "workshop"),
    "Baker": ("cafe_counter", "cafe"),
    "Bookseller": ("shop_counter", "shop"),
    "Independent artist": ("desk", None),
    "Physician": ("hospital_desk", "hospital"),
    "Chef": ("cafe_counter", "cafe"),
    "Mechanic": ("carpenter_station", "workshop"),
    "Programmer": ("office_station", "office_hub"),
    "Civic planner": ("townhall_desk", "town_hall"),
    "Kindergarten educator": ("kindergarten_desk", "kindergarten"),
    "Lifeguard": ("lifeguard_station", "pool"),
    "Bartender": ("bar_counter", "bar"),
    "Club DJ": ("dj_booth", "nightclub"),
    "Professor": ("lectern", "university"),
    "Researcher": ("biology_bench", "university"),
    "University administrator": ("university_desk", "university"),
}


def _records(objects):
    return objects.values() if isinstance(objects, dict) else objects


def _home_object(actor, objects, kind):
    if actor.get('household_id')=='student_residence' and kind in {'bed','wardrobe','table'}:
        choices=[obj for obj in _records(objects) if obj['kind']==kind
                 and obj.get('household_id')=='student_residence']
        slot=max(0,int(actor['id'].rsplit('_',1)[-1])-45)
        index=min(slot,len(choices)-1) if kind!='table' else min(int(slot>=6),len(choices)-1)
        return choices[index] if choices else None
    return next((obj for obj in _records(objects)
                 if obj["kind"] == kind and obj.get("household_id") == actor["household_id"]), None)


def _step(kind, obj):
    return {"kind": kind, "target_id": obj["id"]}


def assigned_workplace(actor, objects):
    """Return one stable station assignment, or None for an unknown job."""
    job = actor.get("profile", {}).get("job")
    assignment = JOB_STATIONS.get(job)
    if assignment is None:
        return None
    kind, building_id = assignment
    stations = [obj for obj in _records(objects) if obj["kind"] == kind
                and obj.get("building_id") == (building_id or actor.get("home_id"))]
    if not stations:
        return None
    station = min(stations, key=lambda obj: obj["id"])
    return {"target_id": station["id"], "building_id": station["building_id"],
            "workplace_id": station["building_id"], "station_kind": kind,
            "work_from_home": building_id is None}


def coworkers_at_work(actor, actors, objects):
    """IDs of residents whose assigned workplace building is the same."""
    assigned = assigned_workplace(actor, objects)
    if assigned is None:
        return []
    values = actors.values() if isinstance(actors, dict) else actors
    return sorted(other["id"] for other in values if other["id"] != actor["id"]
                  and (station := assigned_workplace(other, objects)) is not None
                  and station["workplace_id"] == assigned["workplace_id"])


def daily_state(obj):
    """Read lazily initialized object state without modifying old save records."""
    defaults = {
        "fridge": {"pantry_stock": 8},
        "counter": {"mess": 0, "cleaned_total": 0},
        "table": {"served_meals": 0, "dirty_dishes": 0},
        "sink": {"washed_total": 0},
        "bin": {"trash": 0, "disposed_total": 0},
    }
    return {**defaults.get(obj["kind"], {}), **obj.get("daily", {})}


def plan_groceries(actor, objects):
    fridge = _home_object(actor, objects, "fridge")
    shop = next((obj for obj in _records(objects) if obj["kind"] == "shop_counter"
                 and obj.get("building_id") == "shop"), None)
    if fridge is None or shop is None:
        return []
    if actor.get("inventory", {}).get("groceries", 0) >= 8:
        return [_step("stock_fridge", fridge)]
    return [_step("buy_groceries", shop), _step("stock_fridge", fridge)]


def plan_meal(actor, objects):
    """Resume the furthest available food stage, then clean up the result.

    A held token or an already served meal is canonical evidence of earlier
    work. Replanning must use that food before it draws fresh pantry stock.
    """
    fixtures = {kind: _home_object(actor, objects, kind)
                for kind in ("fridge", "counter", "table", "sink", "bin")}
    if any(value is None for value in fixtures.values()):
        return []
    inventory = actor.get("inventory", {})
    table_state = daily_state(fixtures["table"])
    counter_state = daily_state(fixtures["counter"])
    bin_state = daily_state(fixtures["bin"])
    stages = [
        _step("fetch_ingredients", fixtures["fridge"]),
        _step("prepare_meal", fixtures["counter"]),
        _step("serve_meal", fixtures["table"]),
        _step("eat_meal", fixtures["table"]),
    ]
    if table_state["served_meals"]:
        start = 3
    elif inventory.get("prepared_meal", 0):
        start = 2
    elif inventory.get("ingredients", 0):
        start = 1
    else:
        start = 0
    result = []
    if start == 0 and daily_state(fixtures["fridge"])["pantry_stock"] < 1:
        result.extend(plan_groceries(actor, objects))
        if not result:
            return []
    result.extend(stages[start:])
    result.extend([_step("clear_dishes", fixtures["table"]),
                   _step("wash_dishes", fixtures["sink"])])
    makes_scraps = start <= 1
    if inventory.get("food_scraps", 0) or makes_scraps:
        if bin_state["trash"] and bin_state["trash"] + inventory.get("food_scraps", 0) + int(makes_scraps) > 8:
            result.append(_step("empty_trash", fixtures["bin"]))
        result.extend([_step("bin_trash", fixtures["bin"]),
                       _step("empty_trash", fixtures["bin"])])
    if counter_state["mess"] or makes_scraps:
        result.append(_step("wipe_counter", fixtures["counter"]))
    return result


def plan_cleaning(actor, objects):
    """Build chores from the current dirty state, in a workable order."""
    table = _home_object(actor, objects, "table")
    sink = _home_object(actor, objects, "sink")
    bin_obj = _home_object(actor, objects, "bin")
    counter = _home_object(actor, objects, "counter")
    inventory = actor.get("inventory", {})
    result = []
    if table:
        result.extend(_step("clear_dishes", table)
                      for _ in range(daily_state(table)["dirty_dishes"]))
    if sink and (inventory.get("dirty_dish", 0) or result):
        result.append(_step("wash_dishes", sink))
    if bin_obj:
        if daily_state(bin_obj)["trash"] >= 8:
            result.append(_step("empty_trash", bin_obj))
        if inventory.get("food_scraps", 0):
            result.append(_step("bin_trash", bin_obj))
        if (daily_state(bin_obj)["trash"] or inventory.get("food_scraps", 0)) and not any(step["kind"] == "empty_trash" for step in result):
            result.append(_step("empty_trash", bin_obj))
    if counter and daily_state(counter)["mess"]:
        result.append(_step("wipe_counter", counter))
    return result


def plan_hobby(actor, objects):
    """Choose one home activity matching the resident's strongest relevant interest."""
    kinds = {"craft": ("creative_hobby", "desk"),
             "reading": ("read", "bookshelf"),
             "gardening": ("garden", "planter")}
    preferences = actor.get("preferences", {})
    for interest in sorted(kinds, key=lambda key: (-preferences.get(key, 0), key)):
        action, fixture = kinds[interest]
        obj = _home_object(actor, objects, fixture)
        if obj is not None:
            return [_step(action, obj)]
    return []


def _consume(inventory, token, amount=1):
    if inventory.get(token, 0) < amount:
        raise StepUnavailable(f"Missing {token}")
    left = inventory[token] - amount
    if left:
        inventory[token] = left
    else:
        inventory.pop(token)


def _produce(inventory, token, amount=1):
    inventory[token] = inventory.get(token, 0) + amount


def apply_step(actor, obj, kind):
    """Return complete component values to commit when a reserved step finishes.

    The caller must revalidate the current actor and object at completion, then
    assign inventory to the edited actor and daily to the edited object within
    the same engine transaction. Engine money/need effects remain engine-owned.
    """
    definition = DAILY_ACTIONS.get(kind)
    if definition is None:
        raise StepUnavailable(f"Unknown daily action: {kind}")
    if obj["kind"] not in definition["object_kinds"] and not (kind == "buy_groceries" and obj["kind"] == "supermarket_checkout"):
        raise StepUnavailable(f"{kind} cannot use {obj['kind']}")
    if obj.get("household_id") not in (None, actor.get("household_id")):
        raise StepUnavailable("Cannot use another household's fixture")
    inventory = deepcopy(actor.get("inventory", {}))
    state = daily_state(obj)
    skills = deepcopy(actor.get("skills", {}))

    if kind == "buy_groceries":
        _produce(inventory, "groceries", 8)
    elif kind == "stock_fridge":
        _consume(inventory, "groceries", 8)
        state["pantry_stock"] += 8
    elif kind == "fetch_ingredients":
        if state["pantry_stock"] < 1:
            raise StepUnavailable("The fridge has no ingredients")
        state["pantry_stock"] -= 1
        _produce(inventory, "ingredients")
    elif kind == "prepare_meal":
        _consume(inventory, "ingredients")
        _produce(inventory, "prepared_meal")
        _produce(inventory, "food_scraps")
        state["mess"] += 1
    elif kind == "serve_meal":
        if state["served_meals"] >= 3:
            raise StepUnavailable("The table is full of served meals")
        _consume(inventory, "prepared_meal")
        state["served_meals"] += 1
    elif kind == "eat_meal":
        if state["served_meals"] < 1:
            raise StepUnavailable("No meal has been served")
        state["served_meals"] -= 1
        state["dirty_dishes"] += 1
    elif kind == "clear_dishes":
        if state["dirty_dishes"] < 1:
            raise StepUnavailable("There are no dirty dishes on the table")
        state["dirty_dishes"] -= 1
        _produce(inventory, "dirty_dish")
    elif kind == "wash_dishes":
        amount = inventory.get("dirty_dish", 0)
        _consume(inventory, "dirty_dish", max(1, amount))
        state["washed_total"] += amount
    elif kind == "bin_trash":
        if inventory.get("food_scraps", 0) < 1:
            raise StepUnavailable("Missing food_scraps")
        amount = min(inventory.get("food_scraps", 0), 8 - state["trash"])
        if amount < 1:
            raise StepUnavailable("The bin needs emptying first")
        _consume(inventory, "food_scraps", amount)
        state["trash"] += amount
    elif kind == "empty_trash":
        if state["trash"] < 1:
            raise StepUnavailable("The bin is already empty")
        state["disposed_total"] += state["trash"]
        state["trash"] = 0
    elif kind == "wipe_counter":
        if state["mess"] < 1:
            raise StepUnavailable("The counter is already clean")
        state["cleaned_total"] += state["mess"]
        state["mess"] = 0
    elif kind == "creative_hobby":
        _produce(inventory, "craft_project")
        skills["craft"] = round(min(1, skills.get("craft", 0) + .01), 3)
    return {"inventory": inventory, "object_daily": state, "skills": skills}


def step_available(actor, obj, kind):
    """Check canonical token and fixture preconditions without changing state."""
    try:
        apply_step(actor, obj, kind)
    except StepUnavailable:
        return False
    return True
