# Procedural Psychology Design

`living_world.psychology` is a deterministic gameplay abstraction for fictional
residents. It is not a diagnostic system, a model of real people, or a claim
that an agent has hidden access to another resident's mind.

## Research boundary

The external products are references for player-facing life-simulation patterns,
not copied mechanics. EA's [Growing Together guided tour](https://www.ea.com/games/the-sims/the-sims-4/news/the-sims-4-grow-together-guided-tour)
describes family dynamics, social compatibility, relationship effects, and
milestones. EA's [Whims, Aspirations, and Goals](https://www.ea.com/games/the-sims/the-sims-4/news/whims-aspirations-goals)
describes optional structured guidance. KRAFTON's official [inZOI update notes](https://www.playinzoi.com/en/news/8812)
describe relationship responses that vary with personality, preferences,
relationship state, and current emotion. These sources support distinct traits,
ambitions, consent checks, and relationship layers here.

The supplied [Sims Player's Guide](https://cdn-assets-ts4.pulse.ea.com/Guide/TheSims4_Players_Guide.pdf)
was retained as a provenance link but was unavailable to this implementation's
fetcher, so it is not used for a factual claim above. The supplied [inZOI notes 9309](https://playinzoi.com/en/news/9309)
and [9533](https://playinzoi.com/en/news/9533) were consulted only as official
product-update references; this implementation does not reproduce their systems
or make version, date, or locale-specific claims about them.

The following are implementation inferences, not claims about either product:
Big Five values are continuous `0..1` weights; interaction scoring is bounded;
and Theory of Mind stores only observed evidence. Mosswood deliberately uses
adult-only romance (`age >= 18`) for this first integration even though other
products may support different age systems.

## Data contract and ownership

All helpers are pure: they deep-copy supplied data and return patches. The world
coordinator must apply those patches within `World.transaction` using
`World.edit`; helpers never write the actor dictionary, save, ledger, or global
random generator.

* `initialize_psychology(actor, rng, now=0)` creates `psychology` with Big Five,
  readable gameplay traits, ambitions, hobbies, concerns, and bounded ToM.
* `migrate_existing_actor(actor, rng, now=0)` only adds missing psychology
  fields. It preserves age, legacy relations, and unknown history.
* `initial_family_profiles(actors)` is **new-world-only** authored starter data:
  adult grandparents, parents, adult children, partners, and cousins across
  homes. Apply it before `initialize_social_graph`. Its family data is explicit:
  `family.parent_ids`, `family.partner_id`, `family.relationship_status`, and
  `family.known_kin_ids`; no link is guessed from age or co-residence. This
  authored fixture requires at least 11 actors and raises `ValueError` rather
  than emitting dangling IDs for a smaller fixture.
  It is used only while creating a new world. Save migration keeps the existing
  age and relationship record and leaves unknown prior kinship and biography
  unspecified instead of authoring a retrospective family story.
* `initialize_social_graph(actors, now=0)` keeps legacy edges and creates only
  co-resident, explicit kin, reciprocal partner, or matching `workplace_id`
  edges. It never introduces all residents as acquaintances.

Each relationship has separate `family`, `romance`, `friendship`, `coworker`,
and `household` layers, plus closeness, trust, respect, attraction, and tension.
Household is never used as evidence of kinship. Kin labels are directional
(`parent`/`child`, `grandparent`/`grandchild`, `aunt_uncle`/`niece_nephew`) and
also include sibling and cousin. Any known kin blocks romance. Romantic attempts
also require adults, opt-in, and a runtime recipient-consent draw owned by the
coordinator. A resident committed to someone else cannot initiate or receive a
new romantic category by default; each committed participant must explicitly
set `relationship_preferences.nonmonogamous` to `true` for that structural gate
to be lifted. Established partner status is not overwritten by an early flirt,
and no helper creates a partner link from a flirt or date.

## Actions and social categories

`action_bias(actor, kind, now=None)` returns `[-1, 1]`; ambition progress,
matching hobby enjoyment, and active concerns adjust it. The optional
`conditional_action_probability` and `choose_if_then_action(..., rng)` make the
if-then choice probabilistic only with injected seeded randomness. Availability,
cost, spatial reachability, and recipient consent remain world checks. Engine
aliases normalize to their actual hobbies: `creative_hobby` to `craft`, `stroll`
to `walk`, `eat_meal`/`prepare_meal` to `cooking`, and `read` to `reading`.

`social_category_definitions()` exposes exactly 20 UI/planner contracts: greet,
small talk, share interest, offer help, ask advice, compliment, apologize, check
in, confide, invite activity, celebrate, coordinate work, set boundary, gossip,
reconcile, tell joke, play together, flirt, ask date, and express affection.
Each includes a label, duration, tone, and base score. `social_candidates` lists
all categories with `allowed`, reason, score, probability, duration, and a
separate recipient `willingness`; willingness must never bypass consent.
`coordinate_work` needs a coworker layer or shared `workplace_id` (the helper
also reads the legacy `workplace.workplace_id` object field). `apologize` and
`reconcile` need existing tension, so repair is not context-free.

After one resolved event, call `apply_social` **once** with `accepted` or
`declined`; `positive`, `neutral`, `negative`, and `boundary` are also accepted.
Aliases `success -> positive` and `failure -> negative` are provided for older
callers. It returns bilateral patches, so do not call it once per participant.
Warm/care/task/repair, romance, boundary, and gossip/tension tones update their
respective dimensions differently.

## Bounded observations and concerns

Feed public evidence into:

```python
observe(actor, other_id, "social:small_talk:accepted", now, beat_id)
```

The stored schema is `{at, observation, evidence_id, modality}`. At most 12
observations per person are retained. Only explicit public cues create a
low-confidence inference such as “may prefer space” or “interaction was
receptive”; no private mood, intention, memory, or omniscient state is read.
For six hours, a witnessed decline/space cue reduces `confide` and romantic
category scores; for twelve hours, a witnessed receptive cue modestly boosts
appropriate social scores. These are first-order adjustments from the actor's
own recorded observations, never reads of the other resident's actual state.

`update_fears` uses game concerns, not medical labels. Canonical event names are
`dog_encounter` (only after an actual observed pet encounter),
`work_failed_deadline`, and `work_warning`, which update `dogs` or `job_loss`.
The patch gives the event concern a four-hour `expires_at`; the coordinator owns
event de-duplication/cooldown and passes `now` to `action_bias` to ignore expired
concerns. `complete_activity` advances a matching hobby and compatible ambition
with the ledger evidence ID.
