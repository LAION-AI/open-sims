"""Audit city layouts and real room routes across a reproducible seed set."""
from copy import deepcopy
import json
from pathlib import Path

from living_world.generation.city import SERVICES, generate_city, route_to_city_room
from living_world.spatial import SpatialService


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "story" / "city-seed-verification.json"


def main():
    main_map = SpatialService(42)
    original_cells = bytes(main_map.cells)
    original_objects = deepcopy(main_map.objects)
    original_buildings = deepcopy(main_map.buildings)
    results = []
    for seed in range(24):
        city = generate_city(seed=seed)
        assert city["validation"]["valid"]
        assert set(city["validation"]["services"]) == set(SERVICES)
        assert city["validation"]["connected_public_cells"] == len(city["public_walkable"])
        checked = 0
        for plot in city["plots"]:
            assert plot["design"]["validation"]["valid"]
            assert plot["door"] in city["public_walkable"]
            # One real room route in every plot on every seed; every room on
            # the reference layout also gets an end-to-end route audit.
            rooms = [room for floor in plot["design"]["floors"] for room in floor["rooms"]]
            for room in rooms if seed == 0 else rooms[:1]:
                route = route_to_city_room(city, plot["id"], room["id"])
                assert route["valid"]
                assert route["public_path"][-1] == plot["door"]
                assert route["interior_route"]["start"] == plot["design"]["entrance"]
                checked += 1
        results.append({"seed": seed, "buildings": len(city["plots"]),
                        "room_routes_checked": checked,
                        "public_cells": len(city["public_walkable"]),
                        "jobs": city["validation"]["jobs"]})
        print(f"seed {seed:02d}: {checked} room routes valid", flush=True)
    assert bytes(main_map.cells) == original_cells
    assert main_map.objects == original_objects
    assert main_map.buildings == original_buildings
    report = {"passed": True, "seeds": len(results),
              "room_routes_checked": sum(row["room_routes_checked"] for row in results),
              "main_map_unchanged": True, "results": results}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
