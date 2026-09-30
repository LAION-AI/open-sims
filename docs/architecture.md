# Implementation contract and whitepaper mapping

This prototype uses the supplied **Procedural Living Worlds**, 27 September 2026 (40 pages), and **Living World Model**, 21 September 2026 (32 pages). It implements a bounded procedural neighborhood and a future integration boundary. It does not claim the papers' suggested scale or full cognitive coverage.

The subsequent [housing-generation HTML supplement](procedural_housing_supplement.html) adds an isolated procedural room/house laboratory, floor-aware navigation probes and a street/plot study. The table below describes the original **main simulation**. The newer [life-system HTML supplement](life_systems.html) documents psychology, layered relationships, food/cleanup chains and the southern workplace extension. Existing map cells are preserved, while new geometry is appended. The lab's timed elevator FIFO and floor graph are not yet wired into the main action scheduler or its Beat ledger.

| Source | Prototype implementation | Deliberate limit |
| --- | --- | --- |
| PLW §§2–4, A1–A5 | Stable actor/object records; component dictionaries; declarative needs/actions; scored and seeded selection; explicit action phases | Python records for 44 actors; no compact-array production kernel or arbitrary rule DSL |
| PLW §5, A7 | Integer meter terrain; independent object registry; multi-cell footprints; walkable anchors; rooms/buildings/neighborhood hierarchy | Single flat floor, resident map; no streaming or district routes |
| PLW A4 | Reservation, travel, use, completion, interruption, start costs, final object checks | No fine body collision, dynamic barriers, full failure/planning tree, or fairness queue |
| PLW A5, B2 | Lazy need segments, exact scheduled boundaries, deterministic named draws, bounded timer cleanup | Integer seconds; no fractional subsecond physics |
| PLW §6; LWM §§3, 5 | Explicit personal perceptions, memories, beliefs, relationships, goals, thoughts and emotion appraisal | No exact dialogue, testimony propagation, memory distortion, or higher-order beliefs |
| LWM §4, §14; PLW B1 | Central transactions, ordered Change records, SQLite ledger, versioned projections and replay | Single coordinator; Beat microsteps use record order, not distributed causal clocks |
| PLW §7, B4 | Actor-specific context packet, version/epoch checks, decision ownership transfer while mechanics continue | No Simulation Fields, watermark network, multi-field merge/split, or LLM |
| PLW E1–E2 | Same headless engine, full UI inspectors, browser screenshots, deterministic and long-run checks | No Rule Workshop, statistical behavior validation or city benchmark |

## Time and state

World time is an integer number of seconds from the start of fictional day one. Initialization is at 08:15. The scheduler orders `(due_time, stable_serial, type, actor, token)`. Tokens identify the action or decision opportunity. Interrupted actions leave harmless stale events, which are ignored and periodically compacted; they cannot finish a replacement action.

Needs record a baseline, baseline time, and per-second rate. Beginning an action materializes the current value and installs the relief rate. Interrupting or finishing materializes it again and restores the ordinary rate. Inspecting simply evaluates this function and never mutates state. Travel stores an ordered cardinal path; one grid edge takes one world second. The renderer interpolates within that accepted path. It cannot make a new journey, cross a wall, or finish an interaction.

Action choice samples a numerically stable softmax once at an actual decision opportunity. The stream is derived with SHA-256 from the seed, actor, decision ID, immutable JSON rule hash, and draw purpose. Rendering or subdivision of `advance()` calls does not alter that stream. The rule hash pins declarative configuration; Python mechanics are part of this source release and are not hot reloadable. Source changes require deliberate versioning/migration in a deployed product.

The 1× UI speed is literal world seconds per wall second. API clients may set speeds up to 600×. On overload, the single-threaded simulation takes longer to advance; it does not jump over due events. Server faults stop the clock and surface in health/state/UI. There is no claim of uninterrupted real-time service at 600×.

## Transactions and history

A transaction snapshots only records it touches. Successful resolution writes changed top-level components as an ordered Beat. Actor components receive a new version and last-Beat reference. Reservations and their owning action are changed in that same coordinator transaction. Internal exceptions roll back touched records and scheduled work in the in-memory transaction.

SQLite Beat writes stay in one durable transaction with the latest checkpoint. Every ten wall seconds, on explicit Save, and at graceful shutdown, both become durable. The checkpoint contains actors, objects, world process records, the event heap and its serial, rule hash, world time, and counters. An abrupt exit loses the unsaved tail instead of loading partially durable state. This is a small-world checkpoint design, not an exactly-once distributed message service.

Replay applies recorded component assignments in sequence. It does not resample actions, regenerate text, or interpret intentions. `/api/replay?through=N` returns the committed component projection at Beat N. Continuous needs/trajectory endpoints are represented by their baseline/rate or stored path and must be evaluated at the desired valid time; replay is not a general arbitrary-time temporal graph query.

Raw public render snapshots include world truth for the observer interface. They are **not** appropriate LLM character prompts. Use the bridge context endpoint for character integrations.

## Resource and social rules

Public facilities and each actor's own household furnishings are initialized as known. Eligibility restricts private furniture to household members, checks money, condition, and free interaction slots. Reservations cover travel and the whole action interval; a three-seat sofa may have three users at distinct anchors, while a toilet has one. A competing resident chooses another feasible action and later reconsiders. There is no dedicated first-come-first-served waiting queue or starvation proof.

Conversations need line of sight and proximity. Only unoccupied residents, or residents taking interruptible rest, are offered as partners. Recipients evaluate their own needs and willingness using their own draw. A declined request is logged and the initiator waits before asking again. An accepted conversation has one shared event ID, two actor action states, two eventual individual outcomes, and separate personal evidence. No arbitrary speech is invented.

The current physiology is an authored game model. Need rates, preference weights, emotion bands, and social willingness are design parameters, not claims about real psychology. Emotion changes are triggered by outcomes and interruption, so an inspector can show an older emotion appraisal alongside newly changing physical needs. The time and cause are displayed explicitly.

## Scaling next

The current bottlenecks are expected to be A* requests, JSON history, and Python object manipulation. Rendering uses one cached base canvas, cached roofs, visible-scene culling, and a small number of animated sprites. Static geometry is sent once; a 4 Hz WebSocket sends current actor trajectories for a separate requestAnimationFrame loop.

For a larger world, preserve these APIs while moving hot components into numeric arrays; introduce regional navigation and spatial affordance indices; store incremental evidence rather than copying bounded lists; add history retention policies; and benchmark before adding residents. Then implement the LWM conservative field/watermark contracts as their own tested milestone. A camera zoom must never become a simulation ownership boundary.
