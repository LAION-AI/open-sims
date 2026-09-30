import unittest

from living_world.generation.bed_variants import (
    BED_CAPACITIES,
    BED_SPECS,
    BED_TRAITS,
    bed_placement_access,
)
from living_world.generation.catalog import CATALOG, Furniture, placed


class BedVariantTests(unittest.TestCase):
    def test_specs_are_furniture_compatible_and_namespaced(self):
        expected = {
            "bed_storage_single", "bed_loft", "bed_bunk", "bed_queen",
            "bed_king", "bed_platform_double", "bed_foldaway_guest",
            "bed_hospital",
        }
        self.assertEqual(set(BED_SPECS), expected)
        for kind, spec in BED_SPECS.items():
            furniture = Furniture(**spec)
            self.assertEqual(furniture.sprite, kind)
            self.assertGreater(furniture.w, 0)
            self.assertGreater(furniture.h, 0)
            self.assertTrue(furniture.wall)
            self.assertTrue(furniture.front)

    def test_metadata_covers_every_variant(self):
        self.assertEqual(set(BED_CAPACITIES), set(BED_SPECS))
        self.assertEqual(set(BED_TRAITS), set(BED_SPECS))
        for kind in BED_SPECS:
            self.assertIn(BED_CAPACITIES[kind], (1, 2))
            self.assertIn("sleep", BED_TRAITS[kind]["interactions"])
            self.assertIn("rest", BED_TRAITS[kind]["interactions"])
        self.assertEqual(BED_CAPACITIES["bed_bunk"], 2)
        self.assertIn("adjust_backrest", BED_TRAITS["bed_hospital"]["interactions"])
        self.assertNotIn("adjust_backrest", BED_TRAITS["bed_queen"]["interactions"])

    def test_access_geometry_fits_minimum_rooms_and_rotates(self):
        for kind, spec in BED_SPECS.items():
            for orientation in range(4):
                w, h = spec["w"], spec["h"]
                rw, rh = (h, w) if orientation % 2 else (w, h)
                # Align the headboard edge with the corresponding room wall.
                x, y = [(1, 0), (6 - rw, 1), (1, 6 - rh), (0, 1)][orientation]
                placement = bed_placement_access(kind, x, y, orientation)
                self.assertEqual((placement["base_w"], placement["base_h"]),
                                 (spec["w"], spec["h"]))
                self.assertEqual(placement["anchors"], placement["clearance"])
                self.assertTrue(placement["clearance"])
                # The footprint and access cells fit the project's 6x6 minimum
                # room when placed against the matching wall by the host.
                self.assertLessEqual(placement["w"], 6)
                self.assertLessEqual(placement["h"], 6)
                self.assertGreaterEqual(min(p[0] for p in placement["clearance"]), 0)
                self.assertGreaterEqual(min(p[1] for p in placement["clearance"]), 0)
                self.assertLessEqual(max(p[0] for p in placement["clearance"]), 5)
                self.assertLessEqual(max(p[1] for p in placement["clearance"]), 5)

    def test_access_includes_foot_edge_and_climb_side(self):
        placement = bed_placement_access("bed_queen", 1, 1)
        self.assertIn([1, 4], placement["clearance"])
        self.assertIn([3, 2], placement["clearance"])

    def test_integrated_placed_geometry_matches_variant_helper(self):
        missing = set(BED_SPECS) - set(CATALOG)
        if missing:
            self.skipTest("catalog integration pending: " + ", ".join(sorted(missing)))
        for kind in BED_SPECS:
            for orientation in range(4):
                with self.subTest(kind=kind, orientation=orientation):
                    expected = bed_placement_access(kind, 1, 1, orientation)
                    actual = placed(kind, 1, 1, orientation)
                    for field in ("kind", "name", "sprite", "w", "h", "base_w",
                                  "base_h", "orientation", "clearance", "anchors", "tall"):
                        self.assertEqual(actual[field], expected[field], field)


if __name__ == "__main__":
    unittest.main()
