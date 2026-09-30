# Local API and future agent integration

Interactive OpenAPI: **http://127.0.0.1:8765/docs**. All times are integer world seconds; one meter is one tile. This API is intended for a trusted local prototype and has no network authentication. The launcher binds to `127.0.0.1`.

| Endpoint | Contract |
| --- | --- |
| `GET /api/world` | Static geometry, household membership, objects, regions, decoration |
| `GET /api/state` | Clock, actor positions/trajectories, activity counts, live reservations, metrics |
| `GET /api/actors/{id}` | Full observer inspector, evaluated needs, internal state, coverage |
| `GET /api/actors/{id}/journal?limit=40&before=N` | Resident-indexed accepted Beats, newest first |
| `GET /api/beats?limit=15&before=N` | Shared ledger, newest first; limit is capped at 200 |
| `GET /api/rules` | Pinned manifest plus declarative definitions |
| `GET /api/health` | Current invariant errors, fault state, explicitly disabled model/fields |
| `POST /api/control` | Optional `paused`, `speed` (1–600), `step_seconds` (1–3600, while paused) |
| `POST /api/save` | Atomically checkpoint state, queued events and pending Beat writes |
| `GET /api/export` | Save and return the complete continuation checkpoint |
| `GET /api/replay?through=N` | Reconstruct canonical component projection through an accepted Beat |
| `WS /ws` | Four current-state packets per real second; it does not advance time |
| `POST /api/capture` | PNG of the complete browser UI; Playwright/Chromium required |

Geometry objects carry `w`, `h`, orientation, meter position, interaction anchors, capacity, ownership, condition, and reservations. The live snapshot's resource list includes **currently reserved objects and objects with materialized daily household state**. It is not a full live object registry; for exact non-reserved condition, use an exported checkpoint or the observer world endpoint. The actor inspector adds psychology, family layers, workplace, routine/planned steps, household states, and all 20 social-category definitions. `/life-supplement` documents these contracts and their limits.

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

## LWM bridge 0.1

The runtime creates **no Simulation Fields and makes no model calls**. These three endpoints implement a bounded future decision-provider boundary:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/bridge/{actor_id}/context` | Own state/evidence, visible people without private components, known feasible actions, pending boundaries, versions, and omissions |
| `POST /api/bridge/{actor_id}/ownership` | Transfer decision authority using `owner: "external"` or `"procedural"` and `expected_epoch` |
| `POST /api/bridge/intent` | Submit a supported feasible action at an idle decision boundary |

An ownership transfer increments the actor epoch while preserving identity, active action, need-rate segment, effects, evidence, and reservation. Mechanical completion/interruptions continue. An externally owned idle resident waits for an external decision; its needs still advance. Returning to procedural ownership schedules the next decision. No claim of multi-field synchronization is implied.

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
