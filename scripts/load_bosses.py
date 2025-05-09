#!/usr/bin/env python3
import sqlite3
import json
import os

DB_PATH           = os.path.join("db", "passive_tree.db")
BOSSES_JSON       = "data/bosses.json"
BOSS_SKILLS_JSON  = "data/boss_skills.json"

def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_boss_etl():
    print("▶ Loading Boss ETL…")
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # 1) version row
    cur.execute("INSERT INTO boss_versions DEFAULT VALUES;")
    version_id = cur.lastrowid

    # 2) raw snapshots
    for name, path in [("bosses", BOSSES_JSON), ("boss_skills", BOSS_SKILLS_JSON)]:
        raw = open(path, "r", encoding="utf-8").read()
        cur.execute(
            "INSERT INTO raw_boss_snapshots (version_id, raw_json) VALUES (?, ?);",
            (version_id, raw)
        )
        print(f"  • Raw {name} snapshot saved.")

    # 3) load JSON
    bosses = _load_json(BOSSES_JSON)
    skills = _load_json(BOSS_SKILLS_JSON)

    # 4) upsert bosses
    for key, meta in bosses.items():
        cur.execute("""
        INSERT OR IGNORE INTO bosses
          (version_id, key, name, tier, biome, description)
        VALUES (?, ?, ?, NULL, NULL, NULL);
        """, (version_id, key, key))
        boss_id = cur.execute(
            "SELECT id FROM bosses WHERE version_id=? AND key=?",
            (version_id, key)
        ).fetchone()[0]
        cur.execute("""
        UPDATE bosses
           SET armour_mult = ?, evasion_mult = ?, is_uber = ?
         WHERE id = ?;
        """, (
            meta.get("armourMult"),
            meta.get("evasionMult"),
            1 if meta.get("isUber") else 0,
            boss_id
        ))

    # 5) prepare boss lookup SQL (overrides + fallback)
    FIND_BOSS_SQL = """
    WITH mapped AS (
      SELECT b.id AS boss_id
        FROM skill_to_boss m
        JOIN bosses b ON m.boss_key = b.key
       WHERE b.version_id = :ver
         AND m.skill_key_pattern = :skill
    ), fallback AS (
      SELECT id AS boss_id
        FROM bosses
       WHERE version_id = :ver
         AND INSTR(:skill, key) > 0
       ORDER BY LENGTH(key) DESC
       LIMIT 1
    )
    SELECT boss_id FROM mapped
    UNION ALL
    SELECT boss_id FROM fallback
    LIMIT 1;
    """

    # 6) assign skills and populate normalized tables
    for skill_key, info in skills.items():
        row = cur.execute(
            FIND_BOSS_SQL,
            {"ver": version_id, "skill": skill_key}
        ).fetchone()

        if not row:
            # record unmatched for later review
            print(f"⚠️  Unmatched skill: '{skill_key}'")
            cur.execute(
                "INSERT OR IGNORE INTO unmatched_skills (version_id, skill_key) VALUES (?, ?);",
                (version_id, skill_key)
            )
            continue

        boss_id = row[0]

        # 6a) legacy insert
        cur.execute("""
        INSERT INTO boss_skills
          (boss_id, skill_key, name, description, cooldown, tags)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (
            boss_id,
            skill_key,
            info.get("tooltip"),
            info.get("tooltip"),
            info.get("speed"),
            json.dumps(info.get("tags", {}))
        ))

        # 6b) normalized core table
        cur.execute("""
        INSERT OR IGNORE INTO boss_skills_core
          (boss_id, skill_key, name, damage_type, base_speed,
           crit_chance, uber_multiplier, uber_speed, earlier_uber_flag, tooltip)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            boss_id,
            skill_key,
            info.get("tooltip"),
            info.get("DamageType"),
            info.get("speed"),
            info.get("critChance", 0),
            info.get("UberDamageMultiplier"),
            info.get("UberSpeed"),
            1 if info.get("earlierUber") else 0,
            info.get("tooltip"),
        ))
        # fetch the newly inserted or existing core ID
        skill_id = cur.execute(
            "SELECT id FROM boss_skills_core WHERE boss_id=? AND skill_key=?",
            (boss_id, skill_key)
        ).fetchone()[0]

        # 6c) multipliers
        for dmg_type, (base, ratio) in info.get("DamageMultipliers", {}).items():
            cur.execute("""
            INSERT OR REPLACE INTO boss_skill_multipliers
              (skill_id, damage_type, base_value, ratio_value)
            VALUES (?, ?, ?, ?);
            """, (skill_id, dmg_type, base, ratio))

        # 6d) penetrations (base vs uber)
        for phase, pen_dict in (("base", info.get("DamagePenetrations", {})),
                                ("uber", info.get("UberDamagePenetrations", {}))):
            for pen_type, pen_val in pen_dict.items():
                # ensure row exists
                cur.execute("""
                INSERT OR IGNORE INTO boss_skill_penetrations
                  (skill_id, pen_type)
                VALUES (?, ?);
                """, (skill_id, pen_type))
                # update the appropriate column
                col = "base_pen" if phase == "base" else "uber_pen"
                cur.execute(f"""
                UPDATE boss_skill_penetrations
                   SET {col} = ?
                 WHERE skill_id = ? AND pen_type = ?;
                """, (pen_val or 0, skill_id, pen_type))

        # 6e) additional stats (base vs uber)
        for phase in ("base", "uber"):
            for stat_key, stat_val in info.get("additionalStats", {}).get(phase, {}).items():
                is_flag = 1 if stat_val == "flag" else 0
                val = None if is_flag else stat_val
                cur.execute("""
                INSERT OR REPLACE INTO boss_skill_additional_stats
                  (skill_id, phase, stat_key, stat_value, is_flag)
                VALUES (?, ?, ?, ?, ?);
                """, (skill_id, phase, stat_key, val, is_flag))

    conn.commit()
    conn.close()
    print(f"✔️  Boss ETL complete (version {version_id}).")

if __name__ == "__main__":
    load_boss_etl()
