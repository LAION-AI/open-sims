"""Engine-level acceptance tests for portable items and household custody.

These tests deliberately run decision, travel and completion boundaries.  They
are not unit tests for :mod:`living_world.possessions`: the assertions cover
the canonical ledger state that a client would actually observe.
"""

import unittest

from living_world.engine import RejectedProposal, World
from living_world import possessions
from living_world.daily_life import daily_state
from living_world.storyteller import INCIDENTS


class PossessionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.world = World(seed=2718)
        self.addCleanup(self.world.close)

    def isolate(self, aid="resident_001", *also_procedural):
        """Keep scheduler noise out while retaining the real world and paths."""
        w = self.world
        procedural = {aid, *also_procedural}
        with w.transaction("test.possession_fixture", list(w.actors),
                           "Explicit isolated possession-test fixture."):
            for key in w.actors:
                actor = w.edit("actors", key)
                actor["owner"] = "procedural" if key in procedural else "external"
                actor["action"] = None
                actor["routine"] = None
                actor["cooldowns"] = {}
                actor["needs"] = {need: .02 for need in actor["needs"]}
                actor["needs_at"] = w.now
                actor["schedule"].update(start=0, end=1)
        return w.actors[aid]

    def finish(self, aid):
        """Advance the actual scheduled action through travel and completion."""
        action = self.world.actors[aid]["action"]
        self.assertIsNotNone(action, "expected a started action")
        self.world.advance(action["ends_at"] - self.world.now)
        self.assertIsNone(self.world.actors[aid]["action"])

    def request_and_finish(self, aid, kind):
        self.world.decide(aid, {"action": kind})
        self.assertEqual(self.world.actors[aid]["action"]["kind"], kind)
        self.finish(aid)

    def home(self, actor, kind):
        return next(obj for obj in self.world.objects.values()
                    if obj["household_id"] == actor["household_id"] and obj["kind"] == kind)

    @staticmethod
    def item(actor, item_id):
        return next(item for item in actor["belongings"] if item["id"] == item_id)

    def make_served_pizza(self, aid="resident_001"):
        actor = self.isolate(aid)
        with self.world.transaction("test.hungry", [aid], "A real hungry-meal fixture."):
            current = self.world.edit("actors", aid)
            current["needs"]["hunger"] = .9
            current["needs_at"] = self.world.now
        for kind in ("fetch_pizza_ingredients", "prep_pizza", "load_pizza_oven"):
            self.request_and_finish(aid, kind)
        pizza = next(item for item in self.world.actors[aid]["belongings"] if item["kind"] == "pizza")
        return pizza["id"]

    def test_recipe_moves_one_pizza_oven_to_table_to_consumed_and_cleans(self):
        w = self.world
        pizza_id = self.make_served_pizza()
        actor = w.actors["resident_001"]
        counter, table = self.home(actor, "counter"), self.home(actor, "table")

        heating = self.item(actor, pizza_id)
        self.assertEqual(heating["location"], {"type": "container", "id": counter["id"]})
        self.assertEqual(heating["state"]["stage"], "heating")
        self.assertEqual(daily_state(counter)["oven_item_id"], pizza_id)
        # A table-eat intent cannot consume an item that is merely heating.
        with self.assertRaises(RejectedProposal):
            w.decide(actor["id"], {"action": "eat_recipe"})
        self.assertNotEqual(self.item(w.actors[actor["id"]], pizza_id)["location"]["type"], "consumed")

        # Baking is a timed transition: one second before completion the exact
        # oven item is still heating, so it cannot yield a free meal early.
        w.decide(actor["id"], {"action": "bake_pizza"})
        bake = w.actors[actor["id"]]["action"]
        w.advance(bake["ends_at"] - w.now - 1)
        early = self.item(w.actors[actor["id"]], pizza_id)
        self.assertEqual(early["state"]["stage"], "heating")
        self.assertNotEqual(early["location"]["type"], "consumed")
        self.finish(actor["id"])
        self.assertEqual(self.item(w.actors[actor["id"]], pizza_id)["state"]["stage"], "baked")
        self.request_and_finish(actor["id"], "unload_pizza_oven")
        self.request_and_finish(actor["id"], "serve_recipe")
        served = self.item(w.actors[actor["id"]], pizza_id)
        self.assertEqual(served["location"], {"type": "container", "id": table["id"]})
        self.assertEqual(served["state"]["stage"], "served")

        # A different adult has no candidate that consumes someone else's exact item.
        other = "resident_002"
        with self.assertRaises(RejectedProposal):
            w.decide(other, {"action": "eat_recipe"})

        self.request_and_finish(actor["id"], "eat_recipe")
        consumed = self.item(w.actors[actor["id"]], pizza_id)
        self.assertEqual(consumed["location"]["type"], "consumed")
        self.assertIn(consumed['label'], possessions.DISH_VARIANTS['pizza'])
        self.assertEqual(w.actors[actor['id']]['last_meal']['label'],consumed['label'])
        self.assertIn(consumed['label'], w.store.recent(actor['id'],limit=1)[0]['narration'])
        all_pizzas = [item for person in w.actors.values() for item in person["belongings"]
                      if item["id"] == pizza_id]
        self.assertEqual(len(all_pizzas), 1)
        self.assertEqual(daily_state(table)["dirty_dishes"], 1)

        for kind in ("clear_dishes", "wash_dishes", "bin_trash", "wipe_counter"):
            self.request_and_finish(actor["id"], kind)
        self.assertEqual(daily_state(table)["dirty_dishes"], 0)
        self.assertFalse(any(item["kind"] == "dirty_dish" and item["location"]["type"] != "consumed"
                             for item in w.actors[actor["id"]]["belongings"]))
        self.assertEqual(w.invariants(), [])
        self.assertEqual(w.store.replay(), w.canonical_state())

    def test_interrupted_eating_preserves_served_item_and_hunger(self):
        w = self.world
        pizza_id = self.make_served_pizza()
        aid = "resident_001"
        before = w.needs_at(w.actors[aid])["hunger"]
        self.assertEqual(self.item(w.actors[aid], pizza_id)["state"]["stage"], "heating")
        self.request_and_finish(aid, "bake_pizza")
        self.request_and_finish(aid, "unload_pizza_oven")
        self.request_and_finish(aid, "serve_recipe")
        before = w.needs_at(w.actors[aid])["hunger"]
        w.decide(aid, {"action": "eat_recipe"})
        w.interrupt(aid, "Acceptance-test interruption before consuming the served pizza")
        self.assertAlmostEqual(w.needs_at(w.actors[aid])["hunger"], before, places=7)
        pizza = self.item(w.actors[aid], pizza_id)
        self.assertEqual(pizza["state"]["stage"], "served")
        self.assertEqual(pizza["location"]["type"], "container")
        self.assertFalse(any(item["kind"] == "dirty_dish" for item in w.actors[aid]["belongings"]))
        self.assertEqual(w.invariants(), [])

    def test_low_pantry_routes_to_supermarket_and_stocks_before_recipe(self):
        w = self.world
        actor = self.isolate()
        fridge = self.home(actor, "fridge")
        with w.transaction("test.empty_pantry", [actor["id"], fridge["id"]],
                           "The pantry is explicitly empty."):
            person = w.edit("actors", actor["id"])
            person["needs"]["hunger"] = .9
            person["money"] = 100
            w.edit("objects", fridge["id"])["daily"] = {"pantry_stock": 0}
        before_money = w.actors[actor["id"]]["money"]
        w.decide(actor["id"], {"action": "buy_groceries"})
        self.assertEqual(w.objects[w.actors[actor["id"]]["action"]["target_id"]]["kind"], "supermarket_checkout")
        self.finish(actor["id"])
        incident=w.actors[actor['id']].get('last_story_incident')
        incidental=next((event['money'] for event in INCIDENTS if incident and event['id']==incident['id']),0)
        self.assertEqual(w.actors[actor["id"]]["money"], before_money - 20 + incidental)
        if incident:
            self.assertEqual(incident['trigger'],'buy_groceries')
            self.assertIn(incident['text'],w.store.recent(actor['id'],1)[0]['narration'])
        self.request_and_finish(actor["id"], "stock_fridge")
        self.assertEqual(daily_state(w.objects[fridge["id"]])["pantry_stock"], 8)
        self.assertNotIn("groceries", w.actors[actor["id"]]["inventory"])
        self.assertEqual(w.invariants(), [])

    def test_outfit_projection_changes_after_real_change_action(self):
        w = self.world
        actor = self.isolate()
        before = w.inspect(actor["id"])["appearance"]["outfit"]["top"]["id"]
        self.request_and_finish(actor["id"], "change_outfit")
        inspected = w.inspect(actor["id"])
        after = inspected["appearance"]["outfit"]["top"]["id"]
        self.assertNotEqual(before, after)
        self.assertEqual(w.actors[actor["id"]]["outfit_last_day"], w.now // 86400)
        self.assertEqual(w.invariants(), [])

    def test_housemate_can_clear_foreign_plate_without_changing_owner(self):
        w = self.world
        pizza_id = self.make_served_pizza()
        aid, helper = "resident_001", "resident_002"
        for kind in ("bake_pizza", "unload_pizza_oven", "serve_recipe", "eat_recipe"):
            self.request_and_finish(aid, kind)
        plate = next(item for item in w.actors[aid]["belongings"] if item["kind"] == "dirty_dish")
        plate_id = plate["id"]
        self.assertEqual(plate["owner_id"], aid)
        w.decide(helper, {"action": "clear_dishes"})
        self.finish(helper)
        self.assertFalse(any(item["id"] == plate_id for item in w.actors[aid]["belongings"]))
        custody = self.item(w.actors[helper], plate_id)
        self.assertEqual(custody["owner_id"], aid)
        self.assertEqual(custody["location"], {"type": "carried", "id": helper})
        self.assertEqual(w.invariants(), [])


if __name__ == "__main__":
    unittest.main()
