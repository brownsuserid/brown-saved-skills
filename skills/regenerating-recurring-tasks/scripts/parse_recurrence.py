#!/usr/bin/env python3
"""
Parse a human-entered recurrence string and return the next due date.

Usage:
    python3 parse_recurrence.py "every other Tuesday"
    python3 parse_recurrence.py "4x weekly"
    python3 parse_recurrence.py "Monthly"

Output (JSON):
    {"next_date": "2026-03-01", "canonical": "Monthly"}
    {"next_date": "2026-03-04", "canonical": "every other Tuesday"}
    {"skip": true, "reason": "placeholder text"}
    {"error": "Could not parse recurrence: ..."}

Exit codes:
    0 = success (next_date or skip)
    1 = unrecoverable parse error
"""

import json
import re
import sys
from datetime import date, timedelta

# Placeholder strings that mean "no recurrence"
PLACEHOLDERS = {
    "a description of when you would like the task to repeat",
    "none",
    "",
}

# Canonical patterns -> timedelta/logic
CANONICAL = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "bi-weekly": timedelta(weeks=2),
    "biweekly": timedelta(weeks=2),
    "fortnightly": timedelta(weeks=2),
    "monthly": None,  # handled separately (month arithmetic)
    "quarterly": None,
    "annually": None,
    "yearly": None,
}

WEEKDAYS = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}


def add_months(d: date, months: int) -> date:
    """Add months to a date, clamping day to valid range."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    import calendar

    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_weekday(d: date, weekday: int) -> date:
    """Return the next occurrence of a weekday (0=Mon) after date d."""
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return d + timedelta(days=days_ahead)


def parse_recurrence(text: str) -> dict:
    """Parse a recurrence string, return dict with next_date or skip/error."""
    today = date.today()
    raw = text.strip()
    normalized = raw.lower().strip()

    # Check placeholders
    if normalized in PLACEHOLDERS:
        return {"skip": True, "reason": "placeholder text"}

    # Exact canonical match
    if normalized in CANONICAL:
        delta = CANONICAL[normalized]
        if delta:
            return {"next_date": str(today + delta), "canonical": raw}
        if normalized == "monthly":
            return {"next_date": str(add_months(today, 1)), "canonical": "Monthly"}
        if normalized == "quarterly":
            return {"next_date": str(add_months(today, 3)), "canonical": "Quarterly"}
        if normalized in ("annually", "yearly"):
            return {"next_date": str(add_months(today, 12)), "canonical": "Annually"}

    # "every day" / "each day"
    if re.match(r"(every|each)\s+day", normalized):
        return {"next_date": str(today + timedelta(days=1)), "canonical": "Daily"}

    # "every week" / "each week"
    if re.match(r"(every|each)\s+week", normalized):
        return {"next_date": str(today + timedelta(weeks=1)), "canonical": "Weekly"}

    # "every month" / "each month"
    if re.match(r"(every|each)\s+month", normalized):
        return {"next_date": str(add_months(today, 1)), "canonical": "Monthly"}

    # "every year" / "each year"
    if re.match(r"(every|each)\s+(year|annual)", normalized):
        return {"next_date": str(add_months(today, 12)), "canonical": "Annually"}

    # "every N days/weeks/months"
    m = re.match(r"every\s+(\d+)\s+(day|week|month|year)s?", normalized)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if unit == "day":
            return {"next_date": str(today + timedelta(days=n)), "canonical": raw}
        if unit == "week":
            return {"next_date": str(today + timedelta(weeks=n)), "canonical": raw}
        if unit == "month":
            return {"next_date": str(add_months(today, n)), "canonical": raw}
        if unit == "year":
            return {"next_date": str(add_months(today, n * 12)), "canonical": raw}

    # "every other <weekday>" or "every 2 weeks"
    if re.match(r"every\s+(other|2)\s+week", normalized):
        return {"next_date": str(today + timedelta(weeks=2)), "canonical": "Bi-weekly"}

    # "every other <weekday>"
    m = re.match(r"every\s+other\s+(\w+)", normalized)
    if m:
        day_name = m.group(1)
        if day_name in WEEKDAYS:
            nxt = next_weekday(today, WEEKDAYS[day_name])
            # "other" = skip one, so add another week
            nxt = nxt + timedelta(weeks=1)
            return {"next_date": str(nxt), "canonical": raw}

    # "every <weekday>"
    m = re.match(r"every\s+(\w+)$", normalized)
    if m:
        day_name = m.group(1)
        if day_name in WEEKDAYS:
            nxt = next_weekday(today, WEEKDAYS[day_name])
            return {"next_date": str(nxt), "canonical": "Weekly"}

    # "Nx weekly" (e.g., "4x weekly" = every other day roughly, but intent is N times per week)
    m = re.match(r"(\d+)x?\s*(weekly|per\s+week|a\s+week)", normalized)
    if m:
        times = int(m.group(1))
        if times >= 7:
            return {"next_date": str(today + timedelta(days=1)), "canonical": "Daily"}
        interval = max(1, 7 // times)
        return {"next_date": str(today + timedelta(days=interval)), "canonical": raw}

    # "Nx monthly" / "Nx per month"
    m = re.match(r"(\d+)x?\s*(monthly|per\s+month|a\s+month)", normalized)
    if m:
        times = int(m.group(1))
        interval = max(1, 30 // times)
        return {"next_date": str(today + timedelta(days=interval)), "canonical": raw}

    # "twice a week" / "twice weekly"
    if re.match(r"twice\s+(a\s+week|weekly)", normalized):
        return {"next_date": str(today + timedelta(days=3)), "canonical": raw}

    # "twice a month" / "twice monthly"
    if re.match(r"twice\s+(a\s+month|monthly)", normalized):
        return {"next_date": str(today + timedelta(days=15)), "canonical": raw}

    # "1st and 15th" or "1st & 15th" (semi-monthly)
    if re.search(r"1st\s*(and|&)\s*15th", normalized):
        if today.day < 15:
            nxt = today.replace(day=15)
        else:
            nxt = add_months(today, 1).replace(day=1)
        return {"next_date": str(nxt), "canonical": raw}

    # "end of month" / "last day of month"
    if re.search(r"(end\s+of|last\s+day\s+of)\s+(the\s+)?month", normalized):
        import calendar

        nxt = add_months(today, 1)
        last_day = calendar.monthrange(nxt.year, nxt.month)[1]
        return {"next_date": str(nxt.replace(day=last_day)), "canonical": raw}

    return {"error": f"Could not parse recurrence: {raw}"}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No recurrence string provided"}))
        sys.exit(1)

    text = sys.argv[1]
    result = parse_recurrence(text)
    print(json.dumps(result))

    if "error" in result:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
