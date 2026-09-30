"""Schema and isolation checks for the additive public-institution library."""
from copy import deepcopy
import re
from pathlib import Path
import unittest

from living_world.generation.rooms import generate_room
from living_world.generation.catalog import CATALOG, ROOMS, Furniture
from living_world.generation.civic_catalog import (
    BUILDING_TEMPLATES, CIVIC_AFFORDANCES, CIVIC_OBJECT_ROLES, CIVIC_OBJECT_SPECS,
    CIVIC_ROOMS, PUBLIC_BUILDING_BACKLOG,
)


class CivicCatalogTests(unittest.TestCase):
    def test_furniture_specs_are_constructor_compatible_and_complete(self):
        self.assertGreaterEqual(len(CIVIC_OBJECT_SPECS), 15)
        before = deepcopy((CATALOG, ROOMS))
        for key, spec in CIVIC_OBJECT_SPECS.items():
            self.assertTrue(key.startswith(("school_", "clinic_", "hospital_", "fire_", "civic_")))
            furniture = Furniture(**spec)
            self.assertGreater(furniture.w, 0)
            self.assertGreater(furniture.h, 0)
            self.assertEqual(spec["sprite"], key)
        self.assertEqual(set(CIVIC_OBJECT_ROLES), set(CIVIC_OBJECT_SPECS))
        self.assertEqual(set(CIVIC_AFFORDANCES), set(CIVIC_OBJECT_SPECS))
        known_actions = {"inspect", "sleep", "rest", "make_bed", "adjust_backrest", "sit", "read", "study", "work", "store", "retrieve", "wash", "cook", "eat", "drink", "play", "exercise", "water", "feed_fish", "perform", "repair", "teach", "observe_sample", "simulate_experiment", "check_in", "examine", "monitor", "equip", "dispatch"}
        for affordance in CIVIC_AFFORDANCES.values():
            self.assertTrue(set(affordance["actions"]).issubset(known_actions))
        self.assertEqual((CATALOG, ROOMS), before, "Import and inspection must not mutate shared catalogs")

    def test_room_templates_match_the_existing_room_contract(self):
        for room_id, room in CIVIC_ROOMS.items():
            self.assertEqual(set(room), {"name", "size", "minimum", "required", "optional", "families"})
            self.assertGreaterEqual(room["size"][0], room["minimum"][0])
            self.assertGreaterEqual(room["size"][1], room["minimum"][1])
            kinds = set(room["required"] + room["optional"])
            self.assertTrue(kinds.issubset(CIVIC_OBJECT_SPECS), room_id)
            self.assertTrue(room["families"])
            self.assertTrue(room["name"])
            self.assertTrue(all(family for family in room["families"]))
            self.assertNotIn(room["name"], {"Classroom", "Science Laboratory", "Staff Room", "School Cafeteria", "Examination Room"})
        self.assertEqual(CIVIC_ROOMS["school_classroom"]["required"].count("school_student_desk"), 20)
        self.assertEqual(CIVIC_ROOMS["school_classroom"]["required"].count("school_student_chair"), 20)
        self.assertEqual(CIVIC_ROOMS["school_cafeteria"]["required"].count("civic_cafeteria_table"), 2)

    def test_building_program_references_and_backlog_status(self):
        for building, spec in BUILDING_TEMPLATES.items():
            self.assertIn(spec["profile"], {"education", "health_service", "emergency_service"})
            self.assertEqual(spec["status"], "prototype")
            self.assertFalse(spec["constraints_enforced"])
            self.assertIn("design intent only", spec["constraint_note"])
            self.assertIn("name", spec)
            self.assertEqual(spec["room_program"], spec["rooms"])
            room_ids = set(spec["rooms"])
            self.assertTrue(room_ids.issubset(CIVIC_ROOMS), building)
            self.assertEqual(room_ids, set(spec["access"]))
            self.assertEqual(room_ids, set(spec["privacy"]))
            for a, b in spec["adjacency"]:
                self.assertIn(a, room_ids)
                self.assertIn(b, room_ids)
        self.assertGreaterEqual(len(PUBLIC_BUILDING_BACKLOG), 20)
        statuses = {entry["status"] for entry in PUBLIC_BUILDING_BACKLOG}
        self.assertEqual(statuses, {"implemented", "planned"})
        self.assertTrue({"school", "hospital", "fire station", "university", "town hall", "library", "police station", "courthouse", "museum", "transit station", "post office", "eldercare", "daycare", "sports center"}.issubset({row["building"] for row in PUBLIC_BUILDING_BACKLOG}))

    def test_each_civic_object_has_a_renderer_branch(self):
        source = (Path(__file__).resolve().parents[1] / "web" / "civic-drawing.js").read_text(encoding="utf-8")
        rendered = set(re.findall(r"case '([a-z_]+)'", source))
        self.assertEqual(rendered, set(CIVIC_OBJECT_SPECS))
        self.assertIn("export function drawCivicObject(c,o,palette)", source)
        self.assertIn("o.base_w*s", source)
        self.assertIn("o.base_h*s", source)

    def test_minimum_and_default_programs_generate_across_doors_and_seeds(self):
        objects = {**CATALOG, **{key: Furniture(**spec) for key, spec in CIVIC_OBJECT_SPECS.items()}}
        rooms = {**ROOMS, **CIVIC_ROOMS}
        for room_id, spec in CIVIC_ROOMS.items():
            for dimensions in (spec["minimum"], spec["size"]):
                for side in ("north", "east", "south", "west"):
                    for seed in range(4):
                        with self.subTest(room=room_id, size=dimensions, door=side, seed=seed):
                            room = generate_room(room_id, seed=seed, width=dimensions[0], height=dimensions[1], door_side=side, object_catalog=objects, room_catalog=rooms)
                            self.assertTrue(room["validation"]["valid"], room["validation"]["errors"])
                            self.assertLess(room["search"]["nodes"], 2400)
                            counts = {}
                            for kind in room["required_kinds"]:
                                counts[kind] = counts.get(kind, 0) + 1
                            actual = {}
                            for obj in room["objects"]:
                                actual[obj["kind"]] = actual.get(obj["kind"], 0) + 1
                            self.assertTrue(all(actual.get(kind, 0) >= count for kind, count in counts.items()))
                            if room_id == "school_classroom":
                                seats = room["capacity"]["students"]
                                self.assertIn(seats, (20, 24))
                                self.assertEqual(actual["school_student_desk"], seats)
                                self.assertEqual(actual["school_student_chair"], seats)
                                self.assertEqual(room["seating_layout"]["rows"] * 4, seats)


if __name__ == "__main__":
    unittest.main()
