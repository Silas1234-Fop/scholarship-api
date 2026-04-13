import pathfix  # noqa — must be first

import re
from datetime import date

MONTH_NAMES = {
    "january": 1,  "jan": 1,
    "february": 2, "feb": 2,
    "march": 3,    "mar": 3,
    "april": 4,    "apr": 4,
    "may": 5,
    "june": 6,     "jun": 6,
    "july": 7,     "jul": 7,
    "august": 8,   "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def parse_deadline_to_date(raw: str):
    """
    Convert a raw deadline string to a Python date object.
    Returns None if parsing fails.
    Handles: 2026-11-15 / 15/11/2026 / 15 November 2026 / November 15, 2026
    """
    if not raw:
        return None
    raw = raw.strip()

    # 2026-11-15
    import re as _re
    m = _re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # 15/11/2026
    m = _re.match(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", raw)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= d <= 31 and 1 <= mo <= 12:
                return date(y, mo, d)
        except ValueError:
            pass

    # "15 November 2026" or "November 15, 2026"
    m = _re.search(
        r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})|([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})",
        raw
    )
    if m:
        try:
            if m.group(1):
                day, month_str, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
            else:
                month_str, day, year = m.group(4).lower(), int(m.group(5)), int(m.group(6))
            month = MONTH_NAMES.get(month_str)
            if month:
                return date(year, month, day)
        except ValueError:
            pass

    return None
