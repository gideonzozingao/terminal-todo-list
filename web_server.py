#!/usr/bin/env python3
"""
web_server.py — ZUQONTECH TODO  Web Interface

Starts an HTTP server on a configurable port (default 8080) that:
  • Serves the single-page frontend (index.html) from the same directory
  • Exposes a JSON REST API backed by the same SQLite DB the TUI uses

REST API
--------
  GET    /api/tasks                       list all tasks (with subtask counts)
  POST   /api/tasks                       create task
  GET    /api/tasks/<id>                  get one task
  PUT    /api/tasks/<id>                  update task
  DELETE /api/tasks/<id>                  delete task + its subtasks

  GET    /api/tasks/<id>/subtasks         list subtasks for a task
  POST   /api/tasks/<id>/subtasks         create subtask
  PUT    /api/subtasks/<id>               update subtask
  DELETE /api/subtasks/<id>              delete subtask

Run:
  python3 web_server.py            # port 8080
  python3 web_server.py 9000       # custom port
"""

import http.server
import json
import os
import re
import sqlite3
import sys
import urllib.parse
from datetime import date, datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

DB_PATH   = os.path.expanduser("~/.todo_tasks.db")
PORT      = int(sys.argv[1]) if len(sys.argv) > 1 else 8555
SERVE_DIR = Path(__file__).parent          # directory this file lives in

STATUSES  = ["todo", "in-progress", "on-hold", "done"]

# ── Database helpers ──────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_db() as conn:
        # Create tables if they don't exist yet (fresh install).
        # NOTE: subtasks is defined here without 'description' intentionally —
        # the TUI's database.py may also omit it.  The migration block below
        # adds any missing columns to both tables regardless of who created them.
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            status      TEXT    DEFAULT 'todo',
            start_date  TEXT    DEFAULT '',
            due_date    TEXT    DEFAULT '',
            created_at  TEXT    DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS subtasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            title       TEXT    NOT NULL,
            status      TEXT    DEFAULT 'todo',
            start_date  TEXT    DEFAULT '',
            due_date    TEXT    DEFAULT '',
            created_at  TEXT    DEFAULT (datetime('now'))
        );
        """)

        # ── Migrations ────────────────────────────────────────────────────────
        # Safely add any columns the TUI schema may not have included.
        # PRAGMA table_info() lets us check before ALTER so we never crash
        # on a column that already exists.
        _migrate(conn, "tasks", [
            ("description", "TEXT DEFAULT ''"),
            ("start_date",  "TEXT DEFAULT ''"),
            ("due_date",    "TEXT DEFAULT ''"),
            ("created_at",  "TEXT DEFAULT (datetime('now'))"),
        ])
        _migrate(conn, "subtasks", [
            ("description", "TEXT DEFAULT ''"),
            ("start_date",  "TEXT DEFAULT ''"),
            ("due_date",    "TEXT DEFAULT ''"),
            ("created_at",  "TEXT DEFAULT (datetime('now'))"),
        ])


def _migrate(conn: sqlite3.Connection, table: str, columns: list[tuple]) -> None:
    """Add *columns* to *table* if they are not already present."""
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for col, ddl in columns:
        if col not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
            print(f"[migration] {table}: added column '{col}'")


def row_to_dict(row) -> dict:
    return dict(row) if row else None


def rows_to_list(rows) -> list:
    return [dict(r) for r in rows]

# ── Date helpers ──────────────────────────────────────────────────────────────

_DATE_FMTS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")

def parse_date(s: str):
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except (ValueError, AttributeError):
            pass
    return None

def date_urgency(due_str: str) -> str | None:
    if not due_str:
        return None
    d = parse_date(due_str)
    if not d:
        return None
    delta = (d - date.today()).days
    if delta < 0:   return "overdue"
    if delta == 0:  return "today"
    if delta <= 3:  return "soon"
    return None

def enrich_task(t: dict) -> dict:
    t["urgency"] = date_urgency(t.get("due_date", ""))
    return t

# ── Request handler ───────────────────────────────────────────────────────────

class TodoHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    # ── Routing helpers ───────────────────────────────────────────────────────

    def send_json(self, data, status: int = 200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, msg: str, status: int = 400):
        self.send_json({"error": msg}, status)

    def read_json(self) -> dict | None:
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return None

    def send_file(self, path: Path):
        if not path.exists():
            self.send_error_json("Not found", 404)
            return
        mime = {
            ".html": "text/html; charset=utf-8",
            ".css":  "text/css",
            ".js":   "application/javascript",
            ".ico":  "image/x-icon",
        }.get(path.suffix, "application/octet-stream")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ── CORS pre-flight ───────────────────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── GET ───────────────────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path.rstrip("/")

        # Static files
        if path == "" or path == "/":
            self.send_file(SERVE_DIR / "index.html")
            return
        if not path.startswith("/api"):
            fpath = SERVE_DIR / path.lstrip("/")
            self.send_file(fpath)
            return

        # GET /api/tasks
        if path == "/api/tasks":
            qs     = urllib.parse.parse_qs(parsed.query)
            status = qs.get("status", [None])[0]
            search = qs.get("q", [None])[0]
            with get_db() as db:
                sql    = """
                    SELECT t.*,
                           COUNT(s.id)                                         AS subtask_count,
                           SUM(CASE WHEN s.status='done' THEN 1 ELSE 0 END)   AS subtask_done
                    FROM tasks t
                    LEFT JOIN subtasks s ON s.task_id = t.id
                """
                where, params = [], []
                if status:
                    where.append("t.status = ?"); params.append(status)
                if search:
                    where.append("(t.title LIKE ? OR t.description LIKE ?)")
                    params += [f"%{search}%", f"%{search}%"]
                if where:
                    sql += " WHERE " + " AND ".join(where)
                sql += " GROUP BY t.id ORDER BY t.created_at DESC"
                rows = db.execute(sql, params).fetchall()
            tasks = [enrich_task(row_to_dict(r)) for r in rows]
            self.send_json(tasks)
            return

        # GET /api/tasks/<id>
        m = re.fullmatch(r"/api/tasks/(\d+)", path)
        if m:
            tid = int(m.group(1))
            with get_db() as db:
                row = db.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
            if not row:
                self.send_error_json("Task not found", 404); return
            self.send_json(enrich_task(row_to_dict(row)))
            return

        # GET /api/tasks/<id>/subtasks
        m = re.fullmatch(r"/api/tasks/(\d+)/subtasks", path)
        if m:
            tid = int(m.group(1))
            with get_db() as db:
                rows = db.execute(
                    "SELECT * FROM subtasks WHERE task_id=? ORDER BY created_at",
                    (tid,)
                ).fetchall()
            self.send_json([enrich_task(row_to_dict(r)) for r in rows])
            return

        # GET /api/stats
        if path == "/api/stats":
            with get_db() as db:
                total   = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
                by_st   = db.execute(
                    "SELECT status, COUNT(*) as n FROM tasks GROUP BY status"
                ).fetchall()
                overdue = db.execute(
                    "SELECT COUNT(*) FROM tasks WHERE due_date != '' AND due_date < date('now') AND status != 'done'"
                ).fetchone()[0]
                soon    = db.execute(
                    "SELECT COUNT(*) FROM tasks WHERE due_date != '' AND due_date >= date('now') AND due_date <= date('now','+3 days') AND status != 'done'"
                ).fetchone()[0]
            stats = {
                "total": total,
                "overdue": overdue,
                "due_soon": soon,
                "by_status": {r["status"]: r["n"] for r in by_st},
            }
            self.send_json(stats)
            return

        self.send_error_json("Not found", 404)

    # ── POST ──────────────────────────────────────────────────────────────────

    def do_POST(self):
        path = self.path.rstrip("/")
        body = self.read_json()
        if body is None:
            self.send_error_json("Invalid JSON"); return

        # POST /api/tasks
        if path == "/api/tasks":
            title = (body.get("title") or "").strip()
            if not title:
                self.send_error_json("title is required"); return
            if body.get("status") and body["status"] not in STATUSES:
                self.send_error_json(f"status must be one of {STATUSES}"); return
            with get_db() as db:
                cur = db.execute(
                    "INSERT INTO tasks (title, description, status, start_date, due_date) VALUES (?,?,?,?,?)",
                    (title,
                     body.get("description", ""),
                     body.get("status", "todo"),
                     body.get("start_date", ""),
                     body.get("due_date", ""))
                )
                row = db.execute("SELECT * FROM tasks WHERE id=?", (cur.lastrowid,)).fetchone()
            self.send_json(enrich_task(row_to_dict(row)), 201)
            return

        # POST /api/tasks/<id>/subtasks
        m = re.fullmatch(r"/api/tasks/(\d+)/subtasks", path)
        if m:
            tid   = int(m.group(1))
            title = (body.get("title") or "").strip()
            if not title:
                self.send_error_json("title is required"); return
            with get_db() as db:
                task = db.execute("SELECT id FROM tasks WHERE id=?", (tid,)).fetchone()
                if not task:
                    self.send_error_json("Parent task not found", 404); return
                cur = db.execute(
                    "INSERT INTO subtasks (task_id, title, description, status, start_date, due_date) VALUES (?,?,?,?,?,?)",
                    (tid, title,
                     body.get("description", ""),
                     body.get("status", "todo"),
                     body.get("start_date", ""),
                     body.get("due_date", ""))
                )
                row = db.execute("SELECT * FROM subtasks WHERE id=?", (cur.lastrowid,)).fetchone()
            self.send_json(enrich_task(row_to_dict(row)), 201)
            return

        self.send_error_json("Not found", 404)

    # ── PUT ───────────────────────────────────────────────────────────────────

    def do_PUT(self):
        path = self.path.rstrip("/")
        body = self.read_json()
        if body is None:
            self.send_error_json("Invalid JSON"); return

        # PUT /api/tasks/<id>
        m = re.fullmatch(r"/api/tasks/(\d+)", path)
        if m:
            tid = int(m.group(1))
            with get_db() as db:
                row = db.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
                if not row:
                    self.send_error_json("Task not found", 404); return
                cur = dict(row)
                cur.update({k: body[k] for k in ("title","description","status","start_date","due_date") if k in body})
                if not cur["title"].strip():
                    self.send_error_json("title cannot be empty"); return
                if cur["status"] not in STATUSES:
                    self.send_error_json(f"status must be one of {STATUSES}"); return
                db.execute(
                    "UPDATE tasks SET title=?,description=?,status=?,start_date=?,due_date=? WHERE id=?",
                    (cur["title"], cur["description"], cur["status"],
                     cur["start_date"], cur["due_date"], tid)
                )
                row = db.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
            self.send_json(enrich_task(row_to_dict(row)))
            return

        # PUT /api/subtasks/<id>
        m = re.fullmatch(r"/api/subtasks/(\d+)", path)
        if m:
            sid = int(m.group(1))
            with get_db() as db:
                row = db.execute("SELECT * FROM subtasks WHERE id=?", (sid,)).fetchone()
                if not row:
                    self.send_error_json("Subtask not found", 404); return
                cur = dict(row)
                cur.update({k: body[k] for k in ("title","description","status","start_date","due_date") if k in body})
                if not cur["title"].strip():
                    self.send_error_json("title cannot be empty"); return
                if cur["status"] not in STATUSES:
                    self.send_error_json(f"status must be one of {STATUSES}"); return
                db.execute(
                    "UPDATE subtasks SET title=?,description=?,status=?,start_date=?,due_date=? WHERE id=?",
                    (cur["title"], cur["description"], cur["status"],
                     cur["start_date"], cur["due_date"], sid)
                )
                row = db.execute("SELECT * FROM subtasks WHERE id=?", (sid,)).fetchone()
            self.send_json(enrich_task(row_to_dict(row)))
            return

        self.send_error_json("Not found", 404)

    # ── DELETE ────────────────────────────────────────────────────────────────

    def do_DELETE(self):
        path = self.path.rstrip("/")

        # DELETE /api/tasks/<id>
        m = re.fullmatch(r"/api/tasks/(\d+)", path)
        if m:
            tid = int(m.group(1))
            with get_db() as db:
                row = db.execute("SELECT id FROM tasks WHERE id=?", (tid,)).fetchone()
                if not row:
                    self.send_error_json("Task not found", 404); return
                db.execute("DELETE FROM tasks WHERE id=?", (tid,))
            self.send_json({"deleted": tid})
            return

        # DELETE /api/subtasks/<id>
        m = re.fullmatch(r"/api/subtasks/(\d+)", path)
        if m:
            sid = int(m.group(1))
            with get_db() as db:
                row = db.execute("SELECT id FROM subtasks WHERE id=?", (sid,)).fetchone()
                if not row:
                    self.send_error_json("Subtask not found", 404); return
                db.execute("DELETE FROM subtasks WHERE id=?", (sid,))
            self.send_json({"deleted": sid})
            return

        self.send_error_json("Not found", 404)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), TodoHandler)
    print(f"╔══════════════════════════════════════════╗")
    print(f"║  ZUQONTECH TODO  —  Web Interface        ║")
    print(f"╠══════════════════════════════════════════╣")
    print(f"║  http://localhost:{PORT:<25} ║")
    print(f"║  DB: {DB_PATH:<36} ║")
    print(f"║  Ctrl+C to stop                          ║")
    print(f"╚══════════════════════════════════════════╝")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")