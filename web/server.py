"""
web/server.py — HTTP server lifecycle.

Responsibilities
----------------
- Instantiate and configure ``ThreadingHTTPServer``
- Print the startup banner
- Block on ``serve_forever()`` until interrupted   [standalone mode]
- Start in a daemon thread and return a handle     [embedded/TUI mode]

Public API
----------
``start_server(port)``
    Blocking call used by ``web_server.py`` when run directly.

``start_server_background(port) -> WebServerHandle``
    Non-blocking call used by the TUI.  Returns a handle with:
      - ``.port``        int  — the port the server is listening on
      - ``.is_running``  bool — True while the server thread is alive
      - ``.stop()``      shut the server down gracefully
"""

import http.server
import threading

from .config import DB_PATH, PORT
from .handlers import TodoHandler


# ── Handle returned to callers of start_server_background() ──────────────────


class WebServerHandle:
    """
    A thin wrapper around a running ``ThreadingHTTPServer`` daemon thread.

    Callers receive an instance of this class from
    :func:`start_server_background`.  They should never instantiate it
    directly.
    """

    def __init__(self, server: http.server.ThreadingHTTPServer, port: int) -> None:
        self._server = server
        self._port = port
        self._thread = threading.Thread(
            target=server.serve_forever,
            name=f"web-server:{port}",
            daemon=True,  # dies automatically when the main process exits
        )
        self._thread.start()

    @property
    def port(self) -> int:
        """The TCP port this server is bound to."""
        return self._port

    @property
    def is_running(self) -> bool:
        """``True`` while the server daemon thread is alive."""
        return self._thread.is_alive()

    def stop(self) -> None:
        """
        Shut the server down and wait for the thread to exit.

        Safe to call more than once; subsequent calls are no-ops.
        """
        if self._thread.is_alive():
            self._server.shutdown()  # signals serve_forever() to return
            self._thread.join(timeout=3)


# ── Blocking entry point (used by web_server.py) ──────────────────────────────


def start_server(port: int = PORT) -> None:
    """
    Start the HTTP server on *port* and block until Ctrl-C.

    Used when running ``python3 web_server.py`` directly.
    """
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), TodoHandler)
    _print_banner(port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


# ── Non-blocking entry point (used by the TUI) ────────────────────────────────


def start_server_background(port: int = PORT) -> WebServerHandle:
    """
    Start the HTTP server in a background daemon thread.

    Returns a :class:`WebServerHandle` immediately; the server is already
    accepting connections by the time this function returns.

    Parameters
    ----------
    port : TCP port to bind.  Defaults to ``config.PORT``.

    Raises
    ------
    OSError
        If the port is already in use.
    """
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), TodoHandler)
    return WebServerHandle(server, port)


# ── Banner ────────────────────────────────────────────────────────────────────


def _print_banner(port: int) -> None:
    print("╔══════════════════════════════════════════╗")
    print("║  ZUQONTECH TODO  —  Web Interface        ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  http://localhost:{port:<25}║")
    print(f"║  DB: {DB_PATH:<36}║")
    print("║  Ctrl+C to stop                          ║")
    print("╚══════════════════════════════════════════╝")
