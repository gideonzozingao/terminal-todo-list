"""
ui/dialogs.py — Modal popup dialogs.

Each function blocks until the user confirms or cancels, then returns
a result (or None on cancel).  They never mutate the database directly.
"""

import curses
from todo_app.config import (
    STATUSES,
    STATUS_ICON,
    STATUS_LABEL,
    STATUS_CP,
    CP_TODO,
    CP_TITLE,
    CP_SEL_ACTIVE,
    CP_BORDER_IDLE,
)

# from todo_app.config import STATUSES
from .drawing import sw, draw_border


# ── Multi-field input ─────────────────────────────────────────────────────────


def input_dialog(
    stdscr,
    title: str,
    fields: list[dict],
) -> list[str] | None:
    """
    Display a multi-field text-entry popup.

    *fields* is a list of dicts with keys:
      - ``label``   (str, required)
      - ``default`` (str, optional)
      - ``hint``    (str, optional — shown dimmed after the label)

    Returns a list of strings (one per field) or ``None`` if cancelled.

    Keyboard:
      Tab / Up / Down — move between fields
      Enter           — advance to next field; confirm on the last
      Esc             — cancel
    """
    H, W = stdscr.getmaxyx()
    dh = len(fields) * 3 + 5
    dw = min(64, W - 6)
    dy = (H - dh) // 2
    dx = (W - dw) // 2

    win = curses.newwin(dh, dw, dy, dx)
    win.keypad(True)

    values = [str(f.get("default", "")) for f in fields]
    cur_f = 0

    HINT = curses.color_pair(CP_TODO) | curses.A_DIM
    LABEL = curses.color_pair(CP_TITLE) | curses.A_BOLD
    ACT = curses.color_pair(CP_SEL_ACTIVE)
    IDLE = curses.color_pair(CP_BORDER_IDLE)

    while True:
        win.erase()
        draw_border(win, True, title)

        for i, field in enumerate(fields):
            r = 2 + i * 3
            label = field["label"]
            hint = field.get("hint", "")
            sw(win, r, 2, f"{label}:", LABEL)
            if hint:
                sw(win, r, 3 + len(label), f"  {hint}", HINT)

            bw = dw - 5
            val = values[i]
            disp = val[-(bw - 1) :] if len(val) >= bw else val
            atr = ACT if i == cur_f else IDLE
            try:
                win.addstr(r + 1, 2, " " * bw, atr)
                win.addstr(r + 1, 2, disp, atr)
            except curses.error:
                pass

        sw(
            win,
            dh - 2,
            2,
            "Tab/Up/Down: move field   Enter: next/confirm   Esc: cancel",
            HINT,
        )
        win.refresh()

        ch = win.getch()
        if ch == 27:
            return None
        elif ch in (curses.KEY_ENTER, 10, 13):
            if cur_f < len(fields) - 1:
                cur_f += 1
            else:
                return values
        elif ch == 9:  # Tab
            cur_f = (cur_f + 1) % len(fields)
        elif ch == curses.KEY_UP:
            cur_f = (cur_f - 1) % len(fields)
        elif ch == curses.KEY_DOWN:
            cur_f = (cur_f + 1) % len(fields)
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            values[cur_f] = values[cur_f][:-1]
        elif 32 <= ch <= 126:
            if len(values[cur_f]) < 200:
                values[cur_f] += chr(ch)


# ── Status picker ─────────────────────────────────────────────────────────────


def pick_status(stdscr, current: str) -> str | None:
    """
    Show a small popup listing all statuses; return the chosen one or None.
    """
    H, W = stdscr.getmaxyx()
    dh, dw = len(STATUSES) + 4, 24
    win = curses.newwin(dh, dw, (H - dh) // 2, (W - dw) // 2)
    win.keypad(True)
    sel = STATUSES.index(current) if current in STATUSES else 0

    while True:
        win.erase()
        draw_border(win, True, "Set Status")

        for i, s in enumerate(STATUSES):
            atr = (
                curses.color_pair(CP_SEL_ACTIVE) | curses.A_BOLD
                if i == sel
                else curses.color_pair(STATUS_CP[s])
            )
            sw(win, 2 + i, 3, f"  {STATUS_ICON[s]}  {STATUS_LABEL[s]:<13}", atr)

        sw(
            win,
            dh - 2,
            2,
            "Up/Down  Enter  Esc",
            curses.color_pair(CP_TODO) | curses.A_DIM,
        )
        win.refresh()

        ch = win.getch()
        if ch == 27:
            return None
        elif ch in (curses.KEY_ENTER, 10, 13):
            return STATUSES[sel]
        elif ch == curses.KEY_UP:
            sel = (sel - 1) % len(STATUSES)
        elif ch == curses.KEY_DOWN:
            sel = (sel + 1) % len(STATUSES)


# ── Confirm ───────────────────────────────────────────────────────────────────


def confirm(stdscr, msg: str) -> bool:
    """Ask a yes/no question; return ``True`` only if the user presses ``y``."""
    H, W = stdscr.getmaxyx()
    dw = max(len(msg) + 12, 36)
    win = curses.newwin(5, dw, (H - 5) // 2, (W - dw) // 2)
    win.keypad(True)
    draw_border(win, True, "Confirm")
    sw(win, 2, 3, msg, curses.A_BOLD)
    sw(win, 3, 3, "[y] Yes   [n/Esc] No", curses.color_pair(CP_TODO) | curses.A_DIM)
    win.refresh()

    while True:
        ch = win.getch()
        if ch in (ord("y"), ord("Y")):
            return True
        if ch in (ord("n"), ord("N"), 27):
            return False
