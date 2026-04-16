"""
ui/drawing.py — Low-level curses drawing primitives.

All functions here are pure "output" helpers with no business logic.
They accept a curses window and paint pixels / strings onto it.

Changes from v1
---------------
``draw_header`` now accepts an optional ``extra`` keyword argument.
The caller (``app.py``) passes the web-server status string, e.g.
``" WEB:8080"``, which is appended to the app name on the left side of
the header bar.  When ``extra`` is empty the header is identical to
before.
"""

import curses
from datetime import date
from todo_app.config import (
    CP_HEADER,
    CP_HELP,
    CP_TITLE,
    CP_BORDER_ACT,
    CP_BORDER_IDLE,
)


# ── Safe write ────────────────────────────────────────────────────────────────


def sw(win, y: int, x: int, text: str, attr: int = 0) -> None:
    """Write *text* at (y, x), clipping to window bounds silently."""
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w:
        return
    avail = w - x - 1
    if avail <= 0:
        return
    try:
        win.addstr(y, x, str(text)[:avail], attr)
    except curses.error:
        pass


def fill_row(win, y: int, attr: int) -> None:
    """Paint an entire row with *attr* (used for selection highlights)."""
    _, w = win.getmaxyx()
    try:
        win.addstr(y, 0, " " * (w - 1), attr)
    except curses.error:
        pass


# ── Chrome ────────────────────────────────────────────────────────────────────


def draw_border(win, active: bool, title: str = "") -> None:
    """Draw a border using active or idle colours, with an optional title."""
    cp = CP_BORDER_ACT if active else CP_BORDER_IDLE
    attr = curses.color_pair(cp) | (curses.A_BOLD if active else 0)
    try:
        win.attron(attr)
        win.border()
        win.attroff(attr)
    except curses.error:
        pass
    if title:
        t = f" {title} "
        _, w = win.getmaxyx()
        x = max(2, (w - len(t)) // 2)
        sw(win, 0, x, t, curses.color_pair(CP_TITLE) | curses.A_BOLD)


def draw_header(stdscr, extra: str = "") -> None:
    """
    Draw the full-width blue header bar at row 0.

    Parameters
    ----------
    extra : optional status string appended to the app name, e.g.
            ``" WEB:8080"`` when the background web server is running.
            Pass an empty string (the default) for the original behaviour.
    """
    H, W = stdscr.getmaxyx()
    attr = curses.color_pair(CP_HEADER) | curses.A_BOLD
    fill_row(stdscr, 0, attr)
    today = date.today().strftime("%a %d %b %Y")
    left_txt = f"  ZUQONTECH TODO{extra}"
    sw(stdscr, 0, 2, left_txt, attr)
    sw(stdscr, 0, W - len(today) - 4, today, attr)


def draw_helpbar(stdscr, items: list[tuple[str, str]]) -> None:
    """
    Draw the help bar at the bottom of the screen.

    *items* is a list of ``(key, description)`` tuples,
    e.g. ``[("a", "Add task"), ("q", "Quit")]``.
    """
    H, W = stdscr.getmaxyx()
    attr = curses.color_pair(CP_HELP)
    fill_row(stdscr, H - 1, attr)
    bar = "  ".join(f"[{k}]{v}" for k, v in items)
    sw(stdscr, H - 1, 1, bar, attr)
