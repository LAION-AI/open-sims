"""Parameterized rectangular building plans built from the shared room generator.

Coordinates use one metre cells. Floor ``level`` remains the navigation index
(0..n-1); ``elevation`` identifies the storey relative to grade.
"""
from copy import deepcopy
import math
import random

from . import GENERATOR_VERSION
from .catalog import ROOMS, STYLES, ROOM_AREA_TARGETS
from .bed_variants import BED_CAPACITIES
from .civic_catalog import BUILDING_TEMPLATES
from .rooms import GenerationError, generate_room


BED_CAPACITY = {"double_bed": 2, "single_bed": 1, "crib": 1,
                "hospital_bed": 1, "bed_hospital": 1, **BED_CAPACITIES}


def _room_capacity(kind, catalog):
    spec = catalog[kind]
    alternatives = [spec.get("required", [])] + list(spec.get("programs", {}).values())
    return max((sum(BED_CAPACITY.get(item, 0) for item in alternative)
                for alternative in alternatives), default=0)


def _area_budget(kind, catalog):
    spec = catalog[kind]
    minimum = spec["minimum"][0] * spec["minimum"][1]
    return ROOM_AREA_TARGETS.get(kind, (minimum, spec["size"][0] * spec["size"][1],
                                        min(196, max(minimum, spec["size"][0] * spec["size"][1] + 14))))


def _expanded_widths(group, available, catalog, heights):
    widths = [catalog[k]["minimum"][0] for k in group]
    room_area_width = max(0, available - max(0, len(widths) - 1))
    if sum(widths) > room_area_width:
        raise GenerationError("Room minima exceed the available row width")
    targets = []
    for kind, height in zip(group, heights):
        _, target, maximum = _area_budget(kind, catalog)
        targets.append(min(14, max(widths[len(targets)],
                                   min(maximum // height, math.ceil(target / height)))))
    remaining = room_area_width - sum(widths)
    while remaining:
        candidates = [i for i, value in enumerate(widths) if value < targets[i]]
        if not candidates:
            break
        i = max(candidates, key=lambda index: ((targets[index] - widths[index]) / targets[index], -index))
        widths[i] += 1
        remaining -= 1
    return widths


def _positive_int(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise GenerationError(f"{name} must be an integer of at least {minimum}")
    return value


def _program(request, room_count, residents, room_catalog):
    catalog = ROOMS if room_catalog is None else room_catalog
    adults, children, teens = (residents[k] for k in ("adults", "children", "teens"))
    required = ["bedroom"] * math.ceil(adults / 2) + ["child"] * children + ["teen"] * teens
    if "room_program" in request and request["room_program"] is not None:
        result = request["room_program"]
        if not isinstance(result, list) or len(result) != room_count:
            raise GenerationError("room_program must be a list with exactly room_count entries")
        if any(not isinstance(k, str) or k not in catalog for k in result):
            bad = next((k for k in result if not isinstance(k, str) or k not in catalog), None)
            raise GenerationError(f"Unsupported room type in room_program: {bad}")
        program = list(result)
    else:
        common = ["living", "kitchen", "bathroom"]
        if any(residents.values()) and room_count < len(required) + len(common):
            raise GenerationError(
                f"room_count {room_count} cannot provide {len(required)} sleeping rooms plus living, kitchen, and bathroom"
            )
        if len(required) > room_count:
            raise GenerationError(f"room_count {room_count} cannot provide {len(required)} required sleeping rooms")
        program = common[:min(room_count, len(common))] + list(required)
        fillers = ["laundry", "pantry", "workshop", "office", "library", "gym"]
        while len(program) < room_count:
            program.append(fillers[(len(program) - len(common) - len(required)) % len(fillers)])
    unsupported = [kind for kind in program if kind not in catalog]
    if unsupported:
        raise GenerationError(f"Unsupported room type in generated program: {unsupported[0]}")
    if any(residents.values()):
        missing_common = [kind for kind in ("living", "kitchen", "bathroom") if kind not in program]
        if missing_common:
            raise GenerationError("Residential room_program must include living, kitchen, and bathroom")
    adults_capacity = sum(_room_capacity(k, catalog) for k in program if k in ("bedroom", "guest"))
    child_capacity = sum(_room_capacity(k, catalog) for k in program if k in ("child", "nursery"))
    teen_capacity = sum(_room_capacity(k, catalog) for k in program if k == "teen")
    if adults_capacity < adults or child_capacity < children or teen_capacity < teens:
        raise GenerationError(
            "room_program has insufficient typed sleep capacity "
            f"(adults {adults_capacity}/{adults}, children {child_capacity}/{children}, teens {teen_capacity}/{teens})"
        )
    return program


def _partition(program, width, depth, catalog):
    """Find a contiguous one- or two-sided room arrangement without resizing."""
    # Reserve the east end of the corridor for the stacked shafts and their
    # landing. Room doors therefore cannot open into a stair/lift footprint.
    inner_w = width - 6
    choices = []
    for split in range(len(program) + 1):
        groups = [program[:split], program[split:]]
        nonempty = [g for g in groups if g]
        if len(nonempty) > 1 and depth < 2 * 5 + 4 + 2:
            continue
        row_widths = []
        feasible = True
        for group in nonempty:
            minima = [catalog[k]["minimum"] for k in group]
            used = sum(x for x, _ in minima) + len(group) - 1
            if used > inner_w or max(x for x, _ in minima) > 14 or max(y for _, y in minima) > 14:
                feasible = False
                break
            row_widths.append(used)
        if not feasible:
            continue
        upper_h = max((catalog[k]["minimum"][1] for k in groups[0]), default=0)
        lower_h = max((catalog[k]["minimum"][1] for k in groups[1]), default=0)
        need = upper_h + lower_h + 4 + 2
        if need > depth:
            continue
        # Minimize vertical asymmetry, then horizontal unused width.
        choices.append((abs(len(groups[0]) - len(groups[1])), sum(row_widths), -split,
                        groups, upper_h, lower_h))
    if not choices:
        minima = {k: catalog[k]["minimum"] for k in sorted(set(program))}
        raise GenerationError(f"Footprint {width}x{depth} cannot fit room minima and circulation: {minima}")
    _, _, _, groups, upper_h, lower_h = min(choices)
    return groups, upper_h, lower_h


def generate_building(request: dict, *, object_catalog=None, room_catalog=None):
    """Generate a connected multi-level house from an explicit rectangular brief.

    Required fields: ``width``, ``depth``, ``room_count``,
    ``levels_above_ground``, ``basements``, and ``residents``. The resident
    mapping has integer ``adults``, ``children`` and ``teens`` counts.
    """
    if not isinstance(request, dict):
        raise GenerationError("request must be a dictionary")
    allowed = {"width", "depth", "room_count", "levels_above_ground", "basements",
               "residents", "seed", "style", "elevator", "terrace_exit", "room_program"}
    unknown = sorted(set(request) - allowed)
    if unknown:
        raise GenerationError(f"Unknown request fields: {', '.join(unknown)}")
    width = _positive_int(request.get("width"), "width", 12)
    depth = _positive_int(request.get("depth"), "depth", 10)
    room_count = _positive_int(request.get("room_count"), "room_count", 1)
    above = _positive_int(request.get("levels_above_ground"), "levels_above_ground", 1)
    basements = _positive_int(request.get("basements", 0), "basements", 0)
    if above > 5 or basements > 1:
        raise GenerationError("Supported range is 1-5 above-ground levels and 0-1 basement")
    if width > 80 or depth > 80:
        raise GenerationError("Footprints are limited to 80x80 metres")
    if room_count > 40:
        raise GenerationError("room_count is limited to 40 rooms")
    residents = request.get("residents")
    if not isinstance(residents, dict) or any(k not in residents for k in ("adults", "children", "teens")):
        raise GenerationError("residents must provide adults, children, and teens counts")
    if set(residents) != {"adults", "children", "teens"}:
        raise GenerationError("residents may contain only adults, children, and teens")
    residents = {k: _positive_int(residents[k], f"residents.{k}") for k in ("adults", "children", "teens")}
    if sum(residents.values()) > 64:
        raise GenerationError("Resident counts are limited to 64 people")
    catalog = ROOMS if room_catalog is None else room_catalog
    program = _program(request, room_count, residents, catalog)
    template = next((spec for spec in BUILDING_TEMPLATES.values()
                     if program == spec["room_program"]), None)
    levels = above + basements
    ground = basements
    # Room count is a building total. Put utilities in the cellar, shared rooms
    # on grade, and sleeping rooms above grade whenever an upper floor exists.
    programs_by_floor = [[] for _ in range(levels)]
    basement_kinds = {"laundry", "pantry", "workshop"}
    common_kinds = {"living", "kitchen", "bathroom", "hall"}
    sleeping_kinds = {"bedroom", "child", "teen", "guest", "nursery"}
    leftovers = []
    for kind in program:
        if basements and kind in basement_kinds:
            programs_by_floor[0].append(kind)
        elif kind in common_kinds:
            programs_by_floor[ground].append(kind)
        else:
            leftovers.append(kind)
    # Keep a useful service room on grade. This also avoids a largely empty
    # ground floor for small family programs; upper floors retain bedrooms.
    grade_target = max(4, math.ceil(len(program) / above))
    while len(programs_by_floor[ground]) < grade_target:
        i = next((i for i, kind in enumerate(leftovers) if kind not in sleeping_kinds), None)
        if i is None:
            break
        programs_by_floor[ground].append(leftovers.pop(i))
    upper_levels = list(range(ground + 1, levels)) or [ground]
    for i, kind in enumerate(leftovers):
        programs_by_floor[upper_levels[i % len(upper_levels)]].append(kind)
    layouts = [_partition(kinds, width, depth, catalog) if kinds else ([[], []], 0, 0)
               for kinds in programs_by_floor]
    upper_h = max((layout[1] for layout in layouts), default=0)
    lower_h = max((layout[2] for layout in layouts), default=0)
    desired_heights = [max((min(14, catalog[k]["size"][1]) for groups, _, _ in layouts
                            for k in groups[side]), default=0) for side in (0, 1)]
    extra_height = max(0, depth - 6 - upper_h - lower_h)
    while extra_height:
        sides = [side for side, height in enumerate((upper_h, lower_h))
                 if height and height < desired_heights[side]]
        if not sides:
            break
        side = min(sides, key=lambda i: ((upper_h, lower_h)[i], i))
        if side == 0:
            upper_h += 1
        else:
            lower_h += 1
        extra_height -= 1
    if upper_h + lower_h + 6 > depth:
        raise GenerationError(f"Footprint {width}x{depth} cannot align the stacked circulation spine with all assigned rooms")
    seed = request.get("seed", 42)
    if isinstance(seed, bool) or not isinstance(seed, (int, str)):
        raise GenerationError("seed must be an integer or string")
    elevator = request.get("elevator", False)
    terrace_exit = request.get("terrace_exit", False)
    if not isinstance(elevator, bool) or not isinstance(terrace_exit, bool):
        raise GenerationError("elevator and terrace_exit must be boolean values")
    rng = random.Random(f"{GENERATOR_VERSION}:building:{seed}:{width}:{depth}:{program}:{levels}")
    style = request.get("style")
    style = rng.choice(list(STYLES)) if style is None else style
    if not isinstance(style, str) or style not in STYLES:
        raise GenerationError(f"Unknown palette: {style}")
    identifier = f"building-{seed}-{width}x{depth}-{room_count}-{above}-{basements}"
    house = {"id": identifier, "kind": "house", "name": template["name"] if template else "Wohnhaus mit zentralem Flur", "seed": seed,
             "generator_version": GENERATOR_VERSION, "width": width, "height": depth,
             "depth": depth, "levels": levels, "levels_above_ground": above,
             "basements": basements, "ground_floor_index": ground, "floor_height_m": 3,
             "elevator": elevator, "style": style, "entrance": [ground, 0, 1 + upper_h + 2],
             "floors": [], "portals": [], "program": list(program), "trace": [],
             "residents": residents}
    hall_start = 1 + upper_h
    lower_room_y = depth - 1 - lower_h
    lower_wall_y = lower_room_y - 1
    hall_y = hall_start + 2
    # Stairs and lift occupy distinct, stacked shafts at the far end of the hall.
    stairs_x = width - 4
    lift_x = width - 7
    for level in range(levels):
        elevation = level - ground
        floor = {"level": level, "elevation": elevation,
                 "name": "Kellergeschoss" if elevation == -1 else ("Erdgeschoss" if elevation == 0 else f"{elevation}. Obergeschoss"),
                 "width": width, "height": depth, "terrain": [0] * (width * depth),
                 "rooms": [], "objects": [], "doors": [], "portal_geometry": [],
                 "core": {"x": lift_x if elevator else stairs_x, "y": hall_start, "w": 5 if elevator else 2, "h": 3}}
        terrain = floor["terrain"]
        # The corridor edges are solid walls except at actual room/exterior doors.
        # Its two interior rows remain continuous to the shared portal landing.
        for y in range(hall_start + 1, lower_wall_y):
            for x in range(1, width - 2):
                terrain[y * width + x] = 1
        room_specs = []
        groups = layouts[level][0]
        for side_index, group in enumerate(groups):
            if not group:
                continue
            cursor = 1
            shared_height = upper_h if side_index == 0 else lower_h
            heights = [min(shared_height, max(catalog[kind]["minimum"][1], catalog[kind]["size"][1]))
                       for kind in group]
            widths = _expanded_widths(group, width - 6, catalog, heights)
            for kind, rw, rh in zip(group, widths, heights):
                room_y = hall_start - rh if side_index == 0 else lower_room_y
                ri = len(room_specs)
                room_specs.append((kind, cursor, room_y, rw, rh, "south" if side_index == 0 else "north", level, ri))
                cursor += rw + 1
        for kind, x, y, rw, rh, side, _, ri in room_specs:
            room_seed = int.from_bytes(f"{seed}:{level}:{x}:{kind}".encode(), "little") % (2**31)
            blocked_landing_x = {stairs_x, stairs_x + 1, lift_x, lift_x + 1}
            preferred_size = (rw, rh)
            minimum_size = tuple(catalog[kind]["minimum"])

            def room_kwargs(room_width, room_height):
                offsets = [p for p in range(1, room_width - 1) if x + p not in blocked_landing_x]
                if not offsets:
                    raise GenerationError(f"Footprint leaves no clear corridor doorway for {kind} on floor {level}")
                door_offset = min(offsets, key=lambda p: (abs(p - (room_width - 1) / 2), p))
                room_y = hall_start - room_height if side == "south" else lower_room_y
                outside_sides = []
                if side == "south" and room_y == 1:
                    outside_sides.append("north")
                if side == "north" and room_y + room_height == depth - 1:
                    outside_sides.append("south")
                result = {"style": style, "door_side": side, "door_offset": door_offset,
                          "outside_sides": outside_sides}
                if object_catalog is not None:
                    result["object_catalog"] = object_catalog
                if room_catalog is not None:
                    result["room_catalog"] = room_catalog
                return result

            try:
                room = generate_room(kind, room_seed, rw, rh, **room_kwargs(rw, rh))
            except GenerationError:
                if preferred_size == minimum_size:
                    raise
                # A bounded furnishing search may fail at the preferred size.
                # Fall back only to catalog minima, never below.
                rw, rh = minimum_size
                y = hall_start - rh if side == "south" else lower_room_y
                room = generate_room(kind, room_seed, rw, rh, **room_kwargs(rw, rh))
            room["origin"] = [x, y]
            area_minimum, area_target, area_maximum = _area_budget(kind, catalog)
            room["area_budget_m2"] = {"minimum": area_minimum, "target": area_target,
                                      "maximum": area_maximum, "actual": rw * rh}
            room["floor"] = level
            room["id"] = f"{identifier}:floor:{level}:room:{ri}"
            for yy in range(y, y + rh):
                for xx in range(x, x + rw):
                    terrain[yy * width + xx] = 1
            for door in room["doors"]:
                dx = x + door["cell"][0]
                dy = y + door["cell"][1] + (1 if side == "south" else -1)
                terrain[dy * width + dx] = 2
                if side == "south":
                    for py in range(dy + 1, hall_start + 2):
                        terrain[py * width + dx] = 1
                else:
                    for py in range(lower_wall_y, dy):
                        terrain[py * width + dx] = 1
                floor["doors"].append({"x": dx, "y": dy, "room_id": room["id"], "axis": "vertical"})
            for oi, obj in enumerate(room["objects"]):
                obj["id"] = f"{room['id']}:object:{oi}"
                obj["floor"] = level
                absolute = deepcopy(obj)
                absolute["x"] += x
                absolute["y"] += y
                absolute["room_id"] = room["id"]
                absolute["anchors"] = [[ax + x, ay + y] for ax, ay in obj["anchors"]]
                absolute["clearance"] = [[ax + x, ay + y] for ax, ay in obj["clearance"]]
                floor["objects"].append(absolute)
            floor["rooms"].append(room)
        # Real portal footprint and adjacent, walkable portal anchor.
        floor["portal_geometry"].append({"kind": "stairs", "x": stairs_x, "y": hall_start, "w": 2, "h": 3,
                                         "anchor": [width - 5, hall_y]})
        if elevator:
            floor["portal_geometry"].append({"kind": "elevator", "x": lift_x, "y": hall_start, "w": 2, "h": 2,
                                             "anchor": [lift_x + 2, hall_y]})
        if level == ground:
            ent_y = hall_y
            terrain[ent_y * width] = 2
            floor["doors"].append({"x": 0, "y": ent_y, "room_id": None, "axis": "horizontal"})
            house["entrance"] = [ground, 0, ent_y]
        if terrace_exit and level == ground:
            # The supported form is a grade-level garden terrace door, not a
            # roof destination without any exterior terrace geometry.
            exit_y = hall_y + 1
            terrain[exit_y * width] = 2
            floor["doors"].append({"x": 0, "y": exit_y, "room_id": None, "axis": "horizontal"})
            house["terrace_exit"] = [level, 0, exit_y]
            house["terrace_destination"] = {"kind": "garden_terrace", "floor": ground,
                                            "outside_edge": "west"}
        house["floors"].append(floor)
    for level in range(levels - 1):
        house["portals"].append({"id": f"stairs-{level}-{level+1}", "kind": "stairs",
                                 "resource_id": "stairs-main", "from": [level, width - 5, hall_y],
                                 "to": [level + 1, width - 5, hall_y], "duration_seconds": 12,
                                 "capacity": 1, "accessible": False})
    if elevator and levels > 1:
        for a in range(levels):
            for b in range(a + 1, levels):
                house["portals"].append({"id": f"lift-{a}-{b}", "kind": "elevator", "resource_id": "elevator-main",
                                         "from": [a, lift_x + 2, hall_y], "to": [b, lift_x + 2, hall_y],
                                         "duration_seconds": 8 + 4 * (b - a), "capacity": 1, "accessible": True})
    house["trace"] = ["Das angefragte rechteckige Grundst\u00fcck wird nicht vergr\u00f6\u00dfert",
                      "R\u00e4ume erf\u00fcllen Mindestma\u00dfe und nutzen passende Fl\u00e4chen bis h\u00f6chstens 14 m",
                      "Zimmert\u00fcren \u00f6ffnen ausschlie\u00dflich in den gemeinsamen Flur",
                      "Eine durchgehende Treppe verbindet alle Etagen; der optionale Aufzug liegt in einem eigenen Schacht"]
    from .navigation import FloorNavigation
    nav = FloorNavigation(house)
    nav_result = nav.validate()
    actual_capacity = {}
    for floor in house["floors"]:
        for room in floor["rooms"]:
            beds = sum(BED_CAPACITY.get(kind, 0) for kind in room.get("required_kinds", []))
            actual_capacity[room["id"]] = beds
    typed_rooms = [(room["kind"], actual_capacity[room["id"]])
                   for floor in house["floors"] for room in floor["rooms"]]
    adults_actual = sum(cap for kind, cap in typed_rooms if kind in ("bedroom", "guest"))
    children_actual = sum(cap for kind, cap in typed_rooms if kind in ("child", "nursery"))
    teens_actual = sum(cap for kind, cap in typed_rooms if kind == "teen")
    sleep = {"required": residents["adults"] + residents["children"] + residents["teens"],
             "provided": adults_actual + children_actual + teens_actual,
             "adults_required": residents["adults"],
             "adults_provided": adults_actual,
             "children_required": residents["children"], "children_provided": children_actual,
             "teens_required": residents["teens"], "teens_provided": teens_actual}
    errors = list(nav_result["errors"])
    house["validation"] = {**nav_result, "valid": not errors, "errors": errors,
                           "required_room_count": room_count,
                           "room_count": sum(len(f["rooms"]) for f in house["floors"]),
                           "sleep_capacity": sleep,
                           "sleep_capacity_valid": sleep["adults_provided"] >= sleep["adults_required"] and sleep["children_provided"] >= sleep["children_required"] and sleep["teens_provided"] >= sleep["teens_required"]}
    floor_coverage = []
    for floor in house["floors"]:
        assigned_cells = sum(value > 0 for value in floor["terrain"])
        footprint_cells = width * depth
        floor_coverage.append({"floor": floor["level"], "footprint_cells": footprint_cells,
                               "assigned_cells": assigned_cells,
                               "unassigned_cells": footprint_cells - assigned_cells,
                               "assigned_fraction": round(assigned_cells / footprint_cells, 3)})
    total_footprint = width * depth * levels
    total_assigned = sum(row["assigned_cells"] for row in floor_coverage)
    house["validation"]["footprint_coverage"] = {
        "floors": floor_coverage, "footprint_cells": total_footprint,
        "assigned_cells": total_assigned,
        "unassigned_cells": total_footprint - total_assigned,
        "assigned_fraction": round(total_assigned / total_footprint, 3),
    }
    house["validation"]["student_capacity"] = sum(
        room.get("capacity", {}).get("students", 0)
        for floor in house["floors"] for room in floor["rooms"])
    house["validation"]["valid"] = house["validation"]["valid"] and house["validation"]["sleep_capacity_valid"]
    if not house["validation"]["valid"]:
        if errors:
            raise GenerationError("Building connectivity failed: " + ", ".join(errors))
        raise GenerationError("Generated room selections do not provide the required typed sleeping capacity")
    return house
