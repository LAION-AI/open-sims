"""Authorable furniture and room contracts. Geometry is in integer meters.

An occupied footprint, protected front clearance and interaction anchors are
separate concepts. Rugs are decorative overlays; they never block navigation.
"""
from dataclasses import dataclass, asdict
from . import GENERATOR_VERSION
from .bed_variants import BED_SPECS, BED_CAPACITIES
from .civic_catalog import CIVIC_OBJECT_SPECS, CIVIC_ROOMS, BUILDING_TEMPLATES, PUBLIC_BUILDING_BACKLOG


@dataclass(frozen=True)
class Furniture:
    name: str
    w: int
    h: int
    wall: bool = False
    tall: bool = False
    front: bool = True
    sprite: str | None = None
    extra_access: tuple[str, ...] = ()


CATALOG = {
    "sofa": Furniture("Dreisitziges Sofa", 3, 1, True),
    "armchair": Furniture("Sessel", 1, 1),
    "coffee_table": Furniture("Couchtisch", 2, 1, sprite="table"),
    "tv": Furniture("TV-Konsole", 2, 1, True),
    "bookshelf": Furniture("Bücherregal", 2, 1, True, True),
    "plant": Furniture("Zimmerpflanze", 1, 1),
    "aquarium": Furniture("Aquarium", 2, 1, True),
    "side_table": Furniture("Beistelltisch", 1, 1, sprite="table"),
    "floor_lamp": Furniture("Stehleuchte", 1, 1),
    "double_bed": Furniture("Doppelbett", 2, 3, True, sprite="bed"),
    "single_bed": Furniture("Einzelbett", 1, 2, True, sprite="bed"),
    "wardrobe": Furniture("Kleiderschrank", 2, 1, True, True),
    "desk": Furniture("Schreibtisch", 2, 1, True),
    "toy_storage": Furniture("Spielzeugregal", 2, 1, True),
    "child_table": Furniture("Basteltisch", 1, 1),
    "fridge": Furniture("Kühlschrank", 1, 1, True, True),
    "sink": Furniture("Spüle", 1, 1, True),
    "stove": Furniture("Herd", 1, 1, True),
    "counter": Furniture("Arbeitsfläche", 2, 1, True),
    "dining_table": Furniture("Esstisch mit Sitzplätzen", 2, 2),
    "shower": Furniture("Dusche", 1, 2, True),
    "toilet": Furniture("Toilette", 1, 1, True),
    "basin": Furniture("Waschbecken", 1, 1, True, sprite="sink"),
    "cabinet": Furniture("Wäscheschrank", 1, 1, True, True),
    "washing_machine": Furniture("Waschmaschine", 1, 1, True),
    "bench": Furniture("Sitzbank", 2, 1, True),
    "coat_rack": Furniture("Garderobe", 1, 1, True, True),
    "shoe_rack": Furniture("Schuhregal", 2, 1, True),
    "bar": Furniture("Hausbar", 3, 1, True),
    "stereo": Furniture("Musikanlage", 2, 1, True),
    "sideboard": Furniture("Sideboard", 3, 1, True),
    "display_cabinet": Furniture("Glasvitrine", 2, 1, True, True),
    "large_dining_table": Furniture("Großer Esstisch", 3, 2, extra_access=("back",)),
    "buffet": Furniture("Geschirrbuffet", 2, 1, True),
    "kitchen_island": Furniture("Kücheninsel", 3, 1, extra_access=("back",)),
    "dishwasher": Furniture("Geschirrspüler", 1, 1, True),
    "microwave_cart": Furniture("Mikrowellenwagen", 1, 1, True),
    "coffee_station": Furniture("Kaffeestation", 1, 1, True),
    "pantry_shelf": Furniture("Vorratsregal", 2, 1, True, True),
    "freezer": Furniture("Gefriertruhe", 2, 1, True),
    "produce_crate": Furniture("Obst- und Gemüsekiste", 1, 1, True),
    "dresser": Furniture("Kommode", 2, 1, True),
    "vanity": Furniture("Schminktisch mit Spiegel", 2, 1, True),
    "luggage_rack": Furniture("Kofferbank", 2, 1, True),
    "crib": Furniture("Babybett", 1, 2, True, extra_access=("right",)),
    "changing_table": Furniture("Wickelkommode", 2, 1, True),
    "rocking_chair": Furniture("Schaukelstuhl", 1, 1),
    "baby_storage": Furniture("Babyregal", 2, 1, True),
    "bathtub": Furniture("Badewanne", 3, 1, True),
    "towel_rack": Furniture("Handtuchständer", 1, 1, True),
    "laundry_basket": Furniture("Wäschekorb", 1, 1),
    "dryer": Furniture("Wäschetrockner", 1, 1, True),
    "ironing_board": Furniture("Bügelbrett", 2, 1),
    "drying_rack": Furniture("Wäscheständer", 2, 2, extra_access=("back",)),
    "utility_sink": Furniture("Ausgussbecken", 2, 1, True),
    "filing_cabinet": Furniture("Aktenschrank", 1, 1, True, True),
    "printer_stand": Furniture("Druckerwagen", 1, 1, True),
    "office_desk": Furniture("Großer Büroschreibtisch", 3, 1, True),
    "reading_table": Furniture("Lesetisch", 2, 2, extra_access=("back",)),
    "piano": Furniture("Klavier", 3, 1, True),
    "guitar_stand": Furniture("Gitarre im Ständer", 1, 1, True),
    "drum_kit": Furniture("Schlagzeug", 2, 2),
    "synthesizer": Furniture("Keyboard", 2, 1, True),
    "treadmill": Furniture("Laufband", 1, 2, True),
    "exercise_bike": Furniture("Heimtrainer", 1, 2, True),
    "weight_bench": Furniture("Hantelbank", 1, 2, extra_access=("left", "right")),
    "dumbbell_rack": Furniture("Hantelständer", 2, 1, True),
    "punching_bag": Furniture("Standboxsack", 1, 1, extra_access=("left", "right", "back")),
    "workbench": Furniture("Werkbank", 3, 1, True),
    "tool_cabinet": Furniture("Werkzeugschrank", 2, 1, True, True),
    "storage_rack": Furniture("Lagerregal", 2, 1, True, True),
    "sewing_table": Furniture("Nähmaschinentisch", 2, 1, True),
    "easel": Furniture("Staffelei", 1, 2),
    "potting_bench": Furniture("Pflanztisch", 2, 1, True),
    "planter_box": Furniture("Pflanzkasten", 2, 1, True),
    "plant_shelf": Furniture("Pflanzenregal", 2, 1, True),
    "chess_table": Furniture("Schachtisch", 1, 1, extra_access=("back",)),
    "gaming_desk": Furniture("Gaming-Schreibtisch", 2, 1, True),
    "arcade": Furniture("Spielautomat", 1, 1, True, True),
    "pool_table": Furniture("Billardtisch", 3, 2, extra_access=("back", "left", "right")),
    "foosball_table": Furniture("Tischkicker", 2, 1, front=False, extra_access=("left", "right")),
    "pingpong_table": Furniture("Tischtennisplatte", 3, 2, extra_access=("back",)),
}

ROOMS = {
    "living": {"name": "Wohnzimmer", "size": [8, 7], "minimum": [6, 6],
               "required": ["sofa", "coffee_table", "tv"],
               "optional": ["bookshelf", "armchair", "plant", "aquarium", "floor_lamp", "side_table", "sideboard", "display_cabinet", "chess_table"],
               "families": ["Medienabend", "Lesesalon", "Gesprächsecke"],
               "programs": {"Lesesalon": ["sofa", "coffee_table", "bookshelf"], "Gesprächsecke": ["sofa", "coffee_table", "armchair"]}},
    "bedroom": {"name": "Schlafzimmer", "size": [7, 7], "minimum": [6, 6],
                "required": ["double_bed", "wardrobe", "side_table"],
                "optional": ["desk", "plant", "bookshelf", "floor_lamp", "dresser", "vanity", "laundry_basket"], "families": ["Ruhiger Rückzug", "Schlafen & Lesen"]},
    "kitchen": {"name": "Küche", "size": [6, 6], "minimum": [5, 5],
                "required": ["fridge", "sink", "stove", "counter"],
                "optional": ["dining_table", "plant", "cabinet", "kitchen_island", "dishwasher", "microwave_cart", "coffee_station", "pantry_shelf"], "families": ["Kochzeile", "Küche über Eck"]},
    "bathroom": {"name": "Badezimmer", "size": [5, 5], "minimum": [4, 5],
                 "required": ["shower", "toilet", "basin"],
                 "optional": ["cabinet", "washing_machine", "plant", "bathtub", "towel_rack", "laundry_basket"], "families": ["Duschbad", "Bad & Wäsche", "Badewannenbad"],
                 "programs": {"Bad & Wäsche": ["shower", "toilet", "basin", "washing_machine"], "Badewannenbad": ["bathtub", "toilet", "basin"]}},
    "hall": {"name": "Flur", "size": [5, 7], "minimum": [5, 5],
             "required": ["coat_rack", "shoe_rack"], "optional": ["bench", "plant", "side_table", "dresser", "display_cabinet"], "families": ["Ankommen", "Garderobenflur"]},
    "child": {"name": "Kinderzimmer", "size": [7, 7], "minimum": [6, 6],
              "required": ["single_bed", "toy_storage", "child_table"],
              "optional": ["wardrobe", "bookshelf", "side_table", "easel", "dresser"], "families": ["Bauen & Spielen", "Basteln & Lesen"]},
    "teen": {"name": "Jugendzimmer", "size": [7, 7], "minimum": [6, 6],
             "required": ["single_bed", "desk", "wardrobe"],
             "optional": ["bookshelf", "stereo", "plant", "armchair", "guitar_stand", "gaming_desk", "easel", "dresser"], "families": ["Lernen & Musik", "Kreativzimmer", "Gaming & Lernen"],
             "programs": {"Gaming & Lernen": ["single_bed", "gaming_desk", "wardrobe"]}},
    "party": {"name": "Partyraum", "size": [9, 8], "minimum": [7, 7],
              "required": ["bar", "stereo", "sofa"],
              "optional": ["armchair", "side_table", "plant", "arcade", "foosball_table", "buffet", "display_cabinet"], "families": ["Tanzen & Musik", "Lounge-Abend"]},
    "dining": {"name": "Esszimmer", "size": [8, 7], "minimum": [6, 6],
               "required": ["large_dining_table", "sideboard"], "optional": ["buffet", "display_cabinet", "coffee_station", "plant", "floor_lamp"],
               "families": ["Familientafel", "Kleine Tischrunde"], "programs": {"Kleine Tischrunde": ["dining_table", "buffet", "display_cabinet"]}},
    "office": {"name": "Arbeitszimmer", "size": [7, 7], "minimum": [6, 6],
               "required": ["office_desk", "filing_cabinet", "printer_stand"], "optional": ["bookshelf", "armchair", "side_table", "plant", "floor_lamp", "storage_rack"],
               "families": ["Homeoffice", "Schreiben & Planen"], "programs": {"Schreiben & Planen": ["office_desk", "filing_cabinet", "bookshelf"]}},
    "guest": {"name": "Gästezimmer", "size": [7, 7], "minimum": [6, 6],
              "required": ["single_bed", "dresser", "luggage_rack"], "optional": ["side_table", "wardrobe", "desk", "plant", "floor_lamp", "vanity"],
              "families": ["Willkommen auf Zeit", "Gäste & Lesen"]},
    "nursery": {"name": "Babyzimmer", "size": [7, 7], "minimum": [6, 6],
                "required": ["crib", "changing_table", "baby_storage"], "optional": ["rocking_chair", "side_table", "laundry_basket", "wardrobe", "floor_lamp"],
                "families": ["Schlafen & Wickeln", "Kuscheln & Vorlesen"], "programs": {"Kuscheln & Vorlesen": ["crib", "changing_table", "rocking_chair"]}},
    "laundry": {"name": "Waschküche", "size": [7, 6], "minimum": [6, 6],
                "required": ["washing_machine", "dryer", "utility_sink"], "optional": ["ironing_board", "drying_rack", "laundry_basket", "cabinet", "storage_rack", "towel_rack"],
                "families": ["Waschen & Trocknen", "Waschen & Lufttrocknen"], "programs": {"Waschen & Lufttrocknen": ["washing_machine", "drying_rack", "utility_sink"]}},
    "pantry": {"name": "Vorratsraum", "size": [6, 6], "minimum": [5, 5],
               "required": ["pantry_shelf", "freezer", "produce_crate"], "optional": ["storage_rack", "cabinet", "counter", "microwave_cart"],
               "families": ["Gut bevorratet", "Ernte & Vorräte"]},
    "library": {"name": "Bibliothek", "size": [8, 7], "minimum": [6, 6],
                "required": ["bookshelf", "reading_table", "armchair"], "optional": ["floor_lamp", "side_table", "plant", "display_cabinet", "chess_table", "desk"],
                "families": ["Lesen & Lernen", "Bücher & Schach"], "programs": {"Bücher & Schach": ["bookshelf", "chess_table", "armchair"]}},
    "music": {"name": "Musikzimmer", "size": [8, 8], "minimum": [7, 7],
              "required": ["piano", "synthesizer", "guitar_stand"], "optional": ["drum_kit", "stereo", "armchair", "bookshelf", "side_table", "plant"],
              "families": ["Klavier & Tasten", "Proberaum"], "programs": {"Proberaum": ["drum_kit", "piano", "guitar_stand"]}},
    "gym": {"name": "Fitnessraum", "size": [8, 8], "minimum": [7, 7],
            "required": ["treadmill", "exercise_bike", "dumbbell_rack"], "optional": ["weight_bench", "punching_bag", "bench", "towel_rack", "stereo", "cabinet"],
            "families": ["Ausdauer & Kraft", "Boxen & Kraft"], "programs": {"Boxen & Kraft": ["punching_bag", "weight_bench", "dumbbell_rack"]}},
    "workshop": {"name": "Werkstatt & Atelier", "size": [8, 7], "minimum": [7, 7],
                 "required": ["workbench", "tool_cabinet", "storage_rack"], "optional": ["sewing_table", "easel", "utility_sink", "desk", "floor_lamp", "cabinet"],
                 "families": ["Bauen & Reparieren", "Nähen & Gestalten"], "programs": {"Nähen & Gestalten": ["sewing_table", "easel", "storage_rack"]}},
    "conservatory": {"name": "Wintergarten", "size": [8, 7], "minimum": [6, 6],
                     "required": ["plant_shelf", "potting_bench", "bench"], "optional": ["planter_box", "plant", "armchair", "side_table", "chess_table", "aquarium"],
                     "families": ["Gärtnern & Ausruhen", "Grünes Lesezimmer"]},
    "gaming": {"name": "Spielzimmer", "size": [9, 8], "minimum": [8, 8],
               "required": ["pool_table", "gaming_desk", "arcade"], "optional": ["foosball_table", "pingpong_table", "stereo", "side_table", "display_cabinet", "plant", "chess_table"],
               "families": ["Billard & Arcade", "Gaming & Tischspiele"], "programs": {"Gaming & Tischspiele": ["pingpong_table", "gaming_desk", "foosball_table"]}},
}

# Curated source modules are explicitly assembled here. Runtime agent packs use
# an isolated Library snapshot and never mutate these dictionaries.
CATALOG.update({key: Furniture(**spec) for key, spec in {**BED_SPECS, **CIVIC_OBJECT_SPECS}.items()})
ROOMS.update(CIVIC_ROOMS)

# Square-metre budgets guide building dimensions. The catalog's minimum
# dimensions remain hard constraints for furniture and circulation.
ROOM_AREA_TARGETS = {
    "living": (36, 54, 70), "bedroom": (36, 46, 58),
    "kitchen": (25, 34, 42), "bathroom": (20, 24, 32),
    "hall": (25, 30, 40), "child": (36, 46, 56),
    "teen": (36, 46, 56), "guest": (36, 42, 52),
    "nursery": (36, 46, 56), "laundry": (36, 40, 48),
    "pantry": (25, 30, 36), "dining": (36, 48, 60),
    "office": (36, 44, 54), "library": (36, 48, 60),
    "music": (49, 62, 76), "gym": (49, 62, 76),
    "workshop": (49, 56, 70), "conservatory": (36, 48, 60),
    "gaming": (64, 74, 88), "party": (49, 66, 82),
    "home_care": (49, 58, 70), "school_classroom": (144, 168, 196),
}
for family, bed in (("Queensize & Lesen", "bed_queen"), ("Großzügiges Kingsize", "bed_king"), ("Niedriges Plattformbett", "bed_platform_double")):
    ROOMS["bedroom"]["families"].append(family)
    ROOMS["bedroom"].setdefault("programs", {})[family] = [bed, "wardrobe", "side_table"]
for kind, variants in {
    "child": [("Stauraum & Spielzeug", "bed_storage_single"), ("Schlafen im Hochbett", "bed_loft"), ("Geschwister-Etagenbett", "bed_bunk")],
    "teen": [("Stauraum & Lernen", "bed_storage_single"), ("Hochbett & Schreibtisch", "bed_loft")],
    "guest": [("Flexibles Gästezimmer", "bed_foldaway_guest")],
}.items():
    for family, bed in variants:
        ROOMS[kind]["families"].append(family)
        ROOMS[kind].setdefault("programs", {})[family] = [bed, *ROOMS[kind]["required"][1:]]
ROOMS["home_care"] = {"name": "Häusliches Pflegezimmer", "size": [8, 8], "minimum": [7, 7],
                      "required": ["bed_hospital", "side_table", "dresser"], "optional": ["armchair", "plant", "floor_lamp", "bookshelf"],
                      "families": ["Ruhe & Besuch"]}

STYLES = {
    "sage": {"name": "Salbei & Eiche", "floor": "#d6be95", "wall": "#ede1c7", "fabric": "#8aa486", "accent": "#b48267", "rug": "#b9c1a1"},
    "terracotta": {"name": "Terrakotta & Leinen", "floor": "#d2ab83", "wall": "#f0dfc7", "fabric": "#bb826b", "accent": "#8a9d88", "rug": "#d8ba92"},
    "coastal": {"name": "Blau & Birke", "floor": "#ddcba6", "wall": "#e6e7d6", "fabric": "#7d9fa7", "accent": "#c5a36c", "rug": "#b8cbd0"},
    "plum": {"name": "Pflaume & Nussbaum", "floor": "#bd9e83", "wall": "#e8dcca", "fabric": "#9b829f", "accent": "#acb780", "rug": "#c9a7a0"},
}


def rotate_cell(x, y, w, h, quarter):
    if quarter == 1:
        return h - 1 - y, x
    if quarter == 2:
        return w - 1 - x, h - 1 - y
    if quarter == 3:
        return y, w - 1 - x
    return x, y


def placed(kind, x, y, orientation=0, *, object_catalog=None):
    definition = (CATALOG if object_catalog is None else object_catalog)[kind]
    w, h = definition.w, definition.h
    rw, rh = (h, w) if orientation % 2 else (w, h)
    # All front cells remain free, not just the cell a pathfinder happens to use.
    front = [(xx, h) for xx in range(w)] if definition.front else []
    if kind in ("double_bed", "single_bed") or kind in BED_SPECS:
        front += [(w, yy) for yy in range(1, h)]
    if kind == "dining_table":
        front += [(xx, -1) for xx in range(w)]
    for side in definition.extra_access:
        front += {"back": [(xx, -1) for xx in range(w)],
                  "left": [(-1, yy) for yy in range(h)],
                  "right": [(w, yy) for yy in range(h)]}[side]
    clearance = [[x + a, y + b] for a, b in (rotate_cell(xx, yy, w, h, orientation) for xx, yy in front)]
    return {"kind": kind, "name": definition.name, "sprite": definition.sprite or kind,
            "x": x, "y": y, "w": rw, "h": rh, "base_w": w, "base_h": h,
            "orientation": orientation, "blocking": True, "clearance": clearance,
            "anchors": clearance[:], "tall": definition.tall}


def catalog_data():
    from .affordances import contracts
    return {"generator_version": GENERATOR_VERSION, "objects": {k: asdict(v) for k, v in CATALOG.items()}, "rooms": ROOMS, "styles": STYLES,
            "room_area_targets_m2": {kind: {"minimum": values[0], "target": values[1], "maximum": values[2]}
                                     for kind, values in ROOM_AREA_TARGETS.items()},
            "units": "meters", "grid_size_m": 1, "minimum_walkway_m": 1,
            "bed_capacities": {"single_bed": 1, "double_bed": 2, "crib": 1, "hospital_bed": 1, **BED_CAPACITIES},
            "affordances": contracts(CATALOG), "building_templates": BUILDING_TEMPLATES,
            "public_building_backlog": PUBLIC_BUILDING_BACKLOG}
