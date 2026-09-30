"""Transactional staging, deterministic acceptance and explicit publication.

Published packs are immutable additions to an isolated authoring library. They
do not mutate the live simulation or Python's global furniture dictionaries.
"""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import unicodedata
import uuid

from pydantic import ValidationError
from ..generation import GENERATOR_VERSION
from ..generation.catalog import CATALOG, ROOMS, Furniture
from ..generation.affordances import ACTIONS
from ..generation.rooms import generate_room, validate_room, GenerationError
from .schema import ContentPack

MAX_STORED_JOBS = 2000  # No silent deletion of authoring history.


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def name_key(name):
    return "".join(c for c in unicodedata.normalize("NFKD", name).casefold() if c.isalnum())


def compile_pack(pack, objects, rooms, graphics, buildings):
    for obj in pack.objects:
        objects[obj.id] = Furniture(obj.name, obj.w, obj.h, obj.wall, obj.tall, obj.front,
                                    obj.id, tuple(obj.extra_access))
        graphics[obj.id] = {"pixels": [p.model_dump() for p in obj.pixels], "actions": obj.actions}
    for room in pack.rooms:
        rooms[room.id] = {"name": room.name, "size": [room.width, room.height],
                          "minimum": [room.min_width, room.min_height],
                          "required": room.required, "optional": room.optional,
                          "families": [pack.title]}
    for building in pack.buildings:
        buildings[building.id] = building.model_dump()


class Library:
    def __init__(self, database="data/workshop.sqlite3"):
        if str(database) != ":memory:":
            Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(database), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS jobs(
              id TEXT PRIMARY KEY, focus TEXT NOT NULL, provider TEXT NOT NULL,
              model TEXT NOT NULL, state TEXT NOT NULL, created TEXT NOT NULL,
              updated TEXT NOT NULL, proposal TEXT, pack TEXT, report TEXT,
              usage TEXT NOT NULL DEFAULT '[]', error TEXT);
            CREATE TABLE IF NOT EXISTS events(
              seq INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
              at TEXT NOT NULL, state TEXT NOT NULL, message TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS publications(
              pack_id TEXT PRIMARY KEY, job_id TEXT UNIQUE NOT NULL, content TEXT NOT NULL,
              hash TEXT NOT NULL, reviewer TEXT NOT NULL, published_at TEXT NOT NULL);
        """)
        self.db.commit()

    def close(self):
        self.db.close()

    def create_job(self, focus, provider, model):
        if not isinstance(focus, str) or not 3 <= len(focus) <= 800:
            raise ValueError("Focus must contain 3..800 characters")
        jid = "job_" + uuid.uuid4().hex[:16]
        with self.lock, self.db:
            inserted = self.db.execute(
                "INSERT INTO jobs(id,focus,provider,model,state,created,updated) "
                "SELECT ?,?,?,?,?,?,? WHERE (SELECT COUNT(*) FROM jobs) < ?",
                (jid, focus, provider, model, "queued", now(), now(), MAX_STORED_JOBS)).rowcount
            if not inserted:
                raise ValueError(f"Authoring history limit ({MAX_STORED_JOBS} jobs) reached; archive the library explicitly before starting a new one")
            self.db.execute("INSERT INTO events(job_id,at,state,message) VALUES(?,?,?,?)",
                            (jid, now(), "queued", "Auftrag angelegt; noch keine Modellanfrage."))
        return jid

    def transition(self, jid, state, message, **values):
        allowed = {"proposal", "pack", "report", "usage", "error"}
        if not set(values).issubset(allowed):
            raise ValueError("Invalid job fields")
        with self.lock, self.db:
            fields = ["state=?", "updated=?"] + [k + "=?" for k in values]
            payload = [state, now()] + [json.dumps(v, ensure_ascii=False) if k != "error" else v for k, v in values.items()]
            if self.db.execute("UPDATE jobs SET " + ",".join(fields) + " WHERE id=?", (*payload, jid)).rowcount != 1:
                raise ValueError("Unknown job")
            self.db.execute("INSERT INTO events(job_id,at,state,message) VALUES(?,?,?,?)", (jid, now(), state, message))

    def job(self, jid):
        with self.lock:
            row = self.db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
            if row is None:
                raise ValueError("Unknown job")
            result = dict(row)
            for key in ("proposal", "pack", "report", "usage"):
                result[key] = json.loads(result[key]) if result[key] else None
            result["events"] = [dict(r) for r in self.db.execute("SELECT * FROM events WHERE job_id=? ORDER BY seq", (jid,))]
            return result

    def jobs(self):
        with self.lock:
            return [dict(r) for r in self.db.execute("SELECT id,focus,provider,model,state,created,updated,error FROM jobs ORDER BY created DESC LIMIT 200")]

    def snapshot(self):
        from ..generation.civic_catalog import BUILDING_TEMPLATES
        objects, rooms, graphics, buildings = dict(CATALOG), deepcopy(ROOMS), {}, deepcopy(BUILDING_TEMPLATES)
        with self.lock:
            publications = [dict(row) for row in self.db.execute("SELECT * FROM publications ORDER BY published_at,pack_id")]
        for entry in publications:
            compile_pack(ContentPack.model_validate_json(entry["content"]), objects, rooms, graphics, buildings)
        revision = digest({"generator": GENERATOR_VERSION, "base_objects": {k: asdict(v) for k, v in CATALOG.items()},
                           "base_rooms": ROOMS, "base_buildings": BUILDING_TEMPLATES,
                           "packs": [p["hash"] for p in publications]})
        return {"objects": objects, "rooms": rooms, "graphics": graphics, "buildings": buildings,
                "revision": revision, "publications": [{k: v for k, v in p.items() if k != "content"} for p in publications]}

    def inventory(self):
        snap = self.snapshot()
        return {"revision": snap["revision"], "objects": {k: v.name for k, v in snap["objects"].items()},
                "rooms": {k: v["name"] for k, v in snap["rooms"].items()},
                "buildings": snap["buildings"], "publications": snap["publications"],
                "action_ids": list(ACTIONS)}

    def validate(self, raw):
        snap = self.snapshot()
        report = {"valid": False, "errors": [], "room_checks": 0, "building_checks": 0,
                  "observed_objects": [], "previews": [], "base_revision": snap["revision"],
                  "pack_hash": digest(raw), "generator_version": GENERATOR_VERSION,
                  "visual_review": "required_before_publication", "tested_seeds": [0, 1]}
        try:
            pack = ContentPack.model_validate(raw)
        except ValidationError as exc:
            report["errors"] = ["schema:" + ".".join(map(str, e["loc"])) + ":" + e["msg"]
                                for e in exc.errors(include_input=False, include_url=False)]
            return report
        if pack.id in {p["pack_id"] for p in snap["publications"]}:
            report["errors"].append("pack_id_already_published")
        for items, existing in ((pack.objects, snap["objects"]), (pack.rooms, snap["rooms"]), (pack.buildings, snap["buildings"])):
            names = {name_key(value.name if isinstance(value, Furniture) else value["name"]) for value in existing.values()}
            for item in items:
                if item.id in existing:
                    report["errors"].append("id_collision:" + item.id)
                if name_key(item.name) in names:
                    report["errors"].append("name_collision_requires_review:" + item.id)
                names.add(name_key(item.name))
        for obj in pack.objects:
            if set(obj.actions) - ACTIONS.keys():
                report["errors"].append("unknown_action:" + obj.id)
            # Geometry alone is insufficient for sleep-slot allocation. That
            # requires an engine/capacity extension, never a silent fake bed.
            if "sleep" in obj.actions:
                report["errors"].append("sleep_capacity_engine_extension_required:" + obj.id)
        compile_pack(pack, snap["objects"], snap["rooms"], snap["graphics"], snap["buildings"])
        for room in pack.rooms:
            if (set(room.required) | set(room.optional)) - snap["objects"].keys():
                report["errors"].append("unknown_object_reference:" + room.id)
        for building in pack.buildings:
            if set(building.room_program) - snap["rooms"].keys():
                report["errors"].append("unknown_room_reference:" + building.id)
        used = {kind for room in pack.rooms for kind in room.required}
        for obj in pack.objects:
            if obj.id not in used:
                report["errors"].append("new_object_not_required_in_test_room:" + obj.id)
        if report["errors"]:
            return report
        observed = set()
        for room in pack.rooms:
            for size in sorted({(room.width, room.height), (room.min_width, room.min_height)}):
                for side in ("north", "east", "south", "west"):
                    for seed in report["tested_seeds"]:
                        try:
                            result = generate_room(room.id, seed, *size, door_side=side,
                                                   object_catalog=snap["objects"], room_catalog=snap["rooms"])
                            check = validate_room(result, object_catalog=snap["objects"])
                            if not check["valid"]:
                                raise GenerationError(",".join(check["errors"]))
                            observed.update(o["kind"] for o in result["objects"])
                            for obj in result["objects"]:
                                if obj["kind"] in snap["graphics"]:
                                    obj["procedural_sprite"] = snap["graphics"][obj["kind"]]["pixels"]
                            if size == (room.width, room.height) and side == "south" and seed == 0:
                                report["previews"].append(result)
                        except GenerationError as exc:
                            report["errors"].append(f"room:{room.id}:{size}:{side}:{seed}:{exc}")
                        report["room_checks"] += 1
        for template in pack.buildings:
            from ..generation.buildings import generate_building
            request = {"width": template.width, "depth": template.depth,
                       "levels_above_ground": template.levels, "basements": 0,
                       "room_count": len(template.room_program), "room_program": template.room_program,
                       "residents": {"adults": 0, "children": 0, "teens": 0}, "seed": 42}
            try:
                design = generate_building(request, object_catalog=snap["objects"], room_catalog=snap["rooms"])
                if not design["validation"]["valid"]:
                    report["errors"].append("building_validation:" + template.id)
            except (GenerationError, ValueError) as exc:
                report["errors"].append("building:" + template.id + ":" + str(exc))
            report["building_checks"] += 1
        report["observed_objects"] = sorted(observed)
        report["valid"] = not report["errors"]
        return report

    def stage(self, jid, raw):
        with self.lock, self.db:
            changed = self.db.execute("UPDATE jobs SET state='validating',updated=?,pack=? WHERE id=? AND state IN ('queued','drafting','failed','rejected','awaiting_review')",
                                      (now(), json.dumps(raw, ensure_ascii=False), jid)).rowcount
            if not changed:
                raise ValueError("Job is unknown, currently validating, or immutable after publication")
            self.db.execute("INSERT INTO events(job_id,at,state,message) VALUES(?,?,?,?)",
                            (jid, now(), "validating", "Geometrie, Nutzungsflächen, Referenzen und Pixelvertrag werden geprüft."))
        report = self.validate(raw)
        self.transition(jid, "awaiting_review" if report["valid"] else "rejected",
                        "Technische Prüfung bestanden; Sichtprüfung/Freigabe fehlt." if report["valid"] else "Entwurf abgelehnt; veröffentlichte Bibliothek bleibt unverändert.", report=report)
        return report

    def publish(self, jid, reviewer, *, visual_reviewed=False, expected_pack_hash=None):
        if not visual_reviewed or not isinstance(reviewer, str) or not 2 <= len(reviewer) <= 80:
            raise ValueError("Explicit reviewer and completed visual review required")
        with self.lock:
            # A database write lease also serializes publication across separate
            # CLI/server processes, not just threads using this Library object.
            self.db.execute("BEGIN IMMEDIATE")
            try:
                job = self.job(jid)
                if job["state"] != "awaiting_review":
                    raise ValueError("Only technically validated drafts can be published")
                if not job["report"] or job["report"]["pack_hash"] != digest(job["pack"]):
                    raise ValueError("Preview no longer matches the draft; repeat review")
                if expected_pack_hash is not None and expected_pack_hash != digest(job["pack"]):
                    raise ValueError("The viewed draft changed; load and review it again")
                report = self.validate(job["pack"])
                if not report["valid"]:
                    self.db.rollback()
                    self.transition(jid, "rejected", "Bibliothek hat sich geändert; erneute Prüfung abgelehnt.", report=report)
                    raise ValueError("Current library rejects this pack: " + ", ".join(report["errors"][:3]))
                self.db.execute("INSERT INTO publications VALUES(?,?,?,?,?,?)",
                                (job["pack"]["id"], jid, json.dumps(job["pack"], ensure_ascii=False),
                                 digest(job["pack"]), reviewer, now()))
                self.db.execute("UPDATE jobs SET state='published',updated=?,report=? WHERE id=?", (now(), json.dumps(report), jid))
                self.db.execute("INSERT INTO events(job_id,at,state,message) VALUES(?,?,?,?)",
                                (jid, now(), "published", f"Geprüft und freigegeben durch {reviewer}."))
                self.db.commit()
            except BaseException:
                self.db.rollback()
                raise
            return self.job(jid)
