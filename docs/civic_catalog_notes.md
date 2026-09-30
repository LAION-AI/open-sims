# Civic room and building templates

`living_world.generation.civic_catalog` is an additive, data-only library. It
does not import or mutate the shared furniture and room catalogs. The host can
construct each furniture definition with `Furniture(**spec)` and merge the
room specs when enabling civic generation.

The initial playable room set covers classrooms, general science rooms,
biology and physics rooms, staff rooms and cafeterias; hospital examination
rooms, care wards and reception; and fire-station equipment rooms and garages.
Room and object display names and room families are localized for the German
UI. Every object has geometry, rendering, descriptive role metadata and
executor-safe actions. Required furniture lists may repeat kinds to express
capacity: the classroom requests four student desks and the cafeteria two
tables. The generator validates those counts.

Object interactions are abstract simulation actions. Medical fixtures support
check-in, examination and rest affordances only; they do not model real
treatment, medication or dosage guidance.

`BUILDING_TEMPLATES` provides room programs, intended room adjacency, access
classes and privacy classes. Each template is marked `prototype`; adjacency,
access and privacy are design intent and are not enforced by the current
multi-room generator. `PUBLIC_BUILDING_BACKLOG` tracks the broader
public-building taxonomy. School, hospital and fire station entries are
implemented in this initial data set; university, town hall, library, police,
courts, museum, transit, postal, eldercare, daycare, sports and other civic
programs are marked planned.

The civic `hospital_bed` is a dedicated clinical fixture, distinct in role and
sprite from the household catalog's `bed_hospital` rest/bed variant. The fire
engine bay requires floor clearance at its front and both sides. The room
template leaves a passable route around the vehicle footprint; it does not
model a real vehicle exit or garage door.

`web/civic-drawing.js` exports `drawCivicObject(c, o, palette)`. It uses
`o.base_w` and `o.base_h` in the same 24-pixel-per-meter sprite frame used by
the household renderer and has no imports, so its source can be embedded in
the offline report.
