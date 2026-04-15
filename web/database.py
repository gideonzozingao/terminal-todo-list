"""
web/database.py — Database access layer.

Responsibilities
----------------
- Open SQLite connections with sensible defaults
- Create the schema on a fresh install
- Run non-destructive migrations so the web server works against
  databases created by the TUI (which may be missing columns)
- Provide typed CRUD helpers for tasks and subtasks

Nothing in this module knows about HTTP or JSON.
"""

import sqlite3
from typing import Any

from .config import DB_PATH, STATUSES, TASK_FIELDS

# ── Connection ────────────────────────────────────────────────────────────────


def get_db() -> sqlite3.Connection:
    """Open and return a new SQLite connection with row-dict access enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Schema & migrations ───────────────────────────────────────────────────────


def init_db() -> None:
    """
    Ensure the schema exists and is up-to-date.

    Safe to call on every startup:
    - ``CREATE TABLE IF NOT EXISTS`` is a no-op when tables already exist.
    - ``_migrate()`` only runs ``ALTER TABLE ADD COLUMN`` for columns that
      are genuinely absent, so pre-existing TUI databases are updated
      non-destructively without losing any data.
    """
    with get_db() as conn:
        _create_tables(conn)
        _run_migrations(conn)


def _create_tables(conn: sqlite3.Connection) -> None:
    """Create base tables if they do not already exist."""
    conn.executescript(
        """
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
    """
    )


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Add columns that the TUI schema may not have included."""
    _migrate(
        conn,
        "tasks",
        [
            ("description", "TEXT DEFAULT ''"),
            ("start_date", "TEXT DEFAULT ''"),
            ("due_date", "TEXT DEFAULT ''"),
            ("created_at", "TEXT DEFAULT (datetime('now'))"),
        ],
    )
    _migrate(
        conn,
        "subtasks",
        [
            ("description", "TEXT DEFAULT ''"),
            ("start_date", "TEXT DEFAULT ''"),
            ("due_date", "TEXT DEFAULT ''"),
            ("created_at", "TEXT DEFAULT (datetime('now'))"),
        ],
    )


def _migrate(
    conn: sqlite3.Connection,
    table: str,
    columns: list[tuple[str, str]],
) -> None:
    """
    Add each ``(column, ddl)`` pair to *table* if not already present.

    Uses ``PRAGMA table_info`` to inspect the live schema; no crash if the
    column already exists.
    """
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for col, ddl in columns:
        if col not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
            print(f"[migration] {table}: added column '{col}'")


# ── Helpers ───────────────────────────────────────────────────────────────────


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    """Convert a ``sqlite3.Row`` to a plain dict, or return ``None``."""
    return dict(row) if row else None


# ── Task CRUD ─────────────────────────────────────────────────────────────────


def list_tasks(status: str | None = None, search: str | None = None) -> list[dict]:
    """
    Return all tasks with subtask counts, optionally filtered.

    Parameters
    ----------
    status : filter to a single status string, or ``None`` for all.
    search : substring match against title and description, or ``None``.
    """
    sql = """
        SELECT t.*,
               COUNT(s.id)                                       AS subtask_count,
               SUM(CASE WHEN s.status = 'done' THEN 1 ELSE 0 END) AS subtask_done
        FROM tasks t
        LEFT JOIN subtasks s ON s.task_id = t.id
    """
    where: list[str] = []
    params: list[Any] = []

    if status:
        where.append("t.status = ?")
        params.append(status)
    if search:
        where.append("(t.title LIKE ? OR t.description LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]

    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " GROUP BY t.id ORDER BY t.created_at DESC"

    with get_db() as db:
        return [row_to_dict(r) for r in db.execute(sql, params).fetchall()]


def get_task(task_id: int) -> dict | None:
    """Return one task by ID, or ``None`` if not found."""
    with get_db() as db:
        return row_to_dict(
            db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        )


def create_task(data: dict) -> dict:
    """
    Insert a new task row and return the created record.

    *data* must contain ``title``; all other fields are optional.
    """
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO tasks (title, description, status, start_date, due_date)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                data["title"],
                data.get("description", ""),
                data.get("status", "todo"),
                data.get("start_date", ""),
                data.get("due_date", ""),
            ),
        )
        return row_to_dict(
            db.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
        )


def update_task(task_id: int, data: dict) -> dict | None:
    """
    Apply a partial update to a task and return the updated record.

    Only fields present in *data* and listed in ``TASK_FIELDS`` are changed.
    Returns ``None`` if the task does not exist.
    """
    with get_db() as db:
        row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        merged = {**dict(row), **{k: data[k] for k in TASK_FIELDS if k in data}}
        db.execute(
            "UPDATE tasks"
            " SET title = ?, description = ?, status = ?, start_date = ?, due_date = ?"
            " WHERE id = ?",
            (
                merged["title"],
                merged["description"],
                merged["status"],
                merged["start_date"],
                merged["due_date"],
                task_id,
            ),
        )
        return row_to_dict(
            db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        )


def delete_task(task_id: int) -> bool:
    """
    Delete a task and (via CASCADE) all its subtasks.

    Returns ``True`` if a row was deleted, ``False`` if it did not exist.
    """
    with get_db() as db:
        if not db.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone():
            return False
        db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return True


# ── Subtask CRUD ──────────────────────────────────────────────────────────────


def list_subtasks(task_id: int) -> list[dict]:
    """Return all subtasks for *task_id*, ordered by creation time."""
    with get_db() as db:
        return [
            row_to_dict(r)
            for r in db.execute(
                "SELECT * FROM subtasks WHERE task_id = ? ORDER BY created_at",
                (task_id,),
            ).fetchall()
        ]


def get_subtask(subtask_id: int) -> dict | None:
    """Return one subtask by ID, or ``None`` if not found."""
    with get_db() as db:
        return row_to_dict(
            db.execute("SELECT * FROM subtasks WHERE id = ?", (subtask_id,)).fetchone()
        )


def create_subtask(task_id: int, data: dict) -> dict | None:
    """
    Insert a new subtask under *task_id* and return it.

    Returns ``None`` if the parent task does not exist.
    """
    with get_db() as db:
        if not db.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone():
            return None
        cur = db.execute(
            "INSERT INTO subtasks"
            " (task_id, title, description, status, start_date, due_date)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                task_id,
                data["title"],
                data.get("description", ""),
                data.get("status", "todo"),
                data.get("start_date", ""),
                data.get("due_date", ""),
            ),
        )
        return row_to_dict(
            db.execute(
                "SELECT * FROM subtasks WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
        )


def update_subtask(subtask_id: int, data: dict) -> dict | None:
    """
    Apply a partial update to a subtask and return the updated record.

    Returns ``None`` if the subtask does not exist.
    """
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM subtasks WHERE id = ?", (subtask_id,)
        ).fetchone()
        if not row:
            return None
        merged = {**dict(row), **{k: data[k] for k in TASK_FIELDS if k in data}}
        db.execute(
            "UPDATE subtasks"
            " SET title = ?, description = ?, status = ?, start_date = ?, due_date = ?"
            " WHERE id = ?",
            (
                merged["title"],
                merged["description"],
                merged["status"],
                merged["start_date"],
                merged["due_date"],
                subtask_id,
            ),
        )
        return row_to_dict(
            db.execute("SELECT * FROM subtasks WHERE id = ?", (subtask_id,)).fetchone()
        )


def delete_subtask(subtask_id: int) -> bool:
    """
    Delete a single subtask.

    Returns ``True`` if deleted, ``False`` if not found.
    """
    with get_db() as db:
        if not db.execute(
            "SELECT id FROM subtasks WHERE id = ?", (subtask_id,)
        ).fetchone():
            return False
        db.execute("DELETE FROM subtasks WHERE id = ?", (subtask_id,))
        return True


# ── Stats ─────────────────────────────────────────────────────────────────────


def get_stats() -> dict:
    """
    Return dashboard-level aggregates.

    Keys: ``total``, ``overdue``, ``due_soon``, ``by_status``.
    """
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        by_status_rows = db.execute(
            "SELECT status, COUNT(*) AS n FROM tasks GROUP BY status"
        ).fetchall()
        overdue = db.execute(
            "SELECT COUNT(*) FROM tasks"
            " WHERE due_date != '' AND due_date < date('now') AND status != 'done'"
        ).fetchone()[0]
        due_soon = db.execute(
            "SELECT COUNT(*) FROM tasks"
            " WHERE due_date != ''"
            "   AND due_date >= date('now')"
            "   AND due_date <= date('now', '+3 days')"
            "   AND status != 'done'"
        ).fetchone()[0]

    return {
        "total": total,
        "overdue": overdue,
        "due_soon": due_soon,
        "by_status": {r["status"]: r["n"] for r in by_status_rows},
    }
