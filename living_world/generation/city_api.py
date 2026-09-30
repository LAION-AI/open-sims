"""Isolated city laboratory endpoints; no main-world persistence or mutation."""
from collections import OrderedDict
from pathlib import Path
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from .city import generate_city, route_to_city_room
from .rooms import GenerationError

ROOT = Path(__file__).resolve().parents[2]


class CityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    seed: int = Field(default=42, ge=0, le=2_000_000_000)
    columns: int = Field(default=4, ge=4, le=5)
    rows: int = Field(default=4, ge=4, le=5)


class CityRouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plot_id: str
    room_id: str


def create_city_router():
    router = APIRouter()
    sessions = OrderedDict()

    @router.get("/city", include_in_schema=False)
    def city_page():
        return FileResponse(ROOT / "web" / "city.html")

    @router.post("/api/generation/city")
    def city_generate(brief: CityRequest):
        try:
            design = generate_city(**brief.model_dump())
        except GenerationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        session_id = uuid.uuid4().hex
        sessions[session_id] = design
        while len(sessions) > 12:
            sessions.popitem(last=False)
        return {"session_id": session_id, "design": design}

    @router.post("/api/generation/city/{session_id}/route")
    def city_route(session_id: str, request: CityRouteRequest):
        design = sessions.get(session_id)
        if design is None:
            raise HTTPException(status_code=404, detail="Unknown or expired city session")
        try:
            return route_to_city_room(design, request.plot_id, request.room_id)
        except GenerationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return router
