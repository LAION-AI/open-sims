"""Additive templates for civic and public-service buildings.

Importing this module is data-only: the host may merge these furniture kwargs
and room templates into its generator when desired. Gameplay actions are
abstract simulation affordances; medical entries do not describe real care.
"""

# Values are accepted by catalog.Furniture(**spec). Geometry is in meters.
CIVIC_OBJECT_SPECS = {
    "school_teacher_desk": {"name": "Lehrerpult", "w": 2, "h": 1, "wall": False, "tall": False, "front": True, "sprite": "school_teacher_desk", "extra_access": ()},
    "school_student_desk": {"name": "Schülertisch", "w": 1, "h": 1, "wall": False, "tall": False, "front": True, "sprite": "school_student_desk", "extra_access": ()},
    "school_student_chair": {"name": "Schülerstuhl", "w": 1, "h": 1, "wall": False, "tall": False, "front": True, "sprite": "school_student_chair", "extra_access": ()},
    "school_chalkboard": {"name": "Kreidetafel", "w": 3, "h": 1, "wall": True, "tall": False, "front": False, "sprite": "school_chalkboard", "extra_access": ()},
    "school_lab_bench": {"name": "Labortisch", "w": 2, "h": 1, "wall": True, "tall": False, "front": True, "sprite": "school_lab_bench", "extra_access": ()},
    "school_supply_cabinet": {"name": "Materialschrank", "w": 2, "h": 1, "wall": True, "tall": True, "front": True, "sprite": "school_supply_cabinet", "extra_access": ()},
    "civic_safety_station": {"name": "Sicherheitsstation", "w": 1, "h": 1, "wall": True, "tall": False, "front": True, "sprite": "civic_safety_station", "extra_access": ()},
    "civic_staff_desk": {"name": "Personal-Schreibtisch", "w": 2, "h": 1, "wall": True, "tall": False, "front": True, "sprite": "civic_staff_desk", "extra_access": ()},
    "civic_locker_bank": {"name": "Spindreihe", "w": 3, "h": 1, "wall": True, "tall": True, "front": True, "sprite": "civic_locker_bank", "extra_access": ()},
    "civic_cafeteria_counter": {"name": "Ausgabetheke", "w": 3, "h": 1, "wall": True, "tall": False, "front": True, "sprite": "civic_cafeteria_counter", "extra_access": ()},
    "civic_cafeteria_table": {"name": "Kantinentisch", "w": 2, "h": 2, "wall": False, "tall": False, "front": True, "sprite": "civic_cafeteria_table", "extra_access": ("back",)},
    "clinic_exam_table": {"name": "Untersuchungsliege", "w": 1, "h": 2, "wall": True, "tall": False, "front": True, "sprite": "clinic_exam_table", "extra_access": ()},
    "clinic_screen": {"name": "Paravent", "w": 1, "h": 2, "wall": False, "tall": False, "front": True, "sprite": "clinic_screen", "extra_access": ()},
    "clinic_cart": {"name": "Materialwagen", "w": 1, "h": 1, "wall": False, "tall": False, "front": True, "sprite": "clinic_cart", "extra_access": ()},
    "hospital_bed": {"name": "Verstellbares Pflegebett", "w": 2, "h": 3, "wall": True, "tall": False, "front": True, "sprite": "hospital_bed", "extra_access": ("right",)},
    "hospital_bedside_stand": {"name": "Nachttisch", "w": 1, "h": 1, "wall": False, "tall": False, "front": True, "sprite": "hospital_bedside_stand", "extra_access": ()},
    "civic_reception_desk": {"name": "Empfangstresen", "w": 3, "h": 1, "wall": True, "tall": False, "front": True, "sprite": "civic_reception_desk", "extra_access": ()},
    "civic_waiting_bench": {"name": "Wartebank", "w": 2, "h": 1, "wall": False, "tall": False, "front": True, "sprite": "civic_waiting_bench", "extra_access": ()},
    "fire_gear_rack": {"name": "Schutzkleidungsständer", "w": 2, "h": 1, "wall": True, "tall": True, "front": True, "sprite": "fire_gear_rack", "extra_access": ()},
    "fire_dispatch_console": {"name": "Einsatzleitpult", "w": 2, "h": 1, "wall": True, "tall": False, "front": True, "sprite": "fire_dispatch_console", "extra_access": ()},
    "fire_engine_bay": {"name": "Fahrzeugstellplatz", "w": 3, "h": 4, "wall": False, "tall": False, "front": True, "sprite": "fire_engine_bay", "extra_access": ("left", "right")},
    "civic_archive_shelf": {"name": "Archivregal", "w": 2, "h": 1, "wall": True, "tall": True, "front": True, "sprite": "civic_archive_shelf", "extra_access": ()},
    "civic_service_kiosk": {"name": "Service-Terminal", "w": 1, "h": 1, "wall": False, "tall": False, "front": True, "sprite": "civic_service_kiosk", "extra_access": ()},
    "school_microscope": {"name": "Schülermikroskop", "w": 1, "h": 1, "wall": False, "tall": False, "front": True, "sprite": "school_microscope", "extra_access": ()},
    "school_model_skeleton": {"name": "Skelettmodell", "w": 1, "h": 1, "wall": False, "tall": False, "front": True, "sprite": "school_model_skeleton", "extra_access": ()},
    "school_physics_demo": {"name": "Physik-Experimentiertisch", "w": 2, "h": 1, "wall": True, "tall": False, "front": True, "sprite": "school_physics_demo", "extra_access": ()},
}

# Kept separate from Furniture's stable geometry constructor.
CIVIC_OBJECT_ROLES = {
    "school_teacher_desk": {"tags": ("school", "teaching"), "interactions": ("teach_lesson", "prepare_class")},
    "school_student_desk": {"tags": ("school", "learning"), "interactions": ("attend_class", "study", "do_homework")},
    "school_student_chair": {"tags": ("school", "seating"), "interactions": ("attend_class", "sit")},
    "school_chalkboard": {"tags": ("school", "teaching"), "interactions": ("write_lesson", "present_work")},
    "school_lab_bench": {"tags": ("school", "laboratory"), "interactions": ("practice_experiment", "study")},
    "school_supply_cabinet": {"tags": ("school", "storage"), "interactions": ("organize_supplies",)},
    "civic_safety_station": {"tags": ("safety", "public"), "interactions": ("review_safety_notice",)},
    "civic_staff_desk": {"tags": ("staff", "administration"), "interactions": ("work_shift", "review_schedule")},
    "civic_locker_bank": {"tags": ("staff", "storage"), "interactions": ("store_uniform", "change_for_shift")},
    "civic_cafeteria_counter": {"tags": ("food_service", "public"), "interactions": ("collect_meal", "serve_meal")},
    "civic_cafeteria_table": {"tags": ("food_service", "social"), "interactions": ("eat_meal", "chat")},
    "clinic_exam_table": {"tags": ("clinic", "simulation"), "interactions": ("check_in_for_exam", "rest_briefly")},
    "clinic_screen": {"tags": ("clinic", "privacy"), "interactions": ("request_privacy",)},
    "clinic_cart": {"tags": ("clinic", "supplies"), "interactions": ("organize_supplies",)},
    "hospital_bed": {"tags": ("hospital", "care", "simulation"), "interactions": ("rest", "request_staff_visit", "adjust_bed")},
    "hospital_bedside_stand": {"tags": ("hospital", "care"), "interactions": ("place_personal_item", "retrieve_personal_item")},
    "civic_reception_desk": {"tags": ("public", "administration"), "interactions": ("ask_for_directions", "check_in", "request_service")},
    "civic_waiting_bench": {"tags": ("public", "waiting"), "interactions": ("wait", "chat")},
    "fire_gear_rack": {"tags": ("fire_service", "equipment"), "interactions": ("check_gear", "prepare_for_shift")},
    "fire_dispatch_console": {"tags": ("fire_service", "dispatch"), "interactions": ("review_dispatch_board", "radio_check")},
    "fire_engine_bay": {"tags": ("fire_service", "vehicle"), "interactions": ("inspect_vehicle", "return_vehicle")},
    "civic_archive_shelf": {"tags": ("records", "staff"), "interactions": ("file_record", "retrieve_record")},
    "civic_service_kiosk": {"tags": ("public", "self_service"), "interactions": ("browse_services", "submit_request")},
    "school_microscope": {"tags": ("school", "biology", "laboratory"), "interactions": ("observe_sample", "study")},
    "school_model_skeleton": {"tags": ("school", "biology", "teaching"), "interactions": ("teach", "study")},
    "school_physics_demo": {"tags": ("school", "physics", "laboratory"), "interactions": ("simulate_experiment", "teach")},
}

# Executor-safe action registry. Labels in CIVIC_OBJECT_ROLES may also carry
# richer descriptive verbs; only these action IDs are sent to the simulator.
CIVIC_AFFORDANCES = {
    "school_teacher_desk": {"actions": ["teach", "work", "store"]},
    "school_student_desk": {"actions": ["study", "read", "sit"]},
    "school_student_chair": {"actions": ["sit", "study"]},
    "school_chalkboard": {"actions": ["teach", "study"]},
    "school_lab_bench": {"actions": ["observe_sample", "simulate_experiment", "study"]},
    "school_supply_cabinet": {"actions": ["store", "retrieve"]},
    "civic_safety_station": {"actions": ["read", "observe_sample"]},
    "civic_staff_desk": {"actions": ["work", "store", "retrieve"]},
    "civic_locker_bank": {"actions": ["store", "retrieve", "equip"]},
    "civic_cafeteria_counter": {"actions": ["eat", "drink", "cook"]},
    "civic_cafeteria_table": {"actions": ["eat", "drink", "sit"]},
    "clinic_exam_table": {"actions": ["check_in", "examine", "rest"]},
    "clinic_screen": {"actions": ["check_in"]},
    "clinic_cart": {"actions": ["store", "retrieve"]},
    "hospital_bed": {"actions": ["sleep", "rest", "adjust_backrest", "monitor"]},
    "hospital_bedside_stand": {"actions": ["store", "retrieve"]},
    "civic_reception_desk": {"actions": ["check_in", "work"]},
    "civic_waiting_bench": {"actions": ["sit", "rest"]},
    "fire_gear_rack": {"actions": ["equip", "store", "retrieve"]},
    "fire_dispatch_console": {"actions": ["dispatch", "work"]},
    "fire_engine_bay": {"actions": ["repair", "equip", "dispatch"]},
    "civic_archive_shelf": {"actions": ["store", "retrieve", "read"]},
    "civic_service_kiosk": {"actions": ["check_in", "read", "work"]},
    "school_microscope": {"actions": ["observe_sample", "study"]},
    "school_model_skeleton": {"actions": ["teach", "study"]},
    "school_physics_demo": {"actions": ["simulate_experiment", "teach"]},
}

# Same shape as catalog.ROOMS. Required lists may repeat kinds for room capacity.
CIVIC_ROOMS = {
    "school_classroom": {"name": "Klassenzimmer", "size": [12, 14], "minimum": [12, 12], "required": ["school_teacher_desk", "school_chalkboard"] + ["school_student_desk"] * 20 + ["school_student_chair"] * 20, "optional": [], "families": ["Unterricht & Gespräch", "Selbstständiges Lernen"]},
    "school_lab": {"name": "Naturwissenschaftlicher Fachraum", "size": [10, 9], "minimum": [8, 8], "required": ["school_teacher_desk", "school_lab_bench", "school_supply_cabinet", "civic_safety_station"], "optional": ["school_student_desk", "civic_archive_shelf"], "families": ["Praktikum", "Vorführung"]},
    "school_biology": {"name": "Biologieraum", "size": [10, 9], "minimum": [8, 8], "required": ["school_teacher_desk", "school_lab_bench", "school_microscope", "school_model_skeleton"], "optional": ["school_supply_cabinet", "civic_safety_station", "school_student_desk"], "families": ["Mikroskopieren", "Anatomie-Modell"]},
    "school_physics": {"name": "Physikraum", "size": [10, 9], "minimum": [8, 8], "required": ["school_teacher_desk", "school_physics_demo", "school_supply_cabinet", "civic_safety_station"], "optional": ["school_student_desk", "school_lab_bench"], "families": ["Versuchsaufbau", "Physikvorführung"]},
    "school_staff": {"name": "Lehrerzimmer", "size": [8, 8], "minimum": [7, 7], "required": ["civic_staff_desk", "civic_locker_bank"], "optional": ["civic_waiting_bench", "civic_archive_shelf", "civic_service_kiosk"], "families": ["Planung", "Pause"]},
    "school_cafeteria": {"name": "Schulkantine", "size": [11, 10], "minimum": [9, 8], "required": ["civic_cafeteria_counter", "civic_cafeteria_table", "civic_cafeteria_table"], "optional": ["civic_waiting_bench", "civic_service_kiosk", "civic_safety_station"], "families": ["Essensausgabe", "Gemeinsames Essen"]},
    "hospital_exam": {"name": "Untersuchungszimmer", "size": [8, 8], "minimum": [7, 7], "required": ["clinic_exam_table", "clinic_screen", "clinic_cart"], "optional": ["civic_staff_desk", "civic_safety_station", "civic_archive_shelf"], "families": ["Vertrauliche Untersuchung", "Gespräch mit Personal"]},
    "hospital_ward": {"name": "Pflegestation", "size": [11, 10], "minimum": [9, 9], "required": ["hospital_bed", "hospital_bedside_stand", "civic_staff_desk"], "optional": ["clinic_screen", "civic_safety_station", "civic_waiting_bench"], "families": ["Ruhige Erholung", "Rundgang des Personals"]},
    "hospital_reception": {"name": "Krankenhaus-Empfang", "size": [9, 8], "minimum": [7, 7], "required": ["civic_reception_desk", "civic_waiting_bench", "civic_service_kiosk"], "optional": ["civic_archive_shelf", "civic_safety_station"], "families": ["Besucherempfang", "Service-Schalter"]},
    "fire_equipment": {"name": "Geräteraum der Feuerwehr", "size": [9, 8], "minimum": [7, 7], "required": ["fire_gear_rack", "fire_dispatch_console", "civic_staff_desk"], "optional": ["civic_archive_shelf", "civic_safety_station"], "families": ["Schichtbeginn", "Einsatzplanung"]},
    "fire_garage": {"name": "Feuerwehrgarage", "size": [12, 11], "minimum": [10, 9], "required": ["fire_engine_bay", "fire_gear_rack", "fire_dispatch_console"], "optional": ["civic_safety_station", "civic_staff_desk"], "families": ["Fahrzeugkontrolle", "Bereitschaft"]},
}

# Adjacency, access, and privacy below record design intent only. The current
# multi-room layout generator does not yet enforce these relationships.
BUILDING_TEMPLATES = {
    "school": {"name": "Schule", "status": "prototype", "rooms": ["school_classroom", "school_lab", "school_biology", "school_physics", "school_staff", "school_cafeteria"], "room_program": ["school_classroom", "school_lab", "school_biology", "school_physics", "school_staff", "school_cafeteria"], "profile": "education", "adjacency": [["school_classroom", "school_staff"], ["school_classroom", "school_lab"], ["school_classroom", "school_biology"], ["school_classroom", "school_physics"], ["school_classroom", "school_cafeteria"]], "access": {"school_classroom": "student_supervised", "school_lab": "student_supervised", "school_biology": "student_supervised", "school_physics": "student_supervised", "school_staff": "staff_only", "school_cafeteria": "public_student"}, "privacy": {"school_classroom": "shared_learning", "school_lab": "supervised_work", "school_biology": "supervised_work", "school_physics": "supervised_work", "school_staff": "staff_private", "school_cafeteria": "shared_dining"}, "constraints_enforced": False, "constraint_note": "Adjacency, access and privacy are design intent only; the generator does not enforce them yet."},
    "hospital": {"name": "Krankenhaus", "status": "prototype", "rooms": ["hospital_reception", "hospital_exam", "hospital_ward"], "room_program": ["hospital_reception", "hospital_exam", "hospital_ward"], "profile": "health_service", "adjacency": [["hospital_reception", "hospital_exam"], ["hospital_exam", "hospital_ward"]], "access": {"hospital_reception": "public", "hospital_exam": "staff_patient", "hospital_ward": "staff_patient_restricted"}, "privacy": {"hospital_reception": "public_shared", "hospital_exam": "private_visit", "hospital_ward": "quiet_private"}, "constraints_enforced": False, "constraint_note": "Adjacency, access and privacy are design intent only; the generator does not enforce them yet."},
    "fire_station": {"name": "Feuerwache", "status": "prototype", "rooms": ["fire_equipment", "fire_garage"], "room_program": ["fire_equipment", "fire_garage"], "profile": "emergency_service", "adjacency": [["fire_equipment", "fire_garage"]], "access": {"fire_equipment": "staff_only", "fire_garage": "staff_vehicle"}, "privacy": {"fire_equipment": "staff_private", "fire_garage": "operational"}, "constraints_enforced": False, "constraint_note": "Adjacency, access and privacy are design intent only; the generator does not enforce them yet."},
}

# Roadmap is intentionally broader than the initial implemented room subset.
PUBLIC_BUILDING_BACKLOG = [
    {"building": "school", "status": "implemented", "rooms": ["classroom", "science laboratory", "staff room", "cafeteria"], "objects": ["teacher desk", "student desk", "chalkboard", "lab bench", "safety station"]},
    {"building": "hospital", "status": "implemented", "rooms": ["examination room", "care ward", "reception"], "objects": ["exam table", "privacy screen", "care bed", "reception desk"]},
    {"building": "fire station", "status": "implemented", "rooms": ["equipment room", "garage"], "objects": ["gear rack", "dispatch console", "engine bay"]},
    {"building": "university", "status": "planned", "rooms": ["lecture hall", "seminar room", "research lab", "faculty office", "student commons"], "objects": ["tiered seats", "projector", "lab island", "research board"]},
    {"building": "town hall", "status": "planned", "rooms": ["council chamber", "public counter", "records office", "ceremony hall"], "objects": ["council table", "service counter", "civic seal", "archive cabinet"]},
    {"building": "library", "status": "planned", "rooms": ["reading room", "stacks", "computer nook", "children's corner"], "objects": ["book stacks", "catalog terminal", "reading carrel", "story rug"]},
    {"building": "police station", "status": "planned", "rooms": ["front desk", "briefing room", "evidence store", "staff office"], "objects": ["dispatch board", "evidence locker", "briefing table", "visitor bench"]},
    {"building": "courthouse", "status": "planned", "rooms": ["courtroom", "clerk counter", "jury room", "hearing room"], "objects": ["bench dais", "counsel tables", "jury seats", "case files"]},
    {"building": "museum", "status": "planned", "rooms": ["gallery", "archive", "education room", "conservation lab"], "objects": ["display plinth", "glass case", "interpretive panel", "work table"]},
    {"building": "transit station", "status": "planned", "rooms": ["concourse", "ticket hall", "staff room", "waiting area"], "objects": ["ticket kiosk", "route board", "platform bench", "luggage rack"]},
    {"building": "post office", "status": "planned", "rooms": ["service counter", "sorting floor", "parcel room", "mailbox lobby"], "objects": ["sorting pigeonholes", "parcel scale", "mail bins", "counter window"]},
    {"building": "eldercare", "status": "planned", "rooms": ["resident lounge", "quiet room", "activity room", "care office"], "objects": ["supportive chair", "activity table", "care desk", "personal storage"]},
    {"building": "daycare", "status": "planned", "rooms": ["playroom", "nap room", "snack room", "staff office"], "objects": ["low play shelf", "nap cot", "child table", "check-in desk"]},
    {"building": "sports center", "status": "planned", "rooms": ["court", "changing room", "fitness studio", "reception"], "objects": ["court markings", "locker bank", "equipment rack", "check-in desk"]},
    {"building": "community center", "status": "planned", "rooms": ["meeting hall", "club room", "kitchenette", "advice desk"], "objects": ["folding chairs", "notice board", "serving counter", "welcome desk"]},
    {"building": "shelter", "status": "planned", "rooms": ["intake", "shared sleeping room", "quiet room", "supply store"], "objects": ["intake desk", "single cot", "privacy divider", "supply shelving"]},
    {"building": "municipal clinic", "status": "planned", "rooms": ["waiting room", "consultation room", "records office", "staff room"], "objects": ["check-in kiosk", "consultation desk", "record shelf", "staff lockers"]},
    {"building": "utility depot", "status": "planned", "rooms": ["dispatch", "vehicle bay", "tool store", "crew room"], "objects": ["dispatch console", "service bay", "tool rack", "crew table"]},
    {"building": "recycling center", "status": "planned", "rooms": ["drop-off hall", "sorting floor", "staff office", "education room"], "objects": ["sorting bins", "weigh station", "safety board", "display panel"]},
    {"building": "public market", "status": "planned", "rooms": ["vendor hall", "food court", "service office", "loading room"], "objects": ["stall counter", "shared table", "crate stack", "information kiosk"]},
    {"building": "public bath", "status": "planned", "rooms": ["changing room", "bath hall", "quiet lounge", "attendant desk"], "objects": ["locker bank", "bench", "towel station", "service desk"]},
    {"building": "place of worship", "status": "planned", "rooms": ["assembly hall", "study room", "community kitchen", "care office"], "objects": ["lectern", "reading table", "serving counter", "counsel desk"]},
]
