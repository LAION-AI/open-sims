# Daily life and assigned workplaces

The daily-life module supplies deterministic plans and pure completion effects.
The world engine remains the only writer of canonical actor and object records.
It reserves one target per step, routes the resident to one of that object's
anchors, commits effects at completion, and records the change in its event
ledger. A plan is intent, not a resource reservation over all future steps.

## Household routine

`plan_meal(actor, objects)` returns an ordered list of `{"kind", "target_id"}`
steps. At home, a meal goes from fridge to counter, from counter to dining table,
and finally to the resident's plate. The complete sequence is:

1. `fetch_ingredients`: pantry stock -1, actor ingredients +1.
2. `prepare_meal`: actor ingredients -1, prepared meal +1, food scraps +1,
   counter mess +1.
3. `serve_meal`: actor prepared meal -1, table served meal +1. This is the
   carrying step: the actor travels from counter to table.
4. `eat_meal`: table served meal -1, table dirty dish +1. Hunger relief belongs
   to this action, after a valid served meal exists.
5. `clear_dishes`: table dirty dish -1, actor dirty dish +1.
6. `wash_dishes`: actor dirty dishes removed, sink washed total increases.
7. `bin_trash`: actor food scraps removed, bin trash increases.
8. `empty_trash`: bin trash becomes zero, disposed total increases.
9. `wipe_counter`: counter mess becomes zero, cleaned total increases.

If pantry stock is zero, `plan_meal` prefixes a visit to the existing market
counter (`buy_groceries`, cost 20) and a return to the home fridge
(`stock_fridge`). The market supplies eight portions. Old save records need no
field migration for pantry, dishes or mess: `daily_state(obj)` supplies the
defaults until the first completion writes `obj["daily"]` canonically.
If a routine is abandoned after buying, fetching, preparing or serving,
`plan_meal` resumes from the groceries, ingredients, prepared meal or served
plate already recorded. It never fetches another portion while one of those
food stages can satisfy the meal. A resident can carry more scraps than one
bin holds; `bin_trash` transfers up to the remaining bin capacity and the
next cleaning plan takes another load.

`plan_cleaning` inspects the actual table, actor inventory, bin and counter and
only proposes chores with evidence of dirt. `plan_hobby` chooses craft at a
home desk, reading at a bookshelf or gardening at a planter based on the
resident's preferences. Craft creates a project in inventory and improves the
craft skill. Reading and gardening use the existing engine actions.

Every new action has a `DAILY_ACTIONS` definition compatible with the action
registry: label, object kinds, duration, need relief, cost, preference and
thought. An action can only use an object of the declared kind and, for home
fixtures, from the resident's own household. A table has at most three served
meals and a bin holds eight units of waste. `step_available` is a read-only
precondition check; `apply_step` raises `StepUnavailable` if another resident
changed the resource before completion.

`apply_step(actor, obj, kind)` returns full replacement values for
`actor["inventory"]`, `actor["skills"]`, and `obj["daily"]`. It never mutates
its inputs. The engine should apply all returned values to records obtained
with `edit` inside one completion transaction. Money and need relief remain
engine-owned. On interruption, the active reservation is released but any
already completed token transfer remains canonical. An interrupted prepare
step does not create a meal; a completed prepare step leaves a real prepared
meal in inventory for the next attempt. A resumed routine should recheck the
next step against current state and should never replay a completed step.

## Work and geography

The original 128 by 118 neighborhood and object IDs 0001–0320 remain in
place. A civic strip extends the map south to 154 rows. A road at y=123–125,
side paths and a path at y=149 link three new, walkable buildings to the
existing neighborhood:

| Building | Bounds | Assigned jobs |
| --- | --- | --- |
| Mosswood School (`school`) | x=7–38, y=128–145 | Teacher |
| Mosswood Creative Studio (`studio`) | x=47–73, y=128–145 | Illustrator, Designer |
| Mosswood Works (`workshop`) | x=84–117, y=128–145 | Carpenter, Tailor, Gardener |
| The Daily Crumb (`cafe`) | Existing | Baker |
| Moss & Market (`shop`) | Existing | Bookseller |
| Own home (`home_XX`) | Existing | Independent artist |

Each new department has a physical workstation with separate walkable anchors
and a capacity matching the number of anchors. `assigned_workplace` maps each
job to one station and building; `coworkers_at_work` groups by assigned building.
The studio and works building have multiple departments, so coworkers can have
different jobs while sharing a real workplace. Work from home is explicit for
independent artists. All new objects append after the old IDs: 0321–0323 are
building doors, 0324–0329 are workstations, and 0330–0349 are household bins.

These civic interiors are workstation demos in the live world. The school has
teacher assignments and commutes, but no simulated pupils, classes, lessons or
school day. The separate building workshop can model a classroom with 20–24
student seats; that design is not yet connected to the live world simulation.

The south extension does not change old cell types or existing object geometry.
An existing in-flight route and its reservation continue to refer to the same
old cells and object IDs. On loading a previous checkpoint, the engine must
introduce the appended objects through an explicit canonical transaction so
the checkpoint, event replay and live spatial object registry agree. It should
not replace old object records with newly generated defaults.

## Renderer contract

The world canvas draws the new school, studio and works signs, their individual
workstations, and home bins with the existing code-drawn pixel palette. The
static map has no pre-placed meals on dining tables. Instead, each frame reads
`snapshot.resources[].daily` and overlays served plates, dirty dishes,
counter mess and trash only when canonical state contains them. The server
should include changed, unreserved objects in `resources`; a reservations-only
list would hide household evidence after the actor leaves.

Residents carry a small pixel prop derived from `snapshot.actors[].carried`:
groceries, ingredients, a prepared meal, a dirty dish or food scraps. The
renderer accepts an object of positive item counts keyed by those token names
or an array of token names. It draws the prop on the moving resident, so the
fridge-to-counter-to-table transfer remains visible during travel. A dog is
drawn from each `snapshot.animals[]` record with a `[x, y]` tile `position`;
the first dog is Pippin. These drawings do not change paths or collision.
The minimap marks animals separately from residents. Public building clicks
only open/focus the building; the household callback is used only for homes.
