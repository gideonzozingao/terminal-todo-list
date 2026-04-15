#!/usr/bin/env python3
"""
web_server.py — ZUQONTECH TODO  Web Interface  (entry point)

Run:
    python3 web_server.py            # port 8080
    python3 web_server.py 9000       # custom port

REST API
--------
    GET    /api/tasks                       list tasks (?status= ?q= filters)
    POST   /api/tasks                       create task
    GET    /api/tasks/<id>                  get task
    PUT    /api/tasks/<id>                  update task
    DELETE /api/tasks/<id>                  delete task + its subtasks

    GET    /api/tasks/<id>/subtasks         list subtasks
    POST   /api/tasks/<id>/subtasks         create subtask
    PUT    /api/subtasks/<id>               update subtask
    DELETE /api/subtasks/<id>               delete subtask

    GET    /api/stats                       dashboard counts

All JSON responses include a computed ``urgency`` field on tasks and
subtasks: ``"overdue"`` | ``"today"`` | ``"soon"`` | ``null``.

Module layout
-------------
    web_server.py       <- this file (entry point only)
    web/
        __init__.py     <- public surface: init_db, start_server
        config.py       <- constants: DB_PATH, PORT, STATUSES, ...
        database.py     <- schema, migrations, CRUD helpers
        utils.py        <- pure date helpers and task enrichment
        validators.py   <- request body validation
        handlers.py     <- HTTP handler and URL router
        server.py       <- ThreadingHTTPServer lifecycle
"""

from web.database import init_db
from web.server import start_server
from web.config import PORT

if __name__ == "__main__":
    init_db()
    start_server(PORT)
