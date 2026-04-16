"""
todo_app/web_bridge.py — Background web server bridge.

Responsibilities
----------------
- Own the single ``WebServerHandle`` instance for the process
- Expose a simple toggle / query API so ``app.py`` never imports
  from the ``web`` package directly
- Catch port-in-use errors and surface them as a human-readable string
  instead of an exception, so the TUI never crashes on a bad toggle

Public API
----------
``toggle(port) -> str``
    Start the server if stopped, stop it if running.
    Returns a one-line status message suitable for displaying in the TUI.

``is_running() -> bool``
    True while the background thread is alive.

``port() -> int | None``
    The port currently in use, or None if stopped.

``stop() -> None``
    Unconditionally stop the server.  Called by todo.py on exit.
"""

from __future__ import annotations

from web.config import PORT as DEFAULT_PORT
from web.server import start_server_background, WebServerHandle

# ── Module-level state ────────────────────────────────────────────────────────
# One handle for the lifetime of the process.  None means stopped.

_handle: WebServerHandle | None = None


# ── Public API ────────────────────────────────────────────────────────────────


def toggle(port: int = DEFAULT_PORT) -> str:
    """
    Toggle the web server on or off.

    Returns a short status string for the TUI notification overlay:
      - ``"Web server started on port XXXX"``
      - ``"Web server stopped"``
      - ``"Port XXXX already in use"``
      - ``"Failed to start: <reason>"``
    """
    global _handle

    if _handle is not None and _handle.is_running:
        _handle.stop()
        _handle = None
        return "Web server stopped"

    try:
        _handle = start_server_background(port)
        return f"Web server started  http://localhost:{port}"
    except OSError as exc:
        _handle = None
        if exc.errno == 98 or "address already in use" in str(exc).lower():
            return f"Port {port} already in use"
        return f"Failed to start: {exc}"


def is_running() -> bool:
    """Return ``True`` while the background server thread is alive."""
    return _handle is not None and _handle.is_running


def current_port() -> int | None:
    """Return the active port, or ``None`` if the server is stopped."""
    return _handle.port if is_running() else None


def stop() -> None:
    """
    Unconditionally stop the server if it is running.

    Called by ``todo.py`` on process exit so the daemon thread is joined
    cleanly rather than killed by the interpreter.
    """
    global _handle
    if _handle is not None:
        _handle.stop()
        _handle = None
