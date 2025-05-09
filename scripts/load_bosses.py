#!/usr/bin/env python3
import sqlite3
import json

DB_PATH            = "passive_tree.db"
BOSSES_JSON        = "data/bosses.json"
BOSS_SKILLS_JSON   = "data/boss_skills.json"

def load_boss_etl():
    print("▶ Loading Boss ETL…")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) version row
    cur.execute("INSERT INTO boss_versions DEFAULT VALUES;")
    version_id = cur.lastrowid

    # 2) raw snapshots
    for name, path in [("bosses", BOSSES_JSON), ("boss_skills", BOSS_SKILLS_JSON)]:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        cur.execute(
            "INSERT INTO raw_boss_snapshots (version_id, raw_json) VALUES (?, ?);",
            (version_id, raw)
        )
        print(f"  • Raw {name} snapshot saved.")

    # 3) parse JSON
    bosses      = json.loads(open(BOSSES_JSON,      encoding="utf-8").read())
    boss_skills = json.loads(open(BOSS_SKILLS_JSON, encoding="utf-8").read())

    # 4) load bosses metadata
    for key, meta in bosses.items():
        cur.execute("""
        INSERT OR IGNORE INTO bosses
          (version_id, key, name, tier, biome, description)
        VALUES (?, ?, ?, NULL, NULL, NULL);
        """, (
            version_id,
            key,
            key  # no display name in this file—use key as name
        ))
        cur.execute("SELECT id FROM bosses WHERE version_id=? AND key=?",
                    (version_id, key))
        boss_id = cur.fetchone()[0]

        # update armour/evasion/isUber fields if present in schema
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

    # 5) load boss skills
    for boss_name, skills in boss_skills.items():
        # find boss_id by matching key/name
        cur.execute("""
          SELECT id FROM bosses
           WHERE version_id=? AND key=?
        """, (version_id, boss_name))
        row = cur.fetchone()
        if not row:
            print(f"⚠️  No boss entry for skills '{boss_name}', skipping.")
            continue
        boss_id = row[0]

        for skill_key, info in skills.items():
            cur.execute("""
            INSERT INTO boss_skills
              (boss_id, skill_key, name, description, cooldown, tags)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (
                boss_id,
                skill_key,
                info.get("tooltip"),           # use tooltip as human‑readable name/desc
                info.get("tooltip"),
                info.get("speed"),             # treat as cooldown proxy
                json.dumps(info.get("tags", {}))
            ))

    conn.commit()
    conn.close()
    print(f"✔️  Boss ETL complete (version {version_id}).")

if __name__ == "__main__":
    load_boss_etl()
