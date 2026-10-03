"""Visual smoke check against a separate, paused campus save."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts'/'campus_20261002'
def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8774',
                        help='Paused campus server; never use a cherished live save')
    parser.add_argument('--output',type=Path,default=OUT)
    args=parser.parse_args(argv)
    url=args.url.rstrip('/')
    output=args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    report={'checks':{},'errors':[],'screenshots':[]}
    def check(name,value):report['checks'][name]=bool(value)
    def capture(page,name):
        target=output/name
        page.screenshot(path=str(target),animations='disabled')
        report['screenshots'].append(str(target))
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1500,'height':980},device_scale_factor=1)
        page.on('pageerror',lambda error:report['errors'].append(str(error)))
        page.goto(url,wait_until='domcontentloaded')
        page.wait_for_function('window.mosswood?.ready && window.mosswood?.person')
        world=page.request.get(url+'/api/world').json()
        check('campus_geometry',world['height']==326 and len(world['planning_metadata']['portals'])==2)
        check('three_floor_buttons',page.locator('[data-campus-floor]').count()==3)
        check('glance_emotions_and_needs',page.locator('#person-glance .glance-chip').count()>=3)
        page.evaluate("window.mosswood.configure({building_id:'university',roofs:'open',zoom:.8})")
        capture(page,'01-university.png')
        page.locator('[data-campus-floor="1"]').click()
        check('floor_one_focus',page.evaluate("window.mosswood.renderer.openBuilding==='student_dorm_floor_1'"))
        capture(page,'02-residence-floor-1.png')
        page.locator('[data-campus-floor="2"]').click()
        check('floor_two_focus',page.evaluate("window.mosswood.renderer.openBuilding==='student_dorm_floor_2'"))
        capture(page,'03-residence-floor-2.png')
        page.locator('[data-tab="details"]').click()
        check('w100_visible',page.locator('#inspector-content').get_by_text('W100 · Fähigkeiten').count()==1)
        capture(page,'04-w100-inspector.png')
        page.set_viewport_size({'width':390,'height':844})
        capture(page,'05-mobile.png')
        width=page.evaluate('({document:document.documentElement.scrollWidth,viewport:innerWidth})')
        check('mobile_fits',width['document']<=width['viewport'])
        report['mobile_widths']=width
        browser.close()
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report['errors'] or not all(report['checks'].values()):raise SystemExit(1)


if __name__=='__main__':main()
