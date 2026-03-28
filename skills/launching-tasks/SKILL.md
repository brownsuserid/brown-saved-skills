---
name: launching-tasks
description: Install and configure Warp terminal launch configurations, the pablo:// URL scheme, the localhost redirect server, and Raycast quicklinks so tasks can be launched from clickable links in Airtable, Warp, Raycast, or anywhere. Use this skill whenever setting up a new machine, reinstalling task launchers, troubleshooting the pablo:// URL scheme, debugging Warp launch configs, or when someone asks how to open a task directly from a link. Also triggers for "how do I launch a task", "set up task links", "warp launch config", "pablo url", "clickable task links", or "raycast task launcher".
---

# Launching Tasks from Links

Three Warp launch configs, a local redirect server, and Raycast quicklinks for one-click task launching.

## Entry Points

| Link | What it does | Where it works |
|------|-------------|----------------|
| `warp://launch/My%20Top%20Tasks` | Fetches top scored tasks across all bases | Raycast, browser, CLI |
| `warp://launch/Today's%20Tasks` | Fetches For Today tasks with all statuses | Raycast, browser, CLI |
| `http://localhost:19280/task/Task+Title` | Redirects to pablo://, launches Execute Task | Airtable, Warp, browser |
| `pablo://task/Task+Title` | Launches Execute Task directly | CLI, Finder |

## Raycast Quicklinks

Create two Raycast quicklinks (Raycast > Create Quicklink):

| Name | Link |
|------|------|
| My Top Tasks | `warp://launch/My%20Top%20Tasks` |
| Today's Tasks | `warp://launch/Today's%20Tasks` |

Then just open Raycast and type "top tasks" or "today" to launch.

## How the Task List Displays

Both "My Top Tasks" and "Today's Tasks" launch Claude Code, which presents a markdown table:

| # | Task | Launch | Status | Base | Score |
|---|------|--------|--------|------|-------|
| 1 | Create AI Finance Teammate | [Go](http://localhost:19280/task/Create+AI+Finance+Teammate) | In Progress | BB | 85 |

The "Go" link in the Launch column is clickable in Warp. Clicking it opens a new Warp window with Claude Code searching for and executing that task.

## Why localhost:19280?

Airtable and most web apps strip custom URL schemes like `pablo://` for security. The redirect server accepts standard `http://` links and 302s to `pablo://`, which macOS routes to the URL handler app. This makes task links clickable everywhere.

## Installation

```bash
~/.openclaw/skills/launching-tasks/scripts/install.sh
```

This will:
1. Copy `my-top-tasks.yaml` and `todays-tasks.yaml` to `~/.warp/launch_configurations/`
2. Install `work-task.sh` and `pablo-redirect.py` to `~/scripts/`
3. Build `Pablo URL Handler.app` in `~/Applications/` and register the `pablo://` URL scheme
4. Install a launchd agent (`com.pablo.redirect`) to keep the redirect server running on port 19280
5. Clean up old `openclaw-tasks.yaml` config

Raycast quicklinks must be created manually (see above).

## How It Works

### Task List Profiles (My Top Tasks / Today's Tasks)

1. `warp://launch/` opens a new Warp window
2. Runs `cc` (Claude Code) with a prompt to fetch tasks and present the table
3. Task table includes clickable `[Go]` links using `http://localhost:19280/task/...`

### Task Execution (pablo:// or localhost redirect)

1. If using localhost URL: redirect server 302s to `pablo://task/...`
2. macOS routes `pablo://` URLs to `~/Applications/Pablo URL Handler.app`
3. Applet calls `~/scripts/work-task.sh` with the URL
4. Script URL-decodes the title, writes a temp launch config to `~/.warp/launch_configurations/_work-task-temp.yaml`
5. Opens `warp://launch/Execute%20Task`, which starts Claude Code with a prompt to find and execute that task via the 7-phase workflow

### Warp Launch Config Format

```yaml
layout:
  cwd: /absolute/path
  commands:
    - exec: >-
        cc "your prompt here"
```

The `name` field is what `warp://launch/` uses (URL-encoded), not the filename.

## Files

| Source (in skill) | Installed to | Purpose |
|---|---|---|
| `configs/my-top-tasks.yaml` | `~/.warp/launch_configurations/` | "My Top Tasks" launch config |
| `configs/todays-tasks.yaml` | `~/.warp/launch_configurations/` | "Today's Tasks" launch config |
| `configs/com.pablo.redirect.plist` | `~/Library/LaunchAgents/` | Keeps redirect server running |
| `scripts/work-task.sh` | `~/scripts/` | Generates temp launch config for a specific task |
| `scripts/pablo-redirect.py` | `~/scripts/` | HTTP server on port 19280, 302s to pablo:// |
| (built by install.sh) | `~/Applications/Pablo URL Handler.app` | Registers `pablo://` URL scheme |

## Troubleshooting

- **pablo:// opens wrong app**: `lsregister -dump | grep "pablo:"`
- **Redirect server not running**: `launchctl print gui/$(id -u)/com.pablo.redirect` or check `/tmp/pablo-redirect.log`
- **Port 19280 in use**: `lsof -i :19280`
- **Warp opens but no command runs**: Verify `commands` is nested inside `layout` in the YAML
- **YAML parse error**: Use `>-` block scalar for `exec` values containing quotes
- **URL handler not registered**: Open `Pablo URL Handler.app` manually, then: `lsregister -R ~/Applications/Pablo\ URL\ Handler.app`
- **Links not clickable in Warp**: Warp doesn't support OSC 8 hyperlinks. Use `http://localhost:19280/` URLs (auto-linked) or markdown `[Go](url)` links. Never use bare `pablo://` URLs in Warp output.
- **Links not clickable in Airtable**: Airtable strips custom URL schemes. Use `http://localhost:19280/` URLs with markdown link syntax in rich text fields.

## Known Limitations

- `warp://launch/` always opens a **new window** (Warp limitation, [issue #2490](https://github.com/warpdotdev/Warp/issues/2490)). To open as a tab: `Cmd+Ctrl+L` to open palette, select config, press `Cmd+Enter`.
- The `pablo://` scheme requires macOS (AppleScript applet).
- `cc` (Claude Code) must be in PATH.
- The localhost redirect only works on the local machine.
- Warp does not support OSC 8 terminal hyperlinks ([issue #4194](https://github.com/warpdotdev/Warp/issues/4194)).
