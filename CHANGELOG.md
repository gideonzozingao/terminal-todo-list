Changelog
v2.0.0 — Web Interface & REST API
Date: 2026-04-14
Added
web_server.py — HTTP server & JSON REST API
A zero-dependency Python HTTP server (stdlib http.server + sqlite3) that exposes the same ~/.todo_tasks.db database used by the TUI over a local web port. The TUI and web server can run simultaneously — they share data in real time.
Run with:
bashpython3 web_server.py          # default port 8080
python3 web_server.py 9000     # custom port
Full REST API surface:
MethodEndpointDescriptionGET/api/tasksList all tasks with subtask counts; supports ?status= and ?q= query filtersPOST/api/tasksCreate a new taskGET/api/tasks/<id>Get a single taskPUT/api/tasks/<id>Update a taskDELETE/api/tasks/<id>Delete a task and all its subtasksGET/api/tasks/<id>/subtasksList subtasks for a taskPOST/api/tasks/<id>/subtasksCreate a subtaskPUT/api/subtasks/<id>Update a subtaskDELETE/api/subtasks/<id>Delete a subtaskGET/api/statsDashboard counts: total tasks, overdue, due soon, by-status breakdown
All responses are JSON. All task and subtask objects include a computed urgency field ("overdue", "today", "soon", or null). Errors return {"error": "..."} with an appropriate HTTP status code.
index.html — Single-page web frontend
A self-contained browser UI served at http://localhost:<port>/. No build step, no npm, no framework — plain HTML, CSS, and vanilla JS.
Features:

Terminal-aesthetic dark theme (JetBrains Mono, scanline texture, cyan accent)
Sidebar task list with status badges, urgency indicators (⚠ OVERDUE, ⚠ DUE TODAY, ~ DUE SOON), and subtask progress counts
Status filter bar (All / Todo / In Progress / On Hold / Done) and live search with 250 ms debounce
Task detail panel showing title, status, start/due dates, description, and a subtask list with an animated progress bar
Modal dialogs for creating and editing tasks and subtasks (title, description, status, start date, due date)
Confirmation dialog before any delete operation
Toast notifications for all create / update / delete actions
Keyboard shortcuts: n → new task, Esc → close modal
Auto-refresh every 30 seconds; manual refresh button
CORS headers enabled for local API access from other origins

Changed

Project structure — two new top-level files added alongside todo.py:

todo.py
web_server.py    ← new: HTTP server + REST API
index.html       ← new: browser frontend
todo_app/
└── …            (unchanged)

web_server.py init_db() — the web server contains its own init_db() that creates the same tasks and subtasks schema as database.py, so it can bootstrap the database independently if run before the TUI for the first time. The schema is identical and fully compatible.

Notes

No new dependencies introduced. The web server uses only Python stdlib (http.server, sqlite3, json, re, urllib.parse).
The web server binds to 0.0.0.0 so it is reachable from other devices on the local network by IP address (e.g. http://192.168.x.x:8080). Restrict to 127.0.0.1 in web_server.py if local-only access is preferred.
Date input fields in the web UI use the browser's native <input type="date"> picker and store dates as YYYY-MM-DD, matching the TUI's primary format.


v1.0.0 — Initial TUI Release

Terminal UI built with Python curses and sqlite3
Split-pane layout: scrollable task list (left) + task detail with subtasks (right)
Four task statuses: todo, in-progress, on-hold, done
Due-date urgency system: overdue, due today, due soon (≤ 3 days)
Color-coded status and urgency indicators across all panes
Progress bar for subtask completion in the detail pane
Modal dialogs: multi-field input, status picker, yes/no confirm
Persistent SQLite storage at ~/.todo_tasks.db
Zero external dependencies