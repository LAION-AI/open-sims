"""Strict data-only content packs. No file paths, URLs, code or executable tools."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Pixel(Strict):
    x: int = Field(ge=0, le=143)
    y: int = Field(ge=0, le=143)
    w: int = Field(ge=1, le=144)
    h: int = Field(ge=1, le=144)
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")


class ObjectTemplate(Strict):
    id: str = Field(pattern=r"^ext_[a-z][a-z0-9_]{2,55}$")
    name: str = Field(min_length=3, max_length=80)
    w: int = Field(ge=1, le=4)
    h: int = Field(ge=1, le=6)
    wall: bool = False
    tall: bool = False
    front: bool = True
    extra_access: list[Literal["back", "left", "right"]] = Field(default_factory=list, max_length=3)
    actions: list[str] = Field(min_length=1, max_length=10)
    pixels: list[Pixel] = Field(min_length=3, max_length=128)
    note: str = Field(max_length=500)

    @model_validator(mode="after")
    def validate_pixels(self):
        if any(p.x+p.w > self.w*24 or p.y+p.h > self.h*24 for p in self.pixels):
            raise ValueError("Pixel rectangle extends outside the meter footprint")
        if not self.front:
            raise ValueError("Workshop objects need front access for their action contracts")
        if len(set(self.actions)) != len(self.actions) or len(set(self.extra_access)) != len(self.extra_access):
            raise ValueError("Repeated action/access edge")
        if len({p.color for p in self.pixels}) < 2:
            raise ValueError("Sprites require at least two colours")
        return self


class RoomTemplate(Strict):
    id: str = Field(pattern=r"^ext_[a-z][a-z0-9_]{2,55}$")
    name: str = Field(min_length=3, max_length=80)
    width: int = Field(ge=5, le=14)
    height: int = Field(ge=5, le=14)
    min_width: int = Field(ge=5, le=14)
    min_height: int = Field(ge=5, le=14)
    required: list[str] = Field(min_length=1, max_length=14)
    optional: list[str] = Field(default_factory=list, max_length=18)
    note: str = Field(max_length=500)

    @model_validator(mode="after")
    def minimum_fits(self):
        if self.min_width > self.width or self.min_height > self.height:
            raise ValueError("Default room is smaller than declared minimum")
        return self


class BuildingTemplate(Strict):
    id: str = Field(pattern=r"^ext_[a-z][a-z0-9_]{2,55}$")
    name: str = Field(min_length=3, max_length=80)
    room_program: list[str] = Field(min_length=2, max_length=24)
    width: int = Field(ge=15, le=40)
    depth: int = Field(ge=10, le=60)
    levels: int = Field(ge=1, le=5)
    note: str = Field(max_length=500)


class GapProposal(Strict):
    title: str = Field(min_length=4, max_length=120)
    missing: list[str] = Field(min_length=1, max_length=8)
    rationale: str = Field(min_length=10, max_length=1200)
    acceptance: list[str] = Field(min_length=2, max_length=8)


class ContentPack(Strict):
    schema_version: Literal[1]
    id: str = Field(pattern=r"^pack_[a-z][a-z0-9_]{2,55}$")
    title: str = Field(min_length=3, max_length=120)
    rationale: str = Field(min_length=10, max_length=1600)
    objects: list[ObjectTemplate] = Field(default_factory=list, max_length=12)
    rooms: list[RoomTemplate] = Field(default_factory=list, max_length=6)
    buildings: list[BuildingTemplate] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def nonempty_unique(self):
        if not self.rooms:
            raise ValueError("Every pack needs a room for actual placement testing")
        for items in (self.objects, self.rooms, self.buildings):
            ids = [item.id for item in items]
            if len(ids) != len(set(ids)):
                raise ValueError("Duplicate template IDs")
        return self
