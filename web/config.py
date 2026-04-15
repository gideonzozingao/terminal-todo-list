"""
web/config.py — Web server configuration.

All constants the web layer depends on live here.  Nothing else in the
web package hardcodes paths, ports, or status lists.
"""

import os
import sys
from pathlib import Path

# ── Database ──────────────────────────────────────────────────────────────────

# Shared with the TUI — both processes read/write the same file.
DB_PATH: str = os.path.expanduser("~/.todo_tasks.db")

# ── Server ────────────────────────────────────────────────────────────────────

PORT: int = int(sys.argv[1]) if len(sys.argv) > 1 else 8555

# Directory that contains index.html (the package's parent, i.e. the project root).
SERVE_DIR: Path = Path(__file__).parent.parent

# ── Domain constants ──────────────────────────────────────────────────────────

STATUSES: list[str] = ["todo", "in-progress", "on-hold", "done"]

TASK_FIELDS: tuple[str, ...] = (
    "title",
    "description",
    "status",
    "start_date",
    "due_date",
)

MIME_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css",
    ".js": "application/javascript",
    ".ico": "image/x-icon",
}
