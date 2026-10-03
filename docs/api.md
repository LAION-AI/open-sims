# Local API and future agent integration

Interactive OpenAPI: **http://127.0.0.1:8765/docs**. All times are integer world seconds; one meter is one tile. This API is intended for a trusted local prototype and has no network authentication. The launcher binds to `127.0.0.1`.

| Endpoint | Contract |
| --- | --- |
| `GET /api/world` | Static geometry, household membership, objects, regions, decoration |
| `GET /api/state` | Clock, actor positions/trajectories, activity counts, live reservations, metrics |
| `GET /api/insights` | Read-only, bounded live demographic, mood, relationship, profession, venue and recent-event projections for the Social overlay |
| `GET /api/actors/{id}` | Full observer inspector, evaluated needs, internal state, coverage |
| `GET /api/actors/{id}/journal?limit=40&before=N` | Resident-indexed accepted Beats, newest first |
| `GET /api/beats?limit=15&before=N` | Shared ledger, newest first; limit is capped at 200 |
| `GET /api/rules` | Pinned manifest plus declarative definitions |
| `GET /api/health` | Current invariant errors, fault state, optional model-control status; Simulation Fields remain disabled |
| `GET /api/decision-providers` | Supported optional OpenRouter decision models and server-side configuration flag; never a credential |
| `GET /api/settings/openrouter-key` | Local-only status: `configured` and source, never the key |
| `POST /api/settings/openrouter-key` | Local-only `{ "key": "..." }`; replace the in-memory session key, `Cache-Control: no-store` |
| `DELETE /api/settings/openrouter-key` | Forget the in-memory key; opt-in preferences are preserved and local procedural decisions cover gaps until a key is available again |
| `POST /api/actors/{id}/decision-provider` | Per-Sim opt-in/out with `enabled`, optional `model`, and `expected_version` |
| `POST /api/control` | Optional `paused`, `speed` (1–600), `step_seconds` (1–3600, while paused) |
| `POST /api/save` | Atomically checkpoint state, queued events and pending Beat writes |
| `GET /api/export` | Save and return the complete continuation checkpoint |
| `GET /api/replay?through=N` | Reconstruct canonical component projection through an accepted Beat |
| `WS /ws` | Four current-state packets per real second; it does not advance time |
| `POST /api/capture` | PNG of the complete browser UI; Playwright/Chromium required |

Geometry objects carry `w`, `h`, orientation, meter position, interaction anchors, capacity, ownership, condition, and reservations. The live snapshot's resource list includes **currently reserved objects and objects with materialized daily household state**. It is not a full live object registry; for exact non-reserved condition, use an exported checkpoint or the observer world endpoint. The actor inspector adds psychology, family layers, workplace, routine/planned steps, household states, 24 social-category definitions, `aptitudes` (W100 attributes/social skills/last check), and `education`. `/life-supplement`, `/social-storyteller` and `/campus-social-w100` document these contracts and their limits. Campus `planning_metadata.portals` adds bidirectional stair edges between cutaway floor slabs; ordinary world positions remain 2D meter coordinates.

`/api/insights` is an omniscient **observer** projection, not an agent packet: age bands, mean need satisfaction, current affect labels, profession counts, geometric building occupancy, live social actions, known relationship ties and ongoing ambitions come from resident state. Its event feed classifies the latest 100 accepted ledger Beats and returns at most 50 brief entries; these are recent events, not all-time incident totals. Calling it never advances the clock or writes a Beat. The UI refreshes the overlay only while it is open.

## Capture

```python
import json
from pathlib import Path
from urllib.request import Request, urlopen

request = Request(
    "http://127.0.0.1:8765/api/capture",
    data=json.dumps({
        "width": 1440, "height": 1000,
        "actor_id": "resident_001",
        "view": "home",   # overview | home | follow
        "tab": "mind",    # overview | mind | journal | details
        "grid": True,
    }).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
Path("house.png").write_bytes(urlopen(request).read())
```

The capture renderer is another read-only observer. It never pauses or steps the simulation. For a repeatable capture, pause via the control endpoint first. Captures are serialized to avoid launching an unbounded number of browsers. Dimensions are bounded. Failure to install optional browser tools produces a clear 503 response.

For browser automation:

```javascript
await window.mosswood.configure({
  actor_id: "resident_001", view: "home", tab: "details", grid: true,
  roofs: "open", zoom: 1.4
});
const mapPngDataUrl = window.mosswood.capture();
```

## Plausibility and player recommendations (rule package 3.2)

`GET /api/plausibility` returns a read-only snapshot audit: counts of object kinds and occupations, missing/unreachable home storage, insufficient bed/table capacity, missing workplaces for employed adults, missed work targets, and absent pupils if a save has school desks but no children. It does not alter a save or call an LLM.

`GET /api/actors/{actor_id}` includes `recommendation_options` for feasible next steps and the current `player_recommendation` when present. `POST /api/recommendations` accepts `actor_id`, `expected_version`, `action`, `target_id`, optional `social_category`, and `ttl_seconds` (60–3600, default 1800). The actor must still be procedurally controlled. The suggestion is journaled and adds a bounded utility bias at the next free decision; it is neither a command nor consent from a social partner. It resolves as `followed`, `considered`, `unavailable`, or `expired`. `POST /api/recommendations/{actor_id}/cancel` with `expected_version` changes a pending suggestion to `cancelled`.

`GET /api/actors/{actor_id}/interventions` provides the player menu's currently available contacts, conversation categories, and destination affordances. It makes no long route searches or ledger writes; a nearby named conversation need not appear in the small utility shortlist, and a distant known contact may be called with `social_category: "phone_call"`. The menu checks object condition, capacity, affordability, age and schedule cheaply. The concrete walking route and all other preconditions are revalidated when the player submits. `POST /api/player/recommendations` accepts `actor_id`, `action`, `target_id`, optional `social_category`, and `ttl_seconds`; it reads the current actor version under the same world lock as the recommendation to avoid a separate full-inspector fetch and version race. The versioned `/api/recommendations` endpoint remains available for API clients. Recipient consent and changing preconditions still apply. These are omniscient local UI endpoints, not external-agent perspective packets.

`GET /api/actors/{actor_id}/relationships` and the inspector's `social_graph` now expose explicit viewer-relative roles and both participants' directed relation *scores* where both records exist. They exclude the target's current affect, thoughts and needs. An absent reverse record stays absent.

These omniscient player/QA endpoints are **not** agent perspective packets. An external decision agent must use the bounded bridge below.

## LWM bridge 0.1

The runtime creates **no Simulation Fields**. It makes no model calls by default; a player may opt one Sim into Mercury Decide or Jev through `/api/actors/{id}/decision-provider` when `OPENROUTER_API_KEY` is set in the server environment. These bridge endpoints remain a bounded agent-perspective boundary:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/bridge/{actor_id}/context` | Own state/evidence, visible people without private components, known feasible actions, pending boundaries, versions, and omissions |
| `POST /api/bridge/{actor_id}/ownership` | Transfer decision authority using `owner: "external"` or `"procedural"` and `expected_epoch` |
| `POST /api/bridge/intent` | Submit a supported feasible action at an idle decision boundary |

An ownership transfer increments the actor epoch while preserving identity, active action, need-rate segment, effects, evidence, and reservation. Mechanical completion/interruptions continue. A manually externally owned idle resident waits for an external decision; its needs still advance. For the *opt-in OpenRouter provider* specifically, timeout, rate limit, invalid response, or missing key now records a safe status and lets a procedural choice cover that decision boundary. The provider preference remains active and retries with bounded backoff; it is not silently switched off. Returning to procedural ownership schedules the next decision. No claim of multi-field synchronization is implied.

Example proposed intent:

```json
{
  "actor_id": "resident_001",
  "owner_epoch": 2,
  "expected_version": 21,
  "action": "read",
  "target_id": "object_0007"
}
```

Use the actual epoch, version, and action target from the latest context packet; the numbers above are illustrative. The coordinator rejects stale epochs, stale versions, busy actors, unknown actions, inaccessible targets, or unavailable resources with HTTP 409. Missing entities produce 404 and malformed requests produce 422. Accepted intentions use the same action resolver and ledger as procedural choices. An intent cannot directly set needs, fabricate beliefs, create money, transfer objects, or rewrite history.

For `action: "chat"`, optionally provide `social_category`, such as `small_talk`, and an available partner's ID as `target_id`. This selects a supported contextual interaction; it never bypasses structural eligibility or the recipient's separate willingness check. The endpoint accepting a proposal does not guarantee the other person accepts a conversation. Meal actions offered in the perspective are the feasible next step of an actual resource plan, not permission to skip ingredients or produce food directly.

The action interface currently chooses the nearest available target per action kind; it does not offer all possible alternative objects of that kind. Separate occupation/care planners, exact speech, arbitrary LWM Change proposals, held leases with expiration, and distributed watermarks are future work. Keep any future LLM on the perspective endpoint, not the omniscient observer endpoints.
