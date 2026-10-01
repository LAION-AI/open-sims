"""Local HTTP/WebSocket interface; all clients observe the same Python world."""
import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
import time

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .engine import World, RejectedProposal
from . import affect, possessions
from .object_inspection import inspect_object
from .plausibility import audit as audit_plausibility
from .generation.api import create_generation_router
from .generation.city_api import create_city_router
from .workshop.api import create_workshop_router
from .workshop.library import Library

ROOT=Path(__file__).resolve().parent.parent


class Control(BaseModel):
    model_config=ConfigDict(extra="forbid")
    paused: bool | None = None
    speed: int | None = Field(default=None,ge=1,le=600)
    step_seconds: int | None = Field(default=None,ge=1,le=3600)


class Intent(BaseModel):
    model_config=ConfigDict(extra="forbid")
    actor_id: str
    owner_epoch: int
    expected_version: int
    action: str
    target_id: str | None = None
    social_category: str | None = Field(default=None, max_length=40)


class Recommendation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    actor_id: str
    expected_version: int
    action: str
    target_id: str | None = None
    social_category: str | None = Field(default=None, max_length=40)
    ttl_seconds: int = Field(default=1800, ge=60, le=3600)


class RecommendationCancel(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version: int


class Transfer(BaseModel):
    model_config=ConfigDict(extra="forbid")
    owner: str = Field(pattern="^(procedural|external)$")
    expected_epoch: int


class Capture(BaseModel):
    overlay: str | None = Field(default=None,pattern='^relationships$')
    building_id: str | None = Field(default=None,max_length=100)
    width: int = Field(default=1440,ge=640,le=2560)
    height: int = Field(default=1000,ge=480,le=1800)
    actor_id: str = "resident_001"
    view: str = Field(default="overview",pattern="^(overview|home|follow)$")
    tab: str = Field(default="overview",pattern="^(overview|mind|journal|details)$")
    grid: bool = False


def create_app(database="data/mosswood.sqlite3",seed=42,port=8765,layout='legacy',paused=False):
    if database!=":memory:":
        Path(database).parent.mkdir(parents=True,exist_ok=True)
    workshop_database = ":memory:" if database == ":memory:" else str(Path(database).with_name("workshop.sqlite3" if Path(database).stem == "mosswood" else Path(database).stem + "-workshop.sqlite3"))
    library = Library(workshop_database)

    @asynccontextmanager
    async def lifespan(app):
        app.state.world=World(seed,database,layout=layout)
        if paused:app.state.world.paused=True
        app.state.lock=asyncio.Lock()
        app.state.capture_lock=asyncio.Semaphore(1)
        app.state.capture_task=None

        async def run_clock():
            last=time.perf_counter()
            saved_at=last
            remainder=0.0
            while True:
                await asyncio.sleep(.05)
                current=time.perf_counter()
                # Suspension of the OS does not secretly simulate hours on resume.
                elapsed=min(current-last,1.0)
                last=current
                async with app.state.lock:
                    world=app.state.world
                    if not world.paused and not world.fault:
                        remainder+=elapsed*world.speed
                        seconds=int(remainder)
                        if seconds:
                            try:
                                world.advance(seconds)
                            except Exception as exc:
                                world.fault=f"{type(exc).__name__}: {exc}"
                                world.paused=True
                            remainder-=seconds
                    else:
                        remainder=0
                    if current-saved_at>10:
                        try:world.save()
                        except Exception as exc:
                            world.fault=f'Save failed; simulation paused: {type(exc).__name__}: {exc}'
                            world.paused=True
                        saved_at=current

        task=asyncio.create_task(run_clock())
        yield
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        app.state.world.close()
        library.close()

    app=FastAPI(title="Mosswood · Procedural Living World",version="0.1.0",lifespan=lifespan)
    app.include_router(create_generation_router())
    app.include_router(create_city_router())
    app.include_router(create_workshop_router(library))

    def actor_or_404(aid):
        if aid not in app.state.world.actors:
            raise HTTPException(404,"Resident not found")

    @app.get("/api/health")
    async def health():
        async with app.state.lock:
            w=app.state.world
            return {"status":"fault" if w.fault else "ok","fault":w.fault,"invariants":w.invariants(),"population":len(w.actors),"households":20,"llm_enabled":False,"simulation_fields":False}

    @app.get('/api/plausibility')
    async def plausibility():
        async with app.state.lock:
            return audit_plausibility(app.state.world)

    @app.get("/api/world")
    async def geometry():
        async with app.state.lock:
            return app.state.world.spatial.public_data()

    @app.get("/api/state")
    async def state():
        async with app.state.lock:
            return app.state.world.snapshot()

    @app.get("/api/actors/{aid}")
    async def actor(aid:str):
        actor_or_404(aid)
        async with app.state.lock:
            return app.state.world.inspect(aid)

    @app.get('/api/objects/{oid}')
    async def object_details(oid:str):
        async with app.state.lock:
            world=app.state.world
            if oid not in world.objects:
                raise HTTPException(404,'Object not found')
            return inspect_object(world,oid)

    @app.get("/api/actors/{aid}/journal")
    async def journal(aid:str,limit:int=40,before:int|None=None):
        actor_or_404(aid)
        async with app.state.lock:
            return {"beats":app.state.world.store.recent(aid,limit,before)}

    @app.get('/api/actors/{aid}/relationships')
    async def relationships(aid:str):
        actor_or_404(aid)
        async with app.state.lock:
            w=app.state.world
            return affect.social_graph_projection(w.actors[aid],w.actors,w.now)

    @app.get('/api/emotions/taxonomy')
    async def taxonomy():
        return affect.taxonomy_projection()

    @app.get('/api/items/actions')
    async def item_actions():
        return {'schema':'mosswood.possessions/1','actions':possessions.POSSESSION_ACTIONS,
                'locations':['worn','carried','container','consumed'],
                'authority':'Coordinator validates and commits; never mutate inventory from a rendering client.'}

    @app.get("/api/beats")
    async def beats(limit:int=15,before:int|None=None):
        async with app.state.lock:
            return {"beats":app.state.world.store.recent(limit=limit,before=before)}

    @app.get("/api/rules")
    async def rules():
        return {"manifest":app.state.world.rules.manifest(),"definitions":app.state.world.rules.data}

    @app.post("/api/control")
    async def control(body:Control):
        async with app.state.lock:
            w=app.state.world
            if w.fault and (body.paused is False or body.step_seconds):
                raise HTTPException(409,'World is paused after an error. Resolve the cause and restart from the saved checkpoint.')
            if body.paused is not None:
                w.paused=body.paused
            if body.speed is not None:
                w.speed=body.speed
            if body.step_seconds:
                if not w.paused:
                    raise HTTPException(409,"Pause the world before stepping it")
                w.advance(body.step_seconds)
            return w.snapshot()

    @app.post("/api/save")
    async def save():
        async with app.state.lock:
            try:app.state.world.save()
            except Exception as exc:raise HTTPException(503,'Save failed; simulation paused at its last durable checkpoint.') from exc
            return {"saved":True,"version":app.state.world.store.sequence,"clock":app.state.world.now}

    @app.get("/api/export")
    async def export():
        async with app.state.lock:
            app.state.world.save()
            return app.state.world.store.checkpoint()

    @app.get("/api/replay")
    async def replay(through:int|None=None):
        async with app.state.lock:
            return {"state":app.state.world.store.replay(through),"through":through or app.state.world.store.sequence}

    @app.get("/api/bridge/{aid}/context")
    async def perspective(aid:str):
        actor_or_404(aid)
        async with app.state.lock:
            return app.state.world.perspective(aid)

    @app.post("/api/bridge/intent")
    async def intent(body:Intent):
        actor_or_404(body.actor_id)
        async with app.state.lock:
            try:
                return app.state.world.submit_intent(body.model_dump())
            except RejectedProposal as exc:
                raise HTTPException(409,str(exc)) from exc

    @app.post('/api/recommendations')
    async def recommend(body:Recommendation):
        async with app.state.lock:
            actor_or_404(body.actor_id)
            try:
                return app.state.world.recommend(body.actor_id, body.model_dump())
            except RejectedProposal as exc:
                raise HTTPException(409,str(exc)) from exc

    @app.post('/api/recommendations/{aid}/cancel')
    async def cancel_recommendation(aid:str,body:RecommendationCancel):
        async with app.state.lock:
            actor_or_404(aid)
            try:
                return app.state.world.cancel_recommendation(aid,body.expected_version)
            except RejectedProposal as exc:
                raise HTTPException(409,str(exc)) from exc

    @app.post("/api/bridge/{aid}/ownership")
    async def transfer(aid:str,body:Transfer):
        actor_or_404(aid)
        async with app.state.lock:
            try:
                return app.state.world.transfer(aid,body.owner,body.expected_epoch)
            except RejectedProposal as exc:
                raise HTTPException(409,str(exc)) from exc

    @app.post("/api/capture",response_class=Response)
    async def capture(body:Capture):
        actor_or_404(body.actor_id)
        if body.building_id and not any(b['id']==body.building_id for b in app.state.world.spatial.buildings):
            raise HTTPException(404,'Building not found')
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise HTTPException(503,"Install requirements-dev.txt and run python -m playwright install chromium") from exc
        async with app.state.capture_lock:
            try:
                async with async_playwright() as p:
                    browser=await p.chromium.launch()
                    try:
                        page=await browser.new_page(viewport={"width":body.width,"height":body.height},device_scale_factor=1)
                        await page.goto(f"http://127.0.0.1:{port}/?capture=1",wait_until="networkidle")
                        await page.wait_for_function("window.mosswood?.ready === true")
                        await page.evaluate("async options => await window.mosswood.configure(options)",body.model_dump())
                        await page.wait_for_timeout(200)
                        png=await page.screenshot(type="png")
                    finally:
                        await browser.close()
                return Response(png,media_type="image/png")
            except Exception as exc:
                raise HTTPException(503,f"Capture unavailable: {exc}") from exc

    @app.websocket("/ws")
    async def live(socket:WebSocket):
        await socket.accept()
        try:
            while True:
                async with app.state.lock:
                    packet=app.state.world.snapshot()
                await socket.send_json(packet)
                await asyncio.sleep(.25)
        except (WebSocketDisconnect,RuntimeError):
            pass

    @app.get("/")
    async def index():
        return FileResponse(ROOT/"web"/"index.html")

    @app.get("/life-supplement")
    async def life_supplement():
        return FileResponse(ROOT/"docs"/"life_systems.html")

    @app.get('/story-supplement')
    async def story_supplement():
        return FileResponse(ROOT/'docs'/'story_systems.html')

    @app.get('/expanded-life')
    async def expanded_life():
        return FileResponse(ROOT/'docs'/'expanded_life.html')

    @app.get('/plausibility-plan', include_in_schema=False)
    async def plausibility_plan():
        return FileResponse(ROOT/'web'/'plausibility-plan.html')

    @app.get("/{document_name}", include_in_schema=False)
    async def linked_document(document_name:str):
        # Fixed whitelist: the offline HTML's relative links also work via HTTP.
        if document_name not in {"psychology_design.md", "daily_life_design.md",
                "spatial_plausibility_notes.md", "procedural_housing_supplement.html", "agent_workshop.html",
                'affect_design.md','possessions_design.md','city_design.md','neighborhood_design.md'}:
            raise HTTPException(404,"Document not found")
        return FileResponse(ROOT/"docs"/document_name,
            media_type="text/plain; charset=utf-8" if document_name.endswith(".md") else "text/html")

    app.mount("/static",StaticFiles(directory=ROOT/"web"),name="static")
    app.mount('/artifacts/story',StaticFiles(directory=ROOT/'artifacts'/'story',check_dir=False),name='story-artifacts')
    app.mount('/artifacts/new_neighborhood',StaticFiles(directory=ROOT/'artifacts'/'new_neighborhood',check_dir=False),name='neighborhood-artifacts')
    return app
