"""
colors.py — Curses color-pair initialisation.

Call ``init_colors()`` once, right after ``curses.start_color()``.
All pair IDs come from config so this file never needs editing when
you add a new pair — just update config and add one ``init_pair`` call.
"""

import curses
from .config import (
    CP_HEADER,
    CP_SEL_ACTIVE,
    CP_SEL_IDLE,
    CP_TODO,
    CP_INPROG,
    CP_ONHOLD,
    CP_DONE,
    CP_DUE,
    CP_SOON,
    CP_BORDER_ACT,
    CP_BORDER_IDLE,
    CP_HELP,
    CP_TITLE,
    CP_LABEL,
    CP_PROG_FILL,
    CP_PROG_EMPTY,
)


def init_colors() -> None:
    """Initialise all color pairs.  Must be called after curses.start_color()."""
    curses.start_color()
    curses.use_default_colors()

    # fg, bg  (-1 = terminal default)
    curses.init_pair(CP_HEADER, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(CP_SEL_ACTIVE, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(CP_SEL_IDLE, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(CP_TODO, -1, -1)
    curses.init_pair(CP_INPROG, curses.COLOR_YELLOW, -1)
    curses.init_pair(CP_ONHOLD, curses.COLOR_MAGENTA, -1)
    curses.init_pair(CP_DONE, curses.COLOR_GREEN, -1)
    curses.init_pair(CP_DUE, curses.COLOR_RED, -1)
    curses.init_pair(CP_SOON, curses.COLOR_YELLOW, -1)
    curses.init_pair(CP_BORDER_ACT, curses.COLOR_CYAN, -1)
    curses.init_pair(CP_BORDER_IDLE, curses.COLOR_WHITE, -1)
    curses.init_pair(CP_HELP, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(CP_TITLE, curses.COLOR_CYAN, -1)
    curses.init_pair(CP_LABEL, curses.COLOR_WHITE, -1)
    curses.init_pair(CP_PROG_FILL, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(CP_PROG_EMPTY, curses.COLOR_WHITE, -1)
