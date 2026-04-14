"""
utils.py — Date helpers and task colour resolution.

Kept separate so they can be unit-tested without starting a curses session.
"""

import curses
from datetime import date, datetime
from .config import (
    CP_DONE,
    CP_DUE,
    CP_SOON,
    CP_TODO,
    STATUS_CP,
)


# ── Date helpers ──────────────────────────────────────────────────────────────

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")


def parse_date(s: str) -> date | None:
    """Try several common formats; return a ``date`` or ``None``."""
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except (ValueError, AttributeError):
            pass
    return None


def fmt_date(s: str) -> str:
    """Human-readable date string, e.g. ``'14 Mar 2025'``, or ``'-'``."""
    if not s:
        return "-"
    d = parse_date(s)
    return d.strftime("%d %b %Y") if d else s


def date_urgency(due_str: str) -> str | None:
    """
    Classify how urgent a due date is.

    Returns one of ``'overdue'``, ``'today'``, ``'soon'`` (≤3 days), or
    ``None`` (no date / far future).
    """
    if not due_str:
        return None
    d = parse_date(due_str)
    if not d:
        return None
    delta = (d - date.today()).days
    if delta < 0:
        return "overdue"
    if delta == 0:
        return "today"
    if delta <= 3:
        return "soon"
    return None


# ── Colour resolution ─────────────────────────────────────────────────────────


def task_color(task) -> int:
    """
    Return the curses attribute for a task row.

    Priority: done → overdue/today → soon → status colour.
    """
    urg = date_urgency(task["due_date"])
    st = task["status"]

    if st == "done":
        return curses.color_pair(CP_DONE)
    if urg in ("overdue", "today"):
        return curses.color_pair(CP_DUE) | curses.A_BOLD
    if urg == "soon":
        return curses.color_pair(CP_SOON)
    return curses.color_pair(STATUS_CP.get(st, CP_TODO))
