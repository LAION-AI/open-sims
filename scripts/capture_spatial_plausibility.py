"""Capture the family and classroom workshop views using only the generation API."""
from pathlib import Path
from threading import Thread
import time

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from playwright.sync_api import sync_playwright
import uvicorn

from living_world.generation.api import create_generation_router

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "spatial_plausibility"
PORT = 8766


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    app = FastAPI()
    app.include_router(create_generation_router())
    app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")

    @app.get("/workshop")
    def workshop():
        return FileResponse(ROOT / "web" / "workshop.html")

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="error"))
    thread = Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(.1)
    if not server.started:
        raise RuntimeError("Isolated generation server did not start")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1600, "height": 1000})
            page.goto(f"http://127.0.0.1:{PORT}/workshop", wait_until="domcontentloaded")
            page.wait_for_function("window.workshop?.ready && window.workshop.design")
            family = page.evaluate("window.workshop.design")
            assert (family["width"], family["height"], family["validation"]["room_count"]) == (18, 19, 6)
            page.screenshot(path=str(OUT / "family-default.png"), full_page=True)
            page.locator("#building-template").select_option("school")
            page.locator("#generate").click()
            page.wait_for_function("window.workshop?.ready && window.workshop.design.validation.student_capacity === 24")
            school = page.evaluate("window.workshop.design")
            classroom = next(room for floor in school["floors"] for room in floor["rooms"]
                             if room["kind"] == "school_classroom")
            assert classroom["capacity"]["students"] == 24
            page.screenshot(path=str(OUT / "school-24-seats.png"), full_page=True)
            browser.close()
            print(f"Captured {OUT / 'family-default.png'} and {OUT / 'school-24-seats.png'}")
    finally:
        server.should_exit = True
        thread.join(timeout=10)


if __name__ == "__main__":
    main()
