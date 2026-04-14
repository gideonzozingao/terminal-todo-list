"""
config.py — App-wide constants.

All status definitions and curses color-pair IDs live here so every
other module imports from one place.  To add a new status:
  1. Append to STATUSES
  2. Add an entry to STATUS_ICON, STATUS_LABEL, and STATUS_CP
"""

import os

# ── Database ──────────────────────────────────────────────────────────────────

DB_PATH = os.path.expanduser("~/.todo_tasks.db")

# ── Status definitions ────────────────────────────────────────────────────────

STATUSES = ["todo", "in-progress", "on-hold", "done"]

STATUS_ICON: dict[str, str] = {
    "todo": "○",
    "in-progress": "◑",
    "on-hold": "◌",
    "done": "●",
}

STATUS_LABEL: dict[str, str] = {
    "todo": "TODO",
    "in-progress": "IN PROGRESS",
    "on-hold": "ON HOLD",
    "done": "DONE",
}

# ── Curses color-pair IDs ─────────────────────────────────────────────────────
# Integers 1-16; each is passed to curses.color_pair() everywhere.

CP_HEADER = 1
CP_SEL_ACTIVE = 2  # selected row in focused pane
CP_SEL_IDLE = 3  # selected row in unfocused pane
CP_TODO = 4
CP_INPROG = 5
CP_ONHOLD = 6
CP_DONE = 7
CP_DUE = 8  # due today / overdue
CP_SOON = 9  # due within 3 days
CP_BORDER_ACT = 10  # active pane border
CP_BORDER_IDLE = 11  # inactive pane border
CP_HELP = 12
CP_TITLE = 13
CP_LABEL = 14  # field labels in detail pane
CP_PROG_FILL = 15  # progress bar filled
CP_PROG_EMPTY = 16  # progress bar empty

# Maps status string → color pair ID
STATUS_CP: dict[str, int] = {
    "todo": CP_TODO,
    "in-progress": CP_INPROG,
    "on-hold": CP_ONHOLD,
    "done": CP_DONE,
}

# ── Layout limits ─────────────────────────────────────────────────────────────

MIN_TERMINAL_H = 10
MIN_TERMINAL_W = 40
LEFT_PANE_MIN = 26
LEFT_PANE_MAX = 40
