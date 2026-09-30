# Bed variants integration notes

This module is additive. The existing catalog still defines only `single_bed`
and `double_bed`; the renderer currently draws those through its inline bed
case. There is also no gameplay consumer for sleep capacity or interaction tags
yet. The new module deliberately does not alter shared catalog state when
imported.

Import `BED_SPECS` and construct each entry explicitly with `Furniture(**spec)`
when merging into the catalog. Keep `BED_CAPACITIES` and `BED_TRAITS` as
separate gameplay metadata; the geometry dataclass has no fields for these.
The `bed_foldaway_guest` uses a compact 2-by-1 footprint with its opened sleep
surface running along local +x, so its long axis lies sideways compared with
the other beds. This is intentional to represent a shallow foldaway/guest-bed
placement rather than a head-to-foot bed footprint.

In `catalog.placed()`, extend the existing `single_bed` / `double_bed` access
special case to include `*BED_SPECS`. Its canonical local access rule is:

```python
if kind in ("double_bed", "single_bed", *BED_SPECS):
    front += [(w, yy) for yy in range(1, h)]
```

The existing `front=True` rule retains the full foot edge. `rotate_cell()` then
rotates both edges with the footprint. A candidate at a corner may correctly
be rejected when its side access falls outside the room; another position on
the same wall remains available. Bed footprints are at most 3 by 3, and their
foot and side access fit a 6 by 6 minimum room when placed with one cell of
margin from the adjacent corner.

For browser rendering, import or embed `drawBedVariant` from
`web/bed-variants-drawing.js` and call it before the existing `furnitureSprite`
switch. When it returns `true`, skip the legacy switch; otherwise continue
normally. The function expects the renderer's current object-local transform
and `base_w` / `base_h` fields, at 24 pixels per meter. It has no imports and
draws the pixels directly.

`bed_placement_access()` offers a standalone placement record using the same
canonical foot-plus-right-side rule and rotation function. It is intended for
tests and previews; `placed()` remains the production source of placement
geometry after integration.
