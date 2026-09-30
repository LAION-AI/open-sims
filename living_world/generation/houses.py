"""Room programs, shared circulation core, stacked portals and connected plots."""
from collections import deque
from copy import deepcopy
import random

from . import GENERATOR_VERSION
from .rooms import GenerationError, generate_room
from .catalog import ROOMS


def generate_house(seed=42, levels=3, elevator=True):
    if not 1 <= levels <= 5:
        raise GenerationError("One to five floors are supported")
    rng = random.Random(f"{GENERATOR_VERSION}:house:{seed}")
    left, right = rng.randint(7, 9), rng.randint(7, 9)
    north, south = rng.randint(7, 9), rng.randint(7, 9)
    core_width = 5
    width, height = left + right + core_width + 4, north + south + 3
    core_x = left + 2
    style = rng.choice(["sage", "terracotta", "coastal", "plum"])
    house = {"id": f"house-{seed}-{levels}-{int(elevator)}", "kind": "house", "name": rng.choice(["Haus Lindenblick", "Haus Morgenlicht", "Haus am Garten", "Haus Birkenhof"]),
             "seed": seed, "generator_version": GENERATOR_VERSION, "width": width, "height": height,
             "levels": levels, "floor_height_m": 3, "elevator": elevator, "style": style,
             "entrance": [0, core_x + 2, height - 1], "floors": [], "portals": [],
             "program": "Mehrgeschossiges Test-Wohnhaus mit gemeinsamem Erschließungskern", "trace": []}
    for level in range(levels):
        # Keep essential shared rooms and a stacked wet core. Flex rooms gain
        # new programs only where their declared minimum size actually fits.
        def fitting(options, w, h):
            return rng.choice([k for k in options if ROOMS[k]["minimum"][0] <= w and ROOMS[k]["minimum"][1] <= h])
        kinds = ["living", "kitchen", "bathroom", fitting(["dining", "office", "laundry", "pantry", "conservatory", "hall"], right, south)] if level == 0 else ["bedroom", fitting(["child", "nursery", "guest"], right, north), "bathroom", fitting(["teen", "office", "library", "music", "gym", "workshop", "gaming"], right, south)]
        if level > 1:
            kinds[0] = fitting(["bedroom", "guest", "library"], left, north)
            kinds[1] = fitting(["living", "music", "gym", "workshop", "conservatory", "party", "gaming"], right, north)
        specs = [(1, 1, left, north, "east", ["north", "west"]),
                 (core_x + core_width + 1, 1, right, north, "west", ["north", "east"]),
                 (1, north + 2, left, south, "east", ["south", "west"]),
                 (core_x + core_width + 1, north + 2, right, south, "west", ["south", "east"])]
        terrain = [0] * (width * height)
        for y in range(1, height - 1):
            for x in range(core_x, core_x + core_width):
                terrain[y * width + x] = 1
        floor = {"level": level, "name": "Erdgeschoss" if level == 0 else f"{level}. Obergeschoss",
                 "width": width, "height": height, "terrain": terrain, "rooms": [], "objects": [], "doors": [],
                 "core": {"x": core_x, "y": 1, "w": core_width, "h": height - 2}, "portal_geometry": []}
        for ri, (x, y, w, h, side, outside) in enumerate(specs):
            room_seed = seed * 10000 + level * 100 + ri
            # Door positions are solved at house level before furnishings. The
            # northern doors must be below the stair/lift footprints in the core.
            room = generate_room(kinds[ri], room_seed, w, h, side, style, outside, h - 2 if ri < 2 else 1)
            room["origin"] = [x, y]
            room["floor"] = level
            room["id"] = f"{house['id']}:floor:{level}:room:{ri}"
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    terrain[yy * width + xx] = 1
            for door in room["doors"]:
                dx = x + door["cell"][0] + (1 if side == "east" else -1)
                dy = y + door["cell"][1]
                terrain[dy * width + dx] = 2
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
        if level == 0:
            terrain[(height - 1) * width + core_x + 2] = 2
            floor["doors"].append({"x": core_x + 2, "y": height - 1, "room_id": None, "axis": "horizontal"})
        if levels > 1:
            floor["portal_geometry"].append({"kind": "stairs", "x": core_x, "y": 1, "w": 2, "h": 3, "anchor": [core_x + 1, 4]})
            if elevator:
                floor["portal_geometry"].append({"kind": "elevator", "x": core_x + 3, "y": 1, "w": 2, "h": 2, "anchor": [core_x + 3, 3]})
        house["floors"].append(floor)
    for level in range(levels - 1):
        house["portals"].append({"id": f"stairs-{level}-{level+1}", "kind": "stairs", "resource_id": f"stairs-{level}-{level+1}",
                                  "from": [level, core_x + 1, 4], "to": [level + 1, core_x + 1, 4],
                                  "duration_seconds": 12, "capacity": 1, "accessible": False})
    if elevator and levels > 1:
        for a in range(levels):
            for b in range(a + 1, levels):
                house["portals"].append({"id": f"lift-{a}-{b}", "kind": "elevator", "resource_id": "elevator-main",
                                          "from": [a, core_x + 3, 3], "to": [b, core_x + 3, 3],
                                          "duration_seconds": 8 + 4 * (b - a), "capacity": 1, "accessible": True})
    house["trace"] = ["Raumprogramm vor Einrichtung festgelegt", "Fünf Meter breiter, durchgehender Erschließungskern",
                      "Alle Zimmertüren führen in den Flur; keine Durchgangs-Schlafzimmer",
                      "Bäder liegen übereinander; Außenfenster bleiben an Außenwänden",
                      "Treppen und Aufzugsschacht sind auf allen Etagen deckungsgleich",
                      "Grundriss und jedes Möbelziel von der Haustür aus geprüft"]
    from .navigation import FloorNavigation
    nav = FloorNavigation(house)
    house["validation"] = nav.validate()
    if not house["validation"]["valid"]:
        raise GenerationError("House connectivity failed: " + ", ".join(house["validation"]["errors"]))
    return house


def generate_district(seed=42, count=8):
    """A small connected block proof, not a complete city or traffic simulator."""
    if not 2 <= count <= 12:
        raise GenerationError("Block study supports 2–12 plots")
    rng = random.Random(f"{GENERATOR_VERSION}:district:{seed}")
    columns = (count + 1) // 2
    lot_width, lot_depth = 32, 28
    width, height = columns * lot_width + 16, 2 * lot_depth + 14
    street_y = lot_depth + 7
    nodes = [{"id": "west", "position": [3, street_y]}, {"id": "east", "position": [width - 4, street_y]}]
    edges = [{"from": "west", "to": "east", "width_m": 6, "kind": "local_street", "sidewalk_m": 2}]
    # A return street makes an explicit loop with both ends joined, not parallel
    # road strips that merely look connected at the edge of a screenshot.
    nodes += [{"id": "northwest", "position": [3, 2]}, {"id": "northeast", "position": [width - 4, 2]}]
    edges += [{"from": a, "to": b, "width_m": 4, "kind": "local_street", "sidewalk_m": 1} for a, b in (("west", "northwest"), ("northwest", "northeast"), ("northeast", "east"))]
    plots = []
    for i in range(count):
        row, col = divmod(i, columns)
        x, y = 8 + col * lot_width, 7 if row == 0 else street_y + 6
        bw, bh = rng.randint(22, 26), rng.randint(17, 21)
        bx, by = x + (lot_width - bw) // 2, y + (2 if row == 0 else 3)
        door = [bx + bw // 2, by + bh if row == 0 else by]
        frontage = [door[0], street_y + (-5 if row == 0 else 5)]
        plots.append({"id": f"plot-{i}", "bounds": [x, y, lot_width, lot_depth - 4],
                      "building": [bx, by, bw, bh], "levels": rng.randint(1, 4), "house_seed": seed * 100 + i,
                      "door": door, "frontage": frontage, "footpath": [door, frontage], "footpath_width_m": 2,
                      "street_edge": 0, "style": rng.choice(["sage", "terracotta", "coastal", "plum"])})
    graph = {n["id"]: set() for n in nodes}
    for edge in edges:
        graph[edge["from"]].add(edge["to"])
        graph[edge["to"]].add(edge["from"])
    reached = {nodes[0]["id"]}
    queue = deque(reached)
    while queue:
        for nxt in graph[queue.popleft()]:
            if nxt not in reached:
                reached.add(nxt); queue.append(nxt)
    errors = []
    for i, p in enumerate(plots):
        bx, by, bw, bh = p["building"]
        px, py, pw, ph = p["bounds"]
        if not (px <= bx and py <= by and bx + bw <= px + pw and by + bh <= py + ph):
            errors.append(f"building_outside_plot:{p['id']}")
        for other in plots[:i]:
            ox, oy, ow, oh = other["bounds"]
            if px < ox + ow and px + pw > ox and py < oy + oh and py + ph > oy:
                errors.append("overlapping_plots")
        if p["frontage"][0] != p["door"][0] or not 3 <= p["frontage"][0] <= width - 4:
            errors.append("unconnected_frontage")
    if len(reached) != len(nodes):
        errors.append("disconnected_roads")
    return {"kind": "district", "name": "Ein verbundener Wohnblock", "seed": seed, "width": width, "height": height,
            "generator_version": GENERATOR_VERSION, "nodes": nodes, "edges": edges, "plots": plots,
            "validation": {"valid": not errors, "errors": errors, "connected_plots": len(plots), "connected_road_nodes": len(reached)},
            "limitations": ["Blockstudie: Fassaden und Grundstücke, noch keine Einbindung der Hausinnenräume", "Keine Fahrzeug-, Verkehrs- oder städtebauliche Fachplanung"]}
