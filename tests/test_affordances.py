import unittest

from living_world.generation.affordances import (
    ACTIONS,
    GROUPS,
    check_action,
    contracts,
    object_actions,
    object_capacities,
    use_slot_capacity,
)
from living_world.generation.catalog import CATALOG


class AffordanceContractTests(unittest.TestCase):
    def test_groups_reference_only_current_catalog_kinds(self):
        stale = sorted(kind for group in GROUPS for kind in group if kind not in CATALOG)
        self.assertEqual(stale, [])

    def test_every_catalog_object_has_registered_functional_action(self):
        for kind in CATALOG:
            with self.subTest(kind=kind):
                offered = object_actions(kind)
                self.assertIn("inspect", offered)
                self.assertIn("clean", offered)
                self.assertTrue(set(offered).issubset(ACTIONS))
                self.assertGreater(len(offered), 2, f"{kind} only has generic actions")

    def test_specific_household_and_hobby_actions_exist(self):
        expected = {
            "toilet": "relieve",
            "floor_lamp": "toggle_light",
            "changing_table": "change_baby",
            "chess_table": "play_chess",
            "display_cabinet": "observe_artifact",
        }
        for kind, action in expected.items():
            with self.subTest(kind=kind):
                self.assertIn(action, object_actions(kind))
        # There is no clock object in the current catalog; keep its action
        # available for a future authored clock spec without fabricating one.
        self.assertIn("check_time", ACTIONS)
        self.assertIn("check_time", object_actions("wall_clock"))

    def test_capability_reachability_and_use_slot_are_independent(self):
        work = check_action("work", ["work"], {"capabilities": []},
                            reachable=True, available=True)
        self.assertEqual(work["reasons"], ["capability_missing:work"])

        blocked = check_action("work", ["work"], {"capabilities": ["work"]},
                               reachable=False, available=True)
        self.assertEqual(blocked["reasons"], ["no_reachable_anchor"])

        reserved = check_action("work", ["work"], {"capabilities": ["work"]},
                                reachable=True, available=True,
                                slots_in_use=1, slot_capacity=1)
        self.assertEqual(reserved["reasons"], ["use_slot_reserved"])

    def test_observation_needs_visibility_not_physical_reachability(self):
        observed = check_action("inspect", ["inspect"], {}, reachable=False,
                                available=False, visible=True)
        self.assertTrue(observed["allowed"])
        hidden = check_action("inspect", ["inspect"], {}, visible=False)
        self.assertEqual(hidden["reasons"], ["object_not_visible"])
        self.assertEqual(ACTIONS["inspect"]["requires"], ["object_visible"])

    def test_static_capacity_is_separate_from_actor_capability_and_slots(self):
        self.assertEqual(object_capacities("bed_queen"), {"sleep_slots": 2})
        self.assertEqual(use_slot_capacity("bed_queen", "sleep"), 2)
        self.assertEqual(ACTIONS["sleep"]["capability"], None)
        self.assertTrue(check_action("sleep", ["sleep"], {}, reachable=True,
                                     slots_in_use=1, slot_capacity=2)["allowed"])
        full = check_action("sleep", ["sleep"], {}, reachable=True,
                            slots_in_use=2, slot_capacity=2)
        self.assertEqual(full["reasons"], ["use_slot_reserved"])
        self.assertEqual(contracts(CATALOG)["object_capacities"]["bed_queen"],
                         {"sleep_slots": 2})

    def test_interactions_remain_explicitly_authoring_only(self):
        result = contracts(CATALOG)
        self.assertEqual(result["execution"], "authoring_contract_only")
        self.assertEqual(ACTIONS["change_baby"]["execution"], "authoring_contract_only")
        self.assertIsNone(ACTIONS["inspect"]["reservation"])


if __name__ == "__main__":
    unittest.main()
