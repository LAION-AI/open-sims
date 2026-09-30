# Affect model: evidence, not mind reading

`living_world.affect` is a pure, rule-based gameplay layer for fictional
residents. It can retain several concurrent affect states and select one primary
state for presentation. It is not a clinical model, facial analysis system, or
claim that the simulation knows a person's hidden thoughts.

## Taxonomy provenance

The 40 registered English names and their source groups are imported from
[EmoNet-Face `guide.json`](https://raw.githubusercontent.com/LAION-AI/emonet-face/main/data/guide.json),
retrieved 2026-09-29, SHA-256
`679049ed7ac1dc01ce28891132c8bc285032b84f2319f099fbd4aa2c23ec9191`.
The source repository describes a 40-category, expert-annotated synthetic-face
benchmark and attributes the work to LAION-AI and Schuhmann et al. (2025); its
code is MIT and its datasets CC BY 4.0. [Repository](https://github.com/LAION-AI/emonet-face)

Only label names and groups are used here. No face images, data records,
inference model, demographic feature, or face-recognition behavior is imported.
German labels are authored display translations, not claims that they are source
labels.

The registry is intentionally wider than the active gameplay subset. For
example, `Sexual Lust` and `Intoxication/Altered States of Consciousness` remain
registered so the taxonomy stays complete, but this implementation has no
automatic trigger for either--especially never from age, clothing, appearance,
or attraction.

## Contract

* `initialize_affect(actor, now=0)` returns `{"affect": ...}` with no active
  state.
* `appraise(actor, needs, now, cause, evidence=None)` returns the **affect
  dictionary itself**, ready for `actor["affect"] = result`. It does not mutate
  either input.
* `project_affect(actor, now)` returns an expiry-filtered view and leaves
  canonical stored state untouched.
* `adapt_legacy_emotion(actor, now, evidence_id="legacy")` converts the prior
  single display band to stable IDs without recreating unrecorded history.
* `social_graph_projection(actor, actors, now)` returns only the viewer's
  directed known edges and never another actor's affect, needs, thought, or
  private data.

An active state has a stable taxonomy `id`, English `label`, German `label_de`,
`intensity`, expiry, and evidence-bearing causes.  Its current value is built
from at most six independently expiring components; every component preserves
its exact cause record, activation time and expiry.  A rendered state and its
`actual_narrative` include only still-active components.  This prevents a later
long-lived event from displaying an earlier expired cause.  Old saves that lack
components use their recorded state expiry; if that is absent they receive only
the ordinary bounded default, never a permanent reconstructed feeling.

```json
{"kind":"social_interaction", "text":"Accepted affectionate interaction",
 "evidence_id":"beat_42", "subject_id":"resident_002"}
```

`actual_narrative` is constructed from modeled needs and explicit cause records.
`self_narrative` is a lower-confidence, possibly defensive or uncertain
self-description; it never replaces, edits, or erases `actual_narrative`.
It is a clearly labelled gameplay interpretation of the actor's own Big Five
weights and current evidenced states: extraversion can make an evidenced
affection state read as openness, neuroticism as remaining uncertainty, and
agreeableness as acknowledgement of connection. It does not invent an event,
attribute a thought to someone else, or assert that its interpretation is true.

Current real triggers include urgent modeled needs, a directly observed dog,
work-warning/deadline events, explicit insults or rejection, verified social
outcomes, selected activity states, and need relief.  `Pride` is deliberately
not a reward for every completed action: it requires an explicit completed
goal, work, a completed craft, or a finished cooked recipe. A positive affectionate contact
and an urgent bladder need can therefore coexist as `Affection` and `Distress`.
No trigger reads another actor's current affect or intent.

Structured causes make that boundary executable. `activity_started` and
`activity_completed` use their real action category to add bounded
`Contentment`, `Interest`, or `Concentration`; baseline Contentment is available
only for initialization or an activity start while all modeled needs are below
0.6. `need_relief` requires an actual positive `relief` delta, rather than a
label alone. On every appraisal, components caused solely by physical needs are
removed and recomputed from current values, so a completed toilet interaction
cannot leave an old bladder-driven state at its previous maximum intensity.

`Infatuation` is only activated by an explicit successful
`romantic_affection` cause for `flirt` or `express_affection` that carries
`adult_relation: true`; this also activates Affection. An explicit romantic
rejection adds Sadness and Longing alongside its other evidence-bound effects.
A reserved actor may say "Maybe that was only a friendly conversation" after a
real positive adult romantic interaction. That is a deliberately limited,
trait-weighted self-interpretation, never a denial of the recorded event.

## Relationship graph

The graph is directed from the viewer. Existing relationship records determine
edge type and qualities (closeness, trust, respect, attraction, tension), and
their weighted importance. A direct observation is represented separately in
`observed_not_known`: seeing a resident is not an introduction or a relationship
edge. This preserves target privacy and makes actual acquaintance explicit.

The agent-facing perspective hides `actual_narrative`, state causes, and the
social graph, exposing only primary affect and `self_narrative`. The separate
world snapshot is an explicitly omniscient player presentation and may include
the active state records/cause evidence; it must not be reused as an agent
perspective packet.

New-world family structures are authored by the separate psychology subsystem.
Existing saves retain unknown biography and kinship rather than receiving a
retroactive family narrative; affect's legacy adapter similarly preserves only
the old display value and labels its cause as unreconstructed.
