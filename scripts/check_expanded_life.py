"""Isolated browser review of relationships and advisory controls."""
import json
from pathlib import Path
import socket
import sys
import threading
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import uvicorn
from playwright.sync_api import sync_playwright
from living_world.server import create_app


def main():
    output = ROOT / 'artifacts' / 'expanded_life'
    output.mkdir(parents=True, exist_ok=True)
    report = {'database': ':memory:', 'live_save_touched': False, 'checks': {}, 'errors': []}
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    server = uvicorn.Server(uvicorn.Config(
        create_app(':memory:', seed=73, port=port, layout='neighborhood-v1', paused=True),
        log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 25
        while not server.started:
            if time.monotonic() > deadline:
                raise RuntimeError('Browser test server did not start')
            time.sleep(.1)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1500, 'height': 980})
            page.set_default_timeout(15000)
            page.on('pageerror', lambda error: report['errors'].append(str(error)))
            page.goto(base, wait_until='domcontentloaded')
            page.wait_for_function('window.mosswood?.ready')
            page.evaluate("async()=>await window.mosswood.configure({view:'home',roofs:'open',zoom:1.4})")
            page.screenshot(path=str(output / 'furnished-home.png'))
            page.locator('[data-tab="mind"]').click()
            page.wait_for_selector('[data-life="career"]')
            report['checks']['career_visible'] = page.locator('[data-life="career"]').count() == 1
            page.locator('[data-tab="overview"]').click()
            page.wait_for_selector('[data-recommend-action]')
            report['checks']['recommendation_options'] = page.locator('[data-recommend-action]').count() >= 2
            page.locator('[data-recommend-action]').first.click()
            page.wait_for_selector('[data-cancel-recommendation]')
            report['checks']['recommendation_pending'] = page.evaluate(
                "async()=>{const p=await (await fetch('/api/actors/resident_001')).json();return p.player_recommendation?.status==='pending'}")
            page.locator('[data-cancel-recommendation]').click()
            page.wait_for_function("async()=>{const p=await (await fetch('/api/actors/resident_001')).json();return p.player_recommendation?.status==='cancelled'}")
            report['checks']['recommendation_cancelled'] = True
            page.locator('#open-relationships').click()
            page.wait_for_selector('#relationships-dialog[open] .relation-list-row')
            modal = page.locator('#relationships-dialog')
            report['checks']['spouse_role'] = modal.get_by_text('Ehepartner:in', exact=False).count() >= 1
            report['checks']['bidirectional_feeling'] = modal.locator('.relation-feelings').count() >= 1
            report['checks']['private_mind_not_shown'] = page.evaluate(
                "async()=>{const p=await (await fetch('/api/actors/resident_001')).json();return p.social_graph.edges.every(e=>!('affect' in (e.reciprocal||{}))&&!('thought' in (e.reciprocal||{})))}")
            page.screenshot(path=str(output / 'relationships-desktop.png'))
            modal.locator('#relation-search').fill('Nora')
            report['checks']['search_filters'] = 'von' in modal.locator('#relation-count').inner_text()
            modal.locator('#relation-search').fill('')
            page.set_viewport_size({'width': 390, 'height': 844})
            page.screenshot(path=str(output / 'relationships-mobile.png'))
            widths = page.evaluate('({page:document.documentElement.scrollWidth,viewport:innerWidth,dialog:document.querySelector("#relationships-dialog").getBoundingClientRect().width})')
            report['mobile_widths'] = widths
            report['checks']['mobile_fits'] = widths['page'] <= widths['viewport'] and widths['dialog'] <= widths['viewport']
            modal.locator('.relation-close').click()
            page.evaluate("async()=>await window.mosswood.select('resident_012')")
            page.locator('#open-relationships').click()
            report['checks']['friend_role'] = page.locator('#relationships-dialog').get_by_text('Freund:in', exact=False).count() >= 1
            page.locator('.relation-close').click()
            page.goto(base + '/expanded-life')
            report['checks']['supplement_available'] = 'Alltags- und Beziehungsausbau' in page.title()
            with urlopen(base + '/api/plausibility') as response:
                audit = json.load(response)
            report['checks']['audit_has_storage'] = audit['object_kinds']['wardrobe'] == 20
            browser.close()
    except Exception as error:
        report['errors'].append(f'{type(error).__name__}: {error}')
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        listener.close()
    report['passed'] = bool(report['checks']) and all(report['checks'].values()) and not report['errors']
    (output / 'browser.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
