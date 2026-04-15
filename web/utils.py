"""
web/utils.py — Pure utility functions.

Responsibilities
----------------
- Parse and format date strings in several common formats
- Classify due-date urgency relative to today
- Enrich task/subtask dicts with the computed ``urgency`` field

No HTTP, no database, no side-effects — all functions are unit-testable
in complete isolation.
"""

from datetime import date, datetime

# ── Date parsing ──────────────────────────────────────────────────────────────

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")


def parse_date(s: str) -> date | None:
    """
    Try several common date formats and return a ``datetime.date``.

    Formats tried in order: ``YYYY-MM-DD``, ``DD/MM/YYYY``, ``DD-MM-YYYY``.
    Returns ``None`` if no format matches or *s* is empty/None.
    """
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except (ValueError, AttributeError):
            pass
    return None


def fmt_date(s: str) -> str:
    """
    Return a human-readable date string, e.g. ``'14 Apr 2026'``.

    Returns ``'-'`` when *s* is empty or unparseable.
    """
    if not s:
        return "-"
    d = parse_date(s)
    return d.strftime("%d %b %Y") if d else s


# ── Urgency ───────────────────────────────────────────────────────────────────


def date_urgency(due_str: str) -> str | None:
    """
    Classify how urgent a due date is relative to today.

    Returns
    -------
    ``'overdue'``  — due date is in the past
    ``'today'``    — due date is today
    ``'soon'``     — due within the next 3 days (inclusive)
    ``None``       — no date set, unparseable, or more than 3 days away
    """
    d = parse_date(due_str)
    if not d:
        return None
    delta = (d - date.today()).days
    if delta < 0:
        return "overdue"
    if delta == 0:
        return "today"
    if delta <= 3:
        return "soon"
    return None


# ── Enrichment ────────────────────────────────────────────────────────────────


def enrich(record: dict) -> dict:
    """
    Attach a computed ``urgency`` field to a task or subtask dict.

    Mutates and returns *record* for convenient chaining:

    .. code-block:: python

        task = enrich(db.get_task(tid))
    """
    record["urgency"] = date_urgency(record.get("due_date", ""))
    return record


def enrich_many(records: list[dict]) -> list[dict]:
    """Apply :func:`enrich` to every record in *records*."""
    return [enrich(r) for r in records]
