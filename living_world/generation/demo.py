"""An isolated Python navigation rig, not another autonomous life simulation.

Residents are test walkers. Floors change only when a timed portal traversal
finishes. A shared lift has one cabin and a FIFO queue across all floor pairs.
"""
from copy import deepcopy
from collections import deque

from .navigation import FloorNavigation


class NavigationDemo:
    def __init__(self, house):
        self.house = house
        self.nav = FloorNavigation(house)
        self.now = 0
        self.actors = {}
        self.resources = {p["resource_id"]: {"owner": None, "queue": [], "floor": 0} for p in house["portals"]}
        self.events = []
        self.event_sequence = 0
        self.metrics = {"walk_steps": 0, "stairs_trips": 0, "elevator_trips": 0, "arrivals": 0, "queue_wait_seconds": 0}
        self.targets = []
        for floor in house["floors"]:
            for room in floor["rooms"]:
                obj = next((o for o in floor["objects"] if o["room_id"] == room["id"] and o["anchors"]), None)
                if obj:
                    self.targets.append({"id": room["id"], "name": room["name"], "floor": floor["level"],
                                         "position": [floor["level"], *obj["anchors"][0]]})
        if not self.targets:
            raise ValueError("Testhaus benötigt mindestens einen erreichbaren Raum")
        entrance = tuple(house["entrance"])
        nearby, seen, queue = [], {entrance}, deque([entrance])
        while queue and len(nearby) < 6:
            node = queue.popleft()
            if node != entrance:
                nearby.append(list(node))
            for p, _, portal in self.nav.neighbors(node):
                if portal is None and p not in seen:
                    seen.add(p); queue.append(p)
        if len(nearby) < 3:
            raise ValueError("Eingang bietet zu wenig freie Startplätze")
        spawned = set()
        for i, name in enumerate(("Mara", "Nils", "Juno")):
            position = list(house["entrance"])
            position[2] -= i + 1
            if tuple(position) not in self.nav.free or tuple(position) in spawned:
                position = next(p[:] for p in nearby if tuple(p) not in spawned)
            spawned.add(tuple(position))
            aid = f"walker-{i}"
            self.actors[aid] = {"id": aid, "name": name, "position": position, "route": None, "index": 0,
                                "ride": None, "status": "Bereit", "target": None, "next_at": 0,
                                "transport": "stairs" if i == 0 or not house["elevator"] else "elevator",
                                "appearance": {"shirt": ["#cb775c", "#6b9ca4", "#9684af"][i], "skin": ["#e9ba94", "#996342", "#f0cfad"][i], "hair": ["#574338", "#352f32", "#a56b3f"][i], "style": i},
                                "journeys": 0, "auto": True}
            upstairs = [t for t in self.targets if t["floor"] == max(t["floor"] for t in self.targets)]
            self.command(aid, upstairs[i % len(upstairs)]["id"], self.actors[aid]["transport"])

    def log(self, actor, kind, text, **details):
        self.event_sequence += 1
        self.events.append({"id": self.event_sequence, "time": self.now, "actor_id": actor["id"], "kind": kind, "text": text, **details})
        self.events = self.events[-120:]

    def command(self, aid, target_id, transport="auto"):
        if aid not in self.actors:
            raise ValueError("Unbekannter Test-NPC")
        if transport not in ("auto", "stairs", "elevator"):
            raise ValueError("Unbekannte Bewegungsart")
        actor = self.actors[aid]
        if actor["ride"]:
            raise ValueError("Etagenfahrt läuft; Umplanung ist erst nach der Ankunft möglich")
        target = next((t for t in self.targets if t["id"] == target_id), None)
        if target is None:
            raise ValueError("Unbekanntes Raumziel")
        route = self.nav.route(actor["position"], target["position"], transport)
        if route is None:
            raise ValueError("Kein zulässiger Weg mit dieser Bewegungsart")
        for resource in self.resources.values():
            resource["queue"] = [entry for entry in resource["queue"] if entry != aid]
        actor.update({"route": route, "index": 0, "target": target, "transport": transport, "status": "Unterwegs", "next_at": self.now})
        self.log(actor, "intent", f"{actor['name']} geht zu {target['name']} auf Etage {target['floor']}.", target=target, estimated_seconds=route["seconds_without_queue"])
        return route

    def phase(self, ride):
        elapsed = self.now - ride["start"]
        if ride["kind"] == "stairs":
            return "Treppe steigen"
        if elapsed < ride["call_seconds"]:
            return "Aufzug wird gerufen"
        if elapsed < ride["call_seconds"] + 4:
            return "Einsteigen"
        if elapsed < ride["duration"] - 4:
            return "Aufzug fährt"
        return "Aussteigen"

    def tick(self):
        self.now += 1
        for actor in self.actors.values():
            ride = actor["ride"]
            if ride:
                if self.now >= ride["end"]:
                    resource = self.resources[ride["resource_id"]]
                    actor["position"] = list(ride["to"])
                    resource["owner"] = None
                    resource["floor"] = ride["to"][0]
                    actor["ride"] = None
                    actor["index"] += 1
                    actor["status"] = "Unterwegs"
                    self.metrics["stairs_trips" if ride["kind"] == "stairs" else "elevator_trips"] += 1
                    self.log(actor, "portal_arrival", f"{actor['name']} ist auf Etage {ride['to'][0]} angekommen.", origin=ride["from"], destination=ride["to"], transport=ride["kind"], departed_at=ride["start"], arrived_at=self.now)
                else:
                    phase = self.phase(ride)
                    if phase != actor["status"]:
                        actor["status"] = phase
                        self.log(actor, "portal_phase", f"{actor['name']}: {phase}.", transport=ride["kind"])
                continue
            route = actor["route"]
            if route is None:
                if actor["auto"] and self.now >= actor["next_at"]:
                    candidates = [t for t in self.targets if t["floor"] != actor["position"][0]] or self.targets
                    index = (actor["journeys"] + int(actor["id"].split("-")[-1])) % len(candidates)
                    self.command(actor["id"], candidates[index]["id"], actor["transport"])
                continue
            if actor["index"] >= len(route["steps"]):
                actor["route"] = None
                actor["status"] = "Am Ziel"
                actor["journeys"] += 1
                actor["next_at"] = self.now + 8
                self.metrics["arrivals"] += 1
                self.log(actor, "arrival", f"{actor['name']} hat {actor['target']['name']} erreicht.", position=actor["position"])
                continue
            step = route["steps"][actor["index"]]
            if step["kind"] == "walk":
                actor["position"] = list(step["to"])
                actor["index"] += 1
                actor["status"] = "Geht durch das Haus"
                self.metrics["walk_steps"] += 1
                continue
            resource = self.resources[step["resource_id"]]
            if actor["id"] not in resource["queue"]:
                resource["queue"].append(actor["id"])
            if resource["owner"] is not None or resource["queue"][0] != actor["id"]:
                if actor["status"] != "Wartet am Etagenzugang":
                    self.log(actor, "queue", f"{actor['name']} wartet, bis der Etagenzugang frei ist.", resource_id=step["resource_id"])
                actor["status"] = "Wartet am Etagenzugang"
                self.metrics["queue_wait_seconds"] += 1
                continue
            resource["queue"].pop(0)
            resource["owner"] = actor["id"]
            call = abs(resource["floor"] - step["from"][0]) * 4 if step["kind"] == "elevator" else 0
            duration = step["duration"] + call
            actor["ride"] = {**step, "start": self.now, "end": self.now + duration, "duration": duration, "call_seconds": call}
            actor["status"] = self.phase(actor["ride"])
            self.log(actor, "portal_departure", f"{actor['name']}: {actor['status']}, Ziel Etage {step['to'][0]}.", transport=step["kind"], origin=step["from"], destination=step["to"], due=self.now + duration)

    def advance(self, seconds):
        if not isinstance(seconds, int) or not 0 <= seconds <= 3600:
            raise ValueError("A demo advance supports 0–3600 integer seconds")
        for _ in range(seconds):
            self.tick()
        errors = self.invariants()
        if errors:
            raise RuntimeError("Navigation invariant violated: " + ", ".join(errors))
        return self.snapshot()

    def invariants(self):
        errors = []
        for actor in self.actors.values():
            if actor["ride"]:
                ride = actor["ride"]
                if self.resources[ride["resource_id"]]["owner"] != actor["id"]:
                    errors.append("missing_portal_reservation")
                if tuple(ride["to"]) not in self.nav.free or tuple(ride["from"]) not in self.nav.free:
                    errors.append("blocked_portal_endpoint")
                if self.now >= ride["end"]:
                    errors.append("late_portal_completion")
            elif tuple(actor["position"]) not in self.nav.free:
                errors.append("actor_in_blocked_cell")
        for rid, resource in self.resources.items():
            if len(resource["queue"]) != len(set(resource["queue"])):
                errors.append("duplicate_waiter")
            rides = [a for a in self.actors.values() if a["ride"] and a["ride"]["resource_id"] == rid]
            if len(rides) > 1 or (resource["owner"] is not None and len(rides) != 1):
                errors.append("portal_capacity_violation")
        return errors

    def snapshot(self):
        actors = []
        for person in self.actors.values():
            actor = deepcopy(person)
            if actor["ride"]:
                # A person in a portal is not duplicated on its endpoint floors.
                actor["location"] = {"kind": "portal", "resource_id": actor["ride"]["resource_id"], "from": actor["ride"]["from"], "to": actor["ride"]["to"],
                                     "progress": (self.now - actor["ride"]["start"]) / actor["ride"]["duration"]}
                actor["position"] = None
            else:
                actor["location"] = {"kind": "floor", "floor": actor["position"][0], "x": actor["position"][1], "y": actor["position"][2]}
            actors.append(actor)
        return {"clock": self.now, "actors": actors, "resources": deepcopy(self.resources), "events": deepcopy(self.events[-45:]),
                "metrics": dict(self.metrics), "invariant_errors": self.invariants(), "targets": self.targets,
                "scope": "Isolierter Navigationstest; keine Übernahme von Bewohnerzuständen aus der Hauptwelt"}
