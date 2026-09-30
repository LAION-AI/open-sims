"""Hard-layout regression, reproducibility, and adversarial accessibility cases."""
from copy import deepcopy
import os
import subprocess
import sys
import re
from pathlib import Path
import unittest

from living_world.generation.catalog import CATALOG, ROOMS, placed, rotate_cell
from living_world.generation.rooms import generate_room, validate_room, GenerationError
from living_world.generation.houses import generate_house, generate_district
from living_world.generation.navigation import FloorNavigation
from living_world.generation.demo import NavigationDemo


class GenerationTests(unittest.TestCase):
    def test_catalog_programs_and_sprite_coverage(self):
        self.assertGreaterEqual(len(ROOMS), 30)
        self.assertGreaterEqual(len(CATALOG), 112)
        self.assertTrue({'home_care','school_classroom','hospital_ward','fire_garage'}.issubset(ROOMS))
        referenced = set()
        for spec in ROOMS.values():
            for program in [spec['required'], spec['optional'], *spec.get('programs', {}).values()]:
                self.assertTrue(set(program).issubset(CATALOG))
                referenced.update(program)
            self.assertTrue(set(spec.get('programs', {})).issubset(spec['families']))
        self.assertEqual(referenced, set(CATALOG))
        source = '\n'.join((Path(__file__).resolve().parents[1]/'web'/name).read_text(encoding='utf-8') for name in ('generation-drawing.js','bed-variants-drawing.js','civic-drawing.js'))
        rendered = set(re.findall(r"case '([a-z_]+)'", source))
        self.assertEqual(rendered, set(CATALOG), 'Every furniture kind needs an actual sprite branch')

    def test_access_rings_rotate_with_new_equipment(self):
        pool = placed('pool_table', 5, 5)
        expected = {(x,4) for x in range(5,8)} | {(x,7) for x in range(5,8)} | {(4,y) for y in range(5,7)} | {(8,y) for y in range(5,7)}
        self.assertEqual({tuple(p) for p in pool['clearance']}, expected)
        for kind in CATALOG:
            original = placed(kind, 0, 0)
            for q in range(4):
                actual = placed(kind, 5, 5, q)
                expected = {(5+a,5+b) for a,b in (rotate_cell(x,y,original['w'],original['h'],q) for x,y in original['clearance'])}
                self.assertEqual({tuple(p) for p in actual['clearance']}, expected)
                self.assertFalse(expected & {(x,y) for x in range(actual['x'],actual['x']+actual['w']) for y in range(actual['y'],actual['y']+actual['h'])})

    def test_billiard_side_and_nursery_play_space_are_protected(self):
        room = next(r for seed in range(20) if (r:=generate_room('gaming',seed))['family']=='Billard & Arcade')
        pool = next(o for o in room['objects'] if o['kind']=='pool_table')
        x,y = pool['clearance'][-1]
        blocker = placed('plant',x,y);blocker['id']='blocked-billiard-side'
        room['objects'].append(blocker)
        self.assertIn('clearance_unreachable:'+pool['id'],validate_room(room)['errors'])
        nursery = generate_room('nursery',42)
        zone = next(z for z in nursery['zones'] if z['name']=='Freie Krabbelfläche')
        self.assertEqual(len(zone['cells']),4)
        self.assertTrue(set(nursery['required_kinds']).issuperset({'crib','changing_table'}))

    def test_extended_programs_are_real_not_just_labels(self):
        for kind in ('bathroom','teen','dining','office','nursery','laundry','library','music','gym','workshop','gaming'):
            programs = {tuple(generate_room(kind,seed)['required_kinds']) for seed in range(12)}
            self.assertGreaterEqual(len(programs),2,kind)
    def test_room_programs_many_seeds(self):
        for kind in ROOMS:
            for seed in range(12):
                with self.subTest(kind=kind, seed=seed):
                    room = generate_room(kind, seed)
                    self.assertTrue(validate_room(room)["valid"])
                    self.assertGreaterEqual(len(room["objects"]), len(room["required_kinds"]))

    def test_geometry_diversity_without_counting_palette_or_ids(self):
        rooms = [generate_room("living", seed) for seed in range(30)]
        self.assertGreaterEqual(len({r["signature"] for r in rooms}), 27)
        self.assertGreaterEqual(len({r["family"] for r in rooms}), 3)
        self.assertGreaterEqual(len({next(o for o in r["objects"] if o["kind"] == "sofa")["orientation"] for r in rooms}), 3)
        self.assertEqual(generate_room("living", 19), generate_room("living", 19))

    def test_reproducible_across_process_hash_seeds(self):
        code = "from living_world.generation.rooms import generate_room; import json; print(json.dumps(generate_room('living',42),sort_keys=True))"
        outputs = [subprocess.check_output([sys.executable, "-c", code], env={**os.environ, "PYTHONHASHSEED": seed}) for seed in ("1", "239")]
        self.assertEqual(outputs[0], outputs[1])

    def test_removed_clearance_is_not_a_validation_bypass(self):
        room = generate_room("kitchen", 10)
        room["objects"][0]["clearance"] = []
        self.assertTrue(any(e.startswith("geometry_contract:") for e in validate_room(room)["errors"]))

    def test_fish_tank_in_front_of_fridge_is_rejected(self):
        room = generate_room("kitchen", 8)
        fridge = next(o for o in room["objects"] if o["kind"] == "fridge")
        x, y = fridge["anchors"][0]
        tank = placed("aquarium", x, y)
        tank["id"] = "deliberately-bad-fish-tank"
        room["objects"].append(tank)
        result = validate_room(room)
        self.assertFalse(result["valid"])
        self.assertIn("clearance_unreachable:" + fridge["id"], result["errors"])

    def test_door_blocking_and_missing_furniture_are_rejected(self):
        room = generate_room("bedroom", 2)
        x, y = room["doors"][0]["cell"]
        chair = placed("armchair", x, y)
        chair["id"] = "door-blocker"
        room["objects"].append(chair)
        self.assertFalse(validate_room(room)["valid"])
        room = generate_room("kitchen", 3)
        room["objects"] = [o for o in room["objects"] if o["kind"] != "fridge"]
        self.assertIn("required_furniture_missing", validate_room(room)["errors"])
        with self.assertRaises(GenerationError):
            generate_room("living", 1, 3, 3)

    def test_multiple_floors_stairs_lift_and_accessible_route(self):
        house = generate_house(42, 3, True)
        self.assertTrue(house["validation"]["valid"])
        nav = FloorNavigation(house)
        target = next(o for o in house["floors"][2]["objects"] if o["anchors"])["anchors"][0]
        for transport in ("stairs", "elevator"):
            route = nav.route(house["entrance"], [2, *target], transport)
            self.assertIsNotNone(route)
            vertical = [step for step in route["steps"] if step["kind"] != "walk"]
            self.assertTrue(vertical)
            self.assertTrue(all(s["kind"] == transport for s in vertical))
        accessible = nav.route(house["entrance"], [2, *target], accessible=True)
        self.assertTrue(all(s["kind"] != "stairs" for s in accessible["steps"]))
        no_lift = generate_house(42, 3, False)
        self.assertIsNone(FloorNavigation(no_lift).route(no_lift["entrance"], [2, *target], accessible=True))

    def test_house_diversity_and_connected_block(self):
        for seed in range(6):
            with self.subTest(seed=seed):
                house = generate_house(seed, 1 + seed % 4)
                self.assertTrue(house["validation"]["valid"])
                self.assertEqual(len(house["floors"]), 1 + seed % 4)
                block = generate_district(seed, 8)
                self.assertTrue(block["validation"]["valid"], block["validation"])

    def test_walkers_use_real_timed_portals_and_one_lift(self):
        demo = NavigationDemo(generate_house(42, 3, True))
        saw_transit = False
        for _ in range(900):
            snapshot = demo.advance(1)
            self.assertEqual(snapshot["invariant_errors"], [])
            for actor in snapshot["actors"]:
                if actor["ride"]:
                    saw_transit = True
                    self.assertIsNone(actor["position"])
                    self.assertEqual(actor["location"]["kind"], "portal")
                    self.assertLess(snapshot["clock"], actor["ride"]["end"])
        self.assertTrue(saw_transit)
        self.assertGreater(demo.metrics["stairs_trips"], 0)
        self.assertGreater(demo.metrics["elevator_trips"], 0)
        self.assertGreater(demo.metrics["queue_wait_seconds"], 0)
        self.assertGreater(demo.metrics["arrivals"], 3)
        for event in demo.events:
            if event["kind"] == "portal_arrival":
                self.assertGreaterEqual(event["arrived_at"] - event["departed_at"], 12)

    def test_demo_step_partition_is_deterministic(self):
        design = generate_house(5, 2)
        a, b = NavigationDemo(design), NavigationDemo(design)
        a.advance(300)
        for _ in range(30):
            b.advance(10)
        self.assertEqual(a.snapshot(), b.snapshot())


if __name__ == "__main__":
    unittest.main()
