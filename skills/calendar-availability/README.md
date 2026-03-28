# Calendar Availability Engine

Find available time slots across Google and Apple calendars. Config-driven — which calendars to search, timezone, and other settings are defined in a YAML config file passed via `--config`.

## Scripts

- `fetch_events.py` — Fetches events from Google (via `gog` CLI) and Apple (via EventKit) calendars
- `find_availability.py` — Finds open time slots given busy periods, duration, and time-of-day constraints

## Usage

```bash
# Find 1-hour business-hours slots for the next 7 days
python3 find_availability.py --config /path/to/config.yaml

# Find 2-hour afternoon slots for a specific range
python3 find_availability.py --config /path/to/config.yaml \
    --duration 120 --time-of-day afternoon \
    --start 2026-03-19 --end 2026-03-21

# Fetch raw events as JSON
python3 fetch_events.py --config /path/to/config.yaml \
    --start 2026-03-19 --end 2026-03-21
```

## Config Format

```yaml
timezone: America/Phoenix

google_calendars:
  - label: Work
    account: user@example.com
    calendar_id: primary

apple_calendars:
  - name: Work
    source: Exchange
```

## Config Resolution

`--config` flag > `OPENCLAW_CALENDAR_CONFIG` env var > `config.yaml` in parent directory

## External Dependencies

- `gog` CLI — Google Calendar access ([github.com/aaroneden/gog](https://github.com/aaroneden/gog)). Must be installed and authenticated per Google account.
- `pyobjc-framework-EventKit` — Apple Calendar access (macOS only, optional). Install via `pip install pyobjc-framework-EventKit`.
- `pyyaml` — YAML config parsing

## Features

- Slot finding with configurable duration, time-of-day filters, buffer gaps
- Compact mode (one slot per free window) or granular 15-minute increments
- Weekend skip/include control
- Declined event filtering
- Cross-calendar deduplication (prefers Google metadata)
- Graceful degradation when a calendar source fails
- Human-readable or JSON output
