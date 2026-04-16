"""
app.py — Main application event loop.

``app_loop(stdscr)`` is the only public symbol.  It wires together the
database, dialogs, and pane renderers.  Business logic that belongs
to the UI (focus state, scroll offsets, keybindings) lives here;
everything else is delegated to a dedicated module.

Web server integration
----------------------
Pressing ``W`` in the left pane toggles the background web server on/off.
The current status (port or "off") is shown in the header bar and in a
brief notification overlay after each toggle.
"""

import curses
from datetime import date

from .config import MIN_TERMINAL_H, MIN_TERMINAL_W, LEFT_PANE_MIN, LEFT_PANE_MAX
from .database import (
    get_all_tasks,
    get_subtasks,
    add_task,
    update_task,
    set_task_status,
    delete_task,
    add_subtask,
    set_subtask_status,
    update_subtask,
    delete_subtask,
)
from .utils import parse_date
from . import web_bridge
from ui.drawing import draw_header, draw_helpbar
from ui.dialogs import input_dialog, pick_status, confirm
from ui.panes import draw_left_pane, draw_right_pane

FOCUS_LEFT = "left"
FOCUS_RIGHT = "right"

# ── Help-bar key maps ─────────────────────────────────────────────────────────

_LEFT_HELP = [
    ("a", "Add"),
    ("e", "Edit"),
    ("s", "Status"),
    ("d", "Delete"),
    ("W", "Web"),
    ("Enter/→", "Details"),
    ("q", "Quit"),
]

_RIGHT_HELP = [
    ("a", "Add sub"),
    ("x", "Sub status"),
    ("r", "Rename"),
    ("D", "Del sub"),
    ("e", "Edit task"),
    ("s", "Task status"),
    ("Esc/←", "Back"),
]

# ── Notification overlay ──────────────────────────────────────────────────────


def _show_notify(stdscr, msg: str) -> None:
    """
    Flash a one-line notification centered on the screen for one keypress.

    The overlay is drawn over whatever is currently on screen; the TUI
    redraws itself cleanly on the next iteration of the main loop.
    """
    H, W = stdscr.getmaxyx()
    dw = min(len(msg) + 6, W - 4)
    dy = H // 2
    dx = (W - dw) // 2
    try:
        win = curses.newwin(3, dw, dy, dx)
        win.border()
        attr = curses.color_pair(12) | curses.A_BOLD  # CP_HELP = 12
        text = msg[: dw - 4]
        win.addstr(1, 2, text, attr)
        win.refresh()
        stdscr.getch()  # any key dismisses
    except curses.error:
        pass


# ── Task input fields helper ──────────────────────────────────────────────────


def _task_fields(task=None) -> list[dict]:
    """Build the field list for the add/edit task dialog."""
    return [
        {"label": "Title", "default": task["title"] if task else ""},
        {"label": "Description", "default": task["description"] if task else ""},
        {
            "label": "Start Date",
            "default": (
                task["start_date"] if task else date.today().strftime("%Y-%m-%d")
            ),
            "hint": "YYYY-MM-DD",
        },
        {
            "label": "Due Date",
            "default": task["due_date"] if task else "",
            "hint": "YYYY-MM-DD",
        },
    ]


def _save_task(stdscr, dialog_title: str, task=None) -> bool:
    """
    Open the add/edit dialog and persist the result.

    Returns True if a change was made, False if cancelled.
    """
    vals = input_dialog(stdscr, dialog_title, _task_fields(task))
    if not vals or not vals[0].strip():
        return False

    title, desc, sdate, ddate = vals
    sd = parse_date(sdate)
    dd = parse_date(ddate)
    sd_str = sd.strftime("%Y-%m-%d") if sd else ""
    dd_str = dd.strftime("%Y-%m-%d") if dd else ""

    if task is None:
        add_task(title.strip(), desc.strip(), sd_str, dd_str)
    else:
        update_task(task["id"], title.strip(), desc.strip(), sd_str, dd_str)
    return True


# ── Web status indicator ──────────────────────────────────────────────────────


def _web_status_label() -> str:
    """
    Return a short string for the header showing web server state.

    Examples: ``" WEB:8080"``  or  ``""`` when stopped.
    """
    if web_bridge.is_running():
        return f" WEB:{web_bridge.current_port()}"
    return ""


# ── Main loop ─────────────────────────────────────────────────────────────────


def app_loop(stdscr) -> None:
    """Run the TUI until the user presses q."""
    curses.curs_set(0)
    stdscr.keypad(True)

    tasks = get_all_tasks()
    task_sel = 0
    task_off = 0
    sub_sel = 0
    focus = FOCUS_LEFT

    while True:
        stdscr.erase()
        H, W = stdscr.getmaxyx()

        # ── Minimum terminal size guard ───────────────────────────────────────
        if H < MIN_TERMINAL_H or W < MIN_TERMINAL_W:
            stdscr.addstr(0, 0, "Terminal too small — resize then press any key")
            stdscr.refresh()
            stdscr.getch()
            continue

        # ── Layout ────────────────────────────────────────────────────────────
        LEFT_W = min(max(LEFT_PANE_MIN, W // 3), LEFT_PANE_MAX)
        RIGHT_W = W - LEFT_W - 1
        PANE_H = H - 2  # header row + help bar row
        inner_h = PANE_H - 2

        # ── Clamp selections ──────────────────────────────────────────────────
        if tasks:
            task_sel = max(0, min(task_sel, len(tasks) - 1))
        else:
            task_sel = 0

        cur_task = tasks[task_sel] if tasks else None
        subtasks = get_subtasks(cur_task["id"]) if cur_task else []

        if subtasks:
            sub_sel = max(0, min(sub_sel, len(subtasks) - 1))
        else:
            sub_sel = 0

        # ── Scroll offset for left pane ───────────────────────────────────────
        if task_sel < task_off:
            task_off = task_sel
        elif task_sel >= task_off + inner_h - 1:
            task_off = task_sel - inner_h + 2

        # ── Draw chrome ───────────────────────────────────────────────────────
        draw_header(stdscr, extra=_web_status_label())
        draw_helpbar(stdscr, _LEFT_HELP if focus == FOCUS_LEFT else _RIGHT_HELP)

        # Vertical divider
        div_a = curses.color_pair(11) | curses.A_DIM  # CP_BORDER_IDLE = 11
        for row in range(1, H - 1):
            try:
                stdscr.addch(row, LEFT_W, curses.ACS_VLINE, div_a)
            except curses.error:
                pass
        stdscr.refresh()

        # ── Draw panes ────────────────────────────────────────────────────────
        left_win = curses.newwin(PANE_H, LEFT_W, 1, 0)
        right_win = curses.newwin(PANE_H, RIGHT_W, 1, LEFT_W + 1)
        left_win.keypad(True)
        right_win.keypad(True)

        draw_left_pane(
            left_win, tasks, task_sel, task_off, active=(focus == FOCUS_LEFT)
        )
        draw_right_pane(
            right_win, cur_task, subtasks, sub_sel, active=(focus == FOCUS_RIGHT)
        )

        # ── Read input ────────────────────────────────────────────────────────
        stdscr.move(H - 1, 0)
        ch = stdscr.getch()

        # ── Global / pane-switch keys ─────────────────────────────────────────
        if ch in (ord("q"), ord("Q")) and focus == FOCUS_LEFT:
            break

        elif ch in (curses.KEY_RIGHT, curses.KEY_ENTER, 10, 13) and focus == FOCUS_LEFT:
            if tasks:
                focus = FOCUS_RIGHT
                sub_sel = 0

        elif ch in (curses.KEY_LEFT, 27) and focus == FOCUS_RIGHT:
            focus = FOCUS_LEFT

        # ── Web server toggle (W) — available from either pane ────────────────
        elif ch == ord("W"):
            msg = web_bridge.toggle()
            _show_notify(stdscr, f"  {msg}  ")

        # ── Left-pane keys ────────────────────────────────────────────────────
        elif focus == FOCUS_LEFT:
            if ch == curses.KEY_UP:
                task_sel = max(0, task_sel - 1)
                sub_sel = 0
            elif ch == curses.KEY_DOWN:
                task_sel = min(max(0, len(tasks) - 1), task_sel + 1)
                sub_sel = 0
            elif ch == curses.KEY_PPAGE:
                task_sel = max(0, task_sel - (inner_h - 1))
                sub_sel = 0
            elif ch == curses.KEY_NPAGE:
                task_sel = min(max(0, len(tasks) - 1), task_sel + (inner_h - 1))
                sub_sel = 0

            elif ch == ord("a"):
                if _save_task(stdscr, "Add New Task"):
                    tasks = get_all_tasks()
                    task_sel = 0

            elif ch == ord("e") and tasks:
                if _save_task(stdscr, "Edit Task", cur_task):
                    tasks = get_all_tasks()

            elif ch == ord("s") and tasks:
                new_st = pick_status(stdscr, cur_task["status"])
                if new_st:
                    set_task_status(cur_task["id"], new_st)
                    tasks = get_all_tasks()

            elif ch == ord("d") and tasks:
                if confirm(stdscr, f'Delete "{cur_task["title"][:30]}"?'):
                    delete_task(cur_task["id"])
                    tasks = get_all_tasks()
                    task_sel = max(0, min(task_sel, len(tasks) - 1))

        # ── Right-pane keys ───────────────────────────────────────────────────
        elif focus == FOCUS_RIGHT:
            if ch == curses.KEY_UP:
                sub_sel = max(0, sub_sel - 1)
            elif ch == curses.KEY_DOWN:
                sub_sel = min(max(0, len(subtasks) - 1), sub_sel + 1)

            elif ch == ord("a"):
                vals = input_dialog(stdscr, "Add Subtask", [{"label": "Title"}])
                if vals and vals[0].strip():
                    add_subtask(cur_task["id"], vals[0].strip())
                    subtasks = get_subtasks(cur_task["id"])
                    sub_sel = len(subtasks) - 1

            elif ch == ord("x") and subtasks:
                new_st = pick_status(stdscr, subtasks[sub_sel]["status"])
                if new_st:
                    set_subtask_status(subtasks[sub_sel]["id"], new_st)

            elif ch == ord("r") and subtasks:
                sub = subtasks[sub_sel]
                vals = input_dialog(
                    stdscr,
                    "Rename Subtask",
                    [{"label": "Title", "default": sub["title"]}],
                )
                if vals and vals[0].strip():
                    update_subtask(sub["id"], vals[0].strip())

            elif ch == ord("D") and subtasks:
                sub = subtasks[sub_sel]
                if confirm(stdscr, f'Delete subtask "{sub["title"][:30]}"?'):
                    delete_subtask(sub["id"])
                    sub_sel = max(0, sub_sel - 1)

            elif ch == ord("e") and cur_task:
                if _save_task(stdscr, "Edit Task", cur_task):
                    tasks = get_all_tasks()

            elif ch == ord("s") and cur_task:
                new_st = pick_status(stdscr, cur_task["status"])
                if new_st:
                    set_task_status(cur_task["id"], new_st)
                    tasks = get_all_tasks()

            elif ch == ord("d") and cur_task:
                if confirm(stdscr, f'Delete task "{cur_task["title"][:30]}"?'):
                    delete_task(cur_task["id"])
                    tasks = get_all_tasks()
                    task_sel = max(0, min(task_sel, len(tasks) - 1))
                    focus = FOCUS_LEFT
