"""Small hierarchical district slice: zones -> roads/lots -> actual interiors.

This is a deterministic grid grammar, not an urban planning or OSM importer.
Local building navigation and public paths meet at an explicit entrance node.
"""
from collections import deque
import random

from . import GENERATOR_VERSION
from .buildings import generate_building
from .rooms import GenerationError
from .navigation import FloorNavigation

ZONE_NAMES = {"residential": "Wohnen", "civic": "Öffentliche Einrichtungen", "commercial": "Gewerbe",
              "industrial": "Handwerk & Produktion", "park": "Park", "water": "Gewässer"}


def _line(a, b):
    if a[0] != b[0] and a[1] != b[1]:
        raise GenerationError("Only orthogonal paths are supported")
    return [[x, y] for x in range(min(a[0], b[0]), max(a[0], b[0])+1)
            for y in range(min(a[1], b[1]), max(a[1], b[1])+1)]


def generate_region(seed=42, columns=3, rows=2, zones=None, *, object_catalog=None, room_catalog=None):
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2_000_000_000:
        raise GenerationError("Invalid region seed")
    if not isinstance(columns, int) or not isinstance(rows, int) or not 1 <= columns <= 4 or not 1 <= rows <= 3:
        raise GenerationError("Region supports 1..4 columns and 1..3 rows")
    if zones is not None and (not isinstance(zones, list) or len(zones) != columns*rows or any(z not in ZONE_NAMES for z in zones)):
        raise GenerationError("Provide one known zone per block")
    rng = random.Random(f"{GENERATOR_VERSION}:region:{seed}:{columns}:{rows}")
    kinds = list(zones) if zones is not None else ["residential", "civic", "park", "residential", "commercial", "water", "industrial", "residential", "civic", "park", "residential", "commercial"][:columns*rows]
    if zones is None:
        rng.shuffle(kinds)
    span_x, span_y = 56, 48
    width, height = columns*span_x+16, rows*span_y+16
    xs, ys = [8+i*span_x for i in range(columns+1)], [8+i*span_y for i in range(rows+1)]
    nodes = [{"id": f"junction-{x}-{y}", "x": x, "y": y} for y in ys for x in xs]
    edges = []
    for y in ys:
        for i in range(columns):
            edges.append({"from": f"junction-{xs[i]}-{y}", "to": f"junction-{xs[i+1]}-{y}", "a": [xs[i], y], "b": [xs[i+1], y], "width_m": 6})
    for x in xs:
        for i in range(rows):
            edges.append({"from": f"junction-{x}-{ys[i]}", "to": f"junction-{x}-{ys[i+1]}", "a": [x, ys[i]], "b": [x, ys[i+1]], "width_m": 6})
    # Public walkability includes sidewalks and explicit intersection crossings;
    # motor traffic, signals and collision with moving cars are outside this rig.
    public = set()
    for y in ys:
        public.update((x, y+dy) for x in range(xs[0]-4, xs[-1]+5) for dy in (-4, -3, 3, 4))
    for x in xs:
        public.update((x+dx, y) for y in range(ys[0]-4, ys[-1]+5) for dx in (-4, -3, 3, 4))
    for x in xs:
        for y in ys:
            public.update((x+dx, y+dy) for dx in range(-4,5) for dy in range(-4,5))
    plots, landscapes, errors = [], [], []
    for i, zone in enumerate(kinds):
        col, row = i % columns, i // columns
        left, top = xs[col], ys[row]
        bounds = [left+7, top+7, span_x-14, span_y-14]
        if zone in ("park", "water"):
            landscapes.append({"id": f"land-{i}", "zone": zone, "name": ZONE_NAMES[zone], "bounds": bounds})
            continue
        residents = {"adults": 2, "children": 1, "teens": 0} if zone == "residential" else {"adults": 0, "children": 0, "teens": 0}
        request = {"width": 29, "depth": 27, "room_count": 8, "levels_above_ground": 2,
                   "basements": 0, "residents": residents, "seed": seed*100+i, "elevator": True}
        building_type = "family_home"
        if zone == "civic":
            building_type, program = rng.choice([
                ("school", ["school_classroom", "school_lab", "school_staff", "school_cafeteria"]),
                ("hospital", ["hospital_reception", "hospital_exam", "hospital_ward", "bathroom"]),
                ("fire_station", ["fire_equipment", "fire_garage", "office", "bathroom"]),
            ])
            request.update(room_program=program, room_count=4, levels_above_ground=1)
        elif zone in ("commercial", "industrial"):
            building_type = "office_studio" if zone == "commercial" else "craft_workshop"
            request.update(room_program=["office", "workshop" if zone == "industrial" else "dining", "pantry", "bathroom"], room_count=4, levels_above_ground=1)
        design = generate_building(request, object_catalog=object_catalog, room_catalog=room_catalog)
        bx, by = left+13, top+10
        floor, ex, ey = design["entrance"]
        if ex != 0:
            raise GenerationError("Region grammar currently requires a west-facing entrance")
        door = [bx+ex, by+ey]
        frontage = [left+4, door[1]]
        path = _line(frontage, door)
        public.update(map(tuple, path))
        # Prefix building ID at the boundary; interior IDs live in its namespace.
        plot = {"id": f"plot-{i}", "zone": zone, "name": ZONE_NAMES[zone], "bounds": bounds,
                "building_bounds": [bx, by, design["width"], design["height"]],
                "building_type": building_type, "request": request, "design": design,
                "door": door, "footpath": path, "frontage": frontage,
                "entrance_link": {"world": door, "building": list(design["entrance"])}}
        px, py, pw, ph = bounds
        if not (px <= bx and py <= by and bx+design["width"] <= px+pw and by+design["height"] <= py+ph):
            errors.append("building_outside_plot:"+plot["id"])
        if not design["validation"]["valid"]:
            errors.append("invalid_interior:"+plot["id"])
        plots.append(plot)
    start = (xs[0]-4, ys[0]-4)
    reached, queue = {start}, deque([start])
    while queue:
        x, y = queue.popleft()
        for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if p in public and p not in reached:
                reached.add(p)
                queue.append(p)
    for plot in plots:
        if tuple(plot["door"]) not in reached:
            errors.append("entrance_disconnected:"+plot["id"])
    if len(reached) != len(public):
        errors.append("public_paths_disconnected")
    if errors:
        raise GenerationError("Region rejected: " + ",".join(errors))
    return {"kind": "region", "name": "Ein Quartier, von der Straße bis zum Zimmer", "seed": seed,
            "width": width, "height": height, "generator_version": GENERATOR_VERSION,
            "columns": columns, "rows": rows, "nodes": nodes, "edges": edges, "plots": plots,
            "landscapes": landscapes, "public_start": list(start), "public_walkable": [list(p) for p in sorted(public)],
            "validation": {"valid": True, "errors": [], "connected_entrances": len(plots),
                           "public_walkable_cells": len(reached), "instantiated_buildings": len(plots),
                           "rooms": sum(len(f["rooms"]) for p in plots for f in p["design"]["floors"])},
            "limitations": ["Orthogonale, flache Rastergrammatik; keine freie Stadtform oder Verkehrsplanung.",
                            "Gewerbe/Industrie zunächst Büro- und Handwerksprofile, keine vollständigen Betriebe.",
                            "Parks und Gewässer sind reservierte Flächen; noch kein Landschafts- oder Wassersimulator.",
                            "Gebäude innen begehbar; Regionsrouten geplant, noch keine bevölkerte Hauptkarte."]}


def route_to_room(region, plot_id, room_id):
    plot = next((p for p in region["plots"] if p["id"] == plot_id), None)
    if plot is None:
        raise GenerationError("Unknown plot")
    floor_room = next(((f, r) for f in plot["design"]["floors"] for r in f["rooms"] if r["id"] == room_id), None)
    if floor_room is None:
        raise GenerationError("Unknown room")
    floor, room = floor_room
    target = next((o for o in floor["objects"] if o["room_id"] == room_id and o["anchors"]), None)
    if target is None:
        raise GenerationError("Room has no interaction target")
    interior = FloorNavigation(plot["design"]).route(plot["design"]["entrance"], [floor["level"], *target["anchors"][0]])
    public = {tuple(p) for p in region["public_walkable"]}
    start, end = tuple(region["public_start"]), tuple(plot["door"])
    previous, queue = {start: None}, deque([start])
    while queue and end not in previous:
        x, y = queue.popleft()
        for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if p in public and p not in previous:
                previous[p] = (x,y)
                queue.append(p)
    if end not in previous or interior is None:
        raise GenerationError("No continuous public-to-interior route")
    path, node = [], end
    while node is not None:
        path.append(list(node)); node = previous[node]
    return {"public_path": list(reversed(path)), "boundary": plot["entrance_link"],
            "interior_route": interior, "valid": True, "execution": "route_plan_only"}
