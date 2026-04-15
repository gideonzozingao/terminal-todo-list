"""
web — ZUQONTECH TODO web server package.

Public surface
--------------
    from web import start_server   # used by web_server.py
    from web import init_db        # used by web_server.py

Internal modules
----------------
    web.config      — constants (DB_PATH, PORT, STATUSES, …)
    web.database    — SQLite schema, migrations, CRUD helpers
    web.utils       — pure date/enrichment helpers
    web.validators  — request body validation
    web.handlers    — HTTP handler and URL router
"""

from web.database import init_db
from web.server import start_server

__all__ = ["init_db", "start_server"]
