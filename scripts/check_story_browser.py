"""Review isolated story worlds on localhost:8768 or 8769 with Chromium."""

import argparse
import atexit
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "story"
URL = "http://127.0.0.1:8768"


def main():
    global OUT, URL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=URL)
    args = parser.parse_args()
    parsed = urlparse(args.url)
    if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port not in {8768, 8769}:
        parser.error("Review is restricted to isolated localhost ports 8768 and 8769")
    URL = args.url.rstrip("/")
    OUT = ROOT / "artifacts" / ("new_neighborhood" if parsed.port == 8769 else "story")
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"url": URL, "checks": {}, "page_errors": [], "console_errors": [],
              "failed_requests": [], "actor_requests": [], "actor_responses": [],
              "screenshots": [], "observations": {}, "completed": False}

    def save_report():
        (OUT / "inspector-browser-verification.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    atexit.register(save_report)
    original_excepthook = sys.excepthook

    def record_exception(error_type, error, trace):
        report["fatal_error"] = f"{error_type.__name__}: {error}"
        original_excepthook(error_type, error, trace)

    sys.excepthook = record_exception

    def check(name, result, detail=None):
        report["checks"][name] = {"passed": bool(result), "detail": detail}

    def capture(page, name):
        path = OUT / name
        page.screenshot(path=str(path), animations="disabled")
        report["screenshots"].append(str(path.relative_to(ROOT)).replace("\\", "/"))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        desktop = browser.new_page(viewport={"width": 1500, "height": 980}, device_scale_factor=1)
        for page in (desktop,):
            page.on("pageerror", lambda error: report["page_errors"].append(str(error)))
            page.on("console", lambda message: report["console_errors"].append(message.text)
                    if message.type == "error" else None)
        page.on("requestfailed", lambda request: report["failed_requests"].append(
                    {"url": request.url, "failure": request.failure}))
        page.on("request", lambda request: report["actor_requests"].append(request.url)
                if "/api/actors/" in request.url and len(report["actor_requests"]) < 80 else None)
        page.on("response", lambda response: report["actor_responses"].append(
                {"status": response.status, "url": response.url})
                if "/api/actors/" in response.url and len(report["actor_responses"]) < 80 else None)
        desktop.goto(URL, wait_until="domcontentloaded", timeout=30000)
        desktop.wait_for_function("window.mosswood?.ready && window.mosswood?.person", timeout=45000)
        world = desktop.evaluate("window.mosswood.renderer.world")
        plan = world.get("planning_metadata") or {}
        if parsed.port == 8769:
            check("new_map_metadata", plan.get("layout_id") == "neighborhood-v1"
                  and len(plan.get("roads", [])) >= 10 and len(plan.get("parks", [])) >= 2,
                  {"layout_id": plan.get("layout_id"), "roads": len(plan.get("roads", [])),
                   "parks": len(plan.get("parks", []))})
            check("new_map_dimensions", world.get("width") == 128 and world.get("height") == 180,
                  [world.get("width"), world.get("height")])
            desktop.evaluate("""() => {const r=window.mosswood.renderer;r.roofs='closed';r.fit();r.render(performance.now())}""")
            capture(desktop, "00-neighborhood-overview.png")
            family = next((h for h in world.get("households", []) if len(h.get("members", [])) >= 3), None)
            if family:
                home = next(b for b in world["buildings"] if b["id"] == family["building_id"])
                check("family_home_real_rooms", len(home.get("rooms", [])) >= 6
                      and any("child_room" in room for room in home.get("rooms", [])),
                      {"home": home["id"], "rooms": home.get("rooms")})
                desktop.evaluate("id => window.mosswood.configure({building_id:id,roofs:'open',zoom:1.25})",
                                 home["id"])
                capture(desktop, "00-family-home-interior.png")
            desktop.evaluate("""() => {const r=window.mosswood.renderer;r.focusHome('school');r.roofs='open';r.camera.zoom=1.15;r.render(performance.now())}""")
            capture(desktop, "00-school-interior.png")
            check("classroom_furniture_rendered", sum(o.get("kind") == "school_student_chair"
                  for o in world.get("objects", [])) >= 24
                  and sum(o.get("kind") in ("school_student_desk", "school_desk")
                          for o in world.get("objects", [])) >= 24)
            public_clicks = {}
            for building_id in ("school", "hospital", "supermarket"):
                before = desktop.evaluate("window.mosswood.renderer.selected")
                point = desktop.evaluate("""id => {const r=window.mosswood.renderer,
                  b=r.world.buildings.find(v=>v.id===id);r.roofs='closed';r.focusHome(id);
                  return r.screenAt((b.x+.5)*24,(b.y+.5)*24)}""", building_id)
                box = desktop.locator('#world').bounding_box()
                desktop.mouse.click(box['x'] + point['x'], box['y'] + point['y'])
                after = desktop.evaluate("""() => ({selected:window.mosswood.renderer.selected,
                  opened:window.mosswood.renderer.openBuilding})""")
                public_clicks[building_id] = before == after["selected"] and after["opened"] == building_id
            check("new_public_building_click_safe", all(public_clicks.values()), public_clicks)
            for building_id in ("hospital", "supermarket"):
                desktop.evaluate("id => window.mosswood.configure({building_id:id,roofs:'open',zoom:1.1})",
                                 building_id)
                capture(desktop, "00-" + building_id + "-interior.png")
            snapshot = desktop.evaluate("window.mosswood.state")
            object_by_id = {o["id"]: o for o in world["objects"]}
            meal_resource = next((r for r in snapshot.get("resources", [])
                                  if r.get("daily", {}).get("served_meals", 0) > 0
                                  or r.get("daily", {}).get("dirty_dishes", 0) > 0
                                  or r.get("daily", {}).get("oven_item_id")), None)
            check("real_food_object_state", meal_resource is not None,
                  meal_resource["id"] if meal_resource else None)
            if meal_resource and meal_resource["id"] in object_by_id:
                meal_object = object_by_id[meal_resource["id"]]
                desktop.evaluate("id => window.mosswood.configure({building_id:id,roofs:'open',zoom:2.2})",
                                 meal_object["building_id"])
                desktop.evaluate("""id => {const r=window.mosswood.renderer,
                  o=r.world.objects.find(v=>v.id===id);r.camera.x=(o.x+.5)*24-r.width*.16/r.camera.zoom;
                  r.camera.y=(o.y+.5)*24-r.height*.10/r.camera.zoom;
                  document.getElementById('hover-label').classList.add('hidden');r.render(performance.now())}""",
                                 meal_resource["id"])
                capture(desktop, "00-real-food-state.png")
            desktop.evaluate("""() => {const r=window.mosswood.renderer;r.overview();r.roofs='auto'}""")
        else:
            check("legacy_visual_fallback", not plan
                  and desktop.evaluate("window.mosswood.renderer.mapPlan === null"))
        chosen = desktop.evaluate("window.mosswood.person")
        if not chosen or not chosen.get("social_graph", {}).get("edges"):
            raise RuntimeError("The first inspected resident has no observable relationship graph")
        report["observations"]["chosen_actor"] = chosen["id"]
        report["observations"]["edge_count"] = len(chosen.get("social_graph", {}).get("edges", []))
        report["observations"]["item_count"] = len(chosen.get("belongings", []))
        if desktop.evaluate("window.mosswood.person?.id") != chosen["id"]:
            desktop.evaluate("id => window.mosswood.select(id)", chosen["id"])
            desktop.wait_for_function("id => window.mosswood.person?.id===id", arg=chosen["id"])
        capture(desktop, "01-portrait-overview.png")
        check("portrait_enlarged", desktop.locator("#portrait").evaluate("e => e.width >= 100"))
        check("compact_affect", desktop.locator('[data-story="affect"]').count() == 1)
        desktop.locator('[data-tab="mind"]').click()
        desktop.wait_for_selector('.narrative-pair')
        desktop.locator('.narrative-pair').evaluate("e => e.scrollIntoView({block:'center'})")
        capture(desktop, "02-affect-narratives.png")
        check("two_distinct_narratives", desktop.locator('.narrative-pair > div').count() == 2)
        desktop.locator('[data-tab="details"]').click()
        desktop.wait_for_selector('[data-story="possessions"]')
        capture(desktop, "03-possession-details.png")
        check("concrete_possessions", desktop.locator('.possession-row').count() > 0)
        desktop.locator('#people-toggle').click()
        desktop.wait_for_selector('.person-photo')
        capture(desktop, "04-people-portraits.png")
        check("people_have_portraits", desktop.locator('.person-photo').count() >= 20)
        desktop.locator('#people-toggle').click()
        desktop.evaluate("() => window.mosswood.configure({overlay:'relationships'})")
        desktop.wait_for_selector('#relationships-dialog[open]')
        capture(desktop, "05-relationship-graph.png")
        edges = desktop.locator('#relation-graph .relation-edge').count()
        check("graph_only_own_edges", edges == len(chosen['social_graph']['edges']),
              {"rendered": edges, "canonical": len(chosen['social_graph']['edges'])})
        check("graph_portraits", desktop.locator('#relation-graph image').count() >= edges)
        colors = desktop.locator('#relation-graph .relation-edge').evaluate_all(
            "els => [...new Set(els.map(el => el.getAttribute('stroke')))]")
        report["observations"]["edge_colors"] = colors
        check("relationship_layer_colors", len(colors) > 1, colors)
        types = desktop.locator('#relation-type option').all_text_contents()
        if len(types) > 1:
            desktop.locator('#relation-type').select_option(index=1)
            filtered = desktop.locator('#relation-graph .relation-edge').count()
            check("type_filter", filtered <= edges and filtered >= 1,
                  {"filtered": filtered, "total": edges, "type": types[1]})
            desktop.locator('#relation-type').select_option(index=0)
        desktop.keyboard.press('Escape')
        check("escape_closes_dialog", not desktop.locator('#relationships-dialog').evaluate('e => e.open'))
        desktop.evaluate("() => window.mosswood.configure({overlay:'relationships'})")
        desktop.wait_for_selector('#relationships-dialog[open]')
        desktop.locator('#relation-search').fill('unlikely-no-match-zz')
        check("name_filter_empty", desktop.locator('#relation-graph .relation-edge').count() == 0)
        capture(desktop, "06-relationship-filter.png")
        desktop.locator('#relation-search').fill('')
        target = desktop.locator('#relation-graph .relation-node').first.get_attribute(
            'data-graph-person') if edges else None
        if target:
            request_start = len(report["actor_requests"])
            response_start = len(report["actor_responses"])
            desktop.locator('#relation-graph .relation-node').first.click()
            check("graph_node_selects_person", desktop.evaluate(
                "id => window.mosswood.renderer.selected === id", target))
            check("graph_click_closes_dialog", not desktop.locator(
                '#relationships-dialog').evaluate('e => e.open'))
            desktop.wait_for_timeout(2500)
            report["observations"]["graph_click_network"] = {
                "requests": report["actor_requests"][request_start:],
                "responses": report["actor_responses"][response_start:]}
            check("inspector_after_graph_click", desktop.evaluate(
                "id => window.mosswood.person?.id === id", target),
                {"target": target, "person": desktop.evaluate("window.mosswood.person?.id"),
                 "network": report["observations"]["graph_click_network"]})
        else:
            desktop.locator('.relation-close').click()

        mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        mobile.on("pageerror", lambda error: report["page_errors"].append(str(error)))
        mobile.on("console", lambda message: report["console_errors"].append(message.text)
                  if message.type == "error" else None)
        mobile.goto(URL, wait_until="domcontentloaded", timeout=30000)
        mobile.wait_for_function("window.mosswood?.ready && window.mosswood?.person", timeout=45000)
        if mobile.evaluate("window.mosswood.person?.id") != chosen["id"]:
            mobile.evaluate("id => window.mosswood.select(id)", chosen["id"])
            mobile.wait_for_function("id => window.mosswood.person?.id===id", arg=chosen["id"])
        mobile.locator('[data-tab="details"]').click()
        mobile.wait_for_selector('[data-story="possessions"]')
        capture(mobile, "07-mobile-portrait-possession.png")
        mobile.evaluate("() => window.mosswood.configure({overlay:'relationships'})")
        mobile.wait_for_selector('#relationships-dialog[open]')
        capture(mobile, "08-mobile-relationship-dialog.png")
        widths = mobile.evaluate("""() => ({document:document.documentElement.scrollWidth,
          viewport:innerWidth, dialog:document.querySelector('#relationships-dialog').scrollWidth,
          dialogClient:document.querySelector('#relationships-dialog').clientWidth})""")
        report["observations"]["mobile_widths"] = widths
        check("mobile_no_horizontal_overflow", widths["document"] <= widths["viewport"] + 1
              and widths["dialog"] <= widths["dialogClient"] + 1, widths)
        mobile.locator('.relation-close').click()
        check("mobile_dialog_close", not mobile.locator('#relationships-dialog').evaluate('e => e.open'))
        check("no_browser_errors", not report["page_errors"] and not report["console_errors"]
              and not report["failed_requests"], {"page": report["page_errors"],
                                               "console": report["console_errors"],
                                               "requests": report["failed_requests"]})
        browser.close()
    report["completed"] = True
    save_report()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
