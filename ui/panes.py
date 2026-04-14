"""
ui/panes.py — Left and right split-pane renderers.

``draw_left_pane``  — scrollable task list
``draw_right_pane`` — task details + subtask list with progress bar

Both functions are pure renderers: they receive all needed data as
arguments and call win.refresh() at the end.  No database calls here.
"""

import curses
from todo_app.config import (
    CP_TODO,
    CP_INPROG,
    CP_DONE,
    CP_DUE,
    CP_SOON,
    CP_SEL_ACTIVE,
    CP_SEL_IDLE,
    CP_BORDER_IDLE,
    CP_TITLE,
    CP_LABEL,
    CP_PROG_FILL,
    CP_PROG_EMPTY,
    STATUS_ICON,
    STATUS_LABEL,
    STATUS_CP,
)
from todo_app.utils import date_urgency, fmt_date, task_color
from .drawing import sw, fill_row, draw_border


# ── Left pane ─────────────────────────────────────────────────────────────────


def draw_left_pane(win, tasks, sel: int, offset: int, active: bool) -> None:
    """
    Render the task list.

    Parameters
    ----------
    tasks  : list of sqlite3.Row
    sel    : index of the currently selected task
    offset : first visible row (scroll state)
    active : whether this pane has keyboard focus
    """
    win.erase()
    h, w = win.getmaxyx()
    inner_h = h - 2

    # Badge: count urgent non-done tasks
    n_due = sum(
        1
        for t in tasks
        if date_urgency(t["due_date"]) in ("today", "overdue") and t["status"] != "done"
    )
    badge = f" !{n_due}" if n_due else ""
    draw_border(win, active, f"TASKS {len(tasks)}{badge}")

    if not tasks:
        sw(
            win,
            h // 2,
            2,
            "No tasks — [a] to add",
            curses.color_pair(CP_TODO) | curses.A_DIM,
        )
        win.refresh()
        return

    for i, task in enumerate(tasks[offset : offset + inner_h - 1]):
        idx = offset + i
        row = i + 1
        is_sel = idx == sel

        urg = date_urgency(task["due_date"])
        st = task["status"]
        base = task_color(task)

        # Left-column urgency indicator
        if st != "done" and urg == "today":
            dot = "●"
        elif st != "done" and urg == "overdue":
            dot = "!"
        else:
            dot = " "

        icon = STATUS_ICON.get(st, "?")
        title_txt = task["title"]
        max_t = w - 7
        if len(title_txt) > max_t:
            title_txt = title_txt[: max_t - 1] + "…"

        line = f" {dot}{icon} {title_txt}"

        if is_sel:
            atr = (
                curses.color_pair(CP_SEL_ACTIVE) | curses.A_BOLD
                if active
                else curses.color_pair(CP_SEL_IDLE)
            )
            fill_row(win, row, atr)
            sw(win, row, 0, line, atr)
        else:
            sw(win, row, 0, line, base)

    # Scroll percentage indicator
    if len(tasks) > inner_h - 1:
        pct = int(sel / max(1, len(tasks) - 1) * 100)
        sw(win, h - 1, w - 6, f"{pct:3d}%", curses.color_pair(CP_BORDER_IDLE))

    win.refresh()


# ── Right pane ────────────────────────────────────────────────────────────────


def draw_right_pane(win, task, subtasks, sub_sel: int, active: bool) -> None:
    """
    Render the task detail view (right pane).

    Parameters
    ----------
    task     : sqlite3.Row | None  — the selected task
    subtasks : list of sqlite3.Row
    sub_sel  : index of the highlighted subtask
    active   : whether this pane has keyboard focus
    """
    win.erase()
    h, w = win.getmaxyx()

    if task is None:
        draw_border(win, active, "DETAILS")
        msg = "Select a task  (←/→ or Enter)"
        sw(
            win,
            h // 2,
            max(1, (w - len(msg)) // 2),
            msg,
            curses.color_pair(CP_TODO) | curses.A_DIM,
        )
        win.refresh()
        return

    urg = date_urgency(task["due_date"])
    st = task["status"]
    tc = task_color(task)

    # Urgency badge in the border title
    urg_badge = ""
    if st != "done":
        if urg == "today":
            urg_badge = " ⚠ DUE TODAY"
        elif urg == "overdue":
            urg_badge = " ⚠ OVERDUE!"
        elif urg == "soon":
            urg_badge = " ~ DUE SOON"

    draw_border(win, active, f"DETAILS{urg_badge}")

    LABEL = curses.color_pair(CP_LABEL) | curses.A_BOLD
    DIM = curses.color_pair(CP_TODO) | curses.A_DIM
    YEL = curses.color_pair(CP_INPROG)
    CYAN = curses.color_pair(CP_TITLE) | curses.A_BOLD
    RED = curses.color_pair(CP_DUE) | curses.A_BOLD
    SOON_A = curses.color_pair(CP_SOON) | curses.A_BOLD

    inner_w = w - 4

    # ── Row 1: Title ──────────────────────────────────────────────────────────
    sw(win, 1, 2, "Title  ", LABEL)
    t_txt = task["title"]
    if len(t_txt) > inner_w - 8:
        t_txt = t_txt[: inner_w - 9] + "…"
    sw(win, 1, 9, t_txt, tc | curses.A_BOLD)

    # ── Row 2: Status ─────────────────────────────────────────────────────────
    sw(win, 2, 2, "Status ", LABEL)
    st_str = f"{STATUS_ICON[st]}  {STATUS_LABEL[st]}"
    sw(win, 2, 9, st_str, tc)
    if urg_badge and st != "done":
        ba = RED if urg in ("today", "overdue") else SOON_A
        sw(win, 2, 9 + len(st_str) + 2, urg_badge.strip(), ba)

    # ── Row 3: Dates ──────────────────────────────────────────────────────────
    sw(win, 3, 2, "Start  ", LABEL)
    sw(win, 3, 9, fmt_date(task["start_date"]), YEL)
    due_col = min(w - 24, 9 + 14)
    sw(win, 3, due_col, "Due  ", LABEL)
    da = RED if urg in ("today", "overdue") else YEL
    sw(win, 3, due_col + 5, fmt_date(task["due_date"]), da)

    # ── Row 4: Description ────────────────────────────────────────────────────
    desc = (task["description"] or "").strip()
    div_row = 5
    if desc:
        sw(win, 4, 2, "Desc   ", LABEL)
        # Word-wrap to at most two lines
        words = desc.split()
        line1, line2 = "", ""
        for word in words:
            if len(line1) + len(word) + 1 <= inner_w - 9:
                line1 += (" " if line1 else "") + word
            elif len(line2) + len(word) + 1 <= inner_w - 2:
                line2 += (" " if line2 else "") + word
        sw(win, 4, 9, line1, DIM)
        if line2:
            sw(win, 5, 9, line2, DIM)
            div_row = 6

    # ── Divider ───────────────────────────────────────────────────────────────
    try:
        win.hline(
            div_row, 1, curses.ACS_HLINE, w - 2, curses.color_pair(CP_BORDER_IDLE)
        )
    except curses.error:
        pass

    # ── Subtask header ────────────────────────────────────────────────────────
    n_done = sum(1 for s in subtasks if s["status"] == "done")
    n_total = len(subtasks)
    hdr_row = div_row + 1

    sw(win, hdr_row, 2, "SUBTASKS", CYAN)
    sw(win, hdr_row, 11, f"{n_done}/{n_total}", DIM)

    # ── Progress bar ──────────────────────────────────────────────────────────
    if n_total:
        bar_w = min(inner_w - 18, 18)
        filled = int(n_done / n_total * bar_w)
        pct = int(n_done / n_total * 100)
        bar_x = w - bar_w - 8
        for bx in range(bar_w):
            ba = (
                curses.color_pair(CP_PROG_FILL)
                if bx < filled
                else curses.color_pair(CP_PROG_EMPTY) | curses.A_DIM
            )
            sw(win, hdr_row, bar_x + bx, " ", ba)
        pct_a = curses.color_pair(CP_DONE) if pct == 100 else YEL
        sw(win, hdr_row, bar_x + bar_w + 1, f"{pct}%", pct_a)

    # ── Column header ─────────────────────────────────────────────────────────
    col_row = hdr_row + 1
    sw(
        win,
        col_row,
        2,
        f" # {'':2} {'ST':<13} TITLE",
        curses.color_pair(CP_BORDER_IDLE) | curses.A_DIM,
    )

    # ── Subtask rows ──────────────────────────────────────────────────────────
    list_start = col_row + 1
    list_h = h - list_start - 2

    if not subtasks:
        sw(win, list_start + 1, 4, "No subtasks — [a] to add", DIM)
    else:
        # Keep selected subtask in view
        sub_off = max(0, sub_sel - list_h + 1) if sub_sel >= list_h else 0

        for i, sub in enumerate(subtasks[sub_off : sub_off + list_h]):
            idx = sub_off + i
            is_sel = idx == sub_sel and active
            base_a = curses.color_pair(STATUS_CP.get(sub["status"], CP_TODO))

            arrow = ">" if is_sel else " "
            s_icon = STATUS_ICON.get(sub["status"], "?")
            s_lbl = STATUS_LABEL[sub["status"]]
            s_title = sub["title"]
            max_s = inner_w - 22
            if len(s_title) > max_s:
                s_title = s_title[: max_s - 1] + "…"

            line = f" {arrow}{idx + 1:<2} {s_icon} {s_lbl:<13} {s_title}"
            row = list_start + i

            if is_sel:
                sel_a = curses.color_pair(CP_SEL_ACTIVE) | curses.A_BOLD
                fill_row(win, row, sel_a)
                sw(win, row, 0, line, sel_a)
            else:
                sw(win, row, 0, line, base_a)

    win.refresh()
