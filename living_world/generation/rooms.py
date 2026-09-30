"""Bounded, seeded constraint search with relational furniture groups.

Hard constraints never become soft penalties. A failed search is a rejected
design, not an attractive but inaccessible fallback room.
"""
from collections import Counter, deque
from copy import deepcopy
import hashlib
import json
import random

from . import GENERATOR_VERSION
from .catalog import CATALOG, ROOMS, STYLES, placed


class GenerationError(ValueError):
    pass


def cells(obj):
    return {(x, y) for y in range(obj["y"], obj["y"] + obj["h"]) for x in range(obj["x"], obj["x"] + obj["w"])}


def flood(width, height, occupied, start):
    start = tuple(start)
    if start in occupied or not (0 <= start[0] < width and 0 <= start[1] < height):
        return set()
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for p in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= p[0] < width and 0 <= p[1] < height and p not in occupied and p not in seen:
                seen.add(p)
                queue.append(p)
    return seen


def validate_room(room, *, object_catalog=None):
    """Independent final validator, also suitable for edited/imported plans."""
    catalog = CATALOG if object_catalog is None else object_catalog
    w, h = room["width"], room["height"]
    errors = []
    occupied = set()
    protected = {tuple(p) for p in room["protected"]}
    windows = {tuple(p) for window in room["windows"] for p in window["cells"]}
    for obj in room["objects"]:
        if obj["kind"] not in catalog or obj["orientation"] not in range(4):
            errors.append(f"unknown_geometry:{obj['id']}")
            continue
        canonical = placed(obj["kind"], obj["x"], obj["y"], obj["orientation"], object_catalog=catalog)
        if any(obj.get(k) != canonical[k] for k in ("w", "h", "base_w", "base_h", "clearance", "anchors", "tall")):
            errors.append(f"geometry_contract:{obj['id']}")
        if catalog[obj["kind"]].wall and not [obj["y"] == 0, obj["x"] + obj["w"] == w, obj["y"] + obj["h"] == h, obj["x"] == 0][obj["orientation"]]:
            errors.append(f"wall_alignment:{obj['id']}")
        footprint = cells(obj)
        if any(not (0 <= x < w and 0 <= y < h) for x, y in footprint):
            errors.append(f"outside:{obj['id']}")
        if footprint & occupied:
            errors.append(f"overlap:{obj['id']}")
        if footprint & protected:
            errors.append(f"protected_zone:{obj['id']}")
        if obj["tall"] and footprint & windows:
            errors.append(f"window_blocked:{obj['id']}")
        occupied |= footprint
    reachable = flood(w, h, occupied, room["doors"][0]["cell"])
    for door in room["doors"]:
        if tuple(door["cell"]) not in reachable:
            errors.append("door_unreachable")
    for obj in room["objects"]:
        for anchor in obj["clearance"]:
            if tuple(anchor) not in reachable:
                errors.append(f"clearance_unreachable:{obj['id']}")
    if len(reachable) != w * h - len(occupied):
        errors.append("disconnected_free_floor")
    if Counter(room["required_kinds"]) - Counter(o["kind"] for o in room["objects"]):
        errors.append("required_furniture_missing")
    if room["kind"] == "school_classroom":
        desks = [o for o in room["objects"] if o["kind"] == "school_student_desk"]
        chairs = [o for o in room["objects"] if o["kind"] == "school_student_chair"]
        paired = all(any(chair["x"] == desk["x"] + 1 and chair["y"] == desk["y"]
                         for chair in chairs) for desk in desks)
        if not 20 <= len(desks) <= 25 or len(chairs) != len(desks) or not paired:
            errors.append("classroom_seating_invalid")
        if room.get("capacity", {}).get("students") != len(desks):
            errors.append("classroom_capacity_mismatch")
    sofa = next((o for o in room["objects"] if o["kind"] == "sofa"), None)
    coffee = next((o for o in room["objects"] if o["kind"] == "coffee_table"), None)
    tv = next((o for o in room["objects"] if o["kind"] == "tv"), None)
    if sofa and coffee and not coffee_in_front(sofa, coffee):
        errors.append("coffee_table_not_in_front_of_sofa")
    if sofa and tv and not facing(sofa, tv):
        errors.append("tv_not_facing_sofa")
    if room["kind"] == "living" and coffee:
        for chair in (o for o in room["objects"] if o["kind"] == "armchair"):
            if not chair_faces_table(chair, coffee):
                errors.append("armchair_not_facing_seating_group")
    return {"valid": not errors, "errors": sorted(set(errors)), "walkable_cells": len(reachable),
            "occupied_cells": len(occupied), "usable_anchors": sum(len(o["anchors"]) for o in room["objects"]),
            "free_fraction": round(len(reachable) / (w * h), 3), "reachable_cells": [list(p) for p in sorted(reachable)]}


def center(obj):
    return obj["x"] + obj["w"] / 2, obj["y"] + obj["h"] / 2


def local_offset(base, other):
    bx, by = center(base)
    ox, oy = center(other)
    dx, dy = ox - bx, oy - by
    q = base["orientation"]
    return [(dx, dy), (dy, -dx), (-dx, -dy), (-dy, dx)][q]


def coffee_in_front(sofa, table):
    lateral, forward = local_offset(sofa, table)
    return table["orientation"] == sofa["orientation"] and abs(lateral) <= 1 and forward == 2


def facing(sofa, tv):
    lateral, forward = local_offset(sofa, tv)
    return tv["orientation"] == (sofa["orientation"] + 2) % 4 and abs(lateral) <= 1.5 and 4 <= forward <= 9


def chair_faces_table(chair, table):
    lateral, forward = local_offset(chair, table)
    return abs(lateral) <= 2 and 1.5 <= forward <= 4


def layout_signature(room):
    data = [room["kind"], room["width"], room["height"],
            sorted((o["kind"], o["x"], o["y"], o["orientation"]) for o in room["objects"])]
    return hashlib.sha256(json.dumps(data).encode()).hexdigest()[:16]


def _populate_classroom(room, catalog):
    """Four pupil groups with a continuous central aisle and real seats."""
    width, height = room["width"], room["height"]
    reverse = room["doors"][0]["side"] == "north"
    rows = 6 if height >= 14 else 5
    # The lesson front is opposite a north corridor door. Keep two central
    # columns clear between desks all the way from the doorway to the board.
    front_y = height - 1 if reverse else 0
    teacher_y = height - 2 if reverse else 1
    board = placed("school_chalkboard", 4, front_y, 2 if reverse else 0, object_catalog=catalog)
    teacher = placed("school_teacher_desk", 5, teacher_y, 2 if reverse else 0, object_catalog=catalog)
    objects = [board, teacher]
    for row in range(rows):
        y = height - 3 - 2 * row if reverse else 2 + 2 * row
        for x in (1, 3, 7, 9):
            objects.append(placed("school_student_desk", x, y, 2 if reverse else 0, object_catalog=catalog))
            objects.append(placed("school_student_chair", x + 1, y, 0 if reverse else 2, object_catalog=catalog))
    room["objects"] = objects
    room["required_kinds"] = [o["kind"] for o in objects]
    room["capacity"] = {"students": rows * 4, "seats": rows * 4, "teachers": 1}
    room["seating_layout"] = {"columns": 4, "rows": rows, "central_aisle_columns": [5, 6]}
    room["search"] = {"nodes": 0, "candidates": len(objects), "method": "classroom_rows"}
    return room


def generate_room(kind="living", seed=42, width=None, height=None, door_side="south", style=None, outside_sides=None, door_offset=None, *, object_catalog=None, room_catalog=None):
    catalog = CATALOG if object_catalog is None else object_catalog
    room_specs = ROOMS if room_catalog is None else room_catalog
    if kind not in room_specs:
        raise GenerationError(f"Unknown room type: {kind}")
    spec = room_specs[kind]
    width, height = width or spec["size"][0], height or spec["size"][1]
    if not (spec["minimum"][0] <= width <= 14 and spec["minimum"][1] <= height <= 14):
        raise GenerationError(f"{spec['name']} requires at least {spec['minimum'][0]} × {spec['minimum'][1]} m; maximum is 14 × 14 m")
    if door_side not in ("north", "east", "south", "west"):
        raise GenerationError("Unknown door side")
    if style is not None and style not in STYLES:
        raise GenerationError("Unknown palette")
    rng = random.Random(f"{GENERATOR_VERSION}:{kind}:{seed}:{width}:{height}:{door_side}")
    style = style or rng.choice(list(STYLES))
    family = rng.choice(spec["families"])
    side_index = rng.choice([max(1, width // 2 - 1), min(width - 2, width // 2 + 1)])
    vertical_index = rng.choice([max(1, height // 2 - 1), min(height - 2, height // 2 + 1)])
    if door_offset is not None:
        limit = width if door_side in ("north", "south") else height
        if not 1 <= door_offset <= limit - 2:
            raise GenerationError("Door offset must leave a wall cell at each corner")
        side_index = vertical_index = door_offset
    elif kind == "school_classroom":
        side_index = 5
        vertical_index = 3
    door = {"north": [side_index, 0], "south": [side_index, height - 1],
            "east": [width - 1, vertical_index], "west": [0, vertical_index]}[door_side]
    inward = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}[door_side]
    protected = {tuple(door), (door[0] + inward[0], door[1] + inward[1])}
    zones = [{"name": "Freier Türbereich", "cells": [list(p) for p in sorted(protected)], "reason": "Tür und Eintritt bleiben frei"}]
    free_zones = {"child": (2, "Spielfläche"), "party": (3, "Tanzfläche"),
                  "nursery": (2, "Freie Krabbelfläche"), "gym": (2, "Bewegungsfläche"),
                  "music": (2, "Freie Probefläche"), "workshop": (2, "Freie Arbeitsfläche")}
    if kind in free_zones:
        size, zone_name = free_zones[kind]
        play = {(width // 2 - 1 + x, height // 2 - 1 + y) for x in range(size) for y in range(size)}
        protected |= play
        zones.append({"name": zone_name, "cells": [list(p) for p in sorted(play)], "reason": "Zusammenhängende Nutzungsfläche, nicht nur freie Restzellen"})
    if kind == "hall":
        for y in range(height):
            protected.add((width // 2, y))
        zones.append({"name": "Durchgang", "cells": [[width // 2, y] for y in range(height)], "reason": "Ein Meter freie Durchgangsbreite"})
    window_sides = outside_sides if outside_sides is not None else [side for side in ("north", "east", "south", "west") if side != door_side]
    if any(side not in ("north", "east", "south", "west") for side in window_sides):
        raise GenerationError("Unknown exterior window side")
    window_side = rng.choice(window_sides) if window_sides else None
    if window_side is None:
        window_cells = []
    elif window_side in ("north", "south"):
        wx = rng.randrange(1, width - 2)
        window_cells = [[wx + i, 0 if window_side == "north" else height - 1] for i in range(2)]
    else:
        wy = rng.randrange(1, height - 2)
        window_cells = [[0 if window_side == "west" else width - 1, wy + i] for i in range(2)]
    window_cells = [p for p in window_cells if tuple(p) not in protected]
    required = list(spec.get("programs", {}).get(family, spec["required"]))
    room = {"id": f"{kind}-{seed}", "kind": kind, "name": spec["name"], "seed": seed, "generator_version": GENERATOR_VERSION,
            "width": width, "height": height, "cell_size_m": 1, "family": family, "style": style,
            "palette": STYLES[style], "doors": [{"side": door_side, "cell": door}],
            "windows": [{"side": window_side, "cells": window_cells}] if window_cells else [], "protected": [list(p) for p in sorted(protected)],
            "zones": zones, "objects": [], "required_kinds": required, "omitted": [], "trace": [], "search": {"nodes": 0, "candidates": 0}}
    if kind == "school_classroom":
        _populate_classroom(room, catalog)
        for i, obj in enumerate(room["objects"]):
            obj.update(id=f"{room['id']}:object:{i:02}", floor=0, required=True,
                       reason="Fester Unterrichtsplatz mit freiem Zugang")
        room["trace"] = [f"{room['capacity']['students']} wirkliche Tisch-Stuhl-Paare in vier Spalten",
                         "Mittlerer Gang und Bedienflächen bleiben erreichbar"]
        room["validation"] = validate_room(room, object_catalog=catalog)
        if not room["validation"]["valid"]:
            raise GenerationError("Classroom geometry rejected: " + ", ".join(room["validation"]["errors"]))
        room["signature"] = layout_signature(room)
        return room
    raw_candidates = {}
    # Stable ordering matters across Python processes (hash randomization).
    for furniture in sorted(set(required + spec["optional"])):
        definition = catalog[furniture]
        options = []
        for q in range(4):
            rw, rh = (definition.h, definition.w) if q % 2 else (definition.w, definition.h)
            for y in range(height - rh + 1):
                for x in range(width - rw + 1):
                    if definition.wall and not [y == 0, x + rw == width, y + rh == height, x == 0][q]:
                        continue
                    obj = placed(furniture, x, y, q, object_catalog=catalog)
                    footprint = cells(obj)
                    if footprint & protected or (definition.tall and footprint & {tuple(p) for p in window_cells}):
                        continue
                    if any(not (0 <= xx < width and 0 <= yy < height) for xx, yy in obj["clearance"]):
                        continue
                    score = rng.random() * 2
                    if furniture in ("desk", "office_desk", "gaming_desk", "easel", "sewing_table", "plant_shelf", "potting_bench"):
                        score -= min((abs(x - xx) + abs(y - yy) for xx, yy in window_cells), default=0) * .13
                    if furniture in ("plant", "floor_lamp"):
                        score += .7 if x in (0, width - rw) and y in (0, height - rh) else 0
                    obj["placement_score"] = round(score, 4)
                    options.append(obj)
        raw_candidates[furniture] = sorted(options, key=lambda o: -o["placement_score"])
        room["search"]["candidates"] += len(options)

    def feasible(obj, existing):
        footprint = cells(obj)
        occupied = set().union(*(cells(o) for o in existing)) if existing else set()
        clearance = {tuple(p) for o in existing for p in o["clearance"]}
        if footprint & (occupied | clearance) or {tuple(p) for p in obj["clearance"]} & occupied:
            return False
        occupied |= footprint
        reachable = flood(width, height, occupied, door)
        return len(reachable) == width * height - len(occupied) and all(tuple(p) in reachable for o in existing + [obj] for p in o["clearance"])

    def candidates_for(furniture, existing):
        candidates = raw_candidates[furniture]
        sofa = next((o for o in existing if o["kind"] == "sofa"), None)
        if furniture == "coffee_table" and sofa:
            candidates = [o for o in candidates if coffee_in_front(sofa, o)]
        if furniture == "tv" and sofa:
            candidates = [o for o in candidates if facing(sofa, o)]
        coffee = next((o for o in existing if o["kind"] == "coffee_table"), None)
        if furniture == "armchair" and coffee and kind == "living":
            candidates = [o for o in candidates if chair_faces_table(o, coffee)]
        bed = next((o for o in existing if o["kind"] in ("single_bed", "double_bed", "hospital_bed") or o["kind"].startswith("bed_")), None)
        if furniture == "side_table" and bed:
            candidates = sorted(candidates, key=lambda o: min(abs(x - a) + abs(y - b) for x, y in cells(o) for a, b in cells(bed)) - o["placement_score"] * .2)
        near_groups = {"dryer": ("washing_machine",), "laundry_basket": ("washing_machine", "changing_table"),
                       "printer_stand": ("office_desk", "desk"), "filing_cabinet": ("office_desk",),
                       "changing_table": ("crib",), "baby_storage": ("changing_table",),
                       "rocking_chair": ("crib",), "tool_cabinet": ("workbench",),
                       "towel_rack": ("shower", "bathtub", "utility_sink"), "buffet": ("large_dining_table", "dining_table"),
                       "armchair": ("bookshelf",) if kind == "library" else (),
                       "planter_box": ("plant_shelf", "potting_bench")}
        related = [o for o in existing if o["kind"] in near_groups.get(furniture, ())]
        if related:
            candidates = sorted(candidates, key=lambda o: min(abs(center(o)[0]-center(a)[0])+abs(center(o)[1]-center(a)[1]) for a in related)-o["placement_score"]*.3)
        if furniture in ("sink", "stove", "counter", "dishwasher", "coffee_station", "microwave_cart") and kind == "kitchen" and existing:
            # A compact working run is a preference, not a hard adjacency rule.
            appliances = [o for o in existing if o["kind"] in ("fridge", "sink", "stove", "counter")]
            if appliances:
                candidates = sorted(candidates, key=lambda o: min(abs(center(o)[0] - center(a)[0]) + abs(center(o)[1] - center(a)[1]) for a in appliances) - o["placement_score"] * .15)
        return candidates

    def search(index, existing):
        if index == len(required):
            return existing
        if room["search"]["nodes"] >= 2400:
            return None
        furniture = required[index]
        for obj in candidates_for(furniture, existing)[:180]:
            if room["search"]["nodes"] >= 2400:
                return None
            room["search"]["nodes"] += 1
            if feasible(obj, existing):
                found = search(index + 1, existing + [obj])
                if found is not None:
                    return found
        return None

    objects = search(0, [])
    if objects is None:
        raise GenerationError(f"No valid {kind} room for seed {seed} within the search budget; reduce furniture or enlarge the room")
    optional = [k for k in spec["optional"] if k not in required]
    rng.shuffle(optional)
    # More authorable objects can produce richer rooms, but clearance and the
    # occupancy cap still win over decoration. Tiny optional lists remain legal.
    budget = rng.randint(min(3, len(optional)), min(6, len(optional)))
    for furniture in optional:
        if budget <= 0:
            room["omitted"].append({"kind": furniture, "reason": "Gestalterisches Dichtebudget erreicht"})
            continue
        candidate = next((o for o in candidates_for(furniture, objects) if feasible(o, objects)), None)
        if candidate is not None and sum(o["w"] * o["h"] for o in objects + [candidate]) <= width * height * .43:
            objects.append(candidate)
            budget -= 1
        else:
            room["omitted"].append({"kind": furniture, "reason": "Kein freier Platz mit erreichbarem Bedienbereich"})
    room["objects"] = deepcopy(objects)
    for i, obj in enumerate(room["objects"]):
        obj["id"] = f"{room['id']}:object:{i:02}"
        obj["floor"] = 0
        obj["required"] = obj["kind"] in required
        obj["reason"] = "Funktionsmöbel des Raumprogramms" if obj["required"] else "Optionale Ergänzung innerhalb von Laufwegen und Dichtebudget"
    room["trace"] = [f"Raumprogramm: {family}", f"{len(protected)} Zellen für Eintritt und freie Nutzung geschützt",
                     "Pflichtmöbel zuerst, Dekoration zuletzt", "Bedienflächen und alle freien Zellen per Flood-Fill geprüft",
                     f"{len(room['objects'])} Möbel, {len(room['omitted'])} optionale Möbel bewusst ausgelassen"]
    room["validation"] = validate_room(room, object_catalog=catalog)
    if not room["validation"]["valid"]:
        raise GenerationError("Final validation rejected design: " + ", ".join(room["validation"]["errors"]))
    room["signature"] = layout_signature(room)
    return room
