"""
web/handlers.py — HTTP request handler and router.

Responsibilities
----------------
- Parse the URL and dispatch to the correct service function
- Read / write HTTP request and response bodies (JSON)
- Serve static files from SERVE_DIR
- Handle CORS pre-flight

This module contains *no* SQL, *no* date logic, and *no* validation logic.
All of that lives in database.py, utils.py, and validators.py respectively.
The handler is intentionally thin: route → validate → call service → respond.
"""

import http.server
import json
import re
import urllib.parse
from pathlib import Path

from web import database as db
from web import validators as v
from web.config import SERVE_DIR, MIME_TYPES
from web.utils import enrich, enrich_many

# ── Pre-compiled URL patterns ─────────────────────────────────────────────────

_RE_TASK = re.compile(r"^/api/tasks/(\d+)$")
_RE_TASK_SUBS = re.compile(r"^/api/tasks/(\d+)/subtasks$")
_RE_SUBTASK = re.compile(r"^/api/subtasks/(\d+)$")


# ── Handler ───────────────────────────────────────────────────────────────────


class TodoHandler(http.server.BaseHTTPRequestHandler):
    """
    Single HTTP request handler for the ZUQONTECH TODO web API.

    Each ``do_<METHOD>`` method strips the trailing slash, matches the path
    against the URL patterns above, then calls the appropriate database
    helper.  Validation is delegated to ``validators.py`` before any DB call.
    """

    # ── Logging ───────────────────────────────────────────────────────────────

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    # ── Response helpers ──────────────────────────────────────────────────────

    def send_json(self, data, status: int = 200) -> None:
        """Serialise *data* to JSON and write the complete HTTP response."""
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, msg: str, status: int = 400) -> None:
        """Send a JSON error body with *msg* and the given HTTP *status*."""
        self.send_json({"error": msg}, status)

    def send_file(self, path: Path) -> None:
        """Serve a static file, or 404 if it does not exist."""
        if not path.exists():
            self.send_error_json("Not found", 404)
            return
        mime = MIME_TYPES.get(path.suffix, "application/octet-stream")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ── Request helpers ───────────────────────────────────────────────────────

    def read_json(self) -> dict | None:
        """
        Read and decode the request body as JSON.

        Returns an empty dict for requests with no body, or ``None`` if the
        body is present but not valid JSON.
        """
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return None

    def _path(self) -> str:
        """Return the request path with trailing slash removed."""
        return self.path.rstrip("/")

    # ── CORS ──────────────────────────────────────────────────────────────────

    def do_OPTIONS(self) -> None:
        """Handle CORS pre-flight requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"
        )
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── GET ───────────────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        # ── Static files ──────────────────────────────────────────────────────
        if path in ("", "/"):
            self.send_file(SERVE_DIR / "index.html")
            return
        if not path.startswith("/api"):
            self.send_file(SERVE_DIR / path.lstrip("/"))
            return

        # ── GET /api/tasks ────────────────────────────────────────────────────
        if path == "/api/tasks":
            qs = urllib.parse.parse_qs(parsed.query)
            status = qs.get("status", [None])[0]
            search = qs.get("q", [None])[0]
            self.send_json(enrich_many(db.list_tasks(status=status, search=search)))
            return

        # ── GET /api/tasks/<id> ───────────────────────────────────────────────
        m = _RE_TASK.fullmatch(path)
        if m:
            task = db.get_task(int(m.group(1)))
            if task is None:
                self.send_error_json("Task not found", 404)
                return
            self.send_json(enrich(task))
            return

        # ── GET /api/tasks/<id>/subtasks ──────────────────────────────────────
        m = _RE_TASK_SUBS.fullmatch(path)
        if m:
            self.send_json(enrich_many(db.list_subtasks(int(m.group(1)))))
            return

        # ── GET /api/stats ────────────────────────────────────────────────────
        if path == "/api/stats":
            self.send_json(db.get_stats())
            return

        self.send_error_json("Not found", 404)

    # ── POST ──────────────────────────────────────────────────────────────────

    def do_POST(self) -> None:
        path = self._path()
        body = self.read_json()
        if body is None:
            self.send_error_json("Invalid JSON")
            return

        # ── POST /api/tasks ───────────────────────────────────────────────────
        if path == "/api/tasks":
            cleaned, err = v.validate_task(body, require_title=True)
            if err:
                self.send_error_json(err)
                return
            self.send_json(enrich(db.create_task(cleaned)), 201)
            return

        # ── POST /api/tasks/<id>/subtasks ─────────────────────────────────────
        m = _RE_TASK_SUBS.fullmatch(path)
        if m:
            cleaned, err = v.validate_subtask(body, require_title=True)
            if err:
                self.send_error_json(err)
                return
            result = db.create_subtask(int(m.group(1)), cleaned)
            if result is None:
                self.send_error_json("Parent task not found", 404)
                return
            self.send_json(enrich(result), 201)
            return

        self.send_error_json("Not found", 404)

    # ── PUT ───────────────────────────────────────────────────────────────────

    def do_PUT(self) -> None:
        path = self._path()
        body = self.read_json()
        if body is None:
            self.send_error_json("Invalid JSON")
            return

        # ── PUT /api/tasks/<id> ───────────────────────────────────────────────
        m = _RE_TASK.fullmatch(path)
        if m:
            cleaned, err = v.validate_task(body, require_title=False)
            if err:
                self.send_error_json(err)
                return
            result = db.update_task(int(m.group(1)), cleaned)
            if result is None:
                self.send_error_json("Task not found", 404)
                return
            self.send_json(enrich(result))
            return

        # ── PUT /api/subtasks/<id> ────────────────────────────────────────────
        m = _RE_SUBTASK.fullmatch(path)
        if m:
            cleaned, err = v.validate_subtask(body, require_title=False)
            if err:
                self.send_error_json(err)
                return
            result = db.update_subtask(int(m.group(1)), cleaned)
            if result is None:
                self.send_error_json("Subtask not found", 404)
                return
            self.send_json(enrich(result))
            return

        self.send_error_json("Not found", 404)

    # ── DELETE ────────────────────────────────────────────────────────────────

    def do_DELETE(self) -> None:
        path = self._path()

        # ── DELETE /api/tasks/<id> ────────────────────────────────────────────
        m = _RE_TASK.fullmatch(path)
        if m:
            tid = int(m.group(1))
            if not db.delete_task(tid):
                self.send_error_json("Task not found", 404)
                return
            self.send_json({"deleted": tid})
            return

        # ── DELETE /api/subtasks/<id> ─────────────────────────────────────────
        m = _RE_SUBTASK.fullmatch(path)
        if m:
            sid = int(m.group(1))
            if not db.delete_subtask(sid):
                self.send_error_json("Subtask not found", 404)
                return
            self.send_json({"deleted": sid})
            return

        self.send_error_json("Not found", 404)
