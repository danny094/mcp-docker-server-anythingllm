#!/usr/bin/env python3
import os
import json
import sqlite3
import datetime
from pathlib import Path

# -------------------------------------------------------------
# KONFIG
# -------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "decision.db"
RULES_DIR = BASE_DIR / "jsons"

# -------------------------------------------------------------
# SQL INITIALISIERUNG
# -------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS decision_rules (
        id TEXT PRIMARY KEY,
        category TEXT,
        language TEXT,
        pattern TEXT,
        tool TEXT,
        params TEXT,
        confidence REAL,
        examples TEXT,
        tags TEXT,
        author TEXT,
        source TEXT,
        enabled INTEGER,
        created_at TEXT
    )
    """)
    conn.commit()
    return conn

# -------------------------------------------------------------
# HILFSFUNKTIONEN
# -------------------------------------------------------------
def load_json_file(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Fehler beim Laden von {path.name}: {e}")
        return None


def insert_rule(conn, rule_data):
    c = conn.cursor()
    try:
        c.execute("""
            INSERT OR REPLACE INTO decision_rules
            (id, category, language, pattern, tool, params, confidence, examples, tags, author, source, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule_data.get("id"),
            rule_data.get("category", "default"),
            rule_data.get("language", "de"),
            json.dumps(rule_data.get("pattern", "")),
            rule_data.get("tool"),
            json.dumps(rule_data.get("params", {})),
            rule_data.get("confidence", 0.9),
            json.dumps(rule_data.get("examples", [])),
            json.dumps(rule_data.get("tags", [])),
            rule_data.get("author", "unknown"),
            rule_data.get("source", "local"),
            1 if rule_data.get("enabled", True) else 0,
            datetime.datetime.utcnow().isoformat()
        ))
        conn.commit()
    except Exception as e:
        print(f"❌ Fehler beim Einfügen von Regel {rule_data.get('id')}: {e}")

# -------------------------------------------------------------
# PARSER: SIMPLE vs. ADVANCED
# -------------------------------------------------------------
def parse_and_insert(conn, data, source_file):
    meta_author = "unknown"
    if isinstance(data, dict) and "meta" in data:
        meta_author = data["meta"].get("author", "unknown")

    # --- Advanced Structure ---
    if "categories" in data:
        for cat in data["categories"]:
            category_id = cat.get("id", "default")
            category_name = cat.get("name", {})
            rules = cat.get("rules", [])
            for rule in rules:
                # Sprache bestimmen
                if isinstance(rule.get("pattern"), dict):
                    for lang, pattern in rule["pattern"].items():
                        insert_rule(conn, {
                            "id": f"{rule.get('id','unknown')}_{lang}",
                            "category": category_id,
                            "language": lang,
                            "pattern": pattern,
                            "tool": rule.get("tool"),
                            "params": rule.get("params", {}),
                            "confidence": rule.get("confidence", 0.9),
                            "examples": rule.get("examples", {}).get(lang, []),
                            "tags": cat.get("tags", []),
                            "author": meta_author,
                            "source": source_file.name,
                            "enabled": rule.get("enabled", True)
                        })
                else:
                    insert_rule(conn, {
                        "id": rule.get("id","unknown"),
                        "category": category_id,
                        "language": data.get("meta", {}).get("default_language", "de"),
                        "pattern": rule.get("pattern"),
                        "tool": rule.get("tool"),
                        "params": rule.get("params", {}),
                        "confidence": rule.get("confidence", 0.9),
                        "examples": rule.get("examples", []),
                        "tags": cat.get("tags", []),
                        "author": meta_author,
                        "source": source_file.name,
                        "enabled": rule.get("enabled", True)
                    })

    # --- Simple Structure ---
    elif isinstance(data, dict) and "tool" in data:
        insert_rule(conn, {
            "id": data.get("id", "unknown"),
            "category": "default",
            "language": "de",
            "pattern": data.get("pattern"),
            "tool": data.get("tool"),
            "params": data.get("params", {}),
            "confidence": data.get("confidence", 0.9),
            "examples": data.get("examples", []),
            "tags": [],
            "author": data.get("author", "unknown"),
            "source": source_file.name,
            "enabled": data.get("enabled", True)
        })

    else:
        print(f"⚠️ Keine gültige Struktur erkannt in {source_file.name}")

# -------------------------------------------------------------
# MAIN
# -------------------------------------------------------------
def main():
    conn = init_db()
    json_files = [f for f in RULES_DIR.glob("*.json") if f.name != "example.json"]

    if not json_files:
        print("⚠️ Keine JSON-Regeln gefunden.")
        return

    print("📦 [INFO] Decision Rules Installer gestartet")

    total_new = 0
    for file in json_files:
        data = load_json_file(file)
        if not data:
            continue
        parse_and_insert(conn, data, file)
        total_new += 1

    print(f"📦 [INFO] ✅ {total_new} Regel-Dateien importiert.")
    print("📦 [INFO] 🏁 Installation abgeschlossen.")

    conn.close()

# -------------------------------------------------------------
if __name__ == "__main__":
    main()
