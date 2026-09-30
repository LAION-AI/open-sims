import unittest
from copy import deepcopy

from living_world.daily_life import apply_step as apply_legacy
from living_world.possessions import (
    PossessionUnavailable, apply_step, initialize, plan, plan_outfit,
    step_available, synchronize_cleanup, worn_outfit,
)
from living_world.spatial import SpatialService


class PossessionTests(unittest.TestCase):
    def setUp(self):
        self.objects = SpatialService().objects
        self.actor = {"id": "resident_001", "household_id": "household_01",
                      "home_id": "home_01", "inventory": {"phone": 1},
                      "appearance": {"shirt": "#779977"}}
        self.actor.update(initialize(self.actor, 0))

    def complete(self, step, now):
        obj = self.objects[step["target_id"]]
        effect = apply_step(self.actor, obj, step["kind"], now)
        self.actor.update({k: v for k, v in effect.items() if k != "object_daily"})
        obj["daily"] = effect["object_daily"]

    def test_stable_clothing_ids_and_daily_change(self):
        self.assertEqual(len(self.actor["belongings"]), 8)
        self.assertEqual(len({i["id"] for i in self.actor["belongings"]}), 8)
        self.assertEqual(set(worn_outfit(self.actor)), {"top", "trousers", "shoes"})
        original = worn_outfit(self.actor)["top"]["id"]
        step = plan_outfit(self.actor, self.objects, 50)[0]
        self.complete(step, 50)
        self.assertNotEqual(worn_outfit(self.actor)["top"]["id"], original)
        self.assertEqual(plan_outfit(self.actor, self.objects, 51), [])
        self.assertFalse(step_available(self.actor, self.objects[step["target_id"]],
                                        "change_outfit", 51))
        self.assertTrue(plan_outfit(self.actor, self.objects, 86400))

    def test_new_residents_have_distinct_deterministic_alternative_outfits(self):
        alternatives, coats, trousers = set(), set(), set()
        for number in range(1, 21):
            resident = {"id": f"resident_{number:03d}", "home_id": "home_01",
                        "appearance": {"shirt": "#779977"}}
            first = initialize(resident, 100)
            self.assertEqual(first, initialize(resident, 100))
            self.assertEqual(first["belongings"][0]["state"]["color"], "#779977")
            self.assertEqual(first["belongings"][0]["id"], f"resident_{number:03d}_item_001")
            alternatives.add(first["belongings"][1]["state"]["color"])
            trousers.add(first["belongings"][3]["state"]["color"])
            coats.add(first["belongings"][6]["state"]["color"])
            resident.update(first)
            self.assertEqual(initialize(resident, 200)["belongings"], first["belongings"])
        self.assertGreaterEqual(len(alternatives), 8)
        self.assertGreaterEqual(len(trousers), 8)
        self.assertGreaterEqual(len(coats), 8)

    def test_pizza_oven_table_and_cleanup_are_concrete_and_nonduplicating(self):
        steps = plan(self.actor, self.objects, 0, "pizza")
        self.assertEqual([s["kind"] for s in steps[:7]], [
            "fetch_pizza_ingredients", "prep_pizza", "load_pizza_oven", "bake_pizza",
            "unload_pizza_oven", "serve_recipe", "eat_recipe"])
        self.complete(steps[0], 120)
        self.assertEqual({i["kind"] for i in self.actor["belongings"]
                          if i["location"]["type"] == "carried"}, {"dough", "tomato", "vegetable"})
        self.complete(steps[1], 600)
        pizza = next(i for i in self.actor["belongings"] if i["kind"] == "pizza")
        pizza_id = pizza["id"]
        self.assertEqual(pizza["state"]["stage"], "raw")
        self.complete(steps[2], 690)
        counter = self.objects[steps[2]["target_id"]]
        self.assertEqual(counter["daily"]["oven_item_id"], pizza_id)
        self.assertFalse(step_available(self.actor, counter, "bake_pizza", 689, completion=True))
        self.assertTrue(step_available(self.actor, counter, "bake_pizza", 690))
        prior = deepcopy(self.actor)
        with self.assertRaises(PossessionUnavailable):
            apply_step(self.actor, counter, "bake_pizza", 1589)
        self.assertEqual(self.actor, prior)
        self.complete(steps[3], 1590)
        self.assertEqual(plan(self.actor, self.objects, 1590, "pizza")[0]["kind"],
                         "unload_pizza_oven")
        self.complete(steps[4], 1680)
        self.assertNotIn("oven_item_id", counter["daily"])
        self.complete(steps[5], 1770)
        table = self.objects[steps[5]["target_id"]]
        self.assertEqual(table["daily"]["served_meals"], 1)
        self.assertEqual(plan(self.actor, self.objects, 1770)[0]["kind"], "eat_recipe")
        self.complete(steps[6], 2370)
        self.assertEqual(table["daily"]["served_meals"], 0)
        self.assertEqual(table["daily"]["dirty_dishes"], 1)
        self.assertEqual(next(i for i in self.actor["belongings"] if i["id"] == pizza_id)
                         ["location"]["type"], "consumed")
        self.assertEqual(len([i for i in self.actor["belongings"] if i["kind"] == "pizza"]), 1)
        dish = next(i for i in self.actor["belongings"] if i["kind"] == "dirty_dish")
        self.assertEqual(dish["location"]["id"], table["id"])
        legacy = apply_legacy(self.actor, table, "clear_dishes")
        self.actor["inventory"] = legacy["inventory"]
        table["daily"] = legacy["object_daily"]
        self.actor.update(synchronize_cleanup(self.actor, table, "clear_dishes", 2460))
        self.assertEqual(dish["id"], next(i["id"] for i in self.actor["belongings"]
                                          if i["kind"] == "dirty_dish"
                                          and i["location"]["type"] == "carried"))
        sink = self.objects[steps[8]["target_id"]]
        legacy = apply_legacy(self.actor, sink, "wash_dishes")
        self.actor["inventory"] = legacy["inventory"]
        sink["daily"] = legacy["object_daily"]
        self.actor.update(synchronize_cleanup(self.actor, sink, "wash_dishes", 2700))
        self.assertEqual(next(i for i in self.actor["belongings"] if i["id"] == dish["id"])
                         ["location"]["type"], "consumed")

    def test_pancake_recipe_and_low_pantry_grocery_trip(self):
        steps = plan(self.actor, self.objects, 86400, "pancake")
        self.assertEqual([s["kind"] for s in steps[:5]], [
            "fetch_pancake_ingredients", "prep_pancake", "cook_pancake",
            "serve_recipe", "eat_recipe"])
        self.complete(steps[0], 86520)
        self.assertEqual(plan(self.actor, self.objects, 86520, "pancake")[0]["kind"],
                         "prep_pancake")
        self.complete(steps[1], 86820)
        self.complete(steps[2], 87240)
        self.assertEqual(next(i for i in self.actor["belongings"] if i["kind"] == "pancake")
                         ["state"]["stage"], "cooked")
        fridge = self.objects[steps[0]["target_id"]]
        fridge["daily"] = {"pantry_stock": 0}
        fresh = {**self.actor, "belongings": initialize({"id": "resident_002",
                 "home_id": "home_01", "appearance": {}}, 0)["belongings"]}
        self.assertEqual([s["kind"] for s in plan(fresh, self.objects, 86400, "pancake")[:3]],
                         ["buy_groceries", "stock_fridge", "fetch_pancake_ingredients"])


if __name__ == "__main__":
    unittest.main()
