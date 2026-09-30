import unittest
from copy import deepcopy

from living_world.generation.buildings import generate_building
from living_world.generation.navigation import FloorNavigation
from living_world.generation.demo import NavigationDemo
from living_world.generation.rooms import GenerationError, generate_room, validate_room


class BuildingGenerationTests(unittest.TestCase):
    def test_family_area_budgets_and_staggered_partitions(self):
        house = generate_building({"width": 18, "depth": 19, "room_count": 6,
                                   "levels_above_ground": 2, "basements": 0,
                                   "residents": {"adults": 2, "children": 1, "teens": 0}})
        rooms = [room for floor in house["floors"] for room in floor["rooms"]]
        areas = {room["kind"]: room["width"] * room["height"] for room in rooms}
        self.assertGreater(areas["living"], areas["kitchen"])
        self.assertGreater(areas["kitchen"], areas["bathroom"])
        self.assertGreater(areas["bedroom"], areas["bathroom"])
        self.assertGreater(len(set((r["width"], r["height"]) for r in rooms)), 3)
        self.assertGreater(len(set(r["origin"][1] for r in house["floors"][0]["rooms"])), 2)
        for room in rooms:
            budget = room["area_budget_m2"]
            self.assertLessEqual(budget["minimum"], budget["actual"])
            self.assertLessEqual(budget["actual"], budget["maximum"])
        self.assertTrue(house["validation"]["valid"])

    def test_school_has_actual_accessible_pupil_seats(self):
        program = ["school_classroom", "school_lab", "school_staff", "school_cafeteria"]
        house = generate_building({"width": 29, "depth": 29, "room_count": len(program),
                                   "levels_above_ground": 1, "basements": 0,
                                   "residents": {"adults": 0, "children": 0, "teens": 0},
                                   "room_program": program})
        classroom = next(r for r in house["floors"][0]["rooms"] if r["kind"] == "school_classroom")
        desks = [o for o in classroom["objects"] if o["kind"] == "school_student_desk"]
        chairs = [o for o in classroom["objects"] if o["kind"] == "school_student_chair"]
        self.assertEqual(len(desks), len(chairs))
        self.assertEqual(len(desks), classroom["capacity"]["students"])
        self.assertEqual(house["validation"]["student_capacity"], len(chairs))
        self.assertGreaterEqual(len(chairs), 20)
        self.assertTrue(classroom["validation"]["valid"])
        tampered = deepcopy(classroom)
        tampered["capacity"]["students"] += 1
        self.assertIn("classroom_capacity_mismatch", validate_room(tampered)["errors"])

    def test_deterministic_family_with_child_and_teen(self):
        request = {"width": 24, "depth": 25, "room_count": 6,
                   "levels_above_ground": 2, "basements": 1,
                   "residents": {"adults": 2, "children": 1, "teens": 1},
                   "elevator": True, "seed": 81}
        first = generate_building(request)
        self.assertEqual(first, generate_building(request))
        self.assertTrue(first["validation"]["valid"])
        self.assertEqual(first["validation"]["room_count"], 6)
        self.assertEqual(first["validation"]["sleep_capacity"]["adults_provided"], 2)
        self.assertGreaterEqual(first["validation"]["sleep_capacity"]["children_provided"], 1)
        self.assertGreaterEqual(first["validation"]["sleep_capacity"]["teens_provided"], 1)
        coverage = first["validation"]["footprint_coverage"]
        self.assertEqual(coverage["assigned_cells"] + coverage["unassigned_cells"], coverage["footprint_cells"])
        self.assertEqual([f["elevation"] for f in first["floors"]], [-1, 0, 1])
        nav = FloorNavigation(first)
        for floor in first["floors"]:
            for obj in floor["objects"]:
                for x, y in obj["anchors"]:
                    self.assertIsNotNone(nav.route(first["entrance"], [floor["level"], x, y]))

    def test_explicit_teens_program_has_typed_sleep_slots(self):
        request = {"width": 26, "depth": 20, "room_count": 6,
                   "levels_above_ground": 2, "basements": 0,
                   "residents": {"adults": 2, "children": 0, "teens": 2},
                   "room_program": ["living", "kitchen", "bathroom", "bedroom", "teen", "teen"],
                   "terrace_exit": True}
        house = generate_building(request)
        self.assertTrue(house["validation"]["sleep_capacity_valid"])
        self.assertEqual(house["validation"]["room_count"], 6)
        self.assertIn("terrace_exit", house)
        self.assertIsNotNone(FloorNavigation(house).route(house["entrance"], house["terrace_exit"]))

    def test_basement_stair_and_lift_routes(self):
        house = generate_building({"width": 20, "depth": 20, "room_count": 4,
                                   "levels_above_ground": 2, "basements": 1,
                                   "residents": {"adults": 2, "children": 0, "teens": 0},
                                   "room_program": ["living", "kitchen", "bathroom", "bedroom"], "elevator": True})
        nav = FloorNavigation(house)
        for mode in ("stairs", "elevator"):
            basement_portal = next(p for p in house["portals"] if p["kind"] == mode and p["from"][0] == 0)
            route = nav.route(house["entrance"], basement_portal["from"], transport=mode)
            self.assertIsNotNone(route)
            self.assertTrue(any(step["kind"] == mode for step in route["steps"]))

    def test_navigation_demo_accepts_generated_building(self):
        house = generate_building({"width": 20, "depth": 20, "room_count": 4,
                                   "levels_above_ground": 2, "basements": 1,
                                   "residents": {"adults": 2, "children": 0, "teens": 0},
                                   "room_program": ["living", "kitchen", "bathroom", "bedroom"]})
        demo = NavigationDemo(house)
        snapshot = demo.advance(30)
        self.assertEqual(snapshot["invariant_errors"], [])

    def test_rejects_unfit_dimensions_or_missing_sleep_capacity(self):
        with self.assertRaisesRegex(GenerationError, "Footprint"):
            generate_building({"width": 12, "depth": 10, "room_count": 4,
                               "levels_above_ground": 1, "basements": 0,
                               "residents": {"adults": 2, "children": 0, "teens": 0},
                               "room_program": ["bedroom", "living", "kitchen", "bathroom"]})
        with self.assertRaisesRegex(GenerationError, "sleep capacity"):
            generate_building({"width": 20, "depth": 16, "room_count": 4,
                               "levels_above_ground": 1, "basements": 0,
                               "residents": {"adults": 2, "children": 1, "teens": 0},
                               "room_program": ["bedroom", "living", "kitchen", "bathroom"]})
        with self.assertRaisesRegex(GenerationError, "exactly room_count"):
            generate_building({"width": 20, "depth": 16, "room_count": 2,
                               "levels_above_ground": 1, "basements": 0,
                               "residents": {"adults": 0, "children": 0, "teens": 0},
                               "room_program": ["living"]})
        with self.assertRaisesRegex(GenerationError, "Unknown request fields"):
            generate_building({"footprint": [[0, 0], [1, 0]], "width": 12, "depth": 13,
                               "room_count": 1, "levels_above_ground": 1,
                               "residents": {"adults": 0, "children": 0, "teens": 0}})
        with self.assertRaisesRegex(GenerationError, "Unsupported room type"):
            generate_building({"width": 12, "depth": 13, "room_count": 1,
                               "levels_above_ground": 1, "basements": 0,
                               "residents": {"adults": 0, "children": 0, "teens": 0}},
                              room_catalog={})

    def test_valid_small_rectangular_footprints(self):
        for width, depth in ((12, 13), (18, 13), (16, 18), (22, 18)):
            house = generate_building({"width": width, "depth": depth, "room_count": 1,
                                       "levels_above_ground": 1, "basements": 0,
                                       "residents": {"adults": 0, "children": 0, "teens": 0},
                                       "room_program": ["living"]})
            self.assertEqual((house["width"], house["height"]), (width, depth))
            self.assertTrue(house["validation"]["valid"])

    def test_room_to_corridor_walls_are_open_only_at_doors(self):
        house = generate_building({"width": 25, "depth": 19, "room_count": 6,
                                   "levels_above_ground": 2, "basements": 0,
                                   "residents": {"adults": 2, "children": 1, "teens": 0}})
        for floor in house["floors"]:
            width = floor["width"]
            openings = {}
            for room in floor["rooms"]:
                x, y = room["origin"]
                door = room["doors"][0]
                if door["side"] == "south":
                    wall_y = y + room["height"]
                    door_x = x + door["cell"][0]
                else:
                    wall_y = y - 1
                    door_x = x + door["cell"][0]
                openings.setdefault(wall_y, set()).add(door_x)
                expected_outside = "north" if door["side"] == "south" else "south"
                self.assertTrue(all(window["side"] == expected_outside for window in room["windows"]))
            for wall_y, door_xs in openings.items():
                walkable = {i % width for i, value in enumerate(floor["terrain"])
                            if i // width == wall_y and value}
                self.assertEqual(walkable, door_xs)

    def test_adjacent_rooms_have_solid_separator_columns(self):
        house = generate_building({"width": 25, "depth": 21, "room_count": 8,
                                   "levels_above_ground": 2, "basements": 0,
                                   "residents": {"adults": 2, "children": 1, "teens": 0}})
        for floor in house["floors"]:
            groups = {}
            for room in floor["rooms"]:
                groups.setdefault(room["origin"][1], []).append(room)
            for row in groups.values():
                row.sort(key=lambda room: room["origin"][0])
                for left, right in zip(row, row[1:]):
                    separator_x = left["origin"][0] + left["width"]
                    self.assertEqual(right["origin"][0], separator_x + 1)
                    for y in range(max(left["origin"][1], right["origin"][1]),
                                   min(left["origin"][1] + left["height"], right["origin"][1] + right["height"])):
                        self.assertEqual(floor["terrain"][y * floor["width"] + separator_x], 0)


if __name__ == "__main__":
    unittest.main()
