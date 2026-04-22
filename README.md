# ZUQONTECH TODO

A terminal-based task manager built with Python's `curses` and `sqlite3` — no third-party dependencies required.

```
┌─────────────────────────────────────────────────────────────────┐
│   ZUQONTECH TODO                          Mon 14 Apr 2025       │
├──────────────────────────┬──────────────────────────────────────┤
│ TASKS 5 !1               │ DETAILS ⚠ DUE TODAY                  │
│  !◑ Fix login bug        │ Title   Fix login bug                 │
│  ○ Write unit tests      │ Status  ◑  IN PROGRESS  ⚠ DUE TODAY  │
│  ● Deploy to prod        │ Start   10 Apr 2025                   │
│  ◌ Update docs           │ Due     14 Apr 2025                   │
│  ○ Code review           │ Desc    OAuth token refresh issue      │
│                          ├──────────────────────────────────────┤
│                          │ SUBTASKS  2/3          ████░░░  66%   │
│                          │  # ST            TITLE                │
│                          │  >1 ●  DONE      Write failing test   │
│                          │   2 ◑  IN PROG   Patch token logic    │
│                          │   3 ○  TODO      Update changelog     │
└──────────────────────────┴──────────────────────────────────────┘
 [a]Add  [e]Edit  [s]Status  [d]Del  [A]Subtask  [Tab]Switch  [q]Quit
```

---

## Features

- Split-pane TUI: scrollable task list on the left, full task details on the right
- Tasks and subtasks with status, start date, due date, and description
- Visual urgency indicators — overdue, due today, due soon (≤ 3 days)
- Progress bar showing subtask completion
- Color-coded status badges per task
- Modal dialogs for adding, editing, confirming, and picking status
- Persistent SQLite storage at `~/.todo_tasks.db`
- Zero external dependencies — pure stdlib (`curses` + `sqlite3`)

---

## Requirements

- Python 3.6 or newer
- A terminal with color support (most modern terminals qualify)
- Unix-like OS (Linux, macOS). Windows requires WSL or a curses-compatible layer.

---

## Installation

Clone or copy the project, then run directly — no install step needed:

```bash
git clone https://github.com/your-org/zuqontech-todo.git
cd zuqontech-todo
python3 todo.py
```

The database file is created automatically at `~/.todo_tasks.db` on first run.

---

## Project Structure

```
todo.py                  # Entry point
todo_app/
├── __init__.py
├── app.py               # Main event loop (app_loop)
├── colors.py            # Curses color-pair initialisation
├── config.py            # App-wide constants (statuses, color IDs, layout)
├── database.py          # SQLite schema and CRUD helpers
├── utils.py             # Date helpers and task colour resolution
└── ui/
    ├── __init__.py
    ├── dialogs.py        # Modal popups (input, status picker, confirm)
    ├── drawing.py        # Low-level curses drawing primitives
    └── panes.py          # Left (task list) and right (detail) pane renderers
```

---

## Module Reference

### `todo.py` — Entry Point

The top-level script. Responsibilities:

- Sets the locale for Unicode character support
- Calls `init_db()` to create the SQLite schema if it does not exist
- Wraps `curses.wrapper(main)` so the terminal is always restored cleanly
- Prints `Goodbye!` on exit

```bash
python3 todo.py
```

---

### `config.py` — App-wide Constants

Single source of truth for every magic number and string in the app. Import from here — never hardcode values elsewhere.

#### Database

| Constant  | Value              | Description              |
| --------- | ------------------ | ------------------------ |
| `DB_PATH` | `~/.todo_tasks.db` | SQLite database location |

#### Statuses

| Constant   | Value                                        |
| ---------- | -------------------------------------------- |
| `STATUSES` | `["todo", "in-progress", "on-hold", "done"]` |

```python
STATUS_ICON   = { "todo": "○", "in-progress": "◑", "on-hold": "◌", "done": "●" }
STATUS_LABEL  = { "todo": "TODO", "in-progress": "IN PROGRESS", ... }
STATUS_CP     = { "todo": CP_TODO, "in-progress": CP_INPROG, ... }
```

**To add a new status:** append to `STATUSES`, then add entries in `STATUS_ICON`, `STATUS_LABEL`, and `STATUS_CP`.

#### Color-Pair IDs

Each constant is an integer (1–16) passed to `curses.color_pair()`.

| Constant         | ID  | Usage                                           |
| ---------------- | --- | ----------------------------------------------- |
| `CP_HEADER`      | 1   | Top header bar (white on blue)                  |
| `CP_SEL_ACTIVE`  | 2   | Selected row in focused pane (black on cyan)    |
| `CP_SEL_IDLE`    | 3   | Selected row in unfocused pane (black on white) |
| `CP_TODO`        | 4   | Todo status / dimmed text (terminal default)    |
| `CP_INPROG`      | 5   | In-progress status (yellow)                     |
| `CP_ONHOLD`      | 6   | On-hold status (magenta)                        |
| `CP_DONE`        | 7   | Done status (green)                             |
| `CP_DUE`         | 8   | Overdue / due today (red)                       |
| `CP_SOON`        | 9   | Due within 3 days (yellow)                      |
| `CP_BORDER_ACT`  | 10  | Active pane border (cyan)                       |
| `CP_BORDER_IDLE` | 11  | Inactive pane border (white)                    |
| `CP_HELP`        | 12  | Help bar (white on blue)                        |
| `CP_TITLE`       | 13  | Pane titles (cyan)                              |
| `CP_LABEL`       | 14  | Field labels in detail pane (white)             |
| `CP_PROG_FILL`   | 15  | Progress bar — filled segment (black on cyan)   |
| `CP_PROG_EMPTY`  | 16  | Progress bar — empty segment (white)            |

#### Layout Limits

| Constant         | Value | Description                      |
| ---------------- | ----- | -------------------------------- |
| `MIN_TERMINAL_H` | 10    | Minimum terminal height (rows)   |
| `MIN_TERMINAL_W` | 40    | Minimum terminal width (columns) |
| `LEFT_PANE_MIN`  | 26    | Minimum left-pane width          |
| `LEFT_PANE_MAX`  | 40    | Maximum left-pane width          |

---

### `colors.py` — Color Initialisation

```python
from todo_app.colors import init_colors
```

#### `init_colors() -> None`

Registers all 16 color pairs with curses. Must be called once, after `curses.start_color()` (which `curses.wrapper` calls automatically).

Uses `curses.use_default_colors()` so that `-1` as a background value means "transparent" (inherits the terminal background).

To add a new color pair: add the constant to `config.py`, then add one `curses.init_pair(...)` call here.

---

### `utils.py` — Date Helpers & Color Resolution

Pure functions with no curses session dependency — unit-testable in isolation.

#### Date helpers

```python
parse_date(s: str) -> date | None
```
Tries three formats in order: `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY`. Returns a `datetime.date` or `None`.

---

```python
fmt_date(s: str) -> str
```
Returns a human-readable string such as `"14 Mar 2025"`, or `"-"` if the value is empty or unparseable.

---

```python
date_urgency(due_str: str) -> str | None
```
Classifies how urgent a due date is relative to today.

| Return value | Meaning                                           |
| ------------ | ------------------------------------------------- |
| `"overdue"`  | Due date is in the past                           |
| `"today"`    | Due date is today                                 |
| `"soon"`     | Due within the next 3 days                        |
| `None`       | No date set, or due date is more than 3 days away |

#### Color resolution

```python
task_color(task) -> int
```
Returns the curses attribute integer for a task row. Priority order:

1. **Done** → `CP_DONE` (green)
2. **Overdue or today** → `CP_DUE | A_BOLD` (red, bold)
3. **Soon** → `CP_SOON` (yellow)
4. **Status default** → looked up via `STATUS_CP`

`task` must be a mapping (e.g. `sqlite3.Row`) with keys `"status"` and `"due_date"`.

---

### `ui/drawing.py` — Low-Level Drawing Primitives

Pure output helpers with no business logic. All functions accept a curses window and write to it.

#### `sw(win, y, x, text, attr=0) -> None`

Safe `addstr` wrapper. Clips silently to window bounds; truncates text that would overflow the right edge. Swallows `curses.error` so callers never crash on resize edge cases.

#### `fill_row(win, y, attr) -> None`

Paints an entire row with `attr` (spaces). Used to create selection highlight backgrounds.

#### `draw_border(win, active, title="") -> None`

Draws a box border using `CP_BORDER_ACT` (cyan, bold) when `active=True`, or `CP_BORDER_IDLE` (white) otherwise. If `title` is provided it is centered on the top border in `CP_TITLE | A_BOLD`.

#### `draw_header(stdscr) -> None`

Renders the full-width blue header bar at row 0 with the app name on the left and today's date on the right.

#### `draw_helpbar(stdscr, items) -> None`

Renders the help bar at the bottom row.

`items` is a list of `(key, description)` tuples:

```python
draw_helpbar(stdscr, [("a", "Add"), ("q", "Quit")])
# → [a]Add  [q]Quit
```

---

### `ui/panes.py` — Pane Renderers

Pure renderers that take all data as arguments and call `win.refresh()` at the end. No database calls.

#### `draw_left_pane(win, tasks, sel, offset, active) -> None`

Renders the scrollable task list.

| Parameter | Type                | Description                          |
| --------- | ------------------- | ------------------------------------ |
| `tasks`   | `list[sqlite3.Row]` | All tasks to display                 |
| `sel`     | `int`               | Index of the currently selected task |
| `offset`  | `int`               | First visible row (scroll state)     |
| `active`  | `bool`              | Whether this pane has keyboard focus |

Each row shows a left-column urgency indicator (`●` today, `!` overdue, space otherwise), a status icon, and the task title (truncated with `…` if too long). The border title includes the total task count and a `!N` badge if N tasks are overdue or due today. A scroll percentage is shown at the bottom-right when the list overflows.

#### `draw_right_pane(win, task, subtasks, sub_sel, active) -> None`

Renders the task detail view.

| Parameter  | Type                  | Description                          |
| ---------- | --------------------- | ------------------------------------ |
| `task`     | `sqlite3.Row \| None` | The selected task, or `None`         |
| `subtasks` | `list[sqlite3.Row]`   | Subtasks belonging to this task      |
| `sub_sel`  | `int`                 | Index of the highlighted subtask     |
| `active`   | `bool`                | Whether this pane has keyboard focus |

When `task` is `None`, a placeholder prompt is shown. Otherwise the pane renders:

- **Row 1** — Title (colored by urgency/status)
- **Row 2** — Status icon + label + optional urgency badge
- **Row 3** — Start date and due date side-by-side
- **Row 4–5** — Description word-wrapped to at most two lines
- **Divider** — horizontal rule
- **Subtask header** — count (`done/total`), progress bar, and percentage
- **Subtask list** — scrollable, with status icon, label, and title per row; the focused subtask is highlighted with `>`

---

### `ui/dialogs.py` — Modal Dialogs

Each function blocks until the user confirms or cancels. They return a result or `None` on cancel and never touch the database directly.

#### `input_dialog(stdscr, title, fields) -> list[str] | None`

Multi-field text-entry popup.

`fields` is a list of dicts:

```python
fields = [
    {"label": "Title",       "default": "",           "hint": "required"},
    {"label": "Due date",    "default": "",           "hint": "YYYY-MM-DD"},
    {"label": "Description", "default": ""},
]
result = input_dialog(stdscr, "Add Task", fields)
# → ["My task", "2025-04-20", ""] or None if cancelled
```

| Key       | Required | Description                          |
| --------- | -------- | ------------------------------------ |
| `label`   | Yes      | Field name shown above the input box |
| `default` | No       | Pre-filled value                     |
| `hint`    | No       | Dimmed hint shown after the label    |

**Keyboard:**

| Key               | Action                                     |
| ----------------- | ------------------------------------------ |
| `Tab` / `↑` / `↓` | Move between fields                        |
| `Enter`           | Advance to next field; confirm on the last |
| `Backspace`       | Delete last character                      |
| Printable chars   | Append to current field (max 200 chars)    |
| `Esc`             | Cancel — returns `None`                    |

#### `pick_status(stdscr, current) -> str | None`

Displays a small popup listing all statuses from `STATUSES`. Returns the chosen status string, or `None` if cancelled.

`current` sets the initially highlighted item.

**Keyboard:** `↑`/`↓` to move, `Enter` to confirm, `Esc` to cancel.

#### `confirm(stdscr, msg) -> bool`

Simple yes/no dialog. Returns `True` only if the user presses `y` or `Y`.

```python
if confirm(stdscr, "Delete this task?"):
    db_delete_task(task_id)
```

**Keyboard:** `y`/`Y` → `True`; `n`/`N`/`Esc` → `False`.

---

## Keyboard Reference

> Keys may vary slightly depending on your `app.py` implementation.

### Task List (left pane focused)

| Key           | Action                                   |
| ------------- | ---------------------------------------- |
| `↑` / `↓`     | Move selection                           |
| `a`           | Add a new task                           |
| `e`           | Edit selected task                       |
| `s`           | Change status of selected task           |
| `d`           | Delete selected task (with confirmation) |
| `→` / `Enter` | Focus detail pane                        |
| `Tab`         | Switch pane focus                        |
| `q`           | Quit                                     |

### Detail Pane (right pane focused)

| Key         | Action                    |
| ----------- | ------------------------- |
| `↑` / `↓`   | Move subtask selection    |
| `A`         | Add a subtask             |
| `e`         | Edit selected subtask     |
| `s`         | Change subtask status     |
| `d`         | Delete selected subtask   |
| `←` / `Esc` | Return focus to task list |

---

## Data Storage

Tasks and subtasks are stored in an SQLite database at `~/.todo_tasks.db`. The schema is created by `init_db()` in `database.py` on first run.

To back up your data:

```bash
cp ~/.todo_tasks.db ~/todo_backup_$(date +%F).db
```

To reset all data:

```bash
rm ~/.todo_tasks.db
```

---

## Extending the App

### Adding a new status

1. Append the status string to `STATUSES` in `config.py`
2. Add an entry in `STATUS_ICON`, `STATUS_LABEL`, and `STATUS_CP` in `config.py`
3. Add a `curses.init_pair(CP_<NEW>, ...)` call in `colors.py` with a new constant

### Adding a new color pair

1. Define `CP_<NAME> = <next available integer>` in `config.py`
2. Import it in `colors.py` and call `curses.init_pair(CP_<NAME>, fg, bg)`
3. Use `curses.color_pair(CP_<NAME>)` wherever needed

### Adding a new dialog field

Pass an additional dict to the `fields` list in your `input_dialog` call. The dialog sizes itself automatically based on the number of fields.

---

## License

MIT — see `LICENSE` for details.

---

## Changelog

### v2.0.0 — Web Interface & REST API
**Date:** 2026-04-14

#### Added

**`web_server.py` — HTTP server & JSON REST API**

A zero-dependency Python HTTP server (stdlib `http.server` + `sqlite3`) that exposes the same `~/.todo_tasks.db` database used by the TUI over a local web port. The TUI and web server can run simultaneously — they share data in real time.

Run with:
```bash
python3 web_server.py          # default port 8080
python3 web_server.py 9000     # custom port
```

Full REST API surface:

| Method   | Endpoint                   | Description                                                                     |
| -------- | -------------------------- | ------------------------------------------------------------------------------- |
| `GET`    | `/api/tasks`               | List all tasks with subtask counts; supports `?status=` and `?q=` query filters |
| `POST`   | `/api/tasks`               | Create a new task                                                               |
| `GET`    | `/api/tasks/<id>`          | Get a single task                                                               |
| `PUT`    | `/api/tasks/<id>`          | Update a task                                                                   |
| `DELETE` | `/api/tasks/<id>`          | Delete a task and all its subtasks                                              |
| `GET`    | `/api/tasks/<id>/subtasks` | List subtasks for a task                                                        |
| `POST`   | `/api/tasks/<id>/subtasks` | Create a subtask                                                                |
| `PUT`    | `/api/subtasks/<id>`       | Update a subtask                                                                |
| `DELETE` | `/api/subtasks/<id>`       | Delete a subtask                                                                |
| `GET`    | `/api/stats`               | Dashboard counts: total tasks, overdue, due soon, by-status breakdown           |

All responses are JSON. All task and subtask objects include a computed `urgency` field (`"overdue"`, `"today"`, `"soon"`, or `null`). Errors return `{"error": "..."}` with an appropriate HTTP status code.

**`index.html` — Single-page web frontend**

A self-contained browser UI served at `http://localhost:<port>/`. No build step, no npm, no framework — plain HTML, CSS, and vanilla JS.

Features:
- Terminal-aesthetic dark theme (JetBrains Mono, scanline texture, cyan accent)
- Sidebar task list with status badges, urgency indicators (`⚠ OVERDUE`, `⚠ DUE TODAY`, `~ DUE SOON`), and subtask progress counts
- Status filter bar (All / Todo / In Progress / On Hold / Done) and live search with 250 ms debounce
- Task detail panel showing title, status, start/due dates, description, and a subtask list with an animated progress bar
- Modal dialogs for creating and editing tasks and subtasks (title, description, status, start date, due date)
- Confirmation dialog before any delete operation
- Toast notifications for all create / update / delete actions
- Keyboard shortcuts: `n` → new task, `Esc` → close modal
- Auto-refresh every 30 seconds; manual refresh button
- CORS headers enabled for local API access from other origins

#### Changed

- **Project structure** — two new top-level files added alongside `todo.py`:

```
todo.py
web_server.py    ← new: HTTP server + REST API
index.html       ← new: browser frontend
todo_app/
└── …            (unchanged)
```

- **`web_server.py` `init_db()`** — the web server contains its own `init_db()` that creates the same `tasks` and `subtasks` schema as `database.py`, so it can bootstrap the database independently if run before the TUI for the first time. The schema is identical and fully compatible.

#### Notes

- No new dependencies introduced. The web server uses only Python stdlib (`http.server`, `sqlite3`, `json`, `re`, `urllib.parse`).
- The web server binds to `0.0.0.0` so it is reachable from other devices on the local network by IP address (e.g. `http://192.168.x.x:8080`). Restrict to `127.0.0.1` in `web_server.py` if local-only access is preferred.
- Date input fields in the web UI use the browser's native `<input type="date">` picker and store dates as `YYYY-MM-DD`, matching the TUI's primary format.
---

