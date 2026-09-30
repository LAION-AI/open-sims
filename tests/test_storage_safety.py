"""Failure-atomic SQLite tests without relying on a full disk."""

from copy import deepcopy
import sqlite3
import unittest
from unittest.mock import patch

from living_world.engine import World
from living_world.ledger import BeatStore


def beat(value, participants=("resident_001",)):
    return {"interval": [0, value], "participants": list(participants), "changes": [
        {"collection": "actors", "subject_id": "resident_001", "component_path": "$",
         "new_value": {"value": value}},
    ]}


class _FailingPragmaConnection:
    def __init__(self):
        self.closed = False

    def execute(self, _sql):
        raise sqlite3.OperationalError("simulated initialization failure")

    def close(self):
        self.closed = True


class StorageSafetyTests(unittest.TestCase):
    def setUp(self):
        self.store = BeatStore()
        self.addCleanup(self.store.close)

    def test_initialization_failure_closes_open_connection(self):
        connection = _FailingPragmaConnection()
        with patch("living_world.ledger.sqlite3.connect", return_value=connection):
            with self.assertRaises(sqlite3.OperationalError):
                BeatStore(":memory:")
        self.assertTrue(connection.closed)

    def test_participant_insert_failure_rolls_back_only_that_beat_and_keeps_staged_beat(self):
        self.store.connection.execute("""
            CREATE TRIGGER reject_bad_participant BEFORE INSERT ON participants
            WHEN NEW.entity_id = 'reject-me'
            BEGIN SELECT RAISE(ABORT, 'simulated participant insert failure'); END;
        """)
        accepted = beat(1)
        self.store.append(accepted)
        self.assertTrue(self.store.connection.in_transaction)
        self.assertEqual(self.store.sequence, 1)

        rejected = beat(2, ("resident_002", "reject-me"))
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.append(rejected)

        self.assertEqual(self.store.sequence, 1)
        self.assertNotIn("id", rejected, "failed beat must not receive a committed identity")
        self.assertEqual([row["sequence"] for row in self.store.recent()], [1])
        self.assertEqual(self.store.replay()["actors"]["resident_001"], {"value": 1})
        self.assertEqual(self.store.connection.execute("SELECT COUNT(*) FROM participants").fetchone()[0], 1)
        self.assertTrue(self.store.connection.in_transaction)

        self.store.save_checkpoint({"queue": ["accepted"], "version": 1})
        self.assertFalse(self.store.connection.in_transaction)
        self.assertEqual(self.store.checkpoint()["queue"], ["accepted"])

    def test_checkpoint_failure_preserves_old_checkpoint_and_rolls_back_staged_beats(self):
        self.store.append(beat(1))
        old_checkpoint = {"queue": ["old"], "version": 1}
        self.store.save_checkpoint(old_checkpoint)
        self.store.append(beat(2))
        self.store.connection.execute("""
            CREATE TRIGGER reject_checkpoint_update BEFORE UPDATE ON checkpoint
            BEGIN SELECT RAISE(ABORT, 'simulated checkpoint write failure'); END;
        """)

        with self.assertRaises(sqlite3.IntegrityError):
            self.store.save_checkpoint({"queue": ["new"], "version": 2})

        self.assertEqual(self.store.sequence, 1)
        self.assertEqual(self.store.checkpoint(), old_checkpoint)
        self.assertEqual([row["sequence"] for row in self.store.recent()], [1])
        self.assertEqual(self.store.replay()["actors"]["resident_001"], {"value": 1})
        self.assertFalse(self.store.connection.in_transaction)

    def test_full_transaction_rollback_poison_blocks_checkpoint_and_refreshes_sequence(self):
        self.store.connection.execute("""
            CREATE TRIGGER force_whole_transaction_rollback BEFORE INSERT ON participants
            WHEN NEW.entity_id = 'poison-me'
            BEGIN SELECT RAISE(ROLLBACK, 'simulated full transaction cancellation'); END;
        """)
        self.store.append(beat(1))
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.append(beat(2, ("poison-me",)))

        self.assertTrue(self.store.poisoned)
        self.assertEqual(self.store.sequence, 0)
        self.assertEqual(self.store.replay(), {"actors": {}, "objects": {}, "world": {}})
        with self.assertRaises(sqlite3.OperationalError):
            self.store.save_checkpoint({"queue": ["must-not-write"]})

    def test_world_save_failure_restores_durable_canonical_state_and_queue(self):
        world = World(seed=989)
        self.addCleanup(world.store.close)  # Avoid World.close retrying a deliberately failed save.
        before_state = deepcopy(world.canonical_state())
        before_now, before_queue = world.now, deepcopy(world.queue)
        world.advance(1)
        self.assertNotEqual(world.now, before_now)
        world.store.connection.execute("""
            CREATE TRIGGER reject_world_checkpoint BEFORE UPDATE ON checkpoint
            BEGIN SELECT RAISE(ABORT, 'simulated checkpoint failure after advance'); END;
        """)

        with self.assertRaises(sqlite3.IntegrityError):
            world.save()

        self.assertTrue(world.paused)
        self.assertIn("restored last durable checkpoint", world.fault)
        self.assertEqual(world.canonical_state(), before_state)
        self.assertEqual(world.now, before_now)
        self.assertEqual(world.queue, before_queue)
        self.assertEqual(world.store.replay(), world.canonical_state())


if __name__ == "__main__":
    unittest.main()
