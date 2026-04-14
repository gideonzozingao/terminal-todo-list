#!/usr/bin/env python3
"""
todo.py — Entry point.

Run:   python3 todo.py
DB:    ~/.todo_tasks.db
Needs: Python 3.6+  (stdlib only — curses + sqlite3)
"""
import curses
import locale

locale.setlocale(locale.LC_ALL, "")

from todo_app.database import init_db
from todo_app.colors import init_colors
from todo_app.app import app_loop


def main(stdscr) -> None:
    init_colors()
    stdscr.keypad(True)
    curses.curs_set(0)
    app_loop(stdscr)


if __name__ == "__main__":
    init_db()
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    print("\nGoodbye!\n")
