"""Concrete, serialised possessions and recipe steps.

No function here mutates its arguments. The engine commits the returned full
component patches together with its usual action, need and reservation effects.
"""

from copy import deepcopy

from .daily_life import daily_state


class PossessionUnavailable(ValueError):
    """The canonical state no longer permits this action."""


def _action(label, kinds, duration, *, relief=None, preference=None, thought=""):
    return {"label": label, "object_kinds": kinds, "duration": duration,
            "relief": relief or {}, "cost": 0, "preference": preference,
            "thought": thought}


POSSESSION_ACTIONS = {
    "fetch_pizza_ingredients": _action("Choosing pizza ingredients", ["fridge"], 120,
                                       thought="I have a pizza in mind."),
    "prep_pizza": _action("Preparing pizza", ["counter"], 480,
                          preference="cooking", thought="The dough and toppings are ready."),
    "load_pizza_oven": _action("Putting pizza in the oven", ["counter"], 90),
    "bake_pizza": _action("Baking pizza", ["counter"], 900,
                          preference="cooking", thought="The pizza smells wonderful."),
    "unload_pizza_oven": _action("Taking pizza from the oven", ["counter"], 90),
    "fetch_pancake_ingredients": _action("Choosing pancake ingredients", ["fridge"], 120),
    "prep_pancake": _action("Mixing pancake batter", ["counter"], 300,
                            preference="cooking"),
    "cook_pancake": _action("Cooking pancakes", ["counter"], 420,
                            preference="cooking"),
    "serve_recipe": _action("Carrying food to the table", ["table"], 90),
    "eat_recipe": _action("Eating a home-cooked meal", ["table"], 600,
                          relief={"hunger": .8, "comfort": .1}, preference="cooking"),
    "change_outfit": _action("Changing clothes", ["wardrobe", "bed"], 180,
                             thought="A fresh outfit for today."),
}

RECIPES = {
    "pizza": {"ingredients": ("dough", "tomato", "vegetable"),
              "steps": ("fetch_pizza_ingredients", "prep_pizza", "load_pizza_oven",
                        "bake_pizza", "unload_pizza_oven", "serve_recipe", "eat_recipe")},
    "pancake": {"ingredients": ("egg", "dough"),
                "steps": ("fetch_pancake_ingredients", "prep_pancake", "cook_pancake",
                          "serve_recipe", "eat_recipe")},
}

MAX_CONSUMED = 64


def _serial(actor):
    """Defend against a partially migrated record without reusing an item ID."""
    observed = []
    for item in actor.get("belongings", []):
        suffix = item.get("id", "").rsplit("_item_", 1)
        if len(suffix) == 2 and suffix[1].isdigit():
            observed.append(int(suffix[1]))
    return max([actor.get("possession_serial", 0), *observed])


def _location(place, identifier, slot=None):
    result = {"type": place, "id": identifier}
    if slot is not None:
        result["slot"] = slot
    return result


def _new(actor, items, serial, kind, label, location, state=None):
    serial += 1
    items.append({"id": f"{actor['id']}_item_{serial:03d}", "owner_id": actor["id"],
                  "kind": kind, "label": label, "location": location,
                  "state": deepcopy(state or {})})
    return items[-1], serial


def _held(items, kind=None):
    return next((item for item in items if item["location"]["type"] == "carried"
                 and (kind is None or item["kind"] == kind)), None)


def _at(items, place, identifier, kind=None):
    return next((item for item in items if item["location"]["type"] == place
                 and item["location"].get("id") == identifier
                 and (kind is None or item["kind"] == kind)), None)


def _required(items, predicate, message):
    item = next((i for i in items if predicate(i)), None)
    if item is None:
        raise PossessionUnavailable(message)
    return item


def _consume(item, now):
    item["location"] = _location("consumed", None)
    item["state"]["consumed_at"] = now


def _compact(items):
    consumed = [i for i in items if i["location"]["type"] == "consumed"]
    if len(consumed) <= MAX_CONSUMED:
        return items
    expired = {i["id"] for i in consumed[:-MAX_CONSUMED]}
    return [i for i in items if i["id"] not in expired]


def _patch(items, serial, state, inventory, outfit_last_day):
    return {"belongings": _compact(items), "possession_serial": serial,
            "object_daily": state, "inventory": inventory,
            "outfit_last_day": outfit_last_day}


def initialize(actor, now, wardrobe_id=None):
    """Create stable starting clothes; safe to call on an already migrated actor."""
    if "belongings" in actor:
        return {"belongings": deepcopy(actor["belongings"]),
                "possession_serial": _serial(actor),
                "outfit_last_day": actor.get("outfit_last_day")}
    items, serial = [], 0
    home = wardrobe_id or actor["home_id"]
    palette = (actor.get("appearance") or {}).get("shirt", "#849c83")
    suffix = actor["id"].rsplit("_", 1)[-1]
    palette_index = int(suffix) if suffix.isdigit() else sum((i + 1) * ord(ch) for i, ch in enumerate(actor["id"]))
    alternative_tops = ("#b97665", "#749791", "#c9a46b", "#8c84a0",
                        "#7f956a", "#a88378", "#648095", "#c19b7a")
    everyday_trousers = ("#465f68", "#5b655b", "#69617a", "#7a6c59",
                         "#536f72", "#665c62", "#626d50", "#52627a")
    alternative_trousers = ("#7c6b60", "#5c756e", "#5d657d", "#8d7856",
                            "#6e5c70", "#59685e", "#927366", "#637583")
    coats = ("#627b70", "#8f7569", "#6e7897", "#8e855e",
             "#7a6d84", "#597b83", "#9a775e", "#6e8569")
    jackets = ("#bd9875", "#7c9b8e", "#b08ca1", "#9d9070",
               "#7794a2", "#b58378", "#899e78", "#9c8caa")
    shoes = ("#50483e", "#5c554a", "#515c57", "#66594e")
    canvas_shoes = ("#b3aa85", "#9ea997", "#aaa0a1", "#c2a786")
    alt_top = alternative_tops[palette_index % len(alternative_tops)]
    if alt_top.lower() == palette.lower():
        alt_top = alternative_tops[(palette_index + 1) % len(alternative_tops)]
    clothes = (
        ("top", "Everyday top", palette, 1, True),
        ("top", "Weekend top", alt_top, 1, False),
        ("trousers", "Everyday trousers", everyday_trousers[palette_index % 8], 2, True),
        ("trousers", "Soft trousers", alternative_trousers[palette_index % 8], 2, False),
        ("shoes", "Walking shoes", shoes[palette_index % 4], 1, True),
        ("shoes", "Canvas shoes", canvas_shoes[palette_index % 4], 1, False),
        ("outerwear", "Warm coat", coats[palette_index % 8], 3, False),
        ("outerwear", "Light jacket", jackets[palette_index % 8], 2, False),
    )
    for kind, label, color, warmth, worn in clothes:
        loc = _location("worn", actor["id"], kind) if worn else _location("container", home)
        _, serial = _new(actor, items, serial, kind, label, loc,
                         {"color": color, "warmth": warmth, "acquired_at": now})
    return {"belongings": items, "possession_serial": serial, "outfit_last_day": None}


def worn_outfit(actor):
    """Small render/UI projection from the canonical clothing instances."""
    return {slot: {"id": i["id"], "kind": i["kind"], "label": i["label"],
                   "color": i.get("state", {}).get("color"),
                   "warmth": i.get("state", {}).get("warmth", 0)}
            for slot in ("top", "trousers", "shoes", "outerwear")
            for i in actor.get("belongings", [])
            if i["location"] == _location("worn", actor["id"], slot)}


def plan_outfit(actor, objects, now):
    """Use real clothes storage where available; old saves may still use a bed."""
    if actor.get("outfit_last_day") == int(now // 86400):
        return []
    target = _home_object(actor, objects, "wardrobe") or _home_object(actor, objects, "bed")
    return [{"kind": "change_outfit", "target_id": target["id"]}] if target else []


def _home_object(actor, objects, kind):
    values = objects.values() if isinstance(objects, dict) else objects
    return next((o for o in values if o["kind"] == kind
                 and o.get("household_id") == actor["household_id"]), None)


def _grocery_checkout(objects):
    values = objects.values() if isinstance(objects, dict) else objects
    stations = [o for o in values if o["kind"] in ("supermarket_checkout", "shop_counter")]
    stations.sort(key=lambda o: (o["kind"] != "supermarket_checkout", o["id"]))
    return stations[0] if stations else None


def plan(actor, objects, now, recipe=None):
    """Plan the next household meal, resuming the furthest concrete item stage."""
    recipe = recipe or ("pizza" if int(now // 86400) % 2 == 0 else "pancake")
    if recipe not in RECIPES:
        raise ValueError(f"Unknown recipe: {recipe}")
    fixtures = {kind: _home_object(actor, objects, kind)
                for kind in ("fridge", "counter", "table", "sink", "bin")}
    if any(fixtures[k] is None for k in ("fridge", "counter", "table")):
        return []
    items = actor.get("belongings", [])
    table, counter = fixtures["table"], fixtures["counter"]
    meal = next((i for i in items if i["kind"] in ("pizza", "pancake")
                 and i["location"]["type"] != "consumed"), None)
    if meal:
        recipe = meal["kind"]
    steps = list(RECIPES[recipe]["steps"])
    if meal:
        stage = meal.get("state", {}).get("stage")
        if meal["location"] == _location("container", table["id"]) and stage == "served":
            steps = ["eat_recipe"]
        elif meal["location"] == _location("carried", actor["id"]) and stage == "cooked":
            steps = ["serve_recipe", "eat_recipe"]
        elif meal["location"] == _location("container", counter["id"]) and stage == "baked":
            steps = ["unload_pizza_oven", "serve_recipe", "eat_recipe"]
        elif meal["location"] == _location("container", counter["id"]) and stage == "heating":
            steps = ["bake_pizza", "unload_pizza_oven", "serve_recipe", "eat_recipe"]
        elif meal["location"] == _location("carried", actor["id"]) and stage == "raw":
            steps = list(RECIPES[recipe]["steps"])[2:]
        elif meal["location"] == _location("carried", actor["id"]) and stage == "batter":
            steps = ["cook_pancake", "serve_recipe", "eat_recipe"]
    elif all(_held(items, k) for k in RECIPES[recipe]["ingredients"]):
        steps = steps[1:]
    if steps and steps[0] in ("fetch_pizza_ingredients", "fetch_pancake_ingredients"):
        missing = sum(_held(items, k) is None for k in RECIPES[recipe]["ingredients"])
        if daily_state(fixtures["fridge"])["pantry_stock"] < missing:
            checkout = _grocery_checkout(objects)
            if checkout is None:
                return []
            stock = [{"kind": "stock_fridge", "target_id": fixtures["fridge"]["id"]}]
            if actor.get("inventory", {}).get("groceries", 0) < 8:
                stock.insert(0, {"kind": "buy_groceries", "target_id": checkout["id"]})
            steps = stock + [{"kind": k, "target_id": fixtures[{
                "fetch_pizza_ingredients": "fridge", "fetch_pancake_ingredients": "fridge",
                "prep_pizza": "counter", "load_pizza_oven": "counter",
                "bake_pizza": "counter", "unload_pizza_oven": "counter",
                "prep_pancake": "counter", "cook_pancake": "counter",
                "serve_recipe": "table", "eat_recipe": "table"}[k]]["id"]} for k in steps]
            result = steps
            for action, fixture in (("clear_dishes", "table"), ("wash_dishes", "sink"),
                                    ("bin_trash", "bin"), ("wipe_counter", "counter")):
                if fixtures[fixture] is not None:
                    result.append({"kind": action, "target_id": fixtures[fixture]["id"]})
            return result
    target_kind = {"fetch_pizza_ingredients": "fridge", "fetch_pancake_ingredients": "fridge",
                   "prep_pizza": "counter", "load_pizza_oven": "counter",
                   "bake_pizza": "counter", "unload_pizza_oven": "counter",
                   "prep_pancake": "counter", "cook_pancake": "counter",
                   "serve_recipe": "table", "eat_recipe": "table"}
    result = [{"kind": k, "target_id": fixtures[target_kind[k]]["id"]} for k in steps]
    for action, fixture in (("clear_dishes", "table"), ("wash_dishes", "sink"),
                            ("bin_trash", "bin"), ("wipe_counter", "counter")):
        if fixtures[fixture] is not None:
            result.append({"kind": action, "target_id": fixtures[fixture]["id"]})
    return result


def apply_step(actor, obj, kind, now):
    """Return full patches for a completed, precondition-valid concrete step."""
    definition = POSSESSION_ACTIONS.get(kind)
    if definition is None or obj["kind"] not in definition["object_kinds"]:
        raise PossessionUnavailable(f"Invalid {kind} target")
    if obj.get("household_id") != actor.get("household_id"):
        raise PossessionUnavailable("Not this household's fixture")
    items = deepcopy(actor.get("belongings", []))
    serial = _serial(actor)
    inventory = deepcopy(actor.get("inventory", {}))
    state = daily_state(obj)
    last_day = actor.get("outfit_last_day")
    aid, oid = actor["id"], obj["id"]
    if kind in ("fetch_pizza_ingredients", "fetch_pancake_ingredients"):
        recipe = "pizza" if "pizza" in kind else "pancake"
        missing = [k for k in RECIPES[recipe]["ingredients"] if not _held(items, k)]
        if not missing or state["pantry_stock"] < len(missing):
            raise PossessionUnavailable("Ingredients unavailable or already carried")
        for ingredient in missing:
            _, serial = _new(actor, items, serial, ingredient, ingredient.title(),
                             _location("carried", aid), {"fresh": True})
        state["pantry_stock"] -= len(missing)
    elif kind in ("prep_pizza", "prep_pancake"):
        recipe = "pizza" if kind == "prep_pizza" else "pancake"
        ingredients = [_required(items, lambda i, k=k: i["kind"] == k
                                 and i["location"] == _location("carried", aid),
                                 f"Missing {k}") for k in RECIPES[recipe]["ingredients"]]
        for ingredient in ingredients:
            _consume(ingredient, now)
        _, serial = _new(actor, items, serial, recipe, recipe.title(),
                         _location("carried", aid),
                         {"stage": "raw" if recipe == "pizza" else "batter", "prepared_at": now})
        state["mess"] += 1
        inventory["food_scraps"] = inventory.get("food_scraps", 0) + 1
    elif kind == "load_pizza_oven":
        meal = _required(items, lambda i: i["kind"] == "pizza"
                         and i["location"] == _location("carried", aid)
                         and i["state"].get("stage") == "raw", "No raw pizza to load")
        if state.get("oven_item_id"):
            raise PossessionUnavailable("Oven is occupied")
        meal["location"] = _location("container", oid)
        meal["state"].update(stage="heating", ready_at=now + POSSESSION_ACTIONS["bake_pizza"]["duration"])
        state["oven_item_id"] = meal["id"]
    elif kind == "bake_pizza":
        meal = _required(items, lambda i: i["id"] == state.get("oven_item_id")
                         and i["location"] == _location("container", oid)
                         and i["state"].get("stage") == "heating", "No pizza in oven")
        if now < meal["state"]["ready_at"]:
            raise PossessionUnavailable("Pizza needs more oven time")
        meal["state"].update(stage="baked", baked_at=now)
    elif kind == "unload_pizza_oven":
        meal = _required(items, lambda i: i["id"] == state.get("oven_item_id")
                         and i["location"] == _location("container", oid)
                         and i["state"].get("stage") == "baked", "Pizza is not baked")
        meal["location"] = _location("carried", aid)
        meal["state"]["stage"] = "cooked"
        state.pop("oven_item_id", None)
    elif kind == "cook_pancake":
        meal = _required(items, lambda i: i["kind"] == "pancake"
                         and i["location"] == _location("carried", aid)
                         and i["state"].get("stage") == "batter", "No pancake batter")
        meal["state"].update(stage="cooked", cooked_at=now)
    elif kind == "serve_recipe":
        meal = _required(items, lambda i: i["kind"] in RECIPES
                         and i["location"] == _location("carried", aid)
                         and i["state"].get("stage") == "cooked", "No cooked meal carried")
        if state["served_meals"] >= 3:
            raise PossessionUnavailable("Table is full")
        meal["location"] = _location("container", oid)
        meal["state"].update(stage="served", served_at=now)
        state["served_meals"] += 1
    elif kind == "eat_recipe":
        meal = _required(items, lambda i: i["kind"] in RECIPES
                         and i["location"] == _location("container", oid)
                         and i["state"].get("stage") == "served", "No own served meal")
        if state["served_meals"] < 1:
            raise PossessionUnavailable("Table count and item disagree")
        _consume(meal, now)
        state["served_meals"] -= 1
        state["dirty_dishes"] += 1
        _, serial = _new(actor, items, serial, "dirty_dish", "Used plate",
                         _location("container", oid), {"from_meal_id": meal["id"]})
    elif kind == "change_outfit":
        day = int(now // 86400)
        if last_day == day:
            raise PossessionUnavailable("Already changed today")
        storage_id = oid if obj["kind"] == "wardrobe" and any(
            item["location"] == _location("container", oid) for item in items) else actor["home_id"]
        for slot in ("top", "trousers", "shoes", "outerwear"):
            stored = [i for i in items if i["kind"] == slot
                      and i["location"] == _location("container", storage_id)]
            worn = [i for i in items if i["kind"] == slot
                    and i["location"] == _location("worn", aid, slot)]
            if slot == "outerwear":
                if day % 2 == 0 and not worn and stored:
                    stored[0]["location"] = _location("worn", aid, slot)
                elif day % 2 == 1 and worn:
                    worn[0]["location"] = _location("container", storage_id)
            elif stored:
                if worn:
                    worn[0]["location"] = _location("container", storage_id)
                stored[0]["location"] = _location("worn", aid, slot)
        last_day = day
    return _patch(items, serial, state, inventory, last_day)


def step_available(actor, obj, kind, now, completion=False):
    """Pure preflight; oven action starts only when it can finish ready."""
    check_at = now
    if kind == "bake_pizza" and not completion:
        check_at += POSSESSION_ACTIONS[kind]["duration"]
    try:
        apply_step(actor, obj, kind, check_at)
    except PossessionUnavailable:
        return False
    return True


def synchronize_cleanup(actor, obj, kind, now):
    """Mirror legacy dish cleaning into item locations, without touching counts.

    Call on the actor after the legacy completion has changed generic inventory
    and object.daily. Only this actor's dishes can be reconciled here.
    """
    items = deepcopy(actor.get("belongings", []))
    if kind == "clear_dishes" and obj["kind"] == "table":
        dish = _at(items, "container", obj["id"], "dirty_dish")
        if dish:
            dish["location"] = _location("carried", actor["id"])
    elif kind == "wash_dishes" and obj["kind"] == "sink":
        for item in items:
            if item["kind"] == "dirty_dish" and item["location"] == _location("carried", actor["id"]):
                _consume(item, now)
    else:
        raise PossessionUnavailable("Cleanup adapter only supports dish steps")
    return {"belongings": _compact(items), "possession_serial": _serial(actor)}
