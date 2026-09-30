"""Real-browser regression and evidence capture for the local World Workshop.

Run against an already-running app, for example:
    python scripts/check_workshop_browser.py --base-url http://127.0.0.1:8766

The script only exercises the UI and read-only status endpoints. It never checks
the visual-review box or sends a publish request.
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "artifacts" / "workshop"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", "--base-url", dest="base_url", default="http://127.0.0.1:8765")
    parser.add_argument("--timeout", type=int, default=90000,
                        help="UI wait timeout in milliseconds")
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    report = {
        "passed": False,
        "base_url": args.base_url.rstrip("/"),
        "checks": [],
        "errors": [],
        "actual_counts": {},
        "screenshots": [],
        "external_requests": [],
        "browser_errors": [],
        "console_errors": [],
        "expected_http_errors": [],
        "offline_docs": {"checked": False, "available": False},
        "publication_attempts": 0,
    }

    def check(name, condition, detail=None):
        if not condition:
            raise AssertionError(f"{name}: {detail or 'condition failed'}")
        report["checks"].append({"name": name, "passed": True, "detail": detail})

    def capture(page, filename):
        target = EVIDENCE / filename
        page.screenshot(path=str(target), full_page=True, animations="disabled")
        report["screenshots"].append(str(target.relative_to(ROOT)).replace("\\", "/"))

    def ready(page, predicate="window.workshop?.ready && window.workshop?.design"):
        page.wait_for_function(predicate, timeout=args.timeout)

    def generate(page):
        page.locator("#generate").click()
        page.wait_for_function("!document.querySelector('#generate').disabled", timeout=args.timeout)

    def overflow_report(page):
        return page.evaluate("""() => {
          const root = document.documentElement;
          const clipped = [];
          for (const el of document.querySelectorAll('body *')) {
            const style = getComputedStyle(el), r = el.getBoundingClientRect();
            if (r.width <= 0 || r.height <= 0 || !el.textContent?.trim()) continue;
            if (el.scrollWidth > el.clientWidth + 2 &&
                !['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowX)) {
              clipped.push({tag: el.tagName, id: el.id, className: String(el.className || '').slice(0, 70),
                            clientWidth: el.clientWidth, scrollWidth: el.scrollWidth});
            }
          }
          return {viewport: innerWidth, documentWidth: root.scrollWidth,
                  horizontalOverflow: root.scrollWidth > innerWidth + 1,
                  clippedTextCandidates: clipped.slice(0, 20)};
        }""")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            report["browser_version"] = browser.version
            context = browser.new_context(viewport={"width": 1600, "height": 1100},
                                         device_scale_factor=1)
            page = context.new_page()
            page.set_default_timeout(args.timeout)
            origin = urlparse(args.base_url)

            def requested(request):
                parsed = urlparse(request.url)
                if parsed.scheme not in ("http", "https"):
                    return
                if parsed.hostname not in (origin.hostname, "localhost", "127.0.0.1"):
                    report["external_requests"].append(request.url)

            page.on("request", requested)
            page.on("pageerror", lambda error: report["browser_errors"].append(str(error)))
            page.on("console", lambda msg: report["console_errors"].append(msg.text)
                    if msg.type == "error" else None)
            generation_responses = []
            page.on("response", lambda response: generation_responses.append(
                {"url": response.url, "status": response.status})
                if urlparse(response.url).path == "/api/generation/building" else None)
            page.goto(report["base_url"] + "/workshop", wait_until="domcontentloaded")
            ready(page)
            catalog = page.evaluate("window.workshop.catalog")
            report["generator_version"] = catalog["generator_version"]
            report["room_type_count"] = len(catalog["rooms"])
            report["object_type_count"] = len(catalog["objects"])
            report["actual_counts"].update({"room_types": report["room_type_count"],
                                            "object_types": report["object_type_count"]})
            design = page.evaluate("window.workshop.design")
            check("initial_building_valid", design["validation"]["valid"],
                  design["validation"])
            check("initial_family_six_rooms_18x19",
                  design["validation"].get("room_count") == 6 and design["levels"] == 2
                  and (design["width"], design["height"]) == (18, 19),
                  {"rooms": design["validation"].get("room_count"), "levels": design["levels"]})
            family_areas = {r["kind"]: r["width"] * r["height"]
                            for f in design["floors"] for r in f["rooms"]}
            check("family_room_area_order",
                  family_areas["living"] > family_areas["kitchen"] > family_areas["bathroom"],
                  family_areas)
            report["actual_counts"]["initial_building"] = {
                "rooms": design["validation"].get("room_count"),
                "levels": design["levels"], "objects": sum(len(f["objects"]) for f in design["floors"]),
            }
            capture(page, "01-desktop-building.png")

            # Floors, keyboard navigation, zoom, pan, object selection and actions.
            floor_buttons = page.locator("#floors button[data-floor]")
            check("floor_controls_rendered", floor_buttons.count() == 2, floor_buttons.count())
            floor_buttons.nth(1).click()
            check("floor_button_changes_floor", page.evaluate("window.workshop.floor") == 1)
            page.locator("#canvas").focus()
            page.keyboard.press("PageDown")
            check("keyboard_floor_navigation", page.evaluate("window.workshop.floor") == 0)
            camera_before = page.evaluate("window.workshop.camera.unit")
            page.locator("#zoom-in").click()
            camera_zoomed = page.evaluate("window.workshop.camera.unit")
            check("zoom_control_changes_scale", camera_zoomed > camera_before,
                  {"before": camera_before, "after": camera_zoomed})
            page.locator("#fit").click()
            camera_before = page.evaluate("({x:window.workshop.camera.x,y:window.workshop.camera.y})")
            bounds = page.locator("#canvas").bounding_box()
            px, py = bounds["x"] + bounds["width"] * .5, bounds["y"] + bounds["height"] * .42
            page.mouse.move(px, py)
            page.mouse.down()
            page.mouse.move(px + 70, py + 35, steps=5)
            page.mouse.up()
            camera_after = page.evaluate("({x:window.workshop.camera.x,y:window.workshop.camera.y})")
            check("canvas_pan_changes_camera", camera_after != camera_before,
                  {"before": camera_before, "after": camera_after})
            page.locator("#fit").click()
            target = page.evaluate("""() => {
              const s=window.workshop, f=s.design.floors[s.floor], o=f.objects.find(x=>x.anchors?.length);
              const r=document.querySelector('#canvas').getBoundingClientRect();
              const ox=(s.width-s.design.width*s.camera.unit)/2+s.camera.x;
              const oy=(s.height-s.design.height*s.camera.unit)/2+s.camera.y;
              return {x:r.left+ox+(o.x+o.w/2)*s.camera.unit,
                      y:r.top+oy+(o.y+o.h/2)*s.camera.unit, id:o.id, name:o.name};
            }""")
            page.mouse.click(target["x"], target["y"])
            page.wait_for_selector("#inspector .object-card .pill")
            selected_name = page.locator("#inspector .object-card h3").inner_text()
            action_pills = page.locator("#inspector .object-card .pill").count()
            check("object_click_shows_actions", selected_name == target["name"] and action_pills > 0,
                  {"object_id": target["id"], "name": selected_name, "actions": action_pills})
            report["actual_counts"]["selected_object_actions"] = action_pills

            # Advance test residents without allowing invariant violations.
            actors_before = page.evaluate("window.workshop.demo.actors.length")
            step_counts = []
            for _ in range(4):
                clock_before = page.evaluate("window.workshop.demo.clock")
                page.locator("#step").click()
                page.wait_for_function(f"window.workshop.demo?.clock > {clock_before}", timeout=args.timeout)
                state = page.evaluate("""() => ({clock:window.workshop.demo.clock,
                  arrivals:window.workshop.demo.metrics.arrivals,
                  errors:window.workshop.demo.invariant_errors})""")
                check("npc_step_invariants", not state["errors"], state)
                step_counts.append(state)
            report["actual_counts"]["npc_actors"] = actors_before
            report["actual_counts"]["npc_steps"] = step_counts

            # An impossible brief must leave the previous valid drawing intact.
            previous = page.evaluate("window.workshop.design")
            page.locator("#b-width").fill("12")
            page.locator("#b-depth").fill("10")
            response_start = len(generation_responses)
            console_start = len(report["console_errors"])
            generate(page)
            page.wait_for_function("document.querySelector('#badge').classList.contains('bad')",
                                   timeout=args.timeout)
            still_same = page.evaluate("window.workshop.design")
            check("impossible_footprint_rejected",
                  "Auftrag nicht erfüllbar" in page.locator("#badge").inner_text(),
                  page.locator("#message").inner_text())
            rejected_responses = generation_responses[response_start:]
            check("impossible_footprint_returns_http_422",
                  any(x["status"] == 422 for x in rejected_responses), rejected_responses)
            new_console = report["console_errors"][console_start:]
            expected_console = [x for x in new_console if "422" in x]
            report["expected_http_errors"].append({"status": 422,
                "endpoint": "/api/generation/building",
                "console_messages": expected_console})
            report["console_errors"] = (report["console_errors"][:console_start] +
                                         [x for x in new_console if x not in expected_console])
            check("rejection_preserves_previous_design",
                  still_same["id"] == previous["id"] and still_same["validation"]["valid"],
                  {"previous": previous["id"], "current": still_same["id"]})
            capture(page, "02-rejected-brief-preserved.png")

            # Basement adds UG while preserving the requested six rooms.
            page.locator("#b-width").fill("25")
            page.locator("#b-depth").fill("21")
            page.locator("#b-basement").check()
            generate(page)
            page.wait_for_function("window.workshop.design?.levels === 3 && window.workshop.ready",
                                   timeout=args.timeout)
            basement = page.evaluate("window.workshop.design")
            elevations = [f["elevation"] for f in basement["floors"]]
            names = [page.locator(f"#floors button[data-floor='{f['level']}']").inner_text()
                     for f in basement["floors"]]
            check("basement_toggle_three_floors_elevations",
                  basement["validation"].get("room_count") == 6 and elevations == [-1, 0, 1],
                  {"rooms": basement["validation"].get("room_count"), "elevations": elevations,
                   "floor_labels": names})
            check("basement_floor_labels", len(names) == 3 and "UG" in names[0]
                  and "EG" in names[1] and "OG" in names[2], names)
            report["actual_counts"]["basement_building"] = {
                "rooms": basement["validation"].get("room_count"), "levels": basement["levels"],
                "elevations": elevations,
            }
            capture(page, "03-basement-building.png")

            # Exercise the three public building profiles through the form.
            preset_counts = {}
            for preset in ("school", "hospital", "fire_station"):
                page.locator("#building-template").select_option(preset)
                generate(page)
                preset_design = page.evaluate("window.workshop.design")
                expected_program = page.evaluate(
                    "preset => window.workshop.catalog.building_templates[preset].room_program", preset)
                check("preset_" + preset,
                      preset_design["validation"]["valid"] and preset_design["levels"] == 1
                      and preset_design["program"] == expected_program,
                      {"rooms": preset_design["validation"].get("room_count"),
                       "levels": preset_design["levels"], "program": preset_design.get("program"),
                       "expected_program": expected_program})
                preset_counts[preset] = {"rooms": preset_design["validation"].get("room_count"),
                                         "levels": preset_design["levels"]}
                if preset == "school":
                    classroom = next(r for f in preset_design["floors"] for r in f["rooms"]
                                     if r["kind"] == "school_classroom")
                    kinds = [o["kind"] for o in classroom["objects"]]
                    check("school_24_real_pupil_places",
                          classroom["capacity"]["students"] == 24
                          and kinds.count("school_student_desk") == 24
                          and kinds.count("school_student_chair") == 24
                          and preset_design["validation"]["student_capacity"] == 24,
                          classroom["capacity"])
                    capture(page, "04-school-24-seats.png")
            report["actual_counts"]["presets"] = preset_counts

            # Region generation, selecting a lot, finding a full route, opening it.
            page.locator("[data-tab='region']").click()
            ready(page)
            region = page.evaluate("window.workshop.design")
            plot = region["plots"][0]
            page.evaluate("window.workshop.selected = null")
            page.locator("#fit").click()
            click_plot = page.evaluate("""(id) => {
              const s=window.workshop,p=s.design.plots.find(x=>x.id===id),r=document.querySelector('#canvas').getBoundingClientRect();
              const ox=(s.width-s.design.width*s.camera.unit)/2+s.camera.x;
              const oy=(s.height-s.design.height*s.camera.unit)/2+s.camera.y;
              return {x:r.left+ox+(p.bounds[0]+p.bounds[2]/2)*s.camera.unit,
                      y:r.top+oy+(p.bounds[1]+p.bounds[3]/2)*s.camera.unit};
            }""", plot["id"])
            page.mouse.click(click_plot["x"], click_plot["y"])
            page.wait_for_selector("#open-building")
            check("region_plot_selection", page.locator("#open-building").is_visible(),
                  {"plots": len(region["plots"]), "plot_id": plot["id"]})
            page.locator("#region-route").click()
            page.wait_for_function("document.querySelector('#route-result')?.textContent.includes('Haustür')",
                                   timeout=args.timeout)
            route_text = page.locator("#route-result").inner_text()
            route_public_cells = page.evaluate("window.workshop.route.public_path.length")
            check("region_public_to_room_route", "öffentliche Wegzellen" in route_text, route_text)
            capture(page, "04-region-route-overview.png")
            page.locator("#open-building").click()
            page.wait_for_function("window.workshop.tab === 'building' && window.workshop.ready",
                                   timeout=args.timeout)
            opened = page.evaluate("window.workshop.design")
            check("region_open_building", opened["validation"]["valid"],
                  {"rooms": opened["validation"].get("room_count"), "levels": opened["levels"]})
            report["actual_counts"]["region"] = {
                "plots": len(region["plots"]), "route_public_cells": route_public_cells,
                "opened_rooms": opened["validation"].get("room_count"),
            }
            capture(page, "04-region-opened-building.png")

            # Offline factory demo; leave the job awaiting human visual review.
            page.locator("[data-tab='factory']").click()
            page.locator("#demo-run").click()
            page.wait_for_selector("#job-detail [data-preview]", timeout=args.timeout)
            jobs = page.request.get(report["base_url"] + "/api/workshop/jobs").json()
            jobs_enabled = jobs.get("external_enabled_in_web") is False
            job_id = page.evaluate("window.workshop.job")
            job = page.request.get(report["base_url"] + "/api/workshop/jobs/" + job_id).json()
            check("offline_demo_awaits_review", job["state"] == "awaiting_review",
                  {"state": job["state"], "provider": job["provider"], "model": job["model"]})
            check("offline_demo_valid_previews_and_logs",
                  bool(job["report"]["valid"] and job["report"]["previews"] and job["events"]),
                  {"valid": job["report"]["valid"], "previews": len(job["report"]["previews"]),
                   "events": len(job["events"]), "room_checks": job["report"]["room_checks"],
                   "building_checks": job["report"]["building_checks"]})
            check("browser_factory_external_calls_disabled", jobs_enabled, jobs)
            report["actual_counts"]["offline_job"] = {
                "state": job["state"], "previews": len(job["report"]["previews"]),
                "room_checks": job["report"]["room_checks"],
                "building_checks": job["report"]["building_checks"], "events": len(job["events"]),
            }
            capture(page, "05-factory-offline-review.png")

            publications_before = page.request.get(report["base_url"] + "/api/workshop/library").json().get("publications", [])
            publish_url = f"/api/workshop/jobs/{job_id}/publish"
            publish_requests = []
            page.on("request", lambda request: publish_requests.append(request.url)
                    if urlparse(request.url).path.endswith(publish_url) else None)
            check("publish_checkbox_starts_unchecked", not page.locator("#reviewed").is_checked())
            page.locator("#publish").click()
            page.wait_for_function("!document.querySelector('#message').hidden")
            state_after_unchecked_click = page.request.get(
                report["base_url"] + "/api/workshop/jobs/" + job_id).json()
            publications_after = page.request.get(report["base_url"] + "/api/workshop/library").json().get("publications", [])
            report["publication_attempts"] = len(publish_requests)
            check("unchecked_publish_is_not_sent", len(publish_requests) == 0, publish_requests)
            check("unchecked_publish_keeps_job_awaiting_review",
                  state_after_unchecked_click["state"] == "awaiting_review")
            check("unchecked_publish_keeps_library_unchanged",
                  [x.get("pack_id") for x in publications_after] == [x.get("pack_id") for x in publications_before])
            capture(page, "06-unchecked-publish-blocked.png")

            # A fresh page avoids carrying factory panel state into the
            # responsive building view after the UI clears old designs.
            responsive = context.new_page()
            responsive.set_viewport_size({"width": 390, "height": 844})
            responsive.set_default_timeout(args.timeout)
            responsive.on("request", requested)
            responsive.on("pageerror", lambda error: report["browser_errors"].append(str(error)))
            responsive.on("console", lambda msg: report["console_errors"].append(msg.text)
                          if msg.type == "error" else None)
            responsive.goto(report["base_url"] + "/workshop", wait_until="domcontentloaded")
            ready(responsive)
            responsive.wait_for_timeout(250)
            mobile_overflow = overflow_report(responsive)
            check("mobile_390_no_text_or_page_overflow",
                  not mobile_overflow["horizontalOverflow"] and not mobile_overflow["clippedTextCandidates"],
                  mobile_overflow)
            capture(responsive, "07-mobile-390.png")
            responsive.set_viewport_size({"width": 1600, "height": 1000})
            responsive.wait_for_timeout(250)
            desktop_overflow = overflow_report(responsive)
            check("desktop_1600_no_text_or_page_overflow",
                  not desktop_overflow["horizontalOverflow"] and not desktop_overflow["clippedTextCandidates"],
                  desktop_overflow)
            capture(responsive, "08-desktop-1600-final.png")
            responsive.close()

            docs_file = ROOT / "docs" / "agent_workshop.html"
            report["offline_docs"]["available"] = docs_file.exists()
            report["offline_docs"]["checked"] = docs_file.exists()
            if docs_file.exists():
                docs_page = context.new_page()
                docs_page.on("pageerror", lambda error: report["browser_errors"].append(str(error)))
                docs_response = docs_page.goto(report["base_url"] + "/agent-supplement",
                                               wait_until="domcontentloaded")
                check("offline_agent_gallery_served", docs_response is not None and docs_response.status == 200,
                      docs_response.status if docs_response else None)
                report["offline_docs"]["status"] = docs_response.status if docs_response else None
                capture(docs_page, "09-agent-gallery.png")
                docs_page.goto(docs_file.as_uri(), wait_until="domcontentloaded")
                docs_page.wait_for_selector("#building-choice option", state="attached")
                check("standalone_file_gallery_renders",
                      docs_page.locator("#building-choice option").count() == 5
                      and docs_page.evaluate("document.querySelector('#house-view').getContext('2d').getImageData(525,285,1,1).data[3] > 0"))
                docs_page.locator("#building-choice").select_option("1")
                docs_page.locator("[data-level='0']").click()
                check("standalone_file_basement_navigation", "Kellergeschoss" in docs_page.locator("#house-caption").inner_text())
                report["offline_docs"]["file_protocol_tested"] = True
                docs_page.close()

            check("no_external_network_requests", not report["external_requests"],
                  report["external_requests"])
            check("no_browser_runtime_errors", not report["browser_errors"], report["browser_errors"])
            check("no_unexpected_console_errors", not report["console_errors"], report["console_errors"])
            report["passed"] = True
            browser.close()
    except Exception as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")
        if "page" in locals():
            try:
                capture(page, "failure.png")
            except Exception:
                pass

    target = EVIDENCE / "browser-verification.json"
    target.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
