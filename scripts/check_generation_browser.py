"""Real-browser regression and screenshot evidence for the isolated atelier."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    args = parser.parse_args()
    out = ROOT / 'artifacts' / 'generation'
    out.mkdir(exist_ok=True, parents=True)
    checks, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1600,'height':1050}, device_scale_factor=1)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(args.url + '/atelier', wait_until='networkidle')
        page.wait_for_function('window.atelier?.ready && !atelier.busy')
        catalog = page.evaluate('atelier.catalog')
        assert len(catalog['rooms']) == 32
        assert len(catalog['objects']) == 116
        assert f"{len(catalog['rooms'])} Raumtypen" in page.locator('.catalog-summary').inner_text()
        assert page.locator('.variant').count() == 4
        assert page.locator('#valid-badge').inner_text() == '✓ Regeln erfüllt'
        page.screenshot(path=str(out/'01-living-room.png'))
        checks.append('Initial room, validation badge, four generated variants')
        hit = page.evaluate('''() => {
            const s=atelier,d=s.design,o=d.objects.find(o=>o.kind==='sofa'),u=s.camera.unit;
            return {x:(s.width-d.width*u)/2+s.camera.x+(o.x+o.w/2)*u,
                    y:(s.height-d.height*u)/2+s.camera.y+(o.y+o.h/2)*u};
        }''')
        box = page.locator('#design-canvas').bounding_box()
        page.mouse.click(box['x']+hit['x'],box['y']+hit['y'])
        assert 'Dreisitziges Sofa' in page.locator('#object-inspector').inner_text()
        assert '3 × 1 m' in page.locator('#object-inspector').inner_text() or '1 × 3 m' in page.locator('#object-inspector').inner_text()
        page.screenshot(path=str(out/'02-object-contract.png'))
        unit = page.evaluate('atelier.camera.unit')
        page.locator('#zoom-in').click()
        assert page.evaluate('atelier.camera.unit') > unit
        before = page.evaluate('atelier.camera.x')
        page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2)
        page.mouse.down();page.mouse.move(box['x']+box['width']/2+60,box['y']+box['height']/2+20,steps=5);page.mouse.up()
        assert page.evaluate('atelier.camera.x') != before
        page.locator('#fit').click()
        checks.append('Furniture hit testing, footprint inspector, zoom and pan')
        page.locator('.variant').nth(2).click()
        assert page.evaluate('atelier.design.seed') == 76
        with page.expect_download() as download:
            page.locator('#export-design').click()
        download.value.save_as(str(out/'example-room.json'))
        assert json.loads((out/'example-room.json').read_text())['seed'] == 76
        checks.append('Variant selection and JSON export')
        for kind in [k for k in catalog['rooms'] if k != 'living'] + ['living']:
            page.locator('#room-kind').select_option(kind)
            page.wait_for_function('(kind) => atelier.ready && !atelier.busy && atelier.design.kind===kind',arg=kind)
            assert page.evaluate('atelier.design.validation.valid')
            assert page.locator('.furniture-cards article').count() > 0
            if kind in ('music','gym','nursery','gaming','workshop','conservatory'):
                page.locator('.furniture-library summary').click()
                page.screenshot(path=str(out/f'catalog-{kind}.png'))
        checks.append(f"All {len(catalog['rooms'])} room types generate through the UI, with room-specific furniture previews")
        page.locator('#seed').fill('42')
        page.locator('[data-mode="house"]').click()
        page.wait_for_function('atelier.ready && !atelier.busy && atelier.mode==="house"')
        page.locator('#overlay').uncheck()
        page.locator('#room-labels').check()
        assert page.locator('#floor-controls button').count() == 3
        page.screenshot(path=str(out/'03-house-ground-floor.png'))
        page.locator('#floor-controls button').nth(1).click()
        assert page.evaluate('atelier.floor') == 1
        page.screenshot(path=str(out/'04-house-upper-floor.png'))
        page.locator('#design-canvas').focus()
        page.keyboard.press('PageUp');assert page.evaluate('atelier.floor') == 2
        page.keyboard.press('PageDown');assert page.evaluate('atelier.floor') == 1
        page.locator('#floor-controls button').nth(0).click()
        checks.append('Three-floor house, floor buttons and keyboard switching')
        page.locator('#demo-step').click()
        page.wait_for_function('atelier.demo.clock===10 && !atelier.advancing')
        page.locator('#demo-play').click()
        page.wait_for_function('atelier.demo.clock>=13')
        page.locator('#demo-play').click()
        page.wait_for_function('!atelier.advancing')
        saw_portal = False
        for _ in range(100):
            snapshot = page.evaluate('async () => {await atelier.advance(1);return atelier.demo}')
            in_portal = [a for a in snapshot['actors'] if a['ride']]
            if in_portal:
                saw_portal = True
                assert all(a['position'] is None for a in in_portal)
                assert snapshot['invariant_errors'] == []
                page.screenshot(path=str(out/'05-portal-in-progress.png'))
                break
        assert saw_portal
        page.evaluate('async () => {await atelier.advance(600)}')
        snap = page.evaluate('atelier.demo')
        assert snap['metrics']['stairs_trips'] > 0 and snap['metrics']['elevator_trips'] > 0
        assert snap['metrics']['queue_wait_seconds'] > 0
        checks.append('Real Python clock, timed stairs/lift, transit position and FIFO contention')
        actor = next(a for a in snap['actors'] if not a['ride'])
        target = next(t for t in snap['targets'] if t['floor'] != actor['position'][0])
        page.locator('#route-person').select_option(actor['id'])
        page.locator('#route-target').select_option(target['id'])
        page.locator('#send-walker').click()
        page.wait_for_function('(target) => atelier.demo.actors.find(a=>a.id===atelier.person).target.id===target',arg=target['id'])
        page.locator('#follow-floor').check()
        page.evaluate('async () => {await atelier.advance(1)}')
        if page.evaluate('atelier.demo.actors.find(a=>a.id===atelier.person).position!==null'):
            assert page.evaluate('atelier.floor===atelier.demo.actors.find(a=>a.id===atelier.person).position[0]')
        assert page.locator('.log-entry').count() > 0
        checks.append('Manual route intent, readable log, selected-person floor follow')
        page.locator('[data-mode="district"]').click()
        page.wait_for_function('atelier.ready && !atelier.busy && atelier.mode==="district"')
        assert page.evaluate('atelier.design.validation.connected_plots') == 8
        page.screenshot(path=str(out/'06-connected-block.png'))
        checks.append('Connected eight-plot district view')
        page.locator('[data-mode="room"]').click()
        page.wait_for_function('atelier.ready && !atelier.busy && atelier.mode==="room"')
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(out/'07-mobile-atelier.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        checks.append('390px mobile view has no horizontal overflow')
        offline = browser.new_page(viewport={'width':1440,'height':1050})
        offline.on('pageerror',lambda e:errors.append(str(e)))
        offline.goto((ROOT/'docs'/'procedural_housing_supplement.html').as_uri())
        offline.wait_for_function('window.supplementReady')
        offline.screenshot(path=str(out/'08-whitepaper-supplement.png'))
        offline.locator('#room-kind').select_option('kitchen')
        assert offline.locator('#room-gallery article').count()==4
        offline.locator('#clearances').check()
        offline.locator('#room-gallery').scroll_into_view_if_needed()
        offline.screenshot(path=str(out/'09-offline-gallery.png'))
        offline.locator('#house-choice').select_option('2')
        assert offline.locator('#floors button').count()==5
        offline.locator('#floors button').nth(4).click()
        assert '4. Obergeschoss' in offline.locator('#house-caption').inner_text()
        assert offline.locator('#result-rows tr').count()==len(catalog['rooms'])
        assert offline.locator('#room-kind option').count()==len(catalog['rooms'])
        offline.locator('#object-catalog summary').click()
        assert offline.locator('#object-gallery article').count()==len(catalog['objects'])
        offline.locator('#object-gallery').screenshot(path=str(out/'catalog-all-objects.png'))
        offline.locator('#object-filter').fill('Klavier')
        assert offline.locator('#object-gallery article').count()==1
        assert 'Klavier' in offline.locator('#object-gallery').inner_text()
        offline.locator('#object-filter').fill('')
        assert offline.locator('#object-gallery article').count()==len(catalog['objects'])
        checks.append(f"Offline object catalog renders all {len(catalog['objects'])} sprites; search filters and restores the catalog")
        checks.append('Standalone file:// report: gallery, clearances, five floors, measured table')
        assert errors==[],errors
        report={'passed':True,'generator_version':catalog['generator_version'],'room_type_count':len(catalog['rooms']),'object_type_count':len(catalog['objects']),'checks':checks,'browser_errors':errors,'browser':browser.version,'navigation_metrics':snap['metrics'],'screenshots':sorted(p.name for p in out.glob('*.png'))}
        (out/'browser-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2))
        browser.close()


if __name__=='__main__':
    main()
