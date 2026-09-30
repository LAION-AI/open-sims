import unittest
from copy import deepcopy

from living_world.daily_life import (
    DAILY_ACTIONS, StepUnavailable, apply_step, assigned_workplace,
    coworkers_at_work, daily_state, plan_cleaning, plan_groceries,
    plan_hobby, plan_meal, step_available,
)
from living_world.spatial import SpatialService


class DailyLifeTests(unittest.TestCase):
    def setUp(self):
        self.spatial = SpatialService()
        self.objects = self.spatial.objects
        self.actor = {"id": "resident_001", "household_id": "household_01", "home_id": "home_01",
                      "profile": {"job": "Teacher"}, "preferences": {"craft": .9, "reading": .2, "gardening": .1},
                      "inventory": {"phone": 1}, "skills": {"craft": .2}}

    def complete(self, step):
        obj = self.objects[step["target_id"]]
        effects = apply_step(self.actor, obj, step["kind"])
        self.actor["inventory"] = effects["inventory"]
        self.actor["skills"] = effects["skills"]
        obj["daily"] = effects["object_daily"]

    def test_meal_moves_real_tokens_through_home_and_leaves_chore_evidence(self):
        steps = plan_meal(self.actor, self.objects)
        self.assertEqual([step["kind"] for step in steps], [
            "fetch_ingredients", "prepare_meal", "serve_meal", "eat_meal",
            "clear_dishes", "wash_dishes", "bin_trash", "empty_trash", "wipe_counter"])
        self.assertEqual({self.objects[step["target_id"]]["household_id"] for step in steps},
                         {"household_01"})
        self.complete(steps[0])
        self.assertEqual(self.actor["inventory"]["ingredients"], 1)
        self.complete(steps[1])
        self.assertEqual(self.actor["inventory"]["prepared_meal"], 1)
        self.assertEqual(self.actor["inventory"]["food_scraps"], 1)
        self.complete(steps[2])
        self.assertNotIn("prepared_meal", self.actor["inventory"])
        self.assertEqual(daily_state(self.objects[steps[2]["target_id"]])["served_meals"], 1)
        self.complete(steps[3])
        table = self.objects[steps[3]["target_id"]]
        self.assertEqual(daily_state(table)["dirty_dishes"], 1)
        self.assertEqual([step["kind"] for step in plan_cleaning(self.actor, self.objects)],
                         ["clear_dishes", "wash_dishes", "bin_trash", "empty_trash", "wipe_counter"])
        for step in steps[4:]:
            self.complete(step)
        self.assertEqual(self.actor["inventory"], {"phone": 1})
        self.assertEqual(daily_state(table)["dirty_dishes"], 0)
        self.assertEqual(daily_state(self.objects[steps[5]["target_id"]])["washed_total"], 1)
        self.assertEqual(daily_state(self.objects[steps[7]["target_id"]])["disposed_total"], 1)
        self.assertEqual(daily_state(self.objects[steps[8]["target_id"]])["cleaned_total"], 1)

    def test_preconditions_are_pure_and_failed_steps_do_not_create_food(self):
        step = plan_meal(self.actor, self.objects)[1]
        obj = self.objects[step["target_id"]]
        before_actor, before_obj = deepcopy(self.actor), deepcopy(obj)
        self.assertFalse(step_available(self.actor, obj, "prepare_meal"))
        with self.assertRaises(StepUnavailable):
            apply_step(self.actor, obj, "prepare_meal")
        self.assertEqual(self.actor, before_actor)
        self.assertEqual(obj, before_obj)

    def test_grocery_trip_recovers_empty_pantry(self):
        fridge = next(o for o in self.objects.values() if o["kind"] == "fridge"
                      and o["household_id"] == self.actor["household_id"])
        fridge["daily"] = {"pantry_stock": 0}
        steps = plan_meal(self.actor, self.objects)
        self.assertEqual([step["kind"] for step in steps[:3]],
                         ["buy_groceries", "stock_fridge", "fetch_ingredients"])
        for step in steps[:3]:
            self.complete(step)
        self.assertEqual(daily_state(fridge)["pantry_stock"], 7)
        self.assertEqual(self.actor["inventory"]["ingredients"], 1)
        self.assertEqual(plan_groceries(self.actor, self.objects)[0]["kind"], "buy_groceries")

    def test_abandoned_meal_resumes_held_and_served_food_without_duplication(self):
        original = plan_meal(self.actor, self.objects)
        fridge = self.objects[original[0]["target_id"]]
        self.complete(original[0])
        self.assertEqual(plan_meal(self.actor, self.objects)[0]["kind"], "prepare_meal")
        self.assertEqual(daily_state(fridge)["pantry_stock"], 7)
        self.complete(original[1])
        resumed = plan_meal(self.actor, self.objects)
        self.assertEqual(resumed[0]["kind"], "serve_meal")
        self.assertNotIn("fetch_ingredients", [step["kind"] for step in resumed])
        self.complete(resumed[0])
        served = plan_meal(self.actor, self.objects)
        self.assertEqual(served[0]["kind"], "eat_meal")
        self.assertNotIn("prepare_meal", [step["kind"] for step in served])
        self.assertEqual(daily_state(fridge)["pantry_stock"], 7)
        self.assertEqual(self.actor["inventory"].get("prepared_meal", 0), 0)

    def test_abandoned_grocery_trip_uses_bag_before_buying_another(self):
        fridge = next(o for o in self.objects.values() if o["kind"] == "fridge"
                      and o["household_id"] == self.actor["household_id"])
        fridge["daily"] = {"pantry_stock": 0}
        self.actor["inventory"]["groceries"] = 8
        planned = plan_meal(self.actor, self.objects)
        self.assertEqual([step["kind"] for step in planned[:2]],
                         ["stock_fridge", "fetch_ingredients"])
        self.complete(planned[0])
        self.assertEqual(self.actor["inventory"].get("groceries", 0), 0)
        self.assertEqual(daily_state(fridge)["pantry_stock"], 8)

    def test_recovered_served_meal_without_scraps_has_only_real_chore_steps(self):
        table = next(o for o in self.objects.values() if o["kind"] == "table"
                     and o["household_id"] == self.actor["household_id"])
        table["daily"] = {"served_meals": 1, "dirty_dishes": 0}
        steps = plan_meal(self.actor, self.objects)
        self.assertEqual([step["kind"] for step in steps],
                         ["eat_meal", "clear_dishes", "wash_dishes"])
        for step in steps:
            self.complete(step)
        self.assertEqual(daily_state(table)["served_meals"], 0)
        self.assertEqual(daily_state(table)["dirty_dishes"], 0)

    def test_large_scrap_bag_is_removed_over_multiple_bin_trips(self):
        self.actor["inventory"]["food_scraps"] = 10
        first = plan_cleaning(self.actor, self.objects)
        self.assertEqual([step["kind"] for step in first], ["bin_trash", "empty_trash"])
        for step in first:
            self.complete(step)
        self.assertEqual(self.actor["inventory"]["food_scraps"], 2)
        second = plan_cleaning(self.actor, self.objects)
        for step in second:
            self.complete(step)
        self.assertNotIn("food_scraps", self.actor["inventory"])
        bin_obj = self.objects[first[0]["target_id"]]
        self.assertEqual(daily_state(bin_obj)["disposed_total"], 10)

    def test_meal_plan_empties_a_full_bin_only_when_there_is_trash(self):
        bin_obj = next(o for o in self.objects.values() if o["kind"] == "bin"
                       and o["household_id"] == self.actor["household_id"])
        bin_obj["daily"] = {"trash": 8}
        steps = [step["kind"] for step in plan_meal(self.actor, self.objects)]
        self.assertEqual(steps.count("empty_trash"), 2)
        self.assertLess(steps.index("eat_meal"), steps.index("empty_trash"))
        bin_obj["daily"] = {"trash": 0}
        self.actor["inventory"]["food_scraps"] = 10
        steps = [step["kind"] for step in plan_meal(self.actor, self.objects)]
        self.assertEqual(steps.count("empty_trash"), 1)

    def test_workplaces_are_external_and_all_old_ids_stay_put(self):
        self.assertGreaterEqual(len(self.objects), 349)
        self.assertEqual(self.objects["object_0303"]["kind"], "cafe_counter")
        self.assertEqual(self.objects["object_0304"]["kind"], "shop_counter")
        self.assertEqual(self.objects["object_0320"]["kind"], "park_marker")
        teacher = assigned_workplace(self.actor, self.objects)
        self.assertEqual(teacher["building_id"], "school")
        self.assertEqual(teacher["target_id"], "object_0324")
        self.assertFalse(teacher["work_from_home"])
        for job, building in [("Illustrator", "studio"), ("Designer", "studio"),
                              ("Carpenter", "workshop"), ("Tailor", "workshop"),
                              ("Gardener", "workshop"), ("Baker", "cafe"),
                              ("Bookseller", "shop"), ("Independent artist", "home_01")]:
            person = {**self.actor, "profile": {"job": job}}
            self.assertEqual(assigned_workplace(person, self.objects)["building_id"], building)
        for kind in ("teacher_station", "illustrator_station", "designer_station",
                     "carpenter_station", "tailor_station", "gardener_station"):
            station = next(obj for obj in self.objects.values() if obj["kind"] == kind)
            self.assertEqual(station["capacity"], len(station["anchors"]))
            for anchor in station["anchors"]:
                self.assertIsNotNone(self.spatial.path((2, 2), anchor), (kind, anchor))

    def test_coworkers_and_hobby_have_consistent_targets(self):
        colleagues = [self.actor,
                      {**self.actor, "id": "resident_002", "profile": {"job": "Teacher"}},
                      {**self.actor, "id": "resident_003", "profile": {"job": "Designer"}}]
        self.assertEqual(coworkers_at_work(self.actor, colleagues, self.objects), ["resident_002"])
        step = plan_hobby(self.actor, self.objects)[0]
        self.assertEqual(step["kind"], "creative_hobby")
        self.assertEqual(self.objects[step["target_id"]]["kind"], "desk")
        self.complete(step)
        self.assertEqual(self.actor["inventory"]["craft_project"], 1)
        self.assertEqual(self.actor["skills"]["craft"], .21)
        for definition in DAILY_ACTIONS.values():
            self.assertTrue({"label", "object_kinds", "duration", "relief", "cost",
                             "preference", "thought"}.issubset(definition))


if __name__ == "__main__":
    unittest.main()
