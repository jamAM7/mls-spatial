"""
history.py — MLS Spatial Search Service
SQLite search history. Records every completed search for auditing and review.
Database file: mls_spatial.db (in project root, gitignored)
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from service.models import SearchResult

DB_PATH = Path(__file__).parent.parent / "mls_spatial.db"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the search_history table if it doesn't exist. Call once on startup."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                searched_at      TEXT,
                search_mode      TEXT,
                address_input    TEXT,
                address_resolved TEXT,
                subject_lot      TEXT,
                suburb           TEXT,
                lga              TEXT,
                radius_m         INTEGER,
                marks_radius_m   INTEGER,
                lot_count        INTEGER,
                plan_count       INTEGER,
                mark_count       INTEGER,
                surface_level_ahd REAL
            )
        """)


def record_search(result: SearchResult) -> None:
    """Insert a completed search into the history table."""
    from service.utils import lot_label
    with _get_connection() as conn:
        conn.execute("""
            INSERT INTO search_history (
                searched_at, search_mode, address_input, address_resolved,
                subject_lot, suburb, lga, radius_m, marks_radius_m,
                lot_count, plan_count, mark_count, surface_level_ahd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            result.search_mode,
            result.address.input_string,
            result.address.resolved_string,
            lot_label(result.subject_lot) if result.subject_lot else None,
            result.address.suburb,
            result.address.lga,
            result.search_radius_m,
            result.marks_radius_m,
            len(result.nearby_lots),
            len(result.plans),
            len(result.survey_marks),
            result.address.surface_level_ahd,
        ))


def get_history(limit: int = 20) -> list[dict]:
    """Return the last n searches as a list of dicts, most recent first."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM search_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]