# Parameterized rectangular buildings

`living_world.generation.buildings.generate_building(request, *, object_catalog=None, room_catalog=None)` creates a house-compatible design for `FloorNavigation` and `NavigationDemo`. It leaves the seeded fixed-house generator unchanged.

Required request fields:

```python
{
    "width": 24,                    # metres / one metre cells
    "depth": 25,
    "room_count": 6,                # total across the whole building; circulation excluded
    "levels_above_ground": 2,       # supported range 1..5
    "basements": 1,                 # supported range 0..1
    "residents": {"adults": 2, "children": 1, "teens": 1},
}
```

Optional fields are `seed` (integer or string, default `42`), `style` (a known palette), `elevator` (default false), `terrace_exit` (default false), and `room_program` (a list of room-kind strings). A supplied `room_program` must contain exactly `room_count` entries. Residential programs require living, kitchen, and bathroom rooms; the generator rejects a room count too small to include those plus typed sleeping rooms. Without `room_program`, it adds common and sleeping rooms, then utility and other non-sleeping rooms while slots remain. It rejects a request when the program cannot provide the requested adult, child, and teen sleep slots. Capacity is read from required bed kinds and the shared `BED_CAPACITIES` definitions. A bedroom represents two adult slots, while child and teen rooms each represent one slot of that type by default.

Example:

```python
from living_world.generation.buildings import generate_building

design = generate_building({
    "width": 24, "depth": 25, "room_count": 6,
    "levels_above_ground": 2, "basements": 1,
    "residents": {"adults": 2, "children": 1, "teens": 1},
    "elevator": True,
})
```

Returned `floors` retain contiguous navigation `level` values `0..n-1`; each floor also has `elevation` (`-1` for the basement, `0` at grade, then positive storeys). `ground_floor_index` and `entrance` point to the ground floor. The return value includes standard terrain, objects, room records, doors, `portal_geometry`, stacked stair links, optional elevator links, and `validation`. The validation reports actual room count, graph reachability, typed sleep capacity, and a per-floor and total `footprint_coverage` with assigned and unassigned cell counts. Rooms expand beyond catalog minima as space permits, up to 14 metres per side; if a larger room cannot be furnished by the bounded room search, it retries at the exact catalog minimum. `terrace_exit` adds a second ground-level exterior door and `terrace_destination` describes the adjacent garden terrace as an external destination; it does not add terrain beyond the requested footprint.

## Geometry and limits

This first slice handles rectangular footprints only. It uses room catalog minimum dimensions as hard limits, never grows the requested footprint, and raises `GenerationError` if room minima, circulation, door landings, or typed sleeping needs do not fit. A four-row minimum circulation band reserves the far end for separate stacked stair and elevator shafts; its room-facing edge rows are walls with openings only at actual doors. Living, kitchen, and bathroom rooms go on grade, utility rooms can go in the basement, and sleeping rooms go above grade when an upper floor exists. Every furnished-object anchor must be reachable from the entrance; invalid navigation raises instead of returning a misleading plan. Large residual areas remain unbuilt and are reported in `footprint_coverage` rather than presented as rooms.

The footprints are proof-of-layout grids, not architectural plans. They do not model walls as physical thickness, egress code, structural design, daylight rules, accessibility dimensions, exterior terrace area, or arbitrary polygon footprints. Bedroom variants and other pack-specific room types may be supplied through catalogs when supported by the shared room generator.
