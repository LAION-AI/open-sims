"""Local HTTP/WebSocket interface; all clients observe the same Python world."""
import asyncio
from contextlib import asynccontextmanager, suppress
import json
from pathlib import Path
import os
import time
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .engine import World, RejectedProposal
from . import affect, possessions
from .object_inspection import inspect_object
from .insights import build_world_insights
from .plausibility import audit as audit_plausibility
from .generation.api import create_generation_router
from .generation.city_api import create_city_router
from .workshop.api import create_workshop_router
from .workshop.library import Library
from . import openrouter_control

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


class PlayerRecommendation(BaseModel):
    """Local UI command; the coordinator reads the current version atomically."""
    model_config=ConfigDict(extra='forbid')
    actor_id: str
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


class DecisionProviderToggle(BaseModel):
    model_config=ConfigDict(extra='forbid')
    enabled: bool
    model: str | None = None
    expected_version: int


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
        app.state.provider_pending={}
        app.state.provider_last_attempt={}
        app.state.provider_failures={}
        app.state.provider_next_attempt={}
        app.state.provider_generation=0

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
                    if current-saved_at>10 and not world.fault:
                        try:world.save()
                        except Exception as exc:
                            world.fault=f'Save failed; simulation paused: {type(exc).__name__}: {exc}'
                            world.paused=True
                        saved_at=current

        def provider_fallback(world, aid, model, message, status='retrying', failures=0,
                              expected_epoch=None):
            actor=world.actors.get(aid)
            if (not actor or (actor.get('decision_provider') or {}).get('model')!=model
                    or expected_epoch is not None and actor['owner_epoch']!=expected_epoch):
                return
            if (actor.get('decision_provider_error')!=message
                    or actor['decision_provider'].get('status')!=status
                    or actor['decision_provider'].get('failures')!=failures):
                with world.transaction('external.decision.deferred.v1',[aid],
                        f"{actor['name']} kept their model preference while a procedural decision covered a temporary gap.",
                        [status]):
                    person=world.edit('actors',aid)
                    person['decision_provider_error']=message
                    person['decision_provider']['status']=status
                    person['decision_provider']['failures']=failures
            if not world.actors[aid]['action']:
                try:
                    world.decide(aid,provider_fallback=True)
                except RejectedProposal:
                    # Keep the preference. The next provider loop will re-evaluate
                    # current affordances instead of turning the model off.
                    app.state.provider_next_attempt[aid]=max(
                        app.state.provider_next_attempt.get(aid,0),time.monotonic()+2)

        async def resolve_provider(aid, model, description, key, generation):
            try:
                async with app.state.provider_semaphore:
                    decision=await asyncio.to_thread(openrouter_control.request_decision,model,description,key=key)
                async with app.state.lock:
                    if generation!=app.state.provider_generation:return
                    w=app.state.world
                    actor=w.actors.get(aid)
                    if (not actor or actor['action'] or (actor.get('decision_provider') or {}).get('model')!=model
                            or actor['owner_epoch']!=description['owner_epoch']):return
                    if w.now-description['described_at']>900:
                        provider_fallback(w,aid,model,'World time moved too far during the model call; current choices used instead',
                                          status='ready',expected_epoch=description['owner_epoch'])
                        return
                    selected=openrouter_control.sample_option(decision,w.rng(aid,actor['decision_id']+1,'provider_choice'))
                    intent={**description['options'][selected],'actor_id':aid,
                        'owner_epoch':description['owner_epoch'],'expected_version':actor['version']}
                    try:w.submit_intent(intent)
                    except RejectedProposal:
                        provider_fallback(w,aid,model,'That option changed before it could begin; procedural fallback used',
                                          status='ready',expected_epoch=description['owner_epoch'])
                        return
                    app.state.provider_failures.pop(aid,None)
                    app.state.provider_next_attempt.pop(aid,None)
                    with w.transaction('external.decision.trace.v1',[aid],
                            f"{actor['name']} accepted a bounded decision from {model}.",
                            ['Model selected among coordinator-feasible options']):
                        person=w.edit('actors',aid)
                        person['decision_provider']['status']='connected'
                        person['decision_provider']['failures']=0
                        person['decision_provider_error']=None
                        person['last_decision']['provider']={
                            'model':model,'confidence':decision['confidence'],
                            'probabilities':decision['probabilities'],'selected':selected}
            except Exception as exc:
                # Remote bodies, credentials and transport details never enter the journal.
                async with app.state.lock:
                    if generation!=app.state.provider_generation:return
                    w=app.state.world
                    actor=w.actors.get(aid)
                    if actor and actor.get('decision_provider') and actor['decision_provider']['model']==model:
                        failures=app.state.provider_failures.get(aid,0)+1
                        app.state.provider_failures[aid]=failures
                        retryable=getattr(exc,'retryable',True)
                        delay=min(120,3*2**min(failures,5)) if retryable else 300
                        app.state.provider_next_attempt[aid]=time.monotonic()+delay
                        message=str(exc) if isinstance(exc,openrouter_control.ProviderUnavailable) else \
                            f'Decision service unavailable ({type(exc).__name__}); retrying later'
                        provider_fallback(w,aid,model,message,failures=failures,
                                          expected_epoch=description['owner_epoch'])
            finally:
                if app.state.provider_pending.get(aid) is asyncio.current_task():
                    app.state.provider_pending.pop(aid,None)

        async def run_providers():
            while True:
                await asyncio.sleep(.35)
                key=provider_key()
                async with app.state.lock:
                    w=app.state.world
                    if w.paused or w.fault:continue
                    current=time.monotonic()
                    for aid,actor in w.actors.items():
                        provider=actor.get('decision_provider')
                        if (not provider or actor['action'] or aid in app.state.provider_pending
                                or current-app.state.provider_last_attempt.get(aid,0)<1.5):continue
                        if not key:
                            provider_fallback(w,aid,provider['model'],
                                              'No session key is configured; procedural fallback is active',
                                              status='needs_key',failures=app.state.provider_failures.get(aid,0))
                            continue
                        if current<app.state.provider_next_attempt.get(aid,0):
                            provider_fallback(w,aid,provider['model'],
                                              actor.get('decision_provider_error') or 'Retrying later',
                                              failures=app.state.provider_failures.get(aid,0))
                            continue
                        if len(app.state.provider_pending)>=3:break
                        try:description=openrouter_control.describe_actor(w,aid)
                        except Exception:
                            provider_fallback(w,aid,provider['model'],
                                              'Could not prepare the current choices; procedural fallback used',
                                              failures=app.state.provider_failures.get(aid,0))
                            app.state.provider_next_attempt[aid]=current+5
                            continue
                        app.state.provider_last_attempt[aid]=current
                        app.state.provider_pending[aid]=asyncio.create_task(resolve_provider(
                            aid,provider['model'],description,key,app.state.provider_generation))

        app.state.provider_semaphore=asyncio.Semaphore(3)
        task=asyncio.create_task(run_clock())
        provider_task=asyncio.create_task(run_providers())
        yield
        task.cancel()
        provider_task.cancel()
        for pending in app.state.provider_pending.values():pending.cancel()
        with suppress(asyncio.CancelledError):
            await task
        with suppress(asyncio.CancelledError):
            await provider_task
        if app.state.provider_pending:
            await asyncio.gather(*app.state.provider_pending.values(),return_exceptions=True)
        app.state.world.close()
        library.close()

    app=FastAPI(title="Mosswood · Procedural Living World",version="0.1.0",lifespan=lifespan)
    app.state.openrouter_key=None  # Memory only: never checkpointed or returned.
    app.include_router(create_generation_router())
    app.include_router(create_city_router())
    app.include_router(create_workshop_router(library))

    def actor_or_404(aid):
        if aid not in app.state.world.actors:
            raise HTTPException(404,"Resident not found")

    def provider_key():
        return app.state.openrouter_key or os.environ.get('OPENROUTER_API_KEY','').strip()

    def local_settings_request(request: Request):
        client=request.client.host if request.client else ''
        if client not in {'127.0.0.1','::1','testclient'}:
            raise HTTPException(403,'Settings are available only from the local computer')
        origin=request.headers.get('origin')
        if origin and urlsplit(origin).netloc != request.headers.get('host'):
            raise HTTPException(403,'Cross-origin settings request rejected')

    @app.get("/api/health")
    async def health():
        async with app.state.lock:
            w=app.state.world
            return {"status":"fault" if w.fault else "ok","fault":w.fault,"invariants":w.invariants(),"population":len(w.actors),
                    "households":sum(h.get('household_kind')!='student_residence' for h in w.spatial.households),
                    "residential_units":len(w.spatial.households),
                    "llm_enabled":any(a.get('decision_provider') for a in w.actors.values()),
                    "external_decision_configured":bool(provider_key()),"simulation_fields":False}

    @app.get('/api/decision-providers')
    async def decision_providers():
        return {'configured':bool(provider_key()),'models':openrouter_control.MODELS,
                'credential_location':'runtime memory or server environment',
                'scope':'per opted-in Sim; at most three concurrent model requests'}

    @app.get('/api/settings/openrouter-key')
    async def openrouter_key_status(request: Request):
        local_settings_request(request)
        return Response(content=json.dumps({'configured':bool(provider_key()),
                        'source':'runtime' if app.state.openrouter_key else 'environment' if openrouter_control.configured() else 'none'}),
                        media_type='application/json',headers={'Cache-Control':'no-store'})

    @app.post('/api/settings/openrouter-key')
    async def set_openrouter_key(request: Request):
        local_settings_request(request)
        if request.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':
            raise HTTPException(415,'JSON request required')
        try:
            body=await request.json()
        except (ValueError,UnicodeError):
            raise HTTPException(422,'Invalid JSON request') from None
        if not isinstance(body,dict) or set(body)!={'key'} or not isinstance(body['key'],str):
            raise HTTPException(422,'A key string is required')
        key=body['key'].strip()
        if not 1<=len(key)<=512:
            raise HTTPException(422,'Key must contain 1–512 characters')
        async with app.state.lock:
            app.state.openrouter_key=key
            app.state.provider_generation+=1
            for pending in app.state.provider_pending.values():
                pending.cancel()
            app.state.provider_pending.clear()
            app.state.provider_failures.clear()
            app.state.provider_next_attempt.clear()
            app.state.provider_last_attempt.clear()
        return Response(content='{"configured":true,"source":"runtime"}',media_type='application/json',
                        headers={'Cache-Control':'no-store'})

    @app.delete('/api/settings/openrouter-key')
    async def forget_openrouter_key(request: Request):
        local_settings_request(request)
        async with app.state.lock:
            app.state.openrouter_key=None
            app.state.provider_generation+=1
            for pending in app.state.provider_pending.values():
                pending.cancel()
            app.state.provider_pending.clear()
            app.state.provider_failures.clear()
            app.state.provider_next_attempt.clear()
            app.state.provider_last_attempt.clear()
        return Response(content=json.dumps({'configured':bool(provider_key()),
                        'source':'environment' if openrouter_control.configured() else 'none'}),
                        media_type='application/json',headers={'Cache-Control':'no-store'})

    @app.post('/api/actors/{aid}/decision-provider')
    async def toggle_decision_provider(aid:str,body:DecisionProviderToggle):
        actor_or_404(aid)
        if body.enabled and not provider_key():
            raise HTTPException(503,'Set an OpenRouter key in Settings or the server environment.')
        if body.enabled and body.model not in openrouter_control.MODELS:
            raise HTTPException(422,'Unsupported decision model')
        async with app.state.lock:
            w=app.state.world
            if body.enabled and w.actors[aid]['owner']=='external' and not w.actors[aid].get('decision_provider'):
                raise HTTPException(409,'Resident already belongs to another external controller')
            try:
                result=w.set_decision_provider(aid,body.model if body.enabled else None,body.expected_version)
                pending=app.state.provider_pending.get(aid)
                if pending:
                    pending.cancel()
                    app.state.provider_pending.pop(aid,None)
                app.state.provider_failures.pop(aid,None)
                app.state.provider_next_attempt.pop(aid,None)
                app.state.provider_last_attempt.pop(aid,None)
                return result
            except RejectedProposal as exc:raise HTTPException(409,str(exc)) from exc

    @app.get('/api/plausibility')
    async def plausibility():
        async with app.state.lock:
            return audit_plausibility(app.state.world)

    @app.get('/api/insights')
    async def insights():
        async with app.state.lock:
            return build_world_insights(app.state.world)

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

    @app.get('/api/actors/{aid}/interventions')
    async def interventions(aid:str):
        actor_or_404(aid)
        async with app.state.lock:
            return app.state.world.intervention_options(aid)

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

    @app.post('/api/player/recommendations')
    async def player_recommend(body:PlayerRecommendation):
        """Avoid a second round trip and version race in the player menu."""
        async with app.state.lock:
            actor_or_404(body.actor_id)
            world=app.state.world
            if world.fault:
                raise HTTPException(503,f'Simulation angehalten: {world.fault}')
            payload={**body.model_dump(), 'expected_version':world.actors[body.actor_id]['version']}
            try:
                return world.recommend(body.actor_id,payload)
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

    @app.get('/agentic-daily-life')
    async def agentic_daily_life():
        return FileResponse(ROOT/'docs'/'agentic_daily_life.html')

    @app.get('/social-storyteller')
    async def social_storyteller():
        return FileResponse(ROOT/'docs'/'social_storyteller.html')

    @app.get('/campus-social-w100')
    async def campus_social_w100():
        return FileResponse(ROOT/'docs'/'campus_social_w100.html')

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
