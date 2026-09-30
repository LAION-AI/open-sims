"""City grammar, real interior routes, and append-only service anchors."""
import unittest

from living_world.generation.city import SERVICES, generate_city, route_to_city_room
from living_world.generation.rooms import GenerationError
from living_world.spatial import SpatialService, WATER


class CityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.city = generate_city(seed=42)

    def test_services_streets_and_lots_are_connected(self):
        city = self.city
        self.assertTrue(city["validation"]["valid"])
        self.assertEqual(set(city["validation"]["services"]), set(SERVICES))
        self.assertEqual(city["validation"]["connected_entrances"], len(city["plots"]))
        self.assertEqual(city["validation"]["connected_public_cells"], len(city["public_walkable"]))
        self.assertGreater(len(set(city["block_widths"])), 1)
        self.assertGreater(len(set(city["block_heights"])), 1)
        self.assertTrue({"arterial", "local", "pedestrian"}.issubset({e["class"] for e in city["edges"]}))
        for plot in city["plots"]:
            x, y, w, h = plot["bounds"]
            bx, by, bw, bh = plot["building_bounds"]
            self.assertTrue(x <= bx and y <= by and bx + bw <= x + w and by + bh <= y + h)
            self.assertTrue(plot["design"]["validation"]["valid"])
            self.assertTrue(plot["footpath"])
        for pond in (land for land in city["landscapes"] if land["zone"] == "water"):
            px, py, pw, ph = pond["bounds"]
            self.assertFalse(any(px <= plot["door"][0] < px + pw and py <= plot["door"][1] < py + ph
                                 for plot in city["plots"]))

    def test_capacity_and_jobs_come_from_instantiated_objects(self):
        for plot in self.city["plots"]:
            design = plot["design"]
            kinds = [obj["kind"] for floor in design["floors"] for obj in floor["objects"]]
            self.assertEqual(plot["capacity"]["jobs"], len(plot["jobs"]))
            for job in plot["jobs"]:
                self.assertTrue(any(obj["id"] == job["object_id"] for floor in design["floors"]
                                    for obj in floor["objects"]))
            if plot["service"] == "school":
                self.assertEqual(plot["capacity"]["students"], kinds.count("school_student_chair"))
                self.assertIn(plot["capacity"]["students"], (20, 24))
            if plot["service"] in {"town_hall", "shopping_center", "supermarket"}:
                self.assertTrue(plot["program_fallback"])
        self.assertGreater(self.city["validation"]["jobs"], 0)

    def test_public_to_room_route_and_rejection(self):
        for plot in self.city["plots"]:
            room = plot["design"]["floors"][0]["rooms"][0]
            route = route_to_city_room(self.city, plot["id"], room["id"])
            self.assertTrue(route["valid"])
            self.assertEqual(route["public_path"][-1], plot["door"])
            self.assertEqual(route["interior_route"]["start"], plot["design"]["entrance"])
        with self.assertRaisesRegex(GenerationError, "Unknown plot"):
            route_to_city_room(self.city, "missing", "missing")

    def test_seed_and_brief_are_deterministic_and_bounded(self):
        other = generate_city(seed=43)
        self.assertNotEqual((self.city["block_widths"], self.city["block_heights"]),
                            (other["block_widths"], other["block_heights"]))
        self.assertEqual(self.city["block_widths"], generate_city(seed=42)["block_widths"])
        for kwargs in ({"columns": 3}, {"rows": 6}, {"seed": True}):
            with self.assertRaises(GenerationError):
                generate_city(**kwargs)

    def test_main_map_preserves_old_object_ids_and_adds_reachable_services(self):
        spatial = SpatialService(42)
        self.assertIn("object_0349", spatial.objects)
        self.assertEqual(spatial.objects["object_0349"]["kind"], "bin")
        self.assertEqual(spatial.objects["object_0001"]["kind"], "door")
        self.assertEqual(spatial.cells[23 * spatial.width + 10], 1)  # old road
        kinds = {"gym_station", "nightclub_floor", "townhall_desk", "hospital_desk",
                 "fire_stationdesk", "office_station", "supermarket_checkout", "mall_counter"}
        stations = [obj for obj in spatial.objects.values() if obj["kind"] in kinds]
        self.assertEqual({obj["kind"] for obj in stations}, kinds)
        self.assertEqual(len(stations), 8)
        for obj in stations:
            self.assertGreater(int(obj["id"].split("_")[1]), 349)
            self.assertGreater(obj["y"], 153)
            self.assertIsNotNone(spatial.path((1, 120), obj["anchors"][0]))
            self.assertNotEqual(spatial.cells[obj["y"] * spatial.width + obj["x"]], WATER)


if __name__ == "__main__":
    unittest.main()
