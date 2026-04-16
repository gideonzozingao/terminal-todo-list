#!/usr/bin/env python3
"""
todo.py — Entry point.

Run:   python3 todo.py
DB:    ~/.todo_tasks.db
Needs: Python 3.6+  (stdlib only — curses + sqlite3)

Web server
----------
Press ``W`` inside the TUI to start or stop the background web interface.
The server runs in a daemon thread — it shares the same SQLite database
and is stopped automatically when the TUI exits.  To start the web server
standalone (without the TUI) run ``python3 web_server.py`` instead.
"""

import curses
import locale

locale.setlocale(locale.LC_ALL, "")

from todo_app.database import init_db
from todo_app.colors import init_colors
from todo_app.app import app_loop
from todo_app import web_bridge


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
    finally:
        # Stop the background web server if the user toggled it on,
        # regardless of whether the TUI exited normally or via Ctrl-C.
        web_bridge.stop()

    print("\nGoodbye!\n")
