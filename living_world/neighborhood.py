"""Compact, mixed-use, traversable map for new Mosswood save files.

This is intentionally a 2-D runtime plan. The separate city/house laboratories
may generate multi-floor designs, but this map only claims the rooms and
furniture that can be visited on its active ground plane.
"""
from array import array
from collections import deque
import random

from .spatial import (SpatialService, WIDTH, GRASS, ROAD, PATH, FLOOR, WALL,
                      WATER, SURNAMES)


class LivingNeighborhood(SpatialService):
    """A new-save layout preserving SpatialService's runtime object contract."""

    LAYOUT_ID = "neighborhood-v1"
    MAP_HEIGHT = 180
    HOME_ROWS = (4, 30, 132, 158)
    ROAD_ROWS = (21, 48, 74, 99, 125, 151, 175)
    LOT_X = (4, 29, 54, 79, 104)

    def rect(self, x, y, w, h, terrain):
        for yy in range(max(0, y), min(self.height, y + h)):
            for xx in range(max(0, x), min(self.width, x + w)):
                self.cells[yy * self.width + xx] = terrain

    def walkable(self, p):
        x, y = p
        return (0 <= x < self.width and 0 <= y < self.height
                and (x, y) not in self.blocked
                and self.cells[y * self.width + x] not in (WALL, WATER))

    def visible(self, start, end, radius=7):
        x0, y0 = start
        x1, y1 = end
        if (x1 - x0) ** 2 + (y1 - y0) ** 2 > radius ** 2:
            return False
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(1, steps):
            x = round(x0 + (x1 - x0) * i / steps)
            y = round(y0 + (y1 - y0) * i / steps)
            if self.cells[y * self.width + x] == WALL:
                return False
        return True

    def public_data(self):
        return {"width": self.width, "height": self.height, "cell_size_m": 1,
                "tile_pixels": 24, "terrain": list(self.cells),
                "buildings": self.buildings, "households": self.households,
                "objects": list(self.objects.values()), "decorations": self.decorations,
                "regions": self.regions, "planning_metadata": self.planning_metadata}

    def _road(self, name, x, y, w, h, road_class):
        self.rect(x, y, w, h, ROAD)
        self.planning_metadata["roads"].append(
            {"name": name, "class": road_class, "bounds": [x, y, w, h]})

    def _object(self, kind, name, x, y, w=1, h=1, anchors=None, household=None,
                building=None, capacity=None, blocking=True):
        anchors = anchors or [[x, y + h]]
        return self.add_object(kind, name, x, y, w, h, anchors, household,
                               building, blocking, len(anchors) if capacity is None else capacity)

    def _home(self, index, row, col, rng):
        variant = (index + rng.randrange(3)) % 3
        width = (16, 17, 18)[variant]
        x = self.LOT_X[col] + rng.choice((0, 0, 1))
        y = self.HOME_ROWS[row]
        h = 13
        hid, bid = f"household_{index+1:02}", f"home_{index+1:02}"
        name = f"{SURNAMES[index]} house"
        door = self.building(bid, name, x, y, width, h, index % 6, hid)
        self._frontage(bid, door, self.ROAD_ROWS[(0, 1, 5, 6)[row]])
        split = (9, 10, 11)[variant]
        # A split room, not a painted equal-cell grid: generous living-kitchen,
        # a private bedroom, and a genuinely smaller bathroom.
        self.rect(x + split, y + 1, 1, 11, WALL)
        self.rect(x + split, y + 5, 1, 1, FLOOR)
        self.rect(x + split, y + 9, 1, 1, FLOOR)
        self.rect(x + split + 1, y + 7, width - split - 2, 1, WALL)
        self.rect(x + 1, y + 4, 4, 1, WALL)
        self.rect(x + width - 4, y + 8, 1, 4, WALL)
        self.rect(x + width - 4, y + 10, 1, 1, FLOOR)
        if variant == 1:
            # A side alcove changes the partition outline without blocking the
            # circulation spine or the kitchen work triangle.
            self.rect(x + 7, y + 1, 1, 3, WALL)
            self.rect(x + 7, y + 3, 1, 1, FLOOR)
        members = 3 if index % 5 == 2 else 2
        if members == 3:
            self.rect(x + split + 3, y + 1, 1, 6, WALL)
            self.rect(x + split + 3, y + 5, 1, 1, FLOOR)
        rooms = [
            ("kitchen", "Kitchen", [x + 1, y + 1, 4, 3]),
            ("living", "Living room", [x + 1, y + 5, split - 1, 3]),
            ("dining", "Dining room", [x + 1, y + 8, 5, 4]),
            ("hall", "Hall", [x + 6, y + 8, split - 6, 4]),
            ("bedroom", "Adult bedroom", [x + split + 1, y + 1,
                                         2 if members == 3 else width - split - 2, 6]),
            ("bathroom", "Bathroom", [x + width - 3, y + 9, 2, 3]),
        ]
        if members == 3:
            rooms.append(("child_room", "Child bedroom", [x + split + 4, y + 1,
                                                            width - split - 5, 6]))
        self.regions.extend({"id": bid + "_" + key, "name": title,
                             "bounds": bounds, "parent": bid}
                            for key, title, bounds in rooms)
        fixtures = [
            ("fridge", "Kitchen fridge", 1, 1, 1, 1, [[1, 2]], 1, True),
            ("sink", "Kitchen sink", 2, 1, 1, 1, [[2, 2]], 1, True),
            ("counter", "Food preparation counter", 3, 1, 2, 1, [[3, 2], [4, 2]], 2, True),
            ("sofa", "Living room sofa", 2, 5, 3, 1, [[2, 6], [3, 6], [4, 6]], 3, True),
            ("table", "Family dining table", 2, 8, 2, 1, [[2, 9], [3, 9], [4, 9]], 3, True),
            ("bookshelf", "Bookcase", 6, 4, 1, 1, [[6, 5]], 1, True),
            ("desk", "Writing desk", 6, 1, 1, 1, [[6, 2]], 1, True),
            ("toilet", "Bathroom toilet", width - 2, 9, 1, 1, [[width - 3, 9]], 1, True),
            ("shower", "Bathroom shower", width - 2, 10, 1, 1, [[width - 3, 10]], 1, True),
            ("bin", "Kitchen bin", 5, 1, 1, 1, [[5, 2]], 1, False),
        ]
        if members == 3 or index % 2 == 0:
            fixtures.append(("bed", "Double bed", split + 1, 1, 2, 2,
                             [[split + 1, 3], [split + 2, 3]], 2, True))
            if members == 3:
                fixtures.append(("bed", "Child bed", split + 4, 1, 1, 2,
                                 [[split + 4, 3]], 1, True))
        else:
            for j in (1, 3):
                fixtures.append(("bed", "Single bed", split + j, 1, 1, 2,
                                 [[split + j, 3]], 1, True))
        for kind, label, dx, dy, w, hh, anchors, capacity, blocking in fixtures:
            object_id = self._object(kind, label, x + dx, y + dy, w, hh,
                                     [[x + a, y + b] for a, b in anchors], hid, bid,
                                     capacity, blocking)
            if kind == "bed":
                self.objects[object_id]["bed_variant"] = "double" if capacity == 2 else "single"
        self._object("planter", "Vegetable patch", x + width + 2, y + 5, 2, 2,
                     [[x + width + 1, y + 6]], hid, bid)
        building = self.buildings[-1]
        building["plan_variant"] = ("offset-bedroom", "living-alcove", "wide-bedroom")[variant]
        building["rooms"] = [bid + "_" + key for key, _, _ in rooms]
        self.households.append({"id": hid, "name": SURNAMES[index],
                                "building_id": bid, "address": f"{index+1} {('North Lane', 'Willow Row', 'South Commons', 'Fern Lane')[row]}",
                                "members": [], "palette": index % 6})
        self.decorations.append({"kind": "tree", "x": x + width + 3,
                                 "y": y + 2, "variant": index % 3})

    def _frontage(self, bid, door, road_y):
        x, y = door
        direction = 1 if road_y > y else -1
        self.rect(x, min(y + direction, road_y), 1, abs(road_y - y), PATH)
        building = next(item for item in self.buildings if item["id"] == bid)
        building["frontage"] = [x, road_y]

    def _service(self, kind, col, row, rng):
        definitions = {
            "school": ("Mosswood School", 22, "teacher_station", "Teachers' workroom", 6),
            "studio": ("Creative Studio", 19, "illustrator_station", "Illustration desks", 4),
            "workshop": ("Mosswood Works", 19, "carpenter_station", "Carpentry workbench", 4),
            "hospital": ("Community Hospital", 20, "hospital_desk", "Reception and triage", 5),
            "fire_station": ("Fire Station", 19, "fire_stationdesk", "Dispatch station", 4),
            "cafe": ("The Daily Crumb", 18, "cafe_counter", "Café work counter", 3),
            "shop": ("Moss and Market", 18, "shop_counter", "Shop counter", 3),
            "gym": ("Mosswood Fitness", 19, "gym_station", "Training stations", 6),
            "nightclub": ("Lantern Club", 19, "nightclub_floor", "Dance floor", 12),
            "town_hall": ("Town Hall", 19, "townhall_desk", "Public service desks", 4),
            "office_hub": ("Office Hub", 19, "office_station", "Office desks", 6),
            "supermarket": ("South Market", 19, "supermarket_checkout", "Checkouts", 5),
            "shopping_center": ("Mosswood Arcade", 19, "mall_counter", "Arcade counters", 5),
        }
        name, w, station_kind, station_name, slots = definitions[kind]
        bid = "office_hub" if kind == "office_hub" else kind
        x = self.LOT_X[col] + (1 if col % 2 and kind != "school" else 0)
        y = (56, 81, 106)[row]
        h = 14
        door = self.building(bid, name, x, y, w, h, (col + row + 2) % 6)
        self._frontage(bid, door, (74, 99, 125)[row])
        self.buildings[-1]["service_kind"] = kind
        if kind == "school":
            self.rect(x + 12, y + 1, 1, 11, WALL)
            self.rect(x + 12, y + 7, 1, 1, FLOOR)
            self.regions.extend([
                {"id": "school_classroom", "name": "Classroom", "bounds": [x + 1, y + 1, 11, 11], "parent": bid},
                {"id": "school_staff", "name": "Staff and preparation", "bounds": [x + 13, y + 1, 8, 11], "parent": bid},
            ])
            self._object(station_kind, station_name, x + 14, y + 2, 6, 1,
                         [[x + 14 + i, y + 3] for i in range(6)], building=bid, capacity=6)
            self._object("chalkboard", "Classroom chalkboard", x + 2, y + 1, 6, 1,
                         [[x + 8, y + 2]], building=bid, blocking=False)
            for row_index in range(4):
                for chair_index in range(6):
                    cx, cy = x + 2 + chair_index, y + 2 + 2 * row_index
                    self._object("school_student_desk", "Pupil desk", cx, cy,
                                 anchors=[[cx, cy + 1]], building=bid)
                    self._object("school_student_chair", "Classroom seat", cx, cy + 1,
                                 anchors=[[cx, cy + 1]], building=bid, blocking=False)
        else:
            if kind not in {"gym", "nightclub"}:
                self.rect(x + 1, y + 7, w - 2, 1, WALL)
                self.rect(x + w // 2, y + 7, 1, 1, FLOOR)
                self.regions.extend([
                    {"id": bid + "_service", "name": "Public and work area", "bounds": [x + 1, y + 1, w - 2, 6], "parent": bid},
                    {"id": bid + "_lobby", "name": "Entrance and visitor area", "bounds": [x + 1, y + 8, w - 2, 5], "parent": bid},
                ])
            else:
                self.regions.append({"id": bid + "_floor", "name": "Open activity floor",
                                     "bounds": [x + 1, y + 1, w - 2, 12], "parent": bid})
            if kind == "nightclub":
                anchors = [[x + 4 + j % 4, y + 3 + j // 4] for j in range(slots)]
                self._object(station_kind, station_name, x + 4, y + 3, 4, 3,
                             anchors, building=bid, capacity=slots, blocking=False)
            elif kind == "gym":
                anchors = [[x + 3 + j % 3, y + 3 + j // 3] for j in range(slots)]
                self._object(station_kind, station_name, x + 3, y + 3, 3, 2,
                             anchors, building=bid, capacity=slots, blocking=False)
            else:
                self._object(station_kind, station_name, x + 2, y + 2, slots, 1,
                             [[x + 2 + j, y + 3] for j in range(slots)],
                             building=bid, capacity=slots)
            if kind == "studio":
                self._object("designer_station", "Design desks", x + 10, y + 2, 4, 1,
                             [[x + 10 + j, y + 3] for j in range(4)], building=bid)
            if kind == "workshop":
                for extra, offset in (("tailor_station", 10), ("gardener_station", 4)):
                    yy = y + (2 if extra == "tailor_station" else 9)
                    self._object(extra, extra.replace("_", " ").title(), x + offset, yy, 4, 1,
                                 [[x + offset + j, yy + 1] for j in range(4)], building=bid)
            if kind == "hospital":
                for j in range(3):
                    self._object("hospital_bed", "Treatment bed", x + 2 + 3*j, y + 9,
                                 1, 2, [[x + 2 + 3*j, y + 11]], building=bid)
            if kind in {"cafe", "shop"}:
                for j in range(2):
                    self._object("table" if kind == "cafe" else "shelf",
                                 "Visitor table" if kind == "cafe" else "Market shelf",
                                 x + 3 + 4*j, y + 9, 1, 1,
                                 [[x + 3 + 4*j, y + 10]], building=bid)

    def _park(self, col, row, name):
        x, y, w, h = self.LOT_X[col], (56, 81, 106)[row], 19, 15
        park_id = f"park_{row}_{col}"
        self.planning_metadata["parks"].append({"id": park_id, "name": name,
                                                 "bounds": [x, y, w, h]})
        self.regions.append({"id": park_id, "name": name, "bounds": [x, y, w, h],
                             "parent": "mosswood"})
        self.rect(x + 9, y, 2, h, PATH)
        self.rect(x, y + 7, w, 2, PATH)
        for xx, yy in ((x + 3, y + 3), (x + 15, y + 11)):
            self._object("bench", "Park bench", xx, yy, 2, 1,
                         [[xx, yy + 1]], capacity=1)
        for xx, yy in ((x + 2, y + 11), (x + 15, y + 3)):
            self.decorations.append({"kind": "tree", "x": xx, "y": yy, "variant": row})
        self._object("park_marker", name, x + 9, y + 7,
                     anchors=[[x + 9, y + 7], [x + 10, y + 7],
                              [x + 9, y + 8], [x + 10, y + 8]],
                     capacity=4, blocking=False)

    def _generate(self, seed):
        rng = random.Random(f"{self.LAYOUT_ID}:{seed}")
        self.width, self.height = WIDTH, self.MAP_HEIGHT
        self.cells = array("B", [GRASS]) * (self.width * self.height)
        self.regions = [{"id": "mosswood", "name": "Mosswood",
                         "bounds": [0, 0, self.width, self.height], "parent": None}]
        self.planning_metadata = {"layout_id": self.LAYOUT_ID,
                                  "name": "Mosswood Lindenviertel",
                                  "seed": seed, "roads": [], "parks": [],
                                  "street_hierarchy": ["arterial", "local", "pedestrian"],
                                  "runtime_floors": [0],
                                  "scope": "2-D active neighborhood; no multi-floor runtime claim"}
        for y in self.ROAD_ROWS:
            arterial = y in (74, 125)
            self._road("Market Avenue" if y == 74 else "Commons Avenue" if y == 125
                       else f"Neighbourhood Lane {y}", 0, y,
                       self.width, 3 if arterial else 2,
                       "arterial" if arterial else "local")
            if y > 0:
                self.rect(0, y - 1, self.width, 1, PATH)
        for x in (1, 126):
            self._road("East Connector" if x == 126 else "West Connector",
                       x, 0, 2, self.height, "local")
        # Dogleg mid-block paths break up the grid; every path meets a street.
        for x, ya, yb in ((26, 21, 74), (51, 0, 48), (77, 74, 125),
                          (102, 125, 175)):
            self.rect(x, ya, 1, yb - ya + 1, PATH)
            self.planning_metadata["roads"].append(
                {"name": "Mid-block walk", "class": "pedestrian",
                 "bounds": [x, ya, 1, yb - ya + 1]})
        for row in range(4):
            for col in range(5):
                self._home(row * 5 + col, row, col, rng)
        services = (
            ("school", "studio", None, "hospital", "fire_station"),
            ("cafe", "shop", None, "gym", "nightclub"),
            ("town_hall", "office_hub", "supermarket", "shopping_center", "workshop"),
        )
        for row, entries in enumerate(services):
            for col, kind in enumerate(entries):
                if kind is None:
                    self._park(col, row, "Clover Green" if row == 1 else "School Green")
                else:
                    self._service(kind, col, row, rng)
        self._object("fountain", "Clover Green fountain", 67, 83, 2, 2,
                     [[69, 85], [67, 85]], capacity=2)
        for x, y in ((11, 23), (38, 49), (87, 75), (110, 100), (16, 126), (89, 152)):
            self.decorations.append({"kind": "lamp", "x": x, "y": y, "variant": 0})
        self.blocked.update((i % self.width, i // self.width)
                            for i, terrain in enumerate(self.cells)
                            if terrain in (WALL, WATER))
        for item in self.decorations:
            if item["kind"] == "tree":
                self.blocked.add((item["x"], item["y"]))
        self._validate_anchors()
        self._validate_connections()
        self.park_patrol = [[62, 87], [63, 87], [64, 87], [65, 87],
                            [65, 88], [65, 89], [64, 89], [63, 89],
                            [62, 89], [62, 88]]
        if not all(self.walkable(point) for point in self.park_patrol):
            raise ValueError("Park patrol contains a blocked cell")
        if not all(abs(a[0]-b[0])+abs(a[1]-b[1]) == 1 for a,b in zip(
                self.park_patrol, self.park_patrol[1:] + self.park_patrol[:1])):
            raise ValueError("Park patrol is not a contiguous loop")

    def _validate_connections(self):
        start = (1, 74)
        if not self.walkable(start):
            raise ValueError("Main avenue has no walkable start")
        seen, queue = {start}, deque([start])
        while queue:
            x, y = queue.popleft()
            for point in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if point not in seen and self.walkable(point):
                    seen.add(point)
                    queue.append(point)
        for building in self.buildings:
            if tuple(building["door"]) not in seen or tuple(building["frontage"]) not in seen:
                raise ValueError(f"Disconnected frontage: {building['id']}")
        for obj in self.objects.values():
            for anchor in obj["anchors"]:
                if tuple(anchor) not in seen:
                    raise ValueError(f"Disconnected object anchor: {obj['id']} {anchor}")
        self.planning_metadata["connected_walkable_cells"] = len(seen)
        self.planning_metadata["validated_entrances"] = len(self.buildings)
        self.planning_metadata["validated_object_anchors"] = sum(
            len(obj["anchors"]) for obj in self.objects.values())

    def spawn_for(self, household_id, member_index):
        household = next((h for h in self.households if h["id"] == household_id), None)
        if household is None or not isinstance(member_index, int) or not 0 <= member_index < 3:
            raise ValueError("Unknown household or member slot")
        building = next(b for b in self.buildings if b["id"] == household["building_id"])
        x, y = building["x"], building["y"]
        candidates = [[xx, yy] for yy in range(y + building["h"] - 2, y, -1)
                      for xx in range(x + 1, x + building["w"] - 1)
                      if self.walkable((xx, yy)) and self.cells[yy * self.width + xx] == FLOOR]
        candidates.sort(key=lambda point: (abs(point[0] - building["door"][0])
                                           + abs(point[1] - building["door"][1]),
                                           point[1], point[0]))
        selected = candidates[member_index]
        if self.path(building["door"], selected) is None:
            raise ValueError(f"Unreachable resident spawn: {household_id}")
        return selected
