"""Real-browser city lab check on an isolated, short-lived API server."""
import json
from pathlib import Path
from threading import Thread
import time

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from playwright.sync_api import sync_playwright
import uvicorn

from living_world.generation.city_api import create_city_router

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "story"
PORT = 8784


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    app = FastAPI()
    app.include_router(create_city_router())
    app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="error"))
    thread = Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(.1)
    if not server.started:
        raise RuntimeError("Isolated city server did not start")
    errors = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1600, "height": 1080})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{PORT}/city", wait_until="domcontentloaded")
            page.wait_for_function("window.cityLab?.city?.validation?.valid", timeout=120000)
            city = page.evaluate("window.cityLab.city")
            assert len(city["validation"]["services"]) == 9
            assert city["validation"]["connected_entrances"] == len(city["plots"])
            assert not errors, errors
            page.screenshot(path=str(OUT / "city-overview.png"), full_page=True)
            school = next(plot for plot in city["plots"] if plot["service"] == "school")
            rect = page.locator("#city-canvas").bounding_box()
            target = page.evaluate("plot => {const s=window.cityLab;return {x:s.x+(plot.bounds[0]+plot.bounds[2]/2)*s.unit,y:s.y+(plot.bounds[1]+plot.bounds[3]/2)*s.unit}}", school)
            page.mouse.click(rect["x"] + target["x"], rect["y"] + target["y"])
            page.wait_for_selector("#target-room")
            assert "24" in page.locator("#inspector").inner_text()
            page.locator("#route").click()
            page.wait_for_function("window.cityLab.route?.valid", timeout=30000)
            route = page.evaluate("window.cityLab.route")
            assert route["public_path"][-1] == school["door"]
            page.screenshot(path=str(OUT / "city-school-route.png"), full_page=True)
            result = {"passed": True, "city_version": city["city_version"],
                      "services": city["validation"]["services"],
                      "buildings": city["validation"]["buildings"],
                      "jobs": city["validation"]["jobs"],
                      "public_route_steps": len(route["public_path"])-1,
                      "browser_errors": errors,
                      "screenshots": ["city-overview.png", "city-school-route.png"]}
            (OUT / "city-browser-verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result, indent=2))
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)


if __name__ == "__main__":
    main()
