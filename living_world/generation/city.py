"""Seeded city-scale planning laboratory over validated building interiors.

The result is a connected street and lot grammar, not a geography importer or
traffic model. The existing region and housing generators keep their seeds.
"""
from collections import deque
import random

from .buildings import generate_building
from .civic_catalog import BUILDING_TEMPLATES
from .navigation import FloorNavigation
from .rooms import GenerationError

CITY_VERSION = "housing-0.5.0/city"

# Reused rooms are explicit provisional programs. Their displayed room names
# remain honest; they are not represented as bespoke mall or council assets.
SERVICES = {
    "hospital": {"name": "Hospital", "zone": "civic", "size": (29, 27),
                 "rooms": BUILDING_TEMPLATES["hospital"]["room_program"], "fallback": False},
    "school": {"name": "School", "zone": "civic", "size": (36, 30),
               "rooms": BUILDING_TEMPLATES["school"]["room_program"], "fallback": False},
    "fire_station": {"name": "Fire station", "zone": "civic", "size": (29, 27),
                     "rooms": BUILDING_TEMPLATES["fire_station"]["room_program"], "fallback": False},
    "gym": {"name": "Fitness centre", "zone": "leisure", "size": (29, 27),
            "rooms": ["gym", "office", "bathroom"], "fallback": True},
    "office": {"name": "Office hub", "zone": "commercial", "size": (29, 27),
               "rooms": ["office", "office", "office", "bathroom"], "fallback": True},
    "town_hall": {"name": "Town hall", "zone": "civic", "size": (29, 27),
                  "rooms": ["hospital_reception", "office", "library", "bathroom"], "fallback": True},
    "nightclub": {"name": "Nightclub", "zone": "leisure", "size": (29, 27),
                  "rooms": ["party", "dining", "office", "bathroom"], "fallback": True},
    "shopping_center": {"name": "Shopping centre", "zone": "commercial", "size": (29, 27),
                        "rooms": ["dining", "office", "pantry", "bathroom"], "fallback": True},
    "supermarket": {"name": "Supermarket", "zone": "commercial", "size": (29, 27),
                    "rooms": ["pantry", "dining", "office", "bathroom"], "fallback": True},
}

JOB_FURNITURE = {"office_desk", "civic_staff_desk", "school_teacher_desk",
                 "civic_reception_desk", "civic_cafeteria_counter", "bar",
                 "fire_dispatch_console", "workbench", "school_lab_bench"}
PLACE_CAPACITY = {"school_student_chair": 1, "hospital_bed": 1,
                  "civic_waiting_bench": 2, "civic_cafeteria_table": 4,
                  "sofa": 3, "armchair": 1, "dining_table": 4,
                  "large_dining_table": 6, "treadmill": 1,
                  "exercise_bike": 1, "weight_bench": 1, "bar": 2}


def _line(a, b):
    if a[0] != b[0] and a[1] != b[1]:
        raise GenerationError("City paths must be orthogonal")
    return [[x, y] for x in range(min(a[0], b[0]), max(a[0], b[0]) + 1)
            for y in range(min(a[1], b[1]), max(a[1], b[1]) + 1)]


def _flood(public, start):
    start = tuple(start)
    seen = {start} if start in public else set()
    queue = deque(seen)
    while queue:
        x, y = queue.popleft()
        for cell in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
            if cell in public and cell not in seen:
                seen.add(cell)
                queue.append(cell)
    return seen


def _public_route(city, goal):
    start = tuple(city["public_start"])
    goal = tuple(goal)
    public = {tuple(cell) for cell in city["public_walkable"]}
    queue, previous = deque([start]), {start: None}
    while queue:
        cell = queue.popleft()
        if cell == goal:
            route = []
            while cell is not None:
                route.append(list(cell))
                cell = previous[cell]
            return list(reversed(route))
        x, y = cell
        for other in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
            if other in public and other not in previous:
                previous[other] = cell
                queue.append(other)
    return None


def generate_city(seed=42, columns=4, rows=4):
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2_000_000_000:
        raise GenerationError("seed must be an integer from 0 to 2000000000")
    if isinstance(columns, bool) or isinstance(rows, bool) or not isinstance(columns, int) or not isinstance(rows, int) or not 4 <= columns <= 5 or not 4 <= rows <= 5:
        raise GenerationError("city supports 4–5 columns and 4–5 rows")
    rng = random.Random(f"{CITY_VERSION}:{seed}:{columns}:{rows}")
    spans_x = [rng.randint(52, 62) for _ in range(columns)]
    spans_y = [rng.randint(45, 54) for _ in range(rows)]
    xs, ys = [8], [8]
    for span in spans_x:
        xs.append(xs[-1] + span)
    for span in spans_y:
        ys.append(ys[-1] + span)
    nodes = [{"id": f"junction-{c}-{r}", "x": x, "y": y}
             for r, y in enumerate(ys) for c, x in enumerate(xs)]
    edges, public = [], set()
    for r, y in enumerate(ys):
        for c in range(columns):
            a, b = (xs[c], y), (xs[c+1], y)
            street_class = "arterial" if r == rows // 2 else "local"
            edges.append({"from": f"junction-{c}-{r}", "to": f"junction-{c+1}-{r}",
                          "a": list(a), "b": list(b), "class": street_class,
                          "width_m": 6 if street_class == "arterial" else 3})
            public.update(map(tuple, _line(a, b)))
    for c, x in enumerate(xs):
        for r in range(rows):
            a, b = (x, ys[r]), (x, ys[r+1])
            street_class = "arterial" if c == columns // 2 else "local"
            edges.append({"from": f"junction-{c}-{r}", "to": f"junction-{c}-{r+1}",
                          "a": list(a), "b": list(b), "class": street_class,
                          "width_m": 6 if street_class == "arterial" else 3})
            public.update(map(tuple, _line(a, b)))
    indices = list(range(columns * rows))
    rng.shuffle(indices)
    service_kinds = list(SERVICES)
    rng.shuffle(service_kinds)
    use = {index: ("service", kind) for index, kind in zip(indices, service_kinds)}
    remaining = indices[len(service_kinds):]
    for index in remaining[:2]:
        use[index] = ("park", None)
    if len(remaining) > 2:
        use[remaining[2]] = ("water", None)
    for index in remaining[3:]:
        use[index] = ("residential", None)
    plots, landscapes = [], []
    for index in range(columns * rows):
        c, r = index % columns, index // columns
        left, top = xs[c] + 4, ys[r] + 4
        bounds = [left, top, xs[c+1] - xs[c] - 8, ys[r+1] - ys[r] - 8]
        assignment, service = use[index]
        if assignment in ("park", "water"):
            landscapes.append({"id": f"land-{index}", "zone": assignment,
                               "name": "Neighbourhood park" if assignment == "park" else "Retention pond",
                               "bounds": bounds})
            if assignment == "park":
                center = [left + bounds[2] // 2, top + bounds[3] // 2]
                path = _line((xs[c], center[1]), (xs[c+1], center[1]))
                public.update(map(tuple, path))
                edges.append({"from": f"park-west-{index}", "to": f"park-east-{index}",
                              "a": [xs[c], center[1]], "b": [xs[c+1], center[1]],
                              "class": "pedestrian", "width_m": 2})
            continue
        if assignment == "service":
            profile = SERVICES[service]
            program = list(profile["rooms"])
            bw, bh = profile["size"]
            zone, name = profile["zone"], profile["name"]
            residents = {"adults": 0, "children": 0, "teens": 0}
            above = 1
        else:
            service, zone, name = None, "residential", "Family home"
            program = ["living", "kitchen", "bathroom", "bedroom", "child", "laundry"]
            bw, bh, above = 18, 19, 2
            residents = {"adults": 2, "children": 1, "teens": 0}
        bx, by = left + 5, top + 3
        if bx + bw > left + bounds[2] or by + bh > top + bounds[3]:
            raise GenerationError(f"Block {index} cannot fit {name} and setbacks")
        brief = {"width": bw, "depth": bh, "room_count": len(program),
                 "levels_above_ground": above, "basements": 0,
                 "residents": residents, "room_program": program,
                 "seed": seed * 100 + index, "elevator": True}
        design = generate_building(brief)
        door = [bx + design["entrance"][1], by + design["entrance"][2]]
        frontage = [xs[c], door[1]]
        footpath = _line(frontage, door)
        public.update(map(tuple, footpath))
        jobs = [{"object_id": obj["id"], "kind": obj["kind"],
                 "floor": floor["level"], "anchor": [floor["level"], *obj["anchors"][0]]}
                for floor in design["floors"] for obj in floor["objects"]
                if obj["kind"] in JOB_FURNITURE and obj["anchors"]]
        equipped = sum(PLACE_CAPACITY.get(obj["kind"], 0)
                       for floor in design["floors"] for obj in floor["objects"])
        area = sum(room["width"] * room["height"]
                   for floor in design["floors"] for room in floor["rooms"])
        capacity = {"jobs": len(jobs), "office_units": sum(room["kind"] == "office"
                    for floor in design["floors"] for room in floor["rooms"]),
                    "equipped_places": equipped,
                    "area_based_occupant_estimate": min(100, area // 4),
                    "students": design["validation"].get("student_capacity", 0)}
        plots.append({"id": f"plot-{index}", "zone": zone, "service": service,
                      "name": name, "bounds": bounds, "building_bounds": [bx, by, bw, bh],
                      "design": design, "brief": brief, "door": door, "frontage": frontage,
                      "footpath": footpath, "jobs": jobs, "capacity": capacity,
                      "program_fallback": bool(service and SERVICES[service]["fallback"]),
                      "entrance_link": {"public": door, "building": list(design["entrance"])}})
    start = [xs[0], ys[0]]
    visited = _flood(public, start)
    errors = []
    if len(visited) != len(public):
        errors.append("street_network_disconnected")
    for plot in plots:
        if tuple(plot["door"]) not in visited:
            errors.append("entrance_disconnected:" + plot["id"])
        if not plot["design"]["validation"]["valid"]:
            errors.append("invalid_interior:" + plot["id"])
    if errors:
        raise GenerationError("City rejected: " + ",".join(errors))
    return {"kind": "city", "name": "Mosswood city laboratory", "city_version": CITY_VERSION,
            "seed": seed, "columns": columns, "rows": rows,
            "width": xs[-1] + 8, "height": ys[-1] + 8,
            "block_widths": spans_x, "block_heights": spans_y,
            "nodes": nodes, "edges": edges, "plots": plots, "landscapes": landscapes,
            "public_start": start, "public_walkable": [list(cell) for cell in sorted(public)],
            "validation": {"valid": True, "errors": [], "connected_public_cells": len(visited),
                           "connected_entrances": len(plots), "buildings": len(plots),
                           "services": sorted(p["service"] for p in plots if p["service"]),
                           "jobs": sum(p["capacity"]["jobs"] for p in plots)},
            "limitations": ["Orthogonal planning grammar; no imported geographic data.",
                            "Road widths/classes are visual and topological; traffic is not simulated.",
                            "Some services reuse explicitly labelled room programs pending bespoke interiors.",
                            "Area-based occupant counts are planning estimates, not furnished seats."]}


def route_to_city_room(city, plot_id, room_id):
    plot = next((p for p in city["plots"] if p["id"] == plot_id), None)
    if plot is None:
        raise GenerationError(f"Unknown plot: {plot_id}")
    room = next((room for floor in plot["design"]["floors"] for room in floor["rooms"]
                 if room["id"] == room_id), None)
    if room is None:
        raise GenerationError(f"Unknown room for plot {plot_id}: {room_id}")
    public_path = _public_route(city, plot["door"])
    target = [room["floor"], room["origin"][0] + room["doors"][0]["cell"][0],
              room["origin"][1] + room["doors"][0]["cell"][1]]
    interior = FloorNavigation(plot["design"]).route(plot["design"]["entrance"], target)
    if public_path is None or interior is None:
        raise GenerationError("City-to-room route is not connected")
    return {"valid": True, "plot_id": plot_id, "room_id": room_id,
            "public_path": public_path, "entrance_link": plot["entrance_link"],
            "interior_route": interior,
            "seconds_without_queue": len(public_path)-1+interior["seconds_without_queue"]}
