from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from pi.utils.version import get_version

REPO_VERSION = get_version()

def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None

def column_names(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}

def add_column_if_missing(
    conn: sqlite3.Connection,
    table_name: str,
    column_def_sql: str,
    column_name: str,
) -> None:
    cols = column_names(conn, table_name)
    if column_name not in cols:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_def_sql}")

def ensure_metadata_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS repo_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
            repo_version TEXT NOT NULL,
            note TEXT
        )
        """
    )

def record_repo_version(conn: sqlite3.Connection, note: str = "startup") -> None:
    ensure_metadata_table(conn)
    conn.execute(
        """
        INSERT INTO repo_metadata (repo_version, note)
        VALUES (?, ?)
        """,
        (REPO_VERSION, note),
    )

def ensure_repo_version_columns(
    conn: sqlite3.Connection,
    table_names: Iterable[str],
) -> None:
    for table in table_names:
        if not table_exists(conn, table):
            continue
        add_column_if_missing(conn, table, "repo_version TEXT", "repo_version")

def backfill_repo_version_if_null(
    conn: sqlite3.Connection,
    table_names: Iterable[str],
) -> None:
    for table in table_names:
        if not table_exists(conn, table):
            continue
        cols = column_names(conn, table)
        if "repo_version" not in cols:
            continue
        conn.execute(
            f"""
            UPDATE {table}
            SET repo_version = ?
            WHERE repo_version IS NULL OR TRIM(repo_version) = ''
            """,
            (REPO_VERSION,),
        )

def ensure_db_versioning(
    db_path: str | Path,
    table_names: Iterable[str],
    note: str = "startup",
) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_repo_version_columns(conn, table_names)
        backfill_repo_version_if_null(conn, table_names)
        record_repo_version(conn, note=note)
        conn.commit()
    finally:
        conn.close()
