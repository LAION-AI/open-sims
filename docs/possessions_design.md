# Concrete possessions and cooking slice

`living_world/possessions.py` provides deterministic, pure helpers. It does not
advance the clock, pathfind, reserve stations, or commit state. The engine must
read the current canonical actor/object at completion, call `apply_step`, then
commit all returned actor fields and `object_daily` in one transaction. Failed
preconditions raise `PossessionUnavailable`, leaving input records unchanged.

## Actor record

`initialize(actor, now)` supplies `belongings`, `possession_serial`, and
`outfit_last_day` for old saves. Every possession has an immutable
`<actor-id>_item_<serial>` ID, owner, kind, label, location, and state. Locations
are `carried` by actor, `container` at an existing object/building ID, `worn`
in a clothing slot, or `consumed`. The serial only increases. The actor keeps
the most recent 64 consumed records, while the engine's durable transaction
ledger should retain earlier creation/consumption events for history. Never
infer a new ID from the bounded list length.

Clothing begins as two tops, trousers, and shoes, plus two outerwear items.
One of each basic slot is worn; the remainder is stored in the actor's home.
`plan_outfit` uses an existing home bed as the changing anchor, once per day.
`worn_outfit` projects the actual worn instances to `appearance.outfit` for
rendering. There is no new wardrobe geometry or clothing teleportation during
the action: the actor must reach its bed before the commit.

## Recipe transition

`plan(actor, objects, now, recipe=None)` chooses pizza on even days and pancake
on odd days, unless a concrete unfinished meal already exists. It returns
`[{kind, target_id}, ...]` and resumes from held ingredients, a raw item,
food in the oven, cooked food being carried, or a served meal. If the fridge
cannot supply the missing ingredients, it prefixes `buy_groceries` at a real
`supermarket_checkout` (falling back to existing `shop_counter`) and
`stock_fridge`; these two are existing generic actions. The engine must extend
the grocery action's allowed object kinds to include `supermarket_checkout`.

Pizza uses dough, tomato and vegetable. The recipe consumes those exact
instances at the counter, creates one raw pizza, loads that same pizza item
into the counter's oven slot, bakes it for 900 simulation seconds, unloads it,
carries it to a table, and eats it there. `oven_item_id` and `ready_at` make
the oven occupation and timing durable. `step_available` can preflight
`bake_pizza` at the prospective completion time; `apply_step` checks actual
completion time. Interrupted baking does not fabricate a second pizza.
Pancakes use egg and dough and the shorter counter cooking action. The same
meal item ID persists while carried, cooked and served, then becomes consumed.

Legacy table `served_meals` and `dirty_dishes` counts are updated in the same
patch as the concrete meal transition. `eat_recipe` accepts only the actor's
own served item; it cannot eat a generic old meal or spend a served count
without a matching item. Eating creates a concrete dirty plate. The existing
`clear_dishes` and `wash_dishes` effects still change generic counts and
inventory; call `synchronize_cleanup` after each to move/consume the plate
instance without applying those counters twice. This adapter can inspect
only the passed actor's possessions. If a different resident clears the
owner's plate, the engine needs a global owner-aware reconciliation or
table-owned item index; do not silently claim that cross-owner cleanup is
currently complete.

The kitchen counter is the pre-existing counter footprint, serving as an oven
without changed collision geometry. The eight southern service interiors
(gym, club, town hall, hospital, fire station, offices, supermarket and
shopping centre) are reachable workstations/venues, not full institutional
simulations. Similarly the school is a staff-workstation demonstration, not
a live classroom of pupils. The separate laboratory's 20–24 seats do not
change that scope.

## Renderer

`web/renderer.js` uses worn top/trousers/shoes/outerwear colors on map people,
and exports `drawPortrait(ctx, appearance, x, y, {scale, emotion})` for the
inspector. Its code-drawn overlays show an occupied oven, meal dishes,
counter mess and carried pizza/pancake/ingredients, while new service stations
and public building signs remain non-blocking visual layers. The renderer
never updates canonical resources or items.
