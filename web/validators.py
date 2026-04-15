"""
web/validators.py — Request body validation.

Responsibilities
----------------
- Validate incoming JSON payloads for tasks and subtasks
- Return structured errors so handlers stay thin

No HTTP imports, no database access — validators are pure functions that
accept a dict and return ``(cleaned_data | None, error_message | None)``.
"""

from .config import STATUSES

# ── Type alias ────────────────────────────────────────────────────────────────

ValidationResult = tuple[dict | None, str | None]

# ── Task validation ───────────────────────────────────────────────────────────


def validate_task(body: dict, *, require_title: bool = True) -> ValidationResult:
    """
    Validate and clean a task creation or update payload.

    Parameters
    ----------
    body          : raw decoded JSON dict from the request body.
    require_title : ``True`` for POST (creation), ``False`` for partial PUT.

    Returns
    -------
    ``(cleaned, None)`` on success, ``(None, error_message)`` on failure.

    The returned *cleaned* dict contains only the fields this app accepts,
    with whitespace stripped from strings.
    """
    title = (body.get("title") or "").strip()

    if require_title and not title:
        return None, "title is required"
    if title == "" and "title" in body:
        return None, "title cannot be empty"

    status = body.get("status")
    if status is not None and status not in STATUSES:
        return None, f"status must be one of {STATUSES}"

    cleaned = {}
    if title:
        cleaned["title"] = title
    if "description" in body:
        cleaned["description"] = (body["description"] or "").strip()
    if status is not None:
        cleaned["status"] = status
    if "start_date" in body:
        cleaned["start_date"] = (body.get("start_date") or "").strip()
    if "due_date" in body:
        cleaned["due_date"] = (body.get("due_date") or "").strip()

    # Supply defaults for creation
    if require_title:
        cleaned.setdefault("description", "")
        cleaned.setdefault("status", "todo")
        cleaned.setdefault("start_date", "")
        cleaned.setdefault("due_date", "")

    return cleaned, None


# ── Subtask validation ────────────────────────────────────────────────────────


def validate_subtask(body: dict, *, require_title: bool = True) -> ValidationResult:
    """
    Validate and clean a subtask creation or update payload.

    Subtasks share the same fields as tasks (minus task-level relations),
    so this delegates directly to :func:`validate_task`.
    """
    return validate_task(body, require_title=require_title)
