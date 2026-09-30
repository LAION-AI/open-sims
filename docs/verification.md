# Observed verification results

Checked locally on 28 September 2026. These are prototype measurements, not promises for other hardware or larger populations.

## Life-system v2 update

The sections below describe the **older v1 baseline**, not the performance of v2. Current rule package 2.0.0 adds psychology, real meal/cleanup chains, social categories and external workplaces. The current world has 349 objects and a 128 × 154 map. New measurements and limitations are recorded in [life_systems.html](life_systems.html) and [../artifacts/life_systems/report.json](../artifacts/life_systems/report.json).

The final 24-hour, seed-42, disk-backed v2 simulation took 65.081 seconds for advancement/checks/checkpoints, produced 11,355 Beats, passed invariants after every five world minutes and matched canonical state on full replay. It executed 188 household meals, 190 preparations, 179 dishwashing completions, 12 grocery/restocking trips, 34 creative hobby completions and 242 work completions. Thirteen of the twenty supported social categories occurred naturally in that run; conditional romance and repair are separately tested, not claimed to have occurred in that sample. Browser proof and screenshots are under `artifacts/life_systems/`.

Final full suite: **101 tests passed in 103.665 seconds**, including the regression for an already-completed final chore ending its routine correctly. Chromium checks cover the resident inspector, inventories/household state, actual carried items, the park dog, new workplace shells, public-building clicks, and 390px mobile layout. The standalone HTML supplement was also checked at 1440px and 390px, with embedded images and no horizontal overflow or page errors.

The running main-world v1 migration was separately checked against its pre-migration SQLite backup: population, ages, households and existing object geometry were preserved, unknown kinship was not invented, the clock did not reset and full canonical replay matched. See `artifacts/life_systems/deployment.json`. Screenshots of the generator and new-world family fixture do not imply that old occupied homes or unknown old family biographies were replaced.

Deployment caveat: the main process successfully loaded v2 and resumed its prior running/10× controls. The final one-line routine-status correction was added after that process started. A second process restart was denied by the execution environment, so this final correction is tested on disk but loads in the main world only at its next normal restart. The separate browser-review process on port 8767 remains paused. No files or world histories were deleted.

The old seven-day result below is historical evidence, **not a seven-day test of the new system**.

## Mechanics and API

Nine automated tests passed: eight engine/spatial/persistence tests and one integrated API test.

- Twenty households, 44 residents, and 320 registered objects.
- Every interaction anchor is reachable from the public map.
- Multi-cell sofa footprint is represented as a single object.
- Splitting one hour into sixty one-minute advances preserves canonical state, decisions, and the event heap exactly.
- Replaying accepted changes reproduces current component state.
- Two residents cannot reserve the same toilet simultaneously.
- Interruption preserves elapsed travel and spent resources and releases reservations.
- Decision ownership transfer preserves active actions and rejects stale epochs.
- Agent context excludes other residents' private components.
- Saving and resuming preserves the same continuation as an uninterrupted run.
- API controls, malformed requests, missing residents, save/export, bridge epochs, and replay were checked.

Commands:

```powershell
python -m unittest discover -s tests -v
python run.py --headless --hours 24
python scripts/benchmark.py --hours 168
```

## Long run

Seven complete simulated days, seed 42, were advanced in five-world-minute chunks. The test checked invariants after every chunk and replayed the entire history at the end.

| Measurement | Observed result |
| --- | --- |
| Simulated duration | 168 hours |
| Runtime for simulation loop, including persistence checkpoints and checks | 271.556 real seconds |
| Accepted Beats | 51,062 |
| Decisions | 16,886 |
| Completed actions | 16,212 |
| Accepted / declined conversations | 111 / 836 |
| Path requests | 2,866 |
| Largest observed scheduler queue | 167 |
| Final scheduler queue | 110 |
| Invariant errors | 0 observed |
| Canonical replay | Exact match |
| Five-minute advance p50 / p95 / p99 | 92.143 / 397.813 / 639.869 ms |
| Largest five-minute advance | 1,227.899 ms |
| History database size before final close | 518,410,240 bytes |

The shorter, monolithic 24-hour in-memory run took 17.839 seconds. Its storage mode and workload differ from the seven-day disk-backed benchmark; the figures should not be compared as identical measurements. Final full replay/analysis is outside the reported simulation-loop time.

The neighborhood exercised eating, drinking, bathroom use, sleep, showers, gardening, reading, work, rest, park visits, waiting, and consensual conversation. The seven-day fixture selected 1,467 work actions and 645 park visits. Zero observed invariant failures do not establish psychological realism or prove starvation freedom.

Environment: Windows 10 build 19045, Python 3.14.2, Intel64 Family 6 Model 142 Stepping 9. Other local work and browser captures ran during the benchmark, so it is not an isolated CPU microbenchmark. Complete machine-readable results are in [../artifacts/benchmark.json](../artifacts/benchmark.json).

The roughly 494 MiB ledger after a week is a concrete prototype limitation: exact JSON history needs a more compact representation and a retention policy for long-lived worlds. Current actor memories and beliefs are bounded; durable history is not.

## Browser and visuals

Headless Chromium, 1440 × 1000 viewport, device scale factor 1:

- No browser JavaScript errors in the interaction regression.
- Approximately 59–60 fps observed in the neighborhood view.
- Pan, zoom, fit, one-meter grid, house cutaways, all four inspector tabs, resident search, canvas hit selection, pause, speed, and saving were exercised.
- Narrow layout checked at 390 × 844, with no horizontal page overflow.
- Full-interface screenshot API returned valid PNG output.
- Neighborhood, furnished interior/grid, inner-life inspector, journal, full map, and narrow-layout screenshots were generated and visually inspected.

Run `python scripts/check_browser.py` against a separate test-world server to reproduce the interaction checks. It changes time controls and saves. `python scripts/capture.py` captures a read-only view.

Representative artifacts:

- [Neighborhood](../artifacts/01-neighborhood.png)
- [Furnished home and meter grid](../artifacts/02-home-grid.png)
- [Inner-life inspector](../artifacts/03-inner-life.png)
- [Personal journal](../artifacts/04-journal.png)
- [All twenty households](../artifacts/05-all-households.png)
- [Narrow-screen layout](../artifacts/06-mobile.png)
- [Capture API output](../artifacts/08-refined-neighborhood.png)

Browser fps is a sampled presentation figure, not a frame-time distribution or a guarantee. The Python loop, serialization, and browser run independently; a higher speed multiplier still requires more simulation work.
