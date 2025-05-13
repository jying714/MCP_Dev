# src/api/main.py

import sqlite3
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.routing import APIRouter

from .schemas import (
    CharacterClass,
    StatResponse,
    BossPenetrationResponse,
    BuildRequest,
    BuildResponse,
    BuildMetrics,
)
from .deps import get_db
from .utils import (
    load_passive_graph,
    load_node_effects,
    load_parsed_mods,
    load_starting_node,
    load_ascendancy_nodes,
)
from .optimizer import optimize_path, GOAL_CRITERIA
from .metrics import compute_metrics

app = FastAPI()
router = APIRouter()


@router.get("/stats/{stat_key}", response_model=StatResponse)
def get_stat(stat_key: str, db: sqlite3.Connection = Depends(get_db)):
    cur = db.execute(
        "SELECT stat_key, unit, description FROM stat_definitions WHERE stat_key = ?",
        (stat_key,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Stat not found")
    return StatResponse(stat_key=row[0], unit=row[1], description=row[2])


@router.get(
    "/boss/penetration/{pen_type}",
    response_model=List[BossPenetrationResponse],
)
def get_boss_penetration(
    pen_type: str, db: sqlite3.Connection = Depends(get_db)
):
    rows = db.execute(
        """
        SELECT
          b.id, b.name, p.base_pen, p.uber_pen, sd.unit, sd.description
        FROM boss_skills_core b
        JOIN boss_skill_penetrations p
          ON p.skill_id = b.id
        JOIN stat_definitions sd
          ON sd.stat_key = p.pen_type
        WHERE p.pen_type = ?
        """,
        (pen_type,),
    ).fetchall()
    return [
        BossPenetrationResponse(
            skill_id=r[0],
            skill_name=r[1],
            base_penetration=r[2],
            uber_penetration=r[3],
            unit=r[4],
            description=r[5],
        )
        for r in rows
    ]


@router.post("/build", response_model=BuildResponse)
def build(
    req: BuildRequest,
    db: sqlite3.Connection = Depends(get_db),
):
    # 1) Get latest tree version
    vid_row = db.execute("SELECT MAX(version_id) FROM tree_versions;").fetchone()
    if not vid_row or vid_row[0] is None:
        raise HTTPException(status_code=500, detail="No tree versions available")
    version_id = vid_row[0]

    # 2) Load graph & data
    nodes, edges = load_passive_graph(db, version_id)
    node_effects = load_node_effects(db, version_id)
    parsed_mods = load_parsed_mods(db, version_id)
    try:
        start_node = load_starting_node(db, req.character_class.value, version_id)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    ascendancy_nodes: List[int] = []
    if req.include_ascendancy:
        ascendancy_nodes = load_ascendancy_nodes(
            db, req.character_class.value, version_id
        )

    # 3) Optimize path
    node_list = optimize_path(
        nodes,
        edges,
        node_effects,
        parsed_mods,
        start_node,
        ascendancy_nodes,
        goals=req.goals,
        max_points=req.max_points,
    )

    # 4) Compute metrics & score
    metrics = compute_metrics(node_list, node_effects, parsed_mods)
    from .main import score_build as _score_build  # avoid import cycle
    score = _score_build(metrics, req.goals)

    # 5) Stub out any save/URL fields (no Maxroll integration)
    save_str = ""
    url = ""

    return BuildResponse(
        save=save_str,
        url=url,
        metrics=metrics,
        score=score,
        nodes=node_list,
    )


def score_build(metrics: BuildMetrics, goals: List[str]) -> float:
    total_score = 0.0
    for goal in goals:
        criteria = GOAL_CRITERIA.get(goal.lower())
        if not criteria:
            continue
        for metric_key, weight in criteria.get("weights", {}).items():
            value = getattr(metrics, metric_key, 0.0)
            if metric_key in metrics.damage_inc:
                value = metrics.damage_inc[metric_key]
            total_score += value * weight
    return total_score


app.include_router(router)
