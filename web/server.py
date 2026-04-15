"""
web/server.py — HTTP server lifecycle.

Responsibilities
----------------
- Instantiate and configure ``ThreadingHTTPServer``
- Print the startup banner
- Block on ``serve_forever()`` until interrupted

This module does not know about routes, database, or validation.
It only wires together the stdlib server with ``TodoHandler``.
"""

import http.server

from .config import DB_PATH, PORT
from .handlers import TodoHandler


def start_server(port: int = PORT) -> None:
    """
    Start the HTTP server on *port* and block until Ctrl-C.

    Parameters
    ----------
    port : TCP port to listen on. Defaults to ``config.PORT`` (8080 or
           the value of the first CLI argument).
    """
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), TodoHandler)
    _print_banner(port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


def _print_banner(port: int) -> None:
    print("╔══════════════════════════════════════════╗")
    print("║  ZUQONTECH TODO  —  Web Interface        ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  http://localhost:{port:<25}║")
    print(f"║  DB: {DB_PATH:<36}║")
    print("║  Ctrl+C to stop                          ║")
    print("╚══════════════════════════════════════════╝")
