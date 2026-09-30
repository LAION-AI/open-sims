"""SQLite Beat ledger and exact component projections, independent of narration."""
import json
import sqlite3
from copy import deepcopy
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4


class BeatStore:
    def __init__(self, path=":memory:"):
        self.path = str(path)
        self.connection = None
        connection = None
        try:
            connection = sqlite3.connect(str(path), check_same_thread=False)
            self.connection = connection
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS beats (
                    sequence INTEGER PRIMARY KEY, time INTEGER NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS participants (
                    entity_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                    PRIMARY KEY(entity_id, sequence));
                CREATE TABLE IF NOT EXISTS checkpoint (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS beat_time ON beats(time);
            """)
            self.sequence = connection.execute("SELECT COALESCE(MAX(sequence),0) FROM beats").fetchone()[0]
            self.poisoned = False
        except BaseException:
            if connection is not None:
                connection.close()
            self.connection = None
            raise

    def append(self, beat):
        """Stage one all-or-nothing beat; checkpointing owns durability.

        A savepoint isolates a participant-index error from earlier staged beats.
        In particular, do not increment the public sequence until both the beat
        and every participant row have been written successfully.
        """
        if self.poisoned:
            raise sqlite3.OperationalError("BeatStore is poisoned after a failed rollback; restart before writing")
        candidate = self.sequence + 1
        staged = deepcopy(beat)
        staged["id"] = f"beat_{candidate:08}"
        staged["sequence"] = candidate
        for i, change in enumerate(staged["changes"]):
            change["id"] = f"{staged['id']}/{i}"
        payload = json.dumps(staged, separators=(",", ":"))
        if not self.connection.in_transaction:
            self.connection.execute("BEGIN")
        savepoint = "beat_append_" + uuid4().hex
        self.connection.execute("SAVEPOINT " + savepoint)
        try:
            self.connection.execute("INSERT INTO beats VALUES (?,?,?)", (candidate, staged["interval"][1], payload))
            self.connection.executemany("INSERT INTO participants VALUES (?,?)", [(p, candidate) for p in staged["participants"]])
            self.connection.execute("RELEASE " + savepoint)
        except BaseException:
            try:
                self.connection.execute("ROLLBACK TO " + savepoint)
                self.connection.execute("RELEASE " + savepoint)
            except sqlite3.Error:
                # SQLite may have auto-rolled back the entire outer transaction
                # (for example under SQLITE_FULL).  The savepoint then no
                # longer exists, so earlier staged beats are gone as well.
                # Refuse any later checkpoint/write until a new store reloads
                # the durable state; World.save restores that checkpoint.
                self.poisoned = True
                try:
                    self.connection.rollback()
                except sqlite3.Error:
                    pass
                self.sequence = self.connection.execute(
                    "SELECT COALESCE(MAX(sequence),0) FROM beats").fetchone()[0]
            raise
        self.sequence = candidate
        beat.clear()
        beat.update(staged)
        return beat

    def recent(self, entity_id=None, limit=30, before=None):
        limit = min(max(int(limit),1),200)
        params=[]
        query="SELECT b.payload FROM beats b "
        if entity_id:
            query+="JOIN participants p ON b.sequence=p.sequence WHERE p.entity_id=? "
            params.append(entity_id)
        else:
            query+="WHERE 1=1 "
        if before:
            query+="AND b.sequence<? "
            params.append(before)
        query+="ORDER BY b.sequence DESC LIMIT ?"
        params.append(limit)
        return [json.loads(row[0]) for row in self.connection.execute(query,params)]

    def replay(self, through=None):
        """Apply accepted records, without rerunning decisions or random draws."""
        state={"actors":{},"objects":{},"world":{}}
        query="SELECT payload FROM beats"
        params=[]
        if through is not None:
            query+=" WHERE sequence<=?"
            params.append(through)
        for (raw,) in self.connection.execute(query+" ORDER BY sequence",params):
            beat=json.loads(raw)
            for change in beat["changes"]:
                collection=state[change["collection"]]
                entity=change["subject_id"]
                if change["component_path"]=="$":
                    collection[entity]=deepcopy(change["new_value"])
                else:
                    collection[entity][change["component_path"]]=deepcopy(change["new_value"])
        return state

    def save_checkpoint(self, payload):
        """Commit the checkpoint and all staged beats as one SQLite unit.

        On failure the old committed checkpoint remains in place and every
        staged beat is rolled back, avoiding a newer replay log with an older
        queue snapshot (or the inverse).  The World coordinator restores that
        durable checkpoint before it permits normal operation again.  If an
        append rollback was poisoned, restart/reload is required instead.
        """
        if self.poisoned:
            raise sqlite3.OperationalError("BeatStore is poisoned after a failed rollback; restart before checkpointing")
        encoded = json.dumps(payload, separators=(",", ":"))
        if not self.connection.in_transaction:
            self.connection.execute("BEGIN")
        savepoint = "checkpoint_" + uuid4().hex
        self.connection.execute("SAVEPOINT " + savepoint)
        try:
            # UPSERT updates one row in place; unlike REPLACE it never performs
            # a delete-then-insert transition on an existing checkpoint.
            self.connection.execute("INSERT INTO checkpoint(id,payload) VALUES (1,?) "
                                    "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload", (encoded,))
            self.connection.execute("RELEASE " + savepoint)
            self.connection.commit()
        except BaseException:
            # RELEASE can itself fail under I/O pressure.  A full rollback is
            # still the only valid outcome because queue and staged beats must
            # become durable together.
            try:
                self.connection.execute("ROLLBACK TO " + savepoint)
                self.connection.execute("RELEASE " + savepoint)
            except sqlite3.Error:
                pass
            self.connection.rollback()
            self.sequence = self.connection.execute("SELECT COALESCE(MAX(sequence),0) FROM beats").fetchone()[0]
            raise

    def checkpoint(self):
        row=self.connection.execute("SELECT payload FROM checkpoint WHERE id=1").fetchone()
        return json.loads(row[0]) if row else None

    def migration_backup(self, package='life-v2'):
        """Consistent SQLite backup, including WAL; never replace an older backup."""
        if self.path == ":memory:":
            return None
        source = Path(self.path).resolve()
        directory = source.parent / "backups"
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = directory / f"{source.stem}-pre-{package}-{stamp}-{uuid4().hex[:8]}.sqlite3"
        backup = sqlite3.connect(str(target))
        try:
            self.connection.backup(backup)
        finally:
            backup.close()
        return str(target)

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
