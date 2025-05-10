# src/api/schemas.py
from pydantic import BaseModel

class StatDefinition(BaseModel):
    stat_key: str
    unit: str
    description: str

class BossPenetration(BaseModel):
    skill_id: int
    skill_name: str
    base_penetration: float
    uber_penetration: float
    unit: str
    description: str
