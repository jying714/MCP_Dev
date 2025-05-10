# src/api/main.py
from fastapi import FastAPI, HTTPException, Depends
from typing import List
from sqlite3 import Connection

from .deps import get_db
from .schemas import StatDefinition, BossPenetration

app = FastAPI(title="MCP Build Coach API", version="0.1")

@app.get("/stats/{stat_key}", response_model=StatDefinition)
def read_stat_definition(stat_key: str, db: Connection = Depends(get_db)):
    row = db.execute(
        "SELECT stat_key, unit, description FROM stat_definitions WHERE stat_key = ?",
        (stat_key,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Stat not found")
    return StatDefinition(stat_key=row[0], unit=row[1], description=row[2])

@app.get("/boss/penetration/fire", response_model=List[BossPenetration])
def list_fire_penetration(db: Connection = Depends(get_db)):
    rows = db.execute("""
        SELECT 
          skill_id, skill_name, base_penetration, uber_penetration, unit, description
        FROM vw_boss_fire_penetration;
    """).fetchall()
    return [BossPenetration(**{
        "skill_id": r[0],
        "skill_name": r[1],
        "base_penetration": r[2],
        "uber_penetration": r[3],
        "unit": r[4],
        "description": r[5],
    }) for r in rows]

# Health check
@app.get("/health")
def health():
    return {"status": "ok"}
