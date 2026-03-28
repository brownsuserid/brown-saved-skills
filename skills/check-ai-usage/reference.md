# Monitoring AI Tool Usage

Check Claude Code and Antigravity IDE usage limits.

## How to Run

```bash
~/.openclaw/skills/maintaining-systems/scripts/monitoring-usage/check_at_coding_usage.sh
```

Displays color-coded usage bars for:
- Claude Code: weekly (7-day), session (5-hour), Opus, Sonnet, and extra usage limits
- Antigravity IDE: per-model usage and prompt credits

Use `--json` flag for machine-readable output.

## Requirements

- jq, python3
- macOS Keychain with Claude Code OAuth credentials (user:profile scope)
- Antigravity IDE running (for Antigravity section; fails gracefully if unavailable)
