"""Separate laboratory endpoints, with bounded sessions and no main-world writes."""
import asyncio
from collections import OrderedDict
from pathlib import Path
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from .catalog import catalog_data
from .demo import NavigationDemo
from .houses import generate_house, generate_district
from .rooms import generate_room, GenerationError
from .buildings import generate_building
from .regions import generate_region, route_to_room

ROOT = Path(__file__).resolve().parents[2]


class RoomRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = "living"
    seed: int = Field(default=42, ge=0, le=2_000_000_000)
    width: int | None = Field(default=None, ge=5, le=14)
    height: int | None = Field(default=None, ge=5, le=14)
    style: str | None = None


class HouseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = Field(default=42, ge=0, le=2_000_000_000)
    levels: int = Field(default=3, ge=1, le=5)
    elevator: bool = True


class DistrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = Field(default=42, ge=0, le=2_000_000_000)
    count: int = Field(default=8, ge=2, le=12)


class ResidentsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    adults: int = Field(default=2, ge=0, le=20)
    children: int = Field(default=1, ge=0, le=20)
    teens: int = Field(default=0, ge=0, le=20)


class BuildingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    width: int = Field(default=18, ge=12, le=80)
    depth: int = Field(default=19, ge=10, le=80)
    room_count: int = Field(default=6, ge=1, le=40)
    levels_above_ground: int = Field(default=2, ge=1, le=5)
    basements: int = Field(default=0, ge=0, le=1)
    residents: ResidentsRequest = Field(default_factory=ResidentsRequest)
    room_program: list[str] | None = Field(default=None, max_length=40)
    elevator: bool = True
    terrace_exit: bool = False
    seed: int = Field(default=42, ge=0, le=2_000_000_000)


class RegionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    seed: int = Field(default=42, ge=0, le=2_000_000_000)
    columns: int = Field(default=3, ge=1, le=4)
    rows: int = Field(default=2, ge=1, le=3)
    zones: list[str] | None = Field(default=None, max_length=12)


class RegionRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plot_id: str
    room_id: str


class StepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seconds: int = Field(default=1, ge=0, le=3600)


class RouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor_id: str
    target_id: str
    transport: str = Field(default="auto", pattern="^(auto|stairs|elevator)$")


def create_generation_router():
    router = APIRouter()
    sessions = OrderedDict()
    lock = asyncio.Lock()
    region_sessions = OrderedDict()
    generation_slots = asyncio.Semaphore(2)

    def find_session(sid):
        if sid not in sessions:
            raise HTTPException(404, "Testhaus nicht mehr geladen; bitte erneut generieren")
        sessions.move_to_end(sid)
        return sessions[sid]

    @router.get("/atelier", include_in_schema=False)
    async def atelier():
        return FileResponse(ROOT / "web" / "atelier.html")

    @router.get("/whitepaper-supplement", include_in_schema=False)
    async def supplement():
        target = ROOT / "docs" / "procedural_housing_supplement.html"
        if not target.exists():
            raise HTTPException(404, "Bericht erzeugen: python scripts/generation_report.py")
        return FileResponse(target)

    @router.get("/api/generation/catalog")
    async def catalog():
        return catalog_data()

    @router.post("/api/generation/room")
    async def room(body: RoomRequest):
        try:
            return await asyncio.to_thread(generate_room, **body.model_dump())
        except GenerationError as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.post("/api/generation/house")
    async def house(body: HouseRequest):
        try:
            design = await asyncio.to_thread(generate_house, **body.model_dump())
            demo = NavigationDemo(design)
        except GenerationError as exc:
            raise HTTPException(422, str(exc)) from exc
        async with lock:
            sid = uuid.uuid4().hex
            sessions[sid] = demo
            while len(sessions) > 12:
                sessions.popitem(last=False)
        return {"design": design, "session_id": sid, "demo": demo.snapshot()}

    @router.post("/api/generation/district")
    async def district(body: DistrictRequest):
        return await asyncio.to_thread(generate_district, **body.model_dump())

    @router.post("/api/generation/building")
    async def building(body: BuildingRequest):
        try:
            async with generation_slots:
                design = await asyncio.to_thread(generate_building, body.model_dump())
                demo = NavigationDemo(design)
        except (GenerationError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        async with lock:
            sid = uuid.uuid4().hex
            sessions[sid] = demo
            while len(sessions) > 12:
                sessions.popitem(last=False)
        return {"design": design, "session_id": sid, "demo": demo.snapshot()}

    @router.post("/api/generation/region")
    async def region(body: RegionRequest):
        try:
            async with generation_slots:
                design = await asyncio.to_thread(generate_region, **body.model_dump())
        except GenerationError as exc:
            raise HTTPException(422, str(exc)) from exc
        async with lock:
            sid = uuid.uuid4().hex
            region_sessions[sid] = design
            while len(region_sessions) > 3:
                region_sessions.popitem(last=False)
        return {"design": design, "session_id": sid}

    @router.post("/api/generation/region/{sid}/route")
    async def region_route(sid: str, body: RegionRoute):
        async with lock:
            if sid not in region_sessions:
                raise HTTPException(404, "Quartier erneut generieren")
            design = region_sessions[sid]
        try:
            return await asyncio.to_thread(route_to_room, design, body.plot_id, body.room_id)
        except GenerationError as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.get("/api/generation/demo/{sid}")
    async def demo(sid: str):
        async with lock:
            return find_session(sid).snapshot()

    @router.post("/api/generation/demo/{sid}/advance")
    async def advance(sid: str, body: StepRequest):
        async with lock:
            return find_session(sid).advance(body.seconds)

    @router.post("/api/generation/demo/{sid}/route")
    async def route(sid: str, body: RouteRequest):
        async with lock:
            session = find_session(sid)
            try:
                session.command(body.actor_id, body.target_id, body.transport)
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc
            return session.snapshot()

    return router
