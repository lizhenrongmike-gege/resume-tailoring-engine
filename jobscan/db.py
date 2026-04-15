"""SQLite storage and deduplication for JobScan."""
from __future__ import annotations

import json
import sqlite3
from datetime import date


class JobScanDB:
    def __init__(self, db_path: str = "jobscan/jobscan.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                lane INTEGER,
                fit_score INTEGER,
                why_it_fits TEXT,
                url TEXT,
                location TEXT,
                description TEXT,
                source TEXT,
                first_seen DATE NOT NULL,
                last_seen DATE NOT NULL,
                run_count INTEGER DEFAULT 1,
                status TEXT DEFAULT 'new',
                UNIQUE(company, title)
            );
            CREATE TABLE IF NOT EXISTS scan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date DATE NOT NULL,
                new_roles INTEGER,
                repeat_roles INTEGER,
                filtered_out INTEGER,
                lanes_summary TEXT
            );
        """)
        self.conn.commit()

    def is_seen(self, company: str, title: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM seen_jobs WHERE company = ? AND title = ?",
            (company, title),
        ).fetchone()
        return row is not None

    def insert_job(self, *, company: str, title: str, lane: int, fit_score: int,
                   why_it_fits: str, url: str, location: str, description: str,
                   source: str):
        today = date.today().isoformat()
        self.conn.execute(
            """INSERT INTO seen_jobs
               (company, title, lane, fit_score, why_it_fits, url, location,
                description, source, first_seen, last_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (company, title, lane, fit_score, why_it_fits, url, location,
             description, source, today, today),
        )
        self.conn.commit()

    def touch_job(self, company: str, title: str):
        today = date.today().isoformat()
        self.conn.execute(
            """UPDATE seen_jobs SET last_seen = ?, run_count = run_count + 1
               WHERE company = ? AND title = ?""",
            (today, company, title),
        )
        self.conn.commit()

    def mark_status(self, company: str, title: str, status: str):
        self.conn.execute(
            "UPDATE seen_jobs SET status = ? WHERE company = ? AND title = ?",
            (status, company, title),
        )
        self.conn.commit()

    def get_jobs(self, *, status: str | None = None, lane: int | None = None) -> list[dict]:
        query = "SELECT * FROM seen_jobs WHERE 1=1"
        params: list = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if lane:
            query += " AND lane = ?"
            params.append(lane)
        query += " ORDER BY fit_score DESC"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_repeats(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM seen_jobs WHERE run_count > 1 ORDER BY run_count DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def record_run(self, *, new_roles: int, repeat_roles: int, filtered_out: int,
                   lanes_summary: dict):
        self.conn.execute(
            """INSERT INTO scan_runs (run_date, new_roles, repeat_roles,
               filtered_out, lanes_summary) VALUES (?, ?, ?, ?, ?)""",
            (date.today().isoformat(), new_roles, repeat_roles, filtered_out,
             json.dumps(lanes_summary)),
        )
        self.conn.commit()

    def get_runs(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM scan_runs ORDER BY run_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()
