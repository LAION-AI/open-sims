"""Check the isolated everyday-life UI in a real Chromium browser.

Start a separate world first:
  python run.py --port 8767 --database data/life-review.sqlite3 --no-browser
Then run:
  python scripts/check_life_browser.py --url http://127.0.0.1:8767

Only the supplied test server is paused and advanced. The normal 8765 server
and its database are never contacted.
"""

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "life_systems"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8767")
    args = parser.parse_args()
    url = args.url.rstrip("/")
    parsed = urlparse(url)
    if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port != 8767:
        parser.error("This review script only accepts the isolated local port 8767")
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"url": url, "checks": {}, "issues": [], "page_errors": [],
              "console_errors": [], "failed_requests": [], "screenshots": [],
              "observations": {}}

    def check(name, condition, detail=None):
        report["checks"][name] = {"passed": bool(condition), "detail": detail}
        if not condition:
            report["issues"].append(f"{name}: {detail}")

    def capture(page, filename):
        path = OUT / filename
        page.screenshot(path=str(path), animations="disabled")
        report["screenshots"].append(str(path.relative_to(ROOT)).replace("\\", "/"))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 980},
                                device_scale_factor=1)
        page.on("pageerror", lambda error: report["page_errors"].append(str(error)))
        page.on("console", lambda message: report["console_errors"].append(message.text)
                if message.type == "error" else None)
        page.on("requestfailed", lambda request: report["failed_requests"].append(
            {"url": request.url, "failure": request.failure}))
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_function("window.mosswood?.ready && window.mosswood?.person", timeout=45000)
            paused = page.request.post(url + "/api/control", data={"paused": True})
            check("test_world_paused", paused.ok and paused.json()["paused"], paused.status)

            world = page.request.get(url + "/api/world").json()
            buildings = {b["id"]: b for b in world["buildings"]}
            check("workplace_buildings_present",
                  all(key in buildings for key in ("school", "studio", "workshop")),
                  {key: buildings.get(key, {}).get("name") for key in ("school", "studio", "workshop")})
            check("southern_buildings_in_new_strip",
                  all(buildings[key]["y"] >= 118 for key in ("school", "studio", "workshop")),
                  {key: buildings[key]["y"] for key in ("school", "studio", "workshop")})
            state = page.request.get(url + "/api/state").json()
            check("dog_in_snapshot", any(a.get("name") == "Pippin"
                 for a in state.get("animals", [])), state.get("animals"))
            report["observations"]["initial_clock"] = state["clock"]

            # Frame the southern civic strip while keeping the real inspector visible.
            page.evaluate("""() => {
              const r = window.mosswood.renderer;
              r.follow = false; r.roofs = 'closed';
              r.camera.x = 64 * 24; r.camera.y = 136 * 24; r.camera.zoom = .42;
              r.render(performance.now());
            }""")
            page.wait_for_timeout(200)
            capture(page, "01-southern-workplaces.png")
            check("all_workplaces_on_screen", page.evaluate("""() => {
              const r=window.mosswood.renderer;
              return ['school','studio','workshop'].every(id=>{
                const b=r.world.buildings.find(v=>v.id===id),
                  s=r.screenAt((b.x+b.w/2)*24,(b.y+b.h/2)*24);
                return s.x>0&&s.x<r.width&&s.y>0&&s.y<r.height;
              });
            }"""))

            # Clicking a civic building must not invoke the home selection path.
            click_point = page.evaluate("""() => {
              const r=window.mosswood.renderer,b=r.world.buildings.find(v=>v.id==='school');
              return r.screenAt((b.x+b.w/2)*24,(b.y+7)*24);
            }""")
            canvas_box = page.locator("#world").bounding_box()
            before = page.evaluate("window.mosswood.renderer.selected")
            page.mouse.click(canvas_box["x"] + click_point["x"],
                             canvas_box["y"] + click_point["y"])
            public_click = page.evaluate("""() => ({
              after: window.mosswood.renderer.selected,
              opened: window.mosswood.renderer.openBuilding})""")
            public_click["before"] = before
            check("public_building_click_safe",
                  public_click["before"] == public_click["after"]
                  and public_click["opened"] == "school", public_click)

            # World time advances only in the disposable test world.
            for _ in range(3):
                stepped = page.request.post(url + "/api/control", data={"step_seconds": 1800})
                check("test_world_step", stepped.ok, stepped.status)
                if not stepped.ok:
                    break
            state = page.request.get(url + "/api/state").json()
            report["observations"]["advanced_clock"] = state["clock"]
            report["observations"]["daily_resource_count"] = sum(
                bool(item.get("daily")) for item in state.get("resources", []))
            check("everyday_state_in_snapshot",
                  report["observations"]["daily_resource_count"] > 0,
                  report["observations"]["daily_resource_count"])

            chosen = None
            for actor in state["actors"]:
                candidate = page.request.get(url + "/api/actors/" + actor["id"]).json()
                if candidate.get("planned_steps"):
                    chosen = candidate
                    if candidate.get("routine", {}).get("kind") == "meal":
                        break
            check("resident_has_visible_routine", chosen is not None,
                  chosen["id"] if chosen else None)
            if chosen:
                page.evaluate("id => window.mosswood.select(id)", chosen["id"])
                page.wait_for_function("id => window.mosswood.person?.id === id", arg=chosen["id"])
                page.locator('[data-tab="overview"]').click()
                page.wait_for_selector('[data-life="routine"]')
                page.locator('[data-life="routine"]').evaluate(
                    "element => element.scrollIntoView({block:'start'})")
                capture(page, "02-routine.png")
                check("routine_has_named_steps",
                      page.locator('[data-life="routine"] li').count() > 0,
                      page.locator('[data-life="routine"] li').count())

                page.locator('[data-tab="mind"]').click()
                page.wait_for_selector('[data-life="personality"]')
                sections = ["personality", "ambitions", "fears", "tom", "relationships"]
                check("psychology_sections_present",
                      all(page.locator(f'[data-life="{name}"]').count() == 1 for name in sections),
                      {name: page.locator(f'[data-life="{name}"]').count() for name in sections})
                capture(page, "03-psychology-personality.png")
                page.locator('[data-life="tom"]').scroll_into_view_if_needed()
                capture(page, "04-psychology-tom.png")
                page.locator('[data-life="relationships"]').evaluate(
                    "element => element.scrollIntoView({block:'start'})")
                capture(page, "05-relationships.png")

                page.locator('[data-tab="details"]').click()
                page.wait_for_selector('[data-life="household"]')
                page.locator('[data-life="household"]').locator('details').evaluate_all(
                    "elements => elements.forEach(element => element.open = true)")
                page.locator('[data-life="household"]').evaluate(
                    "element => element.scrollIntoView({block:'start'})")
                capture(page, "06-household-objects.png")
                check("household_objects_visible",
                      page.locator('[data-life="household"] details').count() >= 5,
                      page.locator('[data-life="household"] details').count())
                check("household_daily_values_visible",
                      "Pantry stock" in page.locator('[data-life="household"]').inner_text()
                      and "Dirty dishes" in page.locator('[data-life="household"]').inner_text())
                check("workplace_details_visible",
                      "Arbeitsplatz" in page.locator('#inspector-content').inner_text())

            # Real household effects are visible on furniture with roofs open.
            objects = {item["id"]: item for item in world["objects"]}
            tables = [(item, objects[item["id"]]) for item in state.get("resources", [])
                      if item["id"] in objects and objects[item["id"]]["kind"] == "table"
                      and objects[item["id"]].get("household_id")]
            def nearest_resident_distance(obj):
                return min(abs(actor["position"][0] - obj["x"])
                           + abs(actor["position"][1] - obj["y"])
                           for actor in state["actors"])
            tables.sort(key=lambda pair: (
                pair[0].get("daily", {}).get("dirty_dishes", 0)
                + pair[0].get("daily", {}).get("served_meals", 0),
                nearest_resident_distance(pair[1])), reverse=True)
            if tables:
                table_state, table_object = tables[0]
                household = table_object["household_id"]
                resident = next(actor for actor in state["actors"]
                                if actor["household_id"] == household)
                report["observations"]["home_visual_target"] = {
                    "resident": resident["id"], "household": household,
                    "table": table_object["id"], "daily": table_state.get("daily", {})}
                page.evaluate("""async id => {
                  await window.mosswood.configure({actor_id:id,view:'home',roofs:'open',zoom:1.4,tab:'overview'});
                  window.mosswood.renderer.render(performance.now());
                }""", resident["id"])
                capture(page, "09-home-dishes-and-mess.png")
                check("home_interior_has_real_meal_evidence",
                      table_state.get("daily", {}).get("dirty_dishes", 0)
                      + table_state.get("daily", {}).get("served_meals", 0) > 0,
                      report["observations"]["home_visual_target"])
                check("home_roof_open", page.evaluate(
                    "window.mosswood.renderer.roofs === 'open'"))
            else:
                check("home_interior_has_real_meal_evidence", False, "No home table resource")

            served_table = next((pair for pair in tables
                                 if pair[0].get("daily", {}).get("served_meals", 0) > 0), None)
            if served_table:
                item, obj = served_table
                report["observations"]["served_table"] = {
                    "id": obj["id"], "daily": item["daily"]}
                page.evaluate("""([x,y]) => {
                  const r=window.mosswood.renderer;
                  r.follow=false; r.roofs='open';
                  r.camera.x=(x+.5)*24; r.camera.y=(y+.5)*24;
                  r.camera.zoom=2.4; r.render(performance.now());
                }""", [obj["x"], obj["y"]])
                capture(page, "09a-served-table-closeup.png")

            messy_counter = next(((item, objects[item["id"]])
                for item in state.get("resources", []) if item["id"] in objects
                and objects[item["id"]]["kind"] == "counter"
                and item.get("daily", {}).get("mess", 0) > 0), None)
            if messy_counter:
                item, obj = messy_counter
                report["observations"]["messy_counter"] = {
                    "id": obj["id"], "daily": item["daily"]}
                page.evaluate("""([x,y]) => {
                  const r=window.mosswood.renderer;
                  r.follow=false; r.roofs='open';
                  r.camera.x=(x+1)*24; r.camera.y=(y+.5)*24;
                  r.camera.zoom=2.4; r.render(performance.now());
                }""", [obj["x"], obj["y"]])
                capture(page, "09b-messy-counter-closeup.png")

            dirty_tables = [(item, objects[item["id"]])
                for item in state.get("resources", []) if item["id"] in objects
                and objects[item["id"]]["kind"] == "table"
                and item.get("daily", {}).get("dirty_dishes", 0) > 0]
            if dirty_tables:
                item, obj = max(dirty_tables, key=lambda pair:
                                nearest_resident_distance(pair[1]))
                report["observations"]["dirty_table"] = {
                    "id": obj["id"], "daily": item["daily"]}
                page.evaluate("""([x,y]) => {
                  const r=window.mosswood.renderer;
                  r.follow=false; r.roofs='open';
                  r.camera.x=(x+.5)*24; r.camera.y=(y+.5)*24;
                  r.camera.zoom=2.4; r.render(performance.now());
                }""", [obj["x"], obj["y"]])
                capture(page, "09c-dirty-table-closeup.png")

            for building_id, zoom in (("school", .78), ("studio", .95), ("workshop", .78)):
                page.evaluate("""([id, zoom]) => {
                  const r=window.mosswood.renderer;
                  r.focusHome(id); r.roofs='open'; r.camera.zoom=zoom;
                  r.render(performance.now());
                }""", [building_id, zoom])
                capture(page, f"10-{building_id}-interior.png")
                check(f"{building_id}_interior_open", page.evaluate(
                    "id => !window.mosswood.renderer.roofVisible(window.mosswood.renderer.world.buildings.find(b=>b.id===id))",
                    building_id))

            carrier = next((actor for actor in state["actors"] if actor.get("carried")), None)
            if carrier:
                report["observations"]["carrier"] = {"id": carrier["id"],
                    "carried": carrier["carried"]}
                page.evaluate("""async id => {
                  await window.mosswood.configure({actor_id:id,view:'follow',roofs:'open',zoom:1.8});
                }""", carrier["id"])
                capture(page, "11-resident-carrying-item.png")
                check("carried_inventory_projection_present", bool(carrier["carried"]),
                      report["observations"]["carrier"])
            else:
                check("carried_inventory_projection_present", False,
                      "No resident carrying food or dishes at review time")

            page.evaluate("""() => {
              const r=window.mosswood.renderer,d=window.mosswood.state.animals[0];
              r.follow=false; r.roofs='open';
              r.camera.x=d.position[0]*24; r.camera.y=d.position[1]*24;
              r.camera.zoom=1.45; r.render(performance.now());
            }""")
            capture(page, "12-pippin-in-park.png")

            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(250)
            mobile = page.evaluate("""() => ({viewport: innerWidth,
              documentWidth: document.documentElement.scrollWidth,
              bodyWidth: document.body.scrollWidth,
              canvasWidth: document.querySelector('#world').getBoundingClientRect().width,
              inspectorWidth: document.querySelector('.inspector').getBoundingClientRect().width})""")
            report["observations"]["mobile"] = mobile
            check("mobile_no_document_overflow",
                  mobile["documentWidth"] <= mobile["viewport"] + 1, mobile)
            capture(page, "07-mobile-390.png")
            page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
            page.wait_for_timeout(150)
            mobile_scroll = page.evaluate("""() => ({scrollY: window.scrollY,
              maxScroll: document.documentElement.scrollHeight - innerHeight,
              inspectorBottom: document.querySelector('.inspector').getBoundingClientRect().bottom})""")
            report["observations"]["mobile_scroll"] = mobile_scroll
            check("mobile_inspector_reachable", mobile_scroll["scrollY"] > 0
                  and mobile_scroll["inspectorBottom"] <= 844 + 2, mobile_scroll)
            capture(page, "08-mobile-inspector.png")
            check("no_browser_page_errors", not report["page_errors"], report["page_errors"])
            check("no_console_errors", not report["console_errors"], report["console_errors"])
            check("no_failed_requests", not report["failed_requests"], report["failed_requests"])
        finally:
            browser.close()

    report["passed"] = all(item["passed"] for item in report["checks"].values())
    target = OUT / "browser-report.json"
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
