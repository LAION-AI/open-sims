"""New-save active neighborhood: geometry, fixtures and reachable services."""
import unittest

from living_world.neighborhood import LivingNeighborhood
from living_world.spatial import FLOOR, ROAD, WALL, WATER


class NeighborhoodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map = LivingNeighborhood(42)

    def test_new_save_contract_and_mixed_use(self):
        place = self.map
        self.assertEqual((place.width, place.height), (128, 326))
        self.assertEqual(len(place.households), 21)
        self.assertEqual([h["id"] for h in place.households],
                         [f"household_{i:02}" for i in range(1, 21)]+['student_residence'])
        self.assertEqual([b["id"] for b in place.buildings[:20]],
                         [f"home_{i:02}" for i in range(1, 21)])
        self.assertEqual(len(place.buildings), 41)
        metadata = place.planning_metadata
        self.assertEqual(metadata["layout_id"], "neighborhood-v1")
        self.assertEqual(metadata["runtime_floors"], [0, 1, 2])
        self.assertEqual(metadata["validated_entrances"], 41)
        self.assertEqual(metadata["validated_object_anchors"],
                         sum(len(o["anchors"]) for o in place.objects.values()))
        self.assertEqual({road["class"] for road in metadata["roads"]},
                         {"arterial", "local", "pedestrian"})
        self.assertEqual(len(metadata["parks"]), 3)
        self.assertEqual(place.public_data()["planning_metadata"], metadata)
        for b in place.buildings:
            self.assertIsNotNone(place.path(b["frontage"], b["door"]))
            self.assertEqual(place.cells[b["door"][1] * place.width + b["door"][0]], 2)

    def test_house_families_have_real_beds_and_unequal_rooms(self):
        place = self.map
        homes = place.buildings[:20]
        self.assertEqual(len({b["plan_variant"] for b in homes}), 3)
        self.assertGreater(len({(b["x"], b["w"]) for b in homes}), 5)
        for i, home in enumerate(homes):
            hid = f"household_{i+1:02}"
            members = 3 if i % 5 == 2 else 2
            owned = [obj for obj in place.objects.values()
                     if obj["household_id"] == hid]
            kinds = {obj["kind"] for obj in owned}
            self.assertTrue({"fridge", "sink", "counter", "table", "sofa", "toilet",
                             "shower", "bed", "bin"}.issubset(kinds))
            beds = [obj for obj in owned if obj["kind"] == "bed"]
            self.assertEqual(sum(obj["capacity"] for obj in beds), members)
            self.assertTrue(all(obj["bed_variant"] in {"single", "double"} for obj in beds))
            table = next(obj for obj in owned if obj["kind"] == "table")
            self.assertGreaterEqual(table["capacity"], members)
            self.assertGreaterEqual(len(table["anchors"]), members)
            rooms = [region for region in place.regions if region["parent"] == home["id"]]
            self.assertEqual(len(rooms), 7 if members == 3 else 6)
            areas = {r["id"].rsplit("_", 1)[-1]: r["bounds"][2] * r["bounds"][3]
                     for r in rooms}
            self.assertLess(areas["bathroom"], areas["bedroom"])
            self.assertLessEqual(areas["kitchen"], 12)
            self.assertLess(areas["kitchen"], areas["living"])
            if members == 3:
                self.assertIn("child_room", home["rooms"][-1])
                self.assertEqual(len(beds), 2)
            starts = [place.spawn_for(hid, member) for member in range(members)]
            self.assertEqual(len({tuple(point) for point in starts}), members)
            self.assertTrue(all(place.walkable(point) for point in starts))
            self.assertTrue(all(place.cells[p[1] * place.width + p[0]] == FLOOR for p in starts))

    def test_service_jobs_chairs_and_all_anchors_are_physical(self):
        place = self.map
        service_ids = {"school", "studio", "workshop", "cafe", "shop", "gym",
                       "nightclub", "town_hall", "hospital", "fire_station",
                       "office_hub", "supermarket", "shopping_center",
                       "kindergarten", "pool", "bar", "community_center",
                       "university", "student_dorm", "student_dorm_floor_1",
                       "student_dorm_floor_2"}
        self.assertEqual({b["id"] for b in place.buildings[20:]}, service_ids)
        station_kinds = {"teacher_station", "illustrator_station", "designer_station",
                         "carpenter_station", "tailor_station", "gardener_station",
                         "cafe_counter", "shop_counter", "gym_station",
                         "nightclub_floor", "townhall_desk", "hospital_desk",
                         "fire_stationdesk", "office_station", "supermarket_checkout",
                         "mall_counter", "kindergarten_desk", "kindergarten_mat",
                         "pool_water", "lifeguard_station", "bar_counter", "dj_booth",
                         "community_table"}
        self.assertTrue(station_kinds.issubset({o["kind"] for o in place.objects.values()}))
        chairs = [o for o in place.objects.values() if o["kind"] == "school_student_chair"]
        desks = [o for o in place.objects.values() if o["kind"] == "school_student_desk"]
        beds = [o for o in place.objects.values() if o["kind"] == "hospital_bed"]
        self.assertEqual(len(chairs), 24)
        self.assertEqual(len(desks), 24)
        self.assertEqual(len([o for o in place.objects.values() if o["kind"] == "chalkboard"]), 1)
        self.assertEqual({tuple(o["anchors"][0]) for o in chairs},
                         {tuple(o["anchors"][0]) for o in desks})
        self.assertEqual(len(beds), 3)
        occupied = set()
        for obj in place.objects.values():
            self.assertLessEqual(obj["capacity"], len(obj["anchors"]))
            self.assertTrue(all(place.walkable(anchor) for anchor in obj["anchors"]))
            if obj["blocking"]:
                cells = {(x, y) for x in range(obj["x"], obj["x"] + obj["w"])
                         for y in range(obj["y"], obj["y"] + obj["h"])}
                self.assertFalse(cells & occupied, obj["id"])
                occupied.update(cells)
        self.assertTrue(all(place.walkable(point) for point in place.park_patrol))
        self.assertTrue(all(abs(a[0]-b[0]) + abs(a[1]-b[1]) == 1
                            for a,b in zip(place.park_patrol,
                                           place.park_patrol[1:] + place.park_patrol[:1])))
        terrain = place.cells
        for b in place.buildings:
            self.assertNotIn(terrain[b["door"][1] * place.width + b["door"][0]],
                             (WALL, WATER))
        self.assertIn(ROAD, terrain)

    def test_seeded_variation_and_no_disconnected_anchors(self):
        first = LivingNeighborhood(3)
        replay = LivingNeighborhood(3)
        other = LivingNeighborhood(7)
        self.assertEqual(first.cells, replay.cells)
        self.assertEqual(first.buildings, replay.buildings)
        self.assertNotEqual(first.buildings, other.buildings)
        for seed in range(8):
            place = LivingNeighborhood(seed)
            self.assertEqual(place.planning_metadata["validated_entrances"], 41)
            self.assertEqual(place.planning_metadata["validated_object_anchors"],
                             sum(len(obj["anchors"]) for obj in place.objects.values()))


if __name__ == "__main__":
    unittest.main()
