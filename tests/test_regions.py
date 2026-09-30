import unittest
from living_world.generation.regions import generate_region, route_to_room
from living_world.generation.rooms import GenerationError


class RegionTests(unittest.TestCase):
    def test_region_instantiates_buildings_and_connects_every_entrance(self):
        region = generate_region(42)
        self.assertTrue(region['validation']['valid'])
        self.assertEqual(region, generate_region(42))
        for plot in region['plots']:
            self.assertTrue(plot['design']['validation']['valid'])
            self.assertIn(plot['door'], region['public_walkable'])
            for floor in plot['design']['floors']:
                for room in floor['rooms']:
                    route = route_to_room(region, plot['id'], room['id'])
                    self.assertTrue(route['valid'])
                    self.assertEqual(route['public_path'][-1], plot['door'])
                    self.assertEqual(route['interior_route']['start'], plot['design']['entrance'])

    def test_landscape_regions_and_explicit_zones(self):
        for zones in (['park','water'], ['industrial','civic'], ['residential','commercial']):
            region = generate_region(7, 2, 1, zones)
            self.assertTrue(region['validation']['valid'])
            all_zones = [p['zone'] for p in region['plots']] + [p['zone'] for p in region['landscapes']]
            self.assertCountEqual(all_zones,zones)

    def test_rejects_bad_region_parameters(self):
        for args in ({'columns':5}, {'rows':0}, {'zones':['unknown']}, {'seed':-1}):
            with self.assertRaises(GenerationError):
                generate_region(**args)


if __name__ == '__main__':
    unittest.main()
