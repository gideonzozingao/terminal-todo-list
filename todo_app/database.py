"""
database.py — All SQLite persistence.

Every function either queries or mutates the database.  The rest of the
app never imports sqlite3 directly — it calls these functions instead.
This makes it easy to swap the storage backend without touching UI code.
"""

import sqlite3
from .config import DB_PATH


# ── Connection factory ────────────────────────────────────────────────────────


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Schema ────────────────────────────────────────────────────────────────────


def init_db() -> None:
    """Create tables if they do not already exist."""
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                description TEXT    DEFAULT '',
                status      TEXT    DEFAULT 'todo',
                start_date  TEXT    DEFAULT '',
                due_date    TEXT    DEFAULT '',
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS subtasks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id    INTEGER NOT NULL
                               REFERENCES tasks(id) ON DELETE CASCADE,
                title      TEXT    NOT NULL,
                status     TEXT    DEFAULT 'todo',
                created_at TEXT    DEFAULT (datetime('now','localtime'))
            );
        """
        )


# ── Task queries ──────────────────────────────────────────────────────────────


def get_all_tasks() -> list[sqlite3.Row]:
    """Return every task ordered by urgency then creation time."""
    with _conn() as c:
        return c.execute(
            "SELECT * FROM tasks ORDER BY "
            "CASE WHEN due_date IS NULL OR due_date='' THEN 1 ELSE 0 END,"
            "due_date ASC, created_at DESC"
        ).fetchall()


def get_task(task_id: int) -> sqlite3.Row | None:
    with _conn() as c:
        return c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()


# ── Task mutations ────────────────────────────────────────────────────────────


def add_task(title: str, description: str, start_date: str, due_date: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO tasks (title, description, start_date, due_date) "
            "VALUES (?, ?, ?, ?)",
            (title, description, start_date, due_date),
        )


def update_task(
    task_id: int,
    title: str,
    description: str,
    start_date: str,
    due_date: str,
) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE tasks SET title=?, description=?, start_date=?, due_date=? "
            "WHERE id=?",
            (title, description, start_date, due_date, task_id),
        )


def set_task_status(task_id: int, status: str) -> None:
    with _conn() as c:
        c.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))


def delete_task(task_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM tasks WHERE id=?", (task_id,))


# ── Subtask queries ───────────────────────────────────────────────────────────


def get_subtasks(task_id: int) -> list[sqlite3.Row]:
    with _conn() as c:
        return c.execute(
            "SELECT * FROM subtasks WHERE task_id=? ORDER BY created_at",
            (task_id,),
        ).fetchall()


# ── Subtask mutations ─────────────────────────────────────────────────────────


def add_subtask(task_id: int, title: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO subtasks (task_id, title) VALUES (?, ?)",
            (task_id, title),
        )


def set_subtask_status(subtask_id: int, status: str) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE subtasks SET status=? WHERE id=?",
            (status, subtask_id),
        )


def update_subtask(subtask_id: int, title: str) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE subtasks SET title=? WHERE id=?",
            (title, subtask_id),
        )


def delete_subtask(subtask_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM subtasks WHERE id=?", (subtask_id,))
