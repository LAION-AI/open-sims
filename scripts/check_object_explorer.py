"""Browser acceptance in a temporary in-memory server; never touches a save."""
import json
from pathlib import Path
import socket
import sys
import threading
import time
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import uvicorn
from playwright.sync_api import sync_playwright
from living_world.server import create_app


def main():
    out=ROOT/'artifacts'/'object_explorer';out.mkdir(parents=True,exist_ok=True)
    report={'checks':{},'errors':[],'database':':memory:','live_save_touched':False}
    listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    url=f'http://127.0.0.1:{port}'
    server=uvicorn.Server(uvicorn.Config(create_app(':memory:',seed=73,port=port,layout='neighborhood-v1',paused=True),log_level='error'))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True);thread.start()
    def api(path,body=None):
        request=Request(url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=30) as response:return json.load(response)
    try:
        deadline=time.monotonic()+20
        while not server.started:
            if time.monotonic()>deadline:raise RuntimeError('Temporary server startup timed out')
            time.sleep(.1)
        api('/api/control',{'step_seconds':900})
        initial=api('/api/state')
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':1500,'height':980});page.set_default_timeout(15000)
            page.on('pageerror',lambda error:report['errors'].append(str(error)))
            page.goto(url,wait_until='domcontentloaded');page.wait_for_function('window.mosswood?.ready')
            for speed in (120,300,600,1,10,60):
                page.select_option('#speed-select',str(speed))
                page.wait_for_function('speed=>window.mosswood.state.speed===speed',arg=speed)
            report['checks']['all_speed_presets']=page.evaluate('window.mosswood.state.paused && window.mosswood.state.clock===30600')
            page.select_option('#speed-select','10')
            obj=page.evaluate("window.mosswood.renderer.world.objects.find(o=>o.kind==='sofa')")
            page.evaluate("id=>window.mosswood.configure({building_id:id,roofs:'open',zoom:1.25})",obj['building_id'])
            point=page.evaluate("o=>window.mosswood.renderer.screenAt((o.x+.5)*24,(o.y+.5)*24)",obj)
            box=page.locator('#world').bounding_box();page.mouse.click(box['x']+point['x'],box['y']+point['y'])
            page.wait_for_selector('#object-explorer:not(.hidden) pre',state='attached')
            data=json.loads(page.locator('#object-explorer pre').text_content())
            report['checks']['canvas_object_selection']=data['id']==obj['id']
            report['checks']['authoritative_projection']=data==api('/api/objects/'+obj['id'])['object']
            report['checks']['capability_labels']=page.locator('#object-explorer-body').get_by_text('Fähigkeiten dieses Objekttyps',exact=False).count()==1
            page.screenshot(path=str(out/'desktop.png'))
            page.locator('[data-object-close]').click()
            hidden=page.evaluate("o=>{const r=window.mosswood.renderer;r.roofs='closed';const p=r.screenAt((o.x+.5)*24,(o.y+.5)*24);return !r.objectAt(p.x,p.y)}",obj)
            report['checks']['roof_hides_object_picking']=hidden
            page.locator('#objects-toggle').click();page.fill('#object-search',obj['id'])
            report['checks']['search_exact_id']=page.locator('[data-inspect-object]').count()==1
            page.locator('[data-inspect-object]').click();page.wait_for_selector('#object-explorer pre',state='attached')
            report['checks']['list_focuses_building']=page.evaluate('window.mosswood.renderer.openBuilding')==obj['building_id']
            # Deliberately exercise compatibility without a new backend route.
            page.route('**/openapi.json',lambda route:route.fulfill(json={'paths':{}}))
            page.reload(wait_until='domcontentloaded');page.wait_for_function('window.mosswood?.ready')
            page.locator('#objects-toggle').click();page.fill('#object-search',obj['id']);page.locator('[data-inspect-object]').click()
            page.wait_for_selector('#object-explorer pre',state='attached')
            report['checks']['old_server_fallback_is_explicit']='keine vollständige Inhaltsprojektion' in page.locator('#object-explorer-body').text_content()
            report['checks']['old_server_raw_state_is_fresh']=json.loads(page.locator('#object-explorer pre').text_content())==api('/api/objects/'+obj['id'])['object']
            page.set_viewport_size({'width':390,'height':844})
            page.screenshot(path=str(out/'mobile.png'))
            widths=page.evaluate('({page:document.documentElement.scrollWidth,viewport:innerWidth,panel:document.getElementById("object-explorer").getBoundingClientRect().width})')
            report['checks']['mobile_fits']=widths['page']<=widths['viewport'] and widths['panel']<=widths['viewport']
            report['mobile_widths']=widths
            page.locator('[data-object-close]').focus();page.keyboard.press('Escape')
            report['checks']['escape_closes']=page.locator('#object-explorer').evaluate('e=>e.classList.contains("hidden")')
            page.goto(url+'/static/plausibility-plan.html');report['checks']['plan_available']='Plausibilität' in page.title()
            final=api('/api/state')
            report['checks']['inspection_keeps_world_unchanged']=all(initial[k]==final[k] for k in ('clock','version','paused','speed'))
            browser.close()
    except Exception as exc:report['errors'].append(f'{type(exc).__name__}: {exc}')
    finally:
        server.should_exit=True;thread.join(timeout=15);listener.close()
    report['passed']=len(report['checks'])==13 and all(report['checks'].values()) and not report['errors']
    (out/'browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2),flush=True)
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
