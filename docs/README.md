# Dokumentationswegweiser / Documentation index

Open Sims separates the **inhabited world** from three authoring laboratories. A fresh clone contains source, the two supplied whitepapers, HTML supplements and reproducible evidence, but no local SQLite saves. Start with the [root README](../README.md) for setup and controls.

## Read by concern

| Concern | Primary documentation | Status |
| --- | --- | --- |
| Whitepaper mapping, event ledger, time and replay | [Architecture](architecture.md), [Living World Model PDF](../Living_World_Model_Technical_Report%20%282%29.pdf), [Procedural Living Worlds PDF](../Procedural_Living_Worlds_Whitepaper.pdf) | Prototype bridge; no Simulation Fields |
| HTTP/WebSocket and future agent boundary | [API](api.md) and live `/docs` OpenAPI | Local trusted API |
| Inhabited district and urban services | [Neighborhood](neighborhood_design.md), [City](city_design.md), [Story systems](story_systems.html) | One-level live map; district laboratory separate |
| Room and multi-floor generation | [Housing supplement](procedural_housing_supplement.html), [spatial plausibility](spatial_plausibility_notes.md), [bed variants](bed_variants_notes.md), [buildings](buildings_notes.md), [civic catalog](civic_catalog_notes.md) | Separate generator laboratory |
| Everyday behavior and psychology | [Expanded-life HTML supplement](expanded_life.html), [life systems](life_systems.html), [daily life](daily_life_design.md), [psychology](psychology_design.md), [affect](affect_design.md), [possessions](possessions_design.md) | Rules-based adult model; new careers and relationship view |
| Extensible content-agent workshop | [Workshop supplement](agent_workshop.html) | Review-gated prototype; no unattended publication |
| Evaluation and next interventions | [Verification](verification.md), [plausibility and intervention plan](../web/plausibility-plan.html), [evidence](../artifacts/) | Reported tests plus explicitly planned work |

The HTML supplements can be opened directly from disk; they are also served through the application. Their `*_template.html` counterparts are the sources for report-generated pages. Keep both when changing a report.

## Source layout

```text
living_world/                 Python simulation package
  engine.py                  coordinator, decisions and scheduling
  ledger.py                  SQLite Beats, checkpoints and replay
  spatial.py                 world grid, navigation and objects
  psychology.py, affect.py   needs, emotions, relationships
  generation/               rooms, houses, buildings and districts
  workshop/                 staged catalog and provider adapters
web/                         Canvas renderer and browser inspectors
scripts/                     generation, reports, capture and browser checks
tests/                       unit and integration tests
docs/                        specifications and HTML supplements
artifacts/                   selected PNG/JSON evidence, not runtime logs
data/                        local saves and content library (gitignored)
run.py                       server/headless entry point
```

## Development and reproduction

Install runtime dependencies from `requirements.txt`; use `requirements-dev.txt` and `python -m playwright install chromium` only for browser checks. Run `python -m unittest discover -s tests -v` for the full regression suite. `python run.py --headless --hours 24` exercises the engine without the browser. Browser-check scripts may change time controls and save; give them a separate test database, never a cherished save.

The local server binds to `127.0.0.1` and has no authentication. Do not expose it to the public internet. External model-provider keys are optional for the separate workshop and belong only in process environment variables, never source, browser code, screenshots, or commits. Its review gate is not a security sandbox for public users.

For a release, check that no save, `.env`, log, or credential is tracked; run the suite; inspect representative screenshots and the app on a narrow display; and update the status/limitations in the root README when mechanics change. The repository intentionally has no license until its owner chooses one.
