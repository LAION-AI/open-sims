"""Isolated browser check for life-stage visuals, places and provider controls."""
import json
from pathlib import Path
import socket
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import uvicorn
from playwright.sync_api import sync_playwright
from living_world.server import create_app


def main():
    output=ROOT/'artifacts'/'life_stages_20261001'
    output.mkdir(parents=True,exist_ok=True)
    listener=socket.socket()
    listener.bind(('127.0.0.1',0))
    port=listener.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    server=uvicorn.Server(uvicorn.Config(create_app(':memory:',seed=73,port=port,
        layout='neighborhood-v1',paused=True),log_level='error'))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True)
    thread.start()
    report={'isolated_database':True,'page_errors':[],'checks':{}}
    try:
        deadline=time.monotonic()+30
        while not server.started:
            if time.monotonic()>deadline:raise RuntimeError('Server did not start')
            time.sleep(.1)
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            try:
                page=browser.new_page(viewport={'width':1500,'height':1000},device_scale_factor=1)
                page.on('pageerror',lambda error:report['page_errors'].append(str(error)))
                page.goto(base,wait_until='domcontentloaded')
                page.wait_for_function('window.mosswood?.ready === true')
                population=page.evaluate('window.mosswood.state.actors')
                report['checks']['age_groups']={
                    'child':sum(actor['appearance'].get('age',30)<13 for actor in population),
                    'teen':sum(13<=actor['appearance'].get('age',30)<18 for actor in population),
                    'adult':sum(18<=actor['appearance'].get('age',30)<66 for actor in population),
                    'elder':sum(actor['appearance'].get('age',30)>=66 for actor in population),
                }
                page.screenshot(path=str(output/'new-neighborhood.png'))
                page.evaluate('window.mosswood.renderer.fit()')
                page.screenshot(path=str(output/'whole-neighborhood.png'))
                for stage,select in {
                    'child':lambda age:age<13,
                    'teen':lambda age:13<=age<18,
                    'adult':lambda age:18<=age<66,
                    'elder':lambda age:age>=66,
                }.items():
                    actor=next(row for row in population if select(row['appearance']['age']))
                    page.evaluate('async id=>await window.mosswood.select(id)',actor['id'])
                    page.screenshot(path=str(output/f'{stage}-inspector.png'))
                    report['checks'][f'{stage}_label']=page.locator('#person-description').inner_text()
                page.evaluate("async()=>await window.mosswood.configure({building_id:'pool',roofs:'open',zoom:1.7})")
                page.screenshot(path=str(output/'pool-interior.png'))
                report['checks']['provider_checkbox']=page.locator('#provider-enabled').count()==1
                report['checks']['provider_disabled_without_key']=page.locator('#provider-enabled').is_disabled()
                report['checks']['new_buildings']=page.evaluate("async()=>{const w=await (await fetch('/api/world')).json();return w.buildings.filter(b=>['kindergarten','pool','bar','community_center'].includes(b.id)).map(b=>b.id)}")
                report['checks']['html_doc']=page.evaluate("async()=>{const r=await fetch('/agentic-daily-life');return r.status}")
                report['checks']['no_page_errors']=not report['page_errors']
            finally:browser.close()
    finally:
        server.should_exit=True
        thread.join(timeout=20)
        listener.close()
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if not all(report['checks']['age_groups'].values()) or not report['checks']['no_page_errors']:
        raise SystemExit(1)


if __name__=='__main__':main()
