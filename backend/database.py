"""SQLite persistence layer for Swotify.

Thread-safe approach: open a fresh connection per operation.
All timestamps stored as ISO-8601 UTC strings.
"""

import os
import sqlite3
import uuid
from datetime import datetime, timezone

DB_PATH = os.environ.get("SWOTIFY_DB", os.path.join(os.path.dirname(__file__), "swotify.db"))


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_timestamp(ts_iso: str) -> float:
    try:
        return datetime.strptime(ts_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (ValueError, TypeError):
        return 0.0


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    website     TEXT,
    tracking_id TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS visits (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking_id TEXT NOT NULL,
    entity_id   INTEGER,
    path        TEXT DEFAULT '/',
    title       TEXT DEFAULT '',
    referrer    TEXT DEFAULT '',
    user_agent  TEXT DEFAULT '',
    device      TEXT DEFAULT 'desktop',
    browser     TEXT DEFAULT 'unknown',
    lang        TEXT DEFAULT '',
    width       INTEGER DEFAULT 0,
    height      INTEGER DEFAULT 0,
    visitor_id  TEXT DEFAULT '',
    ts          TEXT NOT NULL,
    duration_s  REAL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_visits_tid ON visits (tracking_id);
CREATE INDEX IF NOT EXISTS idx_visits_entity ON visits (entity_id, ts);

CREATE TABLE IF NOT EXISTS assessments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id  INTEGER NOT NULL,
    responses  TEXT NOT NULL,
    scores     TEXT NOT NULL,
    swot       TEXT NOT NULL,
    impact     TEXT NOT NULL,
    agent_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id  INTEGER NOT NULL,
    filename   TEXT NOT NULL,
    mime       TEXT DEFAULT '',
    size       INTEGER DEFAULT 0,
    text       TEXT DEFAULT '',
    source     TEXT DEFAULT 'client',
    created_at TEXT NOT NULL
);
"""


def init_db() -> None:
    conn = _connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------
def create_entity(name: str, website: str = "") -> dict:
    tracking_id = uuid.uuid4().hex[:16]
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO entities (name, website, tracking_id, created_at) VALUES (?, ?, ?, ?)",
            (name, website or "", tracking_id, now_iso()),
        )
        conn.commit()
        return get_entity(cur.lastrowid)
    finally:
        conn.close()


def get_entity(entity_id: int) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_entity_by_tracking_id(tracking_id: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM entities WHERE tracking_id = ?", (tracking_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_entities() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM entities ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Visits
# ---------------------------------------------------------------------------
def record_visit(v: dict) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            """INSERT INTO visits
               (tracking_id, entity_id, path, title, referrer, user_agent, device,
                browser, lang, width, height, visitor_id, ts, duration_s)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                v.get("tracking_id", ""),
                v.get("entity_id"),
                v.get("path", "/"),
                v.get("title", ""),
                v.get("referrer", ""),
                v.get("user_agent", ""),
                v.get("device", "desktop"),
                v.get("browser", "unknown"),
                v.get("lang", ""),
                v.get("width", 0),
                v.get("height", 0),
                v.get("visitor_id", ""),
                v.get("ts", now_iso()),
                v.get("duration_s", 0.0),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_visit_duration(visit_id: int, duration_s: float) -> None:
    conn = _connect()
    try:
        conn.execute("UPDATE visits SET duration_s = ? WHERE id = ?", (duration_s, visit_id))
        conn.commit()
    finally:
        conn.close()


def visits_in_range(entity_id: int, start_iso: str, end_iso: str) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            """SELECT * FROM visits
               WHERE entity_id = ? AND ts >= ? AND ts < ?
               ORDER BY ts DESC""",
            (entity_id, start_iso, end_iso),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def visits_today(entity_id: int) -> list[dict]:
    conn = _connect()
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rows = conn.execute(
            """SELECT * FROM visits WHERE entity_id = ? AND ts >= ?""",
            (entity_id, f"{today}T00:00:00Z"),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def live_visits(entity_id: int, minutes: int = 10) -> list[dict]:
    import time as _time

    cutoff = datetime.now(timezone.utc).timestamp() - minutes * 60
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return visits_in_range(entity_id, cutoff_iso, now_iso())


# ---------------------------------------------------------------------------
# Assessments
# ---------------------------------------------------------------------------
def save_assessment(entity_id: int, data: dict) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            """INSERT INTO assessments (entity_id, responses, scores, swot, impact, agent_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                entity_id,
                data.get("responses_json", "{}"),
                data.get("scores_json", "{}"),
                data.get("swot_json", "{}"),
                data.get("impact_json", "[]"),
                data.get("agent_json"),
                now_iso(),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def latest_assessment(entity_id: int) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM assessments WHERE entity_id = ? ORDER BY id DESC LIMIT 1",
            (entity_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def all_assessments(entity_id: int) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM assessments WHERE entity_id = ? ORDER BY id DESC",
            (entity_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
def save_document(entity_id: int, filename: str, mime: str, size: int, text: str, source: str) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            """INSERT INTO documents (entity_id, filename, mime, size, text, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (entity_id, filename, mime, size, text, source, now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_documents(entity_id: int) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM documents WHERE entity_id = ? ORDER BY id DESC",
            (entity_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_document(doc_id: int) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_document(doc_id: int) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
    finally:
        conn.close()
