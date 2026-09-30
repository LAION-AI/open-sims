"""Additive bed geometry and gameplay metadata.

This module deliberately does not mutate the shared furniture catalog on import.
The host may construct Furniture values with ``Furniture(**spec)`` and merge
them explicitly when it is ready to expose these variants.
"""

# Furniture-compatible kwargs. Dimensions are meters; beds are headboard-to-foot
# along local +y except the compact foldaway, whose sleep axis runs along +x.
# ``front=True`` provides foot access; the placed() integration hook also adds
# the climb/transfer edge along the canonical local right side.
BED_SPECS = {
    "bed_storage_single": {
        "name": "Stauraum-Einzelbett", "w": 1, "h": 2, "wall": True,
        "tall": False, "front": True, "sprite": "bed_storage_single",
        "extra_access": (),
    },
    "bed_loft": {
        "name": "Hochbett", "w": 1, "h": 2, "wall": True,
        "tall": True, "front": True, "sprite": "bed_loft",
        "extra_access": (),
    },
    "bed_bunk": {
        "name": "Etagenbett", "w": 1, "h": 2, "wall": True,
        "tall": True, "front": True, "sprite": "bed_bunk",
        "extra_access": (),
    },
    "bed_queen": {
        "name": "Queensize-Bett", "w": 2, "h": 3, "wall": True,
        "tall": False, "front": True, "sprite": "bed_queen",
        "extra_access": (),
    },
    "bed_king": {
        "name": "Kingsize-Bett", "w": 3, "h": 3, "wall": True,
        "tall": False, "front": True, "sprite": "bed_king",
        "extra_access": (),
    },
    "bed_platform_double": {
        "name": "Doppelbett mit Plattform", "w": 2, "h": 3,
        "wall": True, "tall": False, "front": True,
        "sprite": "bed_platform_double", "extra_access": (),
    },
    "bed_foldaway_guest": {
        "name": "Gästeklappbett", "w": 2, "h": 1, "wall": True,
        "tall": False, "front": True, "sprite": "bed_foldaway_guest",
        "extra_access": (),
    },
    "bed_hospital": {
        "name": "Pflegebett", "w": 2, "h": 3, "wall": True,
        "tall": False, "front": True, "sprite": "bed_hospital",
        "extra_access": (),
    },
}


# Gameplay data is kept separate from Furniture's geometry contract.
BED_CAPACITIES = {
    "bed_storage_single": 1,
    "bed_loft": 1,
    "bed_bunk": 2,
    "bed_queen": 2,
    "bed_king": 2,
    "bed_platform_double": 2,
    "bed_foldaway_guest": 1,
    "bed_hospital": 1,
}

BED_TRAITS = {
    "bed_storage_single": {"tags": ("bed", "single", "storage"), "interactions": ("sleep", "rest", "make_bed")},
    "bed_loft": {"tags": ("bed", "single", "loft", "child_friendly"), "interactions": ("sleep", "rest", "make_bed")},
    "bed_bunk": {"tags": ("bed", "bunk", "shared"), "interactions": ("sleep", "rest", "make_bed")},
    "bed_queen": {"tags": ("bed", "double", "queen"), "interactions": ("sleep", "rest", "make_bed")},
    "bed_king": {"tags": ("bed", "double", "king"), "interactions": ("sleep", "rest", "make_bed")},
    "bed_platform_double": {"tags": ("bed", "double", "platform"), "interactions": ("sleep", "rest", "make_bed")},
    "bed_foldaway_guest": {"tags": ("bed", "single", "foldaway", "guest"), "interactions": ("sleep", "rest", "make_bed")},
    "bed_hospital": {"tags": ("bed", "single", "hospital", "adjustable"), "interactions": ("sleep", "rest", "make_bed", "adjust_backrest")},
}


def bed_placement_access(kind, x, y, orientation=0):
    """Return the local placement geometry used by the catalog's placed().

    Coordinates are absolute room cells. The full foot edge is reachable; a
    side edge from local y=1 onward is retained for getting into the bed while
    leaving the headboard edge clear for wall placement. ``orientation`` uses
    the same quarter-turn convention as catalog.rotate_cell.
    """
    # Lazy import lets catalog.py import BED_SPECS while defining CATALOG.
    from .catalog import rotate_cell

    spec = BED_SPECS[kind]
    w, h = spec["w"], spec["h"]
    front = ([(xx, h) for xx in range(w)] if spec["front"] else [])
    front += [(w, yy) for yy in range(1, h)]
    clearance = [[x + a, y + b] for a, b in
                 (rotate_cell(xx, yy, w, h, orientation) for xx, yy in front)]
    rw, rh = (h, w) if orientation % 2 else (w, h)
    return {
        "kind": kind, "name": spec["name"], "sprite": spec["sprite"],
        "x": x, "y": y, "w": rw, "h": rh, "base_w": w, "base_h": h,
        "orientation": orientation, "blocking": True,
        "clearance": clearance, "anchors": clearance[:], "tall": spec["tall"],
    }
