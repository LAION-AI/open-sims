"""Visual smoke check for the local social storyteller UI on port 8772.

Use a separate paused, disposable save. Never supply a real credential here.
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts' / 'social_storyteller_20261001'
URL = 'http://127.0.0.1:8772'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'url': URL, 'checks': {}, 'errors': [], 'screenshots': []}

    def check(name, value):
        report['checks'][name] = bool(value)

    def capture(page, name):
        path = OUT / name
        page.screenshot(path=str(path), animations='disabled')
        report['screenshots'].append(str(path.relative_to(ROOT)).replace('\\', '/'))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1500, 'height': 980})
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        page.goto(URL, wait_until='domcontentloaded')
        page.wait_for_function('window.mosswood?.ready && window.mosswood?.person')
        check('paused', page.evaluate('window.mosswood.state.paused'))
        page.locator('#settings-toggle').click()
        page.wait_for_selector('#settings-dialog[open]')
        capture(page, '01-settings-desktop.png')
        synthetic = 'synthetic-browser-check-not-a-credential'
        page.locator('#openrouter-key').fill(synthetic)
        page.locator('#openrouter-key-form button[type=submit]').click()
        page.wait_for_function("document.querySelector('#openrouter-status').textContent.includes('gesetzt')")
        check('key_input_cleared', page.locator('#openrouter-key').input_value() == '')
        check('provider_configured', page.request.get(URL+'/api/decision-providers').json()['configured'])
        check('key_not_in_browser_storage', page.evaluate("!JSON.stringify({...localStorage,...sessionStorage}).includes('synthetic-browser-check')"))
        check('no_key_in_state', synthetic not in page.request.get(URL+'/api/state').text())
        capture(page, '02-settings-connected.png')
        page.locator('#settings-close').click()
        page.locator('[data-tab="mind"]').click()
        page.wait_for_selector('[data-life="social-style"]')
        check('social_style_visible', 'Mitgefühl' in page.locator('[data-life="social-style"]').inner_text())
        page.locator('[data-life="social-style"]').scroll_into_view_if_needed()
        capture(page, '03-social-inspector.png')
        page.locator('#settings-toggle').click()
        page.set_viewport_size({'width': 390, 'height': 844})
        capture(page, '04-settings-mobile.png')
        widths = page.evaluate("({page:document.documentElement.scrollWidth,viewport:innerWidth,dialog:document.querySelector('#settings-dialog').getBoundingClientRect().width})")
        check('mobile_dialog_fits', widths['page'] <= widths['viewport'] and widths['dialog'] <= widths['viewport'])
        report['mobile_widths'] = widths
        page.locator('#openrouter-forget').click()
        page.wait_for_function("document.querySelector('#openrouter-status').textContent.includes('gelöscht')")
        check('key_forgotten', not page.request.get(URL+'/api/decision-providers').json()['configured'])
        browser.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['errors'] or not all(report['checks'].values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
