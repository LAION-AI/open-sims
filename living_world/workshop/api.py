"""Local inspection/demo endpoints. Paid providers are CLI-only, explicit opt-in."""
import asyncio
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from .library import Library
from .providers import DemoProvider
from .runner import Runner, RunLimits
from ..generation.api import RoomRequest, BuildingRequest
from ..generation.rooms import generate_room, GenerationError
from ..generation.buildings import generate_building

ROOT = Path(__file__).resolve().parents[2]


class DemoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    focus: str = Field(default="Kleine zusätzliche Leseplätze", min_length=3, max_length=800)


class Approval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer: str = Field(min_length=2, max_length=80)
    visual_reviewed: bool = False
    expected_pack_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


def create_workshop_router(library):
    router = APIRouter()
    running = asyncio.Lock()
    generation_slots = asyncio.Semaphore(2)

    def same_origin(request):
        host = urlsplit(str(request.base_url)).hostname
        test_client = host == "testserver" and request.client and request.client.host == "testclient"
        if host not in {"127.0.0.1", "localhost", "::1"} and not test_client:
            raise HTTPException(403, "Authoring requires a loopback Host")
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            raise HTTPException(403, "Local same-origin authoring only")

    @router.get("/workshop", include_in_schema=False)
    async def workshop():
        return FileResponse(ROOT / "web" / "workshop.html")

    @router.get("/agent-supplement", include_in_schema=False)
    @router.get("/agent_workshop.html", include_in_schema=False)
    async def documentation():
        return FileResponse(ROOT / "docs" / "agent_workshop.html")

    @router.get("/api/workshop/library")
    async def inventory():
        return await asyncio.to_thread(library.inventory)

    @router.get("/api/workshop/lookup")
    async def lookup(q: str = "", category: str = "rooms"):
        if category not in ("objects", "rooms", "buildings") or len(q) > 120:
            raise HTTPException(422, "Use objects/rooms/buildings and a short query")
        inventory = await asyncio.to_thread(library.inventory)
        matches = [{"id": key, "template": value} for key, value in inventory[category].items()
                   if q.casefold() in (key+" "+(value if isinstance(value,str) else value["name"])).casefold()]
        return {"matches": matches[:100], "revision": inventory["revision"],
                "matching": "lexical_id_or_name", "missing": not matches,
                "request_endpoint": "/api/workshop/requests"}

    @router.post("/api/workshop/requests")
    async def request_template(body: DemoRequest, request: Request):
        same_origin(request)
        try:
            jid = await asyncio.to_thread(library.create_job, body.focus, "codex-handoff", "coordinator-selected")
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"id": jid, "state": "queued", "model_called": False,
                "next": "Coordinator may delegate or run an explicitly budgeted provider job"}

    @router.get("/api/workshop/tools")
    async def tool_manifest():
        return {"version": 1, "transport": "local_http_json", "automatic_llm_execution": False,
                "read": ["GET /api/workshop/library", "GET /api/workshop/lookup", "GET /api/workshop/jobs/{id}"],
                "generate": ["POST /api/workshop/room", "POST /api/workshop/building", "POST /api/generation/region"],
                "request_missing": "POST /api/workshop/requests",
                "publish_requires_review": "POST /api/workshop/jobs/{id}/publish",
                "schemas": "/openapi.json"}

    @router.get("/api/workshop/jobs")
    async def jobs():
        return {"jobs": library.jobs(), "external_enabled_in_web": False,
                "codex_delegation": "interactive_session_only", "max_demo_workers": 1}

    def attach_graphics(objects, graphics):
        for obj in objects:
            if obj["kind"] in graphics:
                obj["procedural_sprite"] = graphics[obj["kind"]]["pixels"]
                obj["actions"] = graphics[obj["kind"]]["actions"]

    @router.post("/api/workshop/room")
    async def library_room(body: RoomRequest):
        try:
            async with generation_slots:
                snap = await asyncio.to_thread(library.snapshot)
                room = await asyncio.to_thread(generate_room, **body.model_dump(), object_catalog=snap["objects"], room_catalog=snap["rooms"])
            attach_graphics(room["objects"], snap["graphics"])
            room["library_revision"] = snap["revision"]
            return room
        except GenerationError as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.post("/api/workshop/building")
    async def library_building(body: BuildingRequest):
        try:
            async with generation_slots:
                snap = await asyncio.to_thread(library.snapshot)
                design = await asyncio.to_thread(generate_building, body.model_dump(), object_catalog=snap["objects"], room_catalog=snap["rooms"])
            for floor in design["floors"]:
                attach_graphics(floor["objects"], snap["graphics"])
                for room in floor["rooms"]:
                    attach_graphics(room["objects"], snap["graphics"])
            design["library_revision"] = snap["revision"]
            return design
        except GenerationError as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.get("/api/workshop/jobs/{jid}")
    async def job(jid: str):
        try:
            return library.job(jid)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.post("/api/workshop/demo")
    async def demo(body: DemoRequest, request: Request):
        same_origin(request)
        if running.locked():
            raise HTTPException(409, "Offline-Prüflauf läuft bereits")
        async with running:
            try:
                return await asyncio.to_thread(Runner(library, DemoProvider(), RunLimits(1, 1, 2)).run, [body.focus])
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc

    @router.post("/api/workshop/jobs/{jid}/publish")
    async def publish(jid: str, body: Approval, request: Request):
        same_origin(request)
        try:
            if body.expected_pack_hash is None:
                raise ValueError("Review the draft first and provide its pack hash")
            return await asyncio.to_thread(library.publish, jid, body.reviewer, visual_reviewed=body.visual_reviewed, expected_pack_hash=body.expected_pack_hash)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    return router
