# src/api/schemas.py

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class CharacterClass(str, Enum):
    Warrior    = "Warrior"
    Ranger     = "Ranger"
    Witch      = "Witch"
    Sorceress  = "Sorceress"
    Duelist    = "Duelist"
    Mercenary  = "Mercenary"
    Shadow     = "Shadow"
    Monk       = "Monk"
    Templar    = "Templar"
    Druid      = "Druid"


class StatResponse(BaseModel):
    stat_key: str = Field(..., description="The stat identifier, e.g. 'FireDamageInc'")
    unit: Optional[str] = Field(None, description="Unit for this stat, e.g. '%' or 'seconds'")
    description: Optional[str] = Field(None, description="Human‑readable description")


class BossPenetrationResponse(BaseModel):
    skill_id: int = Field(..., description="Internal boss skill ID")
    skill_name: str = Field(..., description="Name of the boss skill")
    base_penetration: float = Field(..., description="Base penetration value")
    uber_penetration: float = Field(..., description="Uber (higher‑difficulty) penetration")
    unit: Optional[str] = Field(None, description="Unit, e.g. '%'")
    description: Optional[str] = Field(None, description="Description of the penetration stat")


class BuildRequest(BaseModel):
    character_class: CharacterClass = Field(
        ...,
        description="Primary character class (determines starting node)."
    )
    archetype: str = Field(
        ...,
        description="Build focus or damage type, e.g. 'Lightning', 'Physical'."
    )
    skill_gems: Optional[List[str]] = Field(
        None,
        description="Optional list of skill gem names to prioritize (e.g. ['Lightning Bolt'])."
    )
    goals: List[str] = Field(
        ...,
        description="List of high‑level goals, e.g. ['tanky', 'bossing', 'speed']. "
                    "Used to weight node selection."
    )
    max_points: int = Field(
        122,
        gt=0,
        description="Maximum passive points to spend (defaults to 122)."
    )
    include_ascendancy: bool = Field(
        False,
        description="Whether to include ascendancy keystones in the build."
    )


class BuildMetrics(BaseModel):
    life: float = Field(..., description="Total effective life.")
    armor: float = Field(..., description="Total armor value.")
    eshield: float = Field(..., description="Total energy shield.")
    damage_inc: Dict[str, float] = Field(
        ...,
        description="Mapping of damage type to % increased (e.g. {'Lightning': 180})."
    )
    crit_chance: float = Field(..., description="Total % critical strike chance.")
    total_points: int = Field(..., description="Number of passive points allocated.")


class BuildResponse(BaseModel):
    save: str = Field(
        ...,
        description="Maxroll‑compatible encoded save string."
    )
    url: HttpUrl = Field(
        ...,
        description="URL to load the build in Maxroll, e.g. https://maxroll.gg/poe2/passive-tree/?save=…"
    )
    metrics: BuildMetrics = Field(..., description="Computed stats for the build.")
    score: float = Field(..., description="Composite build score based on goals.")
    nodes: Optional[List[int]] = Field(
        None,
        description="(Optional) List of all allocated passive node IDs, in order."
    )
