"""Bounded read-only UI acceptance against the separate Lindenviertel preview."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts'/'lindenviertel'
URL='http://127.0.0.1:8769'


def main():
    report={'url':URL,'checks':{},'errors':[]}
    OUT.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':1440,'height':1000})
            page.set_default_timeout(12000)
            page.on('pageerror',lambda error:report['errors'].append(str(error)))
            page.goto(URL,wait_until='domcontentloaded',timeout=30000)
            page.wait_for_function('window.mosswood?.ready && window.mosswood?.person')
            before=page.evaluate('({clock:window.mosswood.state.clock,paused:window.mosswood.state.paused})')
            report['initial_state']=before
            original=page.evaluate('window.mosswood.person.id')
            report['checks']['neighborhood_loaded']=page.evaluate("window.mosswood.renderer.world.planning_metadata.layout_id==='neighborhood-v1'")
            page.evaluate("() => window.mosswood.configure({overlay:'relationships'})")
            node=page.locator('#relation-graph .relation-node').first
            target=node.get_attribute('data-graph-person')
            node.click()
            page.wait_for_function('id => window.mosswood.person.id===id',arg=target)
            report['checks']['graph_click_selects_person']=True
            page.evaluate("id => window.mosswood.configure({actor_id:id,overlay:'relationships'})",original)
            node=page.locator('#relation-graph .relation-node').first
            target=node.get_attribute('data-graph-person')
            node.focus()
            page.keyboard.press('Enter')
            page.wait_for_function('id => window.mosswood.person.id===id',arg=target)
            report['checks']['graph_keyboard_selects_person']=True
            page.evaluate("() => window.mosswood.configure({overlay:'relationships'})")
            node=page.locator('#relation-graph .relation-node').first
            target=node.get_attribute('data-graph-person')
            controls=[]
            page.on('request',lambda request:controls.append(request.url) if '/api/control' in request.url else None)
            node.focus()
            page.keyboard.press('Space')
            page.wait_for_function('id => window.mosswood.person.id===id',arg=target)
            report['checks']['graph_space_does_not_control_time']=not controls
            page.evaluate("() => window.mosswood.configure({overlay:'relationships'})")
            page.locator('#relation-search').fill('definitely-no-matching-person')
            report['checks']['graph_search_filters']=page.locator('#relation-graph .relation-edge').count()==0
            page.keyboard.press('Escape')
            report['checks']['escape_closes']=not page.locator('#relationships-dialog').evaluate('e=>e.open')
            page.set_viewport_size({'width':390,'height':844})
            page.locator('[data-tab="details"]').click()
            page.wait_for_selector('[data-story="possessions"]')
            report['checks']['mobile_possessions']=page.locator('.possession-row').count()>0
            page.evaluate("() => window.mosswood.configure({overlay:'relationships'})")
            page.wait_for_selector('#relationships-dialog[open]')
            page.screenshot(path=str(OUT/'ui-mobile.png'))
            widths=page.evaluate("({page:document.documentElement.scrollWidth,viewport:innerWidth,dialog:document.getElementById('relationships-dialog').scrollWidth,inner:document.getElementById('relationships-dialog').clientWidth})")
            report['mobile_widths']=widths
            report['checks']['mobile_no_horizontal_overflow']=widths['page']<=widths['viewport']+1 and widths['dialog']<=widths['inner']+1
            page.locator('.relation-close').click()
            report['checks']['mobile_close']=not page.locator('#relationships-dialog').evaluate('e=>e.open')
            after=page.evaluate('({clock:window.mosswood.state.clock,paused:window.mosswood.state.paused})')
            report['final_state']=after
            report['checks']['paused_clock_unchanged']=before==after and after['paused']
            browser.close()
    except Exception as exc:
        report['errors'].append(f'{type(exc).__name__}: {exc}')
    report['passed']=len(report['checks'])==10 and all(report['checks'].values()) and not report['errors']
    (OUT/'ui-smoke.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report,indent=2,ensure_ascii=False),flush=True)
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
