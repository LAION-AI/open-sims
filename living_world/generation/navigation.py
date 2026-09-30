"""One graph over (floor, x, y); vertical edges are explicit timed portals."""
from collections import deque
import heapq

from .rooms import cells


class FloorNavigation:
    def __init__(self, house):
        self.house = house
        self.free = set()
        self.portal_edges = {}
        for floor in house["floors"]:
            blocked = set().union(*(cells(o) for o in floor["objects"] + floor["portal_geometry"]))
            for i, terrain in enumerate(floor["terrain"]):
                x, y = i % floor["width"], i // floor["width"]
                if terrain and (x, y) not in blocked:
                    self.free.add((floor["level"], x, y))
        for portal in house["portals"]:
            a, b = tuple(portal["from"]), tuple(portal["to"])
            self.portal_edges.setdefault(a, []).append((b, portal))
            self.portal_edges.setdefault(b, []).append((a, portal))

    def neighbors(self, node, transport="auto", accessible=False):
        level, x, y = node
        for p in ((level, x + 1, y), (level, x - 1, y), (level, x, y + 1), (level, x, y - 1)):
            if p in self.free:
                yield p, 1, None
        for target, portal in self.portal_edges.get(node, []):
            if target not in self.free or (accessible and not portal["accessible"]):
                continue
            if transport in ("stairs", "elevator") and portal["kind"] != transport:
                continue
            yield target, portal["duration_seconds"], portal

    def route(self, start, end, transport="auto", accessible=False):
        start, end = tuple(start), tuple(end)
        if start not in self.free or end not in self.free:
            return None
        frontier = [(0, start)]
        costs = {start: 0}
        previous = {}
        while frontier:
            cost, node = heapq.heappop(frontier)
            if cost != costs[node]:
                continue
            if node == end:
                steps = []
                while node != start:
                    parent, duration, portal = previous[node]
                    steps.append({"from": list(parent), "to": list(node), "duration": duration,
                                  "kind": portal["kind"] if portal else "walk", "portal_id": portal["id"] if portal else None,
                                  "resource_id": portal["resource_id"] if portal else None})
                    node = parent
                steps.reverse()
                return {"start": list(start), "end": list(end), "seconds_without_queue": cost,
                        "steps": steps, "transport": transport, "accessible": accessible}
            for target, duration, portal in self.neighbors(node, transport, accessible):
                nc = cost + duration
                if nc < costs.get(target, float("inf")):
                    costs[target] = nc
                    previous[target] = (node, duration, portal)
                    heapq.heappush(frontier, (nc, target))
        return None

    def validate(self):
        start = tuple(self.house["entrance"])
        visited = {start} if start in self.free else set()
        queue = deque(visited)
        errors = [] if visited else ["blocked_entrance"]
        while queue:
            for target, _, _ in self.neighbors(queue.popleft()):
                if target not in visited:
                    visited.add(target); queue.append(target)
        anchors = []
        for floor in self.house["floors"]:
            for obj in floor["objects"]:
                for x, y in obj["anchors"]:
                    target = (floor["level"], x, y)
                    anchors.append(target)
                    if target not in visited:
                        errors.append(f"unreachable:{obj['id']}")
        for portal in self.house["portals"]:
            if tuple(portal["from"]) not in self.free or tuple(portal["to"]) not in self.free:
                errors.append(f"blocked_portal:{portal['id']}")
        if len(visited) != len(self.free):
            errors.append("disconnected_floor_area")
        return {"valid": not errors, "errors": sorted(set(errors)), "reachable_cells": len(visited),
                "total_walkable_cells": len(self.free), "reachable_anchors": len(anchors), "floor_count": self.house["levels"],
                "stairs_links": sum(p["kind"] == "stairs" for p in self.house["portals"]),
                "lift_links": sum(p["kind"] == "elevator" for p in self.house["portals"])}
