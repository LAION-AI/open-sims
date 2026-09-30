"""Real-browser interaction regression and screenshot evidence."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument("--url",default="http://127.0.0.1:8765")
args=parser.parse_args()
out=Path("artifacts");out.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={"width":1440,"height":1000},device_scale_factor=1)
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.goto(args.url,wait_until="networkidle")
    page.wait_for_function("window.mosswood?.ready")
    page.request.post(args.url+"/api/control",data={"paused":True})
    page.wait_for_timeout(400)
    assert page.locator("#person-name").inner_text()=="Maya Bennett"
    assert page.locator(".need-row").count()==8
    page.evaluate("window.mosswood.configure({view:'overview'})")
    page.screenshot(path=str(out/"01-neighborhood.png"))
    before=page.evaluate("window.mosswood.renderer.camera.zoom")
    page.locator("#zoom-in").click()
    assert page.evaluate("window.mosswood.renderer.camera.zoom")>before
    before_x=page.evaluate("window.mosswood.renderer.camera.x")
    page.keyboard.down("ArrowRight");page.wait_for_timeout(180);page.keyboard.up("ArrowRight")
    assert page.evaluate("window.mosswood.renderer.camera.x")>before_x
    page.locator("#go-home").click()
    page.locator("#grid-toggle").click()
    assert page.evaluate("window.mosswood.renderer.grid")
    page.wait_for_timeout(200)
    page.screenshot(path=str(out/"02-home-grid.png"))
    page.locator('[data-tab="mind"]').click()
    page.wait_for_function("document.querySelector('#inspector-content').textContent.includes('Intentions & possibilities')")
    page.screenshot(path=str(out/"03-inner-life.png"))
    page.locator('[data-tab="details"]').click()
    page.wait_for_selector("#raw-state")
    page.locator('#raw-state summary').click()
    assert page.locator('#raw-state').get_attribute('open') is not None
    page.locator('[data-tab="journal"]').click()
    page.wait_for_selector('.journal-entry')
    page.screenshot(path=str(out/"04-journal.png"))
    page.locator('#people-toggle').click()
    page.locator('#people-search').fill('Yuki')
    assert page.locator('.person-row').count()==1
    page.locator('.person-row').click()
    page.wait_for_function("document.querySelector('#person-name').textContent.includes('Yuki')")
    assert page.locator('#people-drawer').evaluate("e=>e.classList.contains('hidden')")
    # Select a visible resident using the canvas hit coordinates.
    page.evaluate("window.mosswood.configure({actor_id:'resident_001',view:'follow',tab:'overview',grid:false})")
    page.wait_for_timeout(150)
    coords=page.evaluate("window.mosswood.renderer.hitPeople.find(p=>p.id==='resident_001')")
    box=page.locator('#world').bounding_box()
    page.mouse.click(box['x']+coords['x'],box['y']+coords['y']-4)
    assert page.locator('#person-name').inner_text()=='Maya Bennett'
    page.locator('#fit').click()
    page.screenshot(path=str(out/"05-all-households.png"))
    # Pause/resume and speed are verified against authoritative Python state.
    page.locator('[data-speed="60"]').click()
    page.wait_for_timeout(350)
    assert page.request.get(args.url+'/api/state').json()['speed']==60
    page.locator('#pause').click()
    page.wait_for_timeout(300)
    assert page.request.get(args.url+'/api/state').json()['paused']
    page.locator('#save').click()
    page.wait_for_selector('#toast:not(.hidden)')
    page.set_viewport_size({"width":390,"height":844})
    page.wait_for_timeout(300)
    page.evaluate("document.getElementById('toast').classList.add('hidden')")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(path=str(out/"06-mobile.png"),full_page=True)
    page.set_viewport_size({"width":1440,"height":1000})
    page.evaluate("window.mosswood.configure({view:'overview',tab:'overview',grid:false})")
    page.wait_for_timeout(1500)
    metrics=page.evaluate("({fps:window.mosswood.renderer.fps, population:window.mosswood.state.population, households:window.mosswood.state.households, zoom:window.mosswood.renderer.camera.zoom})")
    print(json.dumps({"browser_errors":errors,"metrics":metrics,"screenshots":str(out.resolve()),"health":page.request.get(args.url+'/api/health').json()},indent=2))
    assert not errors,errors
    browser.close()
