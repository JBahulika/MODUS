"""SQLite persistence for research jobs and reports."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings


def _connect() -> sqlite3.Connection:
    settings = get_settings()
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                report_json TEXT,
                error TEXT,
                viewer TEXT
            )
            """
        )
        # Lightweight migration for older DBs
        cols = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
        if "viewer" not in cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN viewer TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                step TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            )
            """
        )
        conn.commit()


def create_job(job_id: str, query: str, viewer: str | None = None) -> None:
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO jobs (id, query, status, created_at, updated_at, viewer) VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, query, "queued", now, now, viewer or "guest"),
        )
        conn.commit()


def update_job_status(job_id: str, status: str, error: str | None = None) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE jobs SET status = ?, error = ?, updated_at = ? WHERE id = ?",
            (status, error, _now(), job_id),
        )
        conn.commit()


def save_report(job_id: str, report: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE jobs SET status = ?, report_json = ?, updated_at = ? WHERE id = ?",
            ("completed", json.dumps(report), _now(), job_id),
        )
        conn.commit()


def add_event(job_id: str, step: str, message: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO job_events (job_id, step, message, created_at) VALUES (?, ?, ?, ?)",
            (job_id, step, message, _now()),
        )
        conn.execute(
            "UPDATE jobs SET updated_at = ? WHERE id = ?",
            (_now(), job_id),
        )
        conn.commit()


def get_job(job_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        report = json.loads(row["report_json"]) if row["report_json"] else None
        return {
            "id": row["id"],
            "query": row["query"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "report": report,
            "error": row["error"],
            "viewer": row["viewer"] if "viewer" in row.keys() else "guest",
        }


def get_events(job_id: str, after_id: int = 0) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, step, message, created_at
            FROM job_events
            WHERE job_id = ? AND id > ?
            ORDER BY id ASC
            """,
            (job_id, after_id),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "step": r["step"],
                "message": r["message"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]


def list_jobs(limit: int = 20, viewer: str | None = None) -> list[dict[str, Any]]:
    with _connect() as conn:
        if viewer:
            rows = conn.execute(
                """
                SELECT id, query, status, created_at, updated_at, viewer
                FROM jobs
                WHERE viewer = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (viewer, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, query, status, created_at, updated_at, viewer
                FROM jobs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
