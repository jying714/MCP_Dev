import sqlite3
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from .schemas import (
    StatResponse,
    BossPenetrationResponse,
    BuildRequest,
    BuildResponse,
    BuildMetrics
)
from .deps import get_db
from .utils import (
    load_passive_graph,
    load_node_effects,
    load_parsed_mods,
    load_starting_node,
    load_ascendancy_nodes
)
from .optimizer import optimize_path, GOAL_CRITERIA
from .metrics import compute_metrics

router = APIRouter()


@router.get("/stats/{stat_key}", response_model=StatResponse)
def get_stat(stat_key: str, db: sqlite3.Connection = Depends(get_db)):
    cur = db.execute(
        "SELECT stat_key, unit, description FROM stat_definitions WHERE stat_key = ?",
        (stat_key,)
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Stat not found")
    return StatResponse(stat_key=row[0], unit=row[1], description=row[2])


@router.get(
    "/boss/penetration/{pen_type}",
    response_model=List[BossPenetrationResponse]
)
def get_boss_penetration(pen_type: str, db: sqlite3.Connection = Depends(get_db)):
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
        (pen_type,)
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
    db: sqlite3.Connection = Depends(get_db)
):
    # Determine latest tree version
    vid_row = db.execute("SELECT MAX(version_id) FROM tree_versions;").fetchone()
    if not vid_row or vid_row[0] is None:
        raise HTTPException(status_code=500, detail="No tree versions available")
    version_id = vid_row[0]

    # Load data with error handling
    try:
        nodes, edges = load_passive_graph(db, version_id)
        node_effects = load_node_effects(db, version_id)
        parsed_mods = load_parsed_mods(db, version_id)
        start_node = load_starting_node(db, req.character_class.value, version_id)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    ascendancy_nodes: List[int] = []
    if req.include_ascendancy:
        ascendancy_nodes = load_ascendancy_nodes(db, req.character_class.value, version_id)

    # Optimize path
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

    # Compute metrics & score
    metrics = compute_metrics(node_list, node_effects, parsed_mods)
    score = score_build(metrics, req.goals)

    # Encode Maxroll save
    save_str = encode_maxroll_save(node_list)
    url = f"https://maxroll.gg/poe2/passive-tree/?save={save_str}"

    return BuildResponse(
        save=save_str,
        url=url,
        metrics=metrics,
        score=score,
        nodes=node_list
    )


def score_build(metrics: BuildMetrics, goals: List[str]) -> float:
    total_score = 0.0
    for goal in goals:
        criteria = GOAL_CRITERIA.get(goal.lower())
        if not criteria:
            continue
        weights = criteria.get("weights", {})
        for metric_key, weight in weights.items():
            value = 0.0
            if hasattr(metrics, metric_key):
                value = getattr(metrics, metric_key)
            elif metric_key in metrics.damage_inc:
                value = metrics.damage_inc.get(metric_key, 0.0)
            total_score += value * weight
    return total_score


def encode_maxroll_save(node_list: List[int]) -> str:
    # TODO: implement actual Maxroll encoding
    return ""
