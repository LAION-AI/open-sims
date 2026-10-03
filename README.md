# Open Sims · Mosswood

Open Sims is a persistent, rules-driven neighborhood inspired by the supplied [Procedural Living Worlds](Procedural_Living_Worlds_Whitepaper.pdf) and [Living World Model](Living_World_Model_Technical_Report%20%282%29.pdf) whitepapers. New `neighborhood-v1` worlds have 20 family households, a ten-room student residence with ten residents, a university and civic/leisure workplaces: 54 simulated people in total. Existing saves retain their population. The original pixel-art Canvas view lets you follow them, zoom and pan through the neighborhood, inspect objects, visit homes and move between the three residence floors. The simulation runs locally without a language model, API key, Simulation Field or frontend build.

This is a research prototype, not a finished game or a real-city reconstruction. The [documentation index](docs/README.md) distinguishes the inhabited world from the separate housing, district and content-agent laboratories, and links the architecture, APIs, HTML whitepaper supplements, verification and limitations.

![Lindenviertel map and homes](artifacts/new_neighborhood/00-neighborhood-overview.png)

## Quick start

Python 3.11+ is required. In PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py --layout neighborhood-v1 --seed 73
```

On macOS/Linux use `.venv/bin/python`. Open <http://127.0.0.1:8765/> and <http://127.0.0.1:8765/docs> for the API. The first run creates `data/mosswood.sqlite3`; subsequent runs resume it. To keep multiple worlds, pass distinct `--database` paths. **Never run two servers against the same SQLite file.** `data/` and secrets are excluded from Git. The loopback server is unauthenticated, so do not expose it to the public internet.

```powershell
python run.py --no-browser --port 8765
python run.py --database data/another-neighborhood.sqlite3 --layout neighborhood-v1 --seed 73
python run.py --headless --layout neighborhood-v1 --seed 73 --hours 24
```

The separately named Lindenviertel historical save can be created once with `python scripts/create_lindenviertel.py`, then opened using `python run.py --database data/mosswood-lindenviertel-20260929.sqlite3 --layout neighborhood-v1 --seed 73 --port 8769`. Existing files are not overwritten by the creator. The supplied `Start Lindenviertel.bat` and `Start Mosswood.bat` are Windows shortcuts.

## Explore and intervene

| Control | Effect |
| --- | --- |
| Drag, WASD, arrow keys | Pan the map |
| Wheel, pinch, + / − | Zoom around the pointer |
| F, fit button, minimap | Reorient the camera |
| Click a person, house or object | Open the corresponding inspector |
| People / P, Objects | Search residents or furniture |
| Social | Open the live neighborhood insights overlay (relationships, mood, demographics, venues, careers and recent events) |
| Plan contact & outing | Suggest a reachable person and conversation type, call a known contact, or choose a specific destination; the other Sim can still decline |
| Follow, Visit home, Go to work | Navigate to a resident or destination |
| EN / DE in the header | Switch the interface language without reloading or advancing the simulation; the choice is saved in this browser |
| Floor controls | Jump between the residence's ground, first and second floors |
| G, R | Toggle meter grid or cycle roofs |
| Space; speed menu | Pause/resume; request 1×, 10×, 60×, 120×, 300× or 600× |
| Camera | Download the rendered Canvas PNG |

The person inspector shows at-a-glance emotions, needs, intention, goals, relationships, action options, journal, object use, career, skills, attributes and recent W100 checks. Need values in the engine are *urgency* (one is critical); UI bars invert them so fuller means better. Narrative explanations distinguish causal events from a Sim's own interpretation. Forecast choices are possibilities, not promises. Object details expose state, occupants, reservations, anchors, inventory and available interactions. The local API additionally exposes world snapshots, object detail and capture routes; see [API docs](docs/api.md).

English is the default interface language. The EN/DE switch is shared by the main viewer, building atelier, world workshop and city lab via `web/i18n.js`; it translates visible controls and labels, including content inserted after live updates. English speech bubbles use short contextual lines; German shows the original authored phrase. Switching does not alter save data, decision rules or API identifiers. Free-form procedural journal entries, thoughts and catalog names are still authored in their source language and are not machine-translated; full bilingual narrative generation is a separate future task. Add new UI phrases as English/German pairs in the shared module and run `node web/i18n.test.js`.

In Settings, an optional OpenRouter key can be entered for opt-in per-Sim decisions. It stays in server memory, not the save. The default is procedural and offline. An opted-in Sim keeps its model choice through temporary provider failures or key removal; local procedural decisions cover gaps, with retry/backoff and a visible status in the inspector. Jev and Mercury can be switched from the same picker. Do not paste provider keys into chat, files, screenshots or commits. Provider usage and model availability are external and may change.

## Simulated systems

- World time, scheduler, deterministic named random streams, accepted-event SQLite ledger, save checkpoints and exact component replay. The Python coordinator alone writes state; browser observation does not create actions.
- One-meter terrain and furniture footprints, interaction anchors, walls, traversable doors, A* paths and timed stair portals. The live residence has two upper floors, ten individually assigned beds, shared facilities and ten adult students in new worlds. Routes between floors are simulated; the view uses separated 2D floor slabs rather than 3D stacking.
- Fifty-four residents in new worlds with Big Five traits, ambitions, hobbies, fears, needs, careers/school commitments, wealth, possessions, clothing, emotional layers, relationships and a bounded first-order Theory of Mind. Student residents are aged 18–24. Existing saves retain their biographies and population.
- Multi-step domestic routines (groceries, cooking, carrying, serving, eating and cleaning) with six named dishes across the existing pizza/pancake preparation pipelines; job-specific microtasks and college activities; contextual leisure, relationship and group actions. Leisure actions select concrete, seeded micro-scenes. An expanded set of conversations includes care, planning, debate and conflict; known contacts can also be called from afar. All conversations still require willingness. Causal incidents require an action, encounter or message before they alter state. Responses and outcomes remain probabilistic and seeded.
- An original percentile (W100) roll-under check uses attributes, skills, context and difficulty for selected work, study and social actions. This is a prototype mechanic, not a copy of a tabletop ruleset. Results and effects are exposed in the inspector and accepted journal.
- A university with 20 lecture seats, seminar rooms, labs, library, cafeteria and administration, plus a dorm; school, hospital, fire station, fitness, pool, night club, bar and other neighborhood destinations. The facilities provide assigned stations and context-appropriate activities, but not a complete institutional service simulation.

The current live city is a small designed neighborhood, not a generator of arbitrary large cities. It has no crowd collision solver, building-code guarantees, authentic medical or educational curriculum, full economic closure, reproduction mechanics, higher-order Theory of Mind or distributed Simulation Fields. True door locks, lifts in the live dorm, precise course calendars and persistent long-form group episodes remain open work. See [Campus/social/W100 supplement](docs/campus_social_w100.html), [social storyteller](docs/social_storyteller.html) and [plausibility plan](web/plausibility-plan.html).

## Authoring laboratories

The [Bauatelier](docs/procedural_housing_supplement.html) generates 32 room types with 116 furniture/equipment kinds, varied room budgets, protected doors, reachable anchors and a final validator. It can produce one- to five-floor houses with aligned stairs and an optional lift. Its test walkers and generated houses are **separate from the inhabited world**. The [Weltwerkstatt](docs/agent_workshop.html) provides exact building briefs, a small region grammar and a staged, reviewer-approved content library. It includes bounded OpenAI, Gemini and OpenRouter adapters plus offline fixtures; it neither borrows Codex subscription credentials nor automatically publishes generated code into the live world.

```powershell
python scripts/generation_report.py --seeds 64
python scripts/workshop.py run --provider demo --focus "Neue Leseplätze"
python scripts/workshop.py status
```

External content runs require an explicitly configured provider environment variable, exact provider model ID, `--allow-external` and finite job/call/output limits. Model calls were mock-tested; no claim is made that a particular provider/model is currently available or free. The [workshop documentation](docs/agent_workshop.html) explains review and publication. The full LWM protocol, unattended self-improvement, live-world generator integration and geodata reconstruction are future work.

## Verification and captures

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q -p no:cacheprovider
python run.py --headless --layout neighborhood-v1 --seed 73 --hours 24
python scripts/benchmark.py --hours 168
```

For browser checks, install Chromium with `python -m playwright install chromium`, run a server on a **separate test database**, then use `python scripts/check_browser.py` and the specialized checks in `scripts/`. They may change time controls and save. `python scripts/capture.py --output artifacts/neighborhood.png` and `POST /api/capture` request UI PNGs; the Canvas camera saves a map PNG directly. Historical verification and screenshots are in [docs/verification.md](docs/verification.md) and `artifacts/`. They document particular versions, not an evergreen guarantee. Visual inspection of the newest campus build remains necessary before release.

## Architecture, files and provenance

`living_world/engine.py` coordinates scheduling and actions; `spatial.py` and `campus.py` hold navigation and geometry; `psychology.py`, `affect.py`, `storyteller.py`, `campus_life.py` and `percentile.py` implement behavior; `ledger.py` stores ordered Beats and checkpoints; `server.py` exposes HTTP/WebSocket APIs. `web/` contains the original Canvas renderer and inspector, `tests/` the regression suite, and `docs/` the design and HTML supplements. [Architecture](docs/architecture.md) maps these contracts to the two whitepapers.

No third-party sprite sheet was copied. The Stanford [Generative Agents / Smallville project](https://github.com/joonspk-research/generative_agents) was consulted as a reference, not used as a code or asset dependency. The repository has no license selected; do not assume redistribution permissions beyond GitHub's standard viewing/forking terms.
