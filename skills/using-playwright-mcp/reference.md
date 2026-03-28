# Using Playwright MCP Tools

**Playwright MCP tools are the only supported browser control method.** Do not use `openclaw browser` CLI commands, do not write Python scripts with `playwright.sync_api`, do not invent other browser automation approaches. If you need to control a browser, use the `mcp__playwright__browser_*` tools described here.

Legacy Python Playwright scripts exist in some skill directories as historical artifacts. They should not be used for new work or called as fallbacks.

## Browser Profile & Auth

The Playwright MCP server uses OpenClaw's persistent browser profile at `~/.openclaw/browser/openclaw/user-data/`. This means:

- **Auth sessions persist** across MCP restarts. Once you sign in to Google, LinkedIn, etc., you stay signed in.
- **No re-authentication** needed each session for sites already logged in.
- If a site does require login, ask Aaron to sign in once. The session will persist for future runs.

**mcporter config** (`~/.mcporter/mcporter.json`):
```json
"playwright": {
  "command": "npx",
  "args": [
    "@playwright/mcp@latest",
    "--user-data-dir",
    "/Users/aaroneden/.openclaw/browser/openclaw/user-data"
  ]
}
```

## Available Tools

| Tool | Purpose | Key Params |
|------|---------|------------|
| `browser_navigate` | Go to a URL | `url` |
| `browser_snapshot` | Read page as accessibility tree (includes `ref=` for each element) | -- |
| `browser_click` | Click an element | `ref`, `element` (description) |
| `browser_type` | Type into an input | `ref`, `text`, `submit` (optional Enter) |
| `browser_fill_form` | Fill multiple fields at once | `fields[]` with `ref`, `value`, `type` |
| `browser_press_key` | Press a keyboard key | `key` (e.g. `Enter`, `ArrowDown`) |
| `browser_hover` | Hover over an element | `ref` |
| `browser_select_option` | Pick from a dropdown | `ref`, `values[]` |
| `browser_evaluate` | Run arbitrary JS on the page | `function` |
| `browser_file_upload` | Upload file(s) via file chooser | `paths[]` (absolute) |
| `browser_take_screenshot` | Capture visual screenshot | `type` (png/jpeg), `fullPage` |
| `browser_tabs` | List, create, close, select tabs | `action` |
| `browser_wait_for` | Wait for text to appear/disappear or time | `text`, `textGone`, `time` |
| `browser_console_messages` | Read console output | `level` |
| `browser_network_requests` | View network activity | `includeStatic` |
| `browser_navigate_back` | Go back one page | -- |
| `browser_close` | Close the browser | -- |
| `browser_drag` | Drag and drop between elements | `startRef`, `endRef` |
| `browser_install` | Install browser if missing | -- |

## Core Patterns

### Navigate and Read

```
1. browser_navigate → URL
2. browser_snapshot → read the accessibility tree
3. Find the element you need by its text/role in the tree
4. Use its ref= value for the next action
```

Always snapshot after navigating. The snapshot is your eyes.

### Click

```
1. browser_snapshot → find element ref
2. browser_click → ref="<value>", element="<description>"
```

The `element` param is a human-readable description for audit/permission purposes.

### Type into a Field

```
1. browser_snapshot → find input ref
2. browser_click → ref (focus the field)
3. browser_type → ref, text="your content"
```

For form submission, add `submit: true` to press Enter after typing.

### File Upload

```
1. browser_click → the upload button/area (triggers file chooser)
2. browser_file_upload → paths=["/absolute/path/to/file.pdf"]
```

Paths must be absolute.

### Scroll / Load More Content

```
browser_evaluate → function="() => window.scrollBy(0, 800)"
browser_snapshot → read newly loaded content
```

Repeat as needed for infinite-scroll pages.

### Long-Running Operations (Polling)

When waiting for async operations (audio generation, report processing):

```
1. Trigger the action (click Generate, etc.)
2. browser_wait_for → text="Ready" or time=30
3. browser_snapshot → check status
4. If not done, repeat steps 2-3 (max N iterations)
```

### Authentication (Login Walls)

When a page requires login:

```
1. browser_navigate → target URL
2. browser_snapshot → check for login/sign-in elements
3. If sign-in page detected:
   - Tell the user: "The browser needs authentication for [service]. Please sign in."
   - browser_snapshot → wait for user to complete login
   - Verify login succeeded before continuing
```

Never type passwords. The user handles auth interactively.

### Tab Management

```
browser_tabs → action="list"     # see all open tabs
browser_tabs → action="new"      # open a blank tab
browser_tabs → action="select", index=0  # switch to first tab
browser_tabs → action="close"    # close current tab
```

## Anti-Patterns

- **Don't guess refs.** Always `browser_snapshot` first to get current ref values. Refs change after every navigation or page mutation.
- **Don't use `browser_take_screenshot` to read content.** Use `browser_snapshot` instead. Screenshots are for visual debugging only.
- **Always re-snapshot after actions.** Clicking a button, navigating, or typing can change the page. Snapshot again to see the new state.
- **Don't hardcode CSS selectors.** MCP uses the accessibility tree. Find elements by their visible text, role, or ARIA label.
- **Don't batch-click without snapshots.** Each action can change the DOM. Snapshot between actions.

## Differences from Python Playwright Scripts

| Python Scripts | MCP Tools |
|---------------|-----------|
| CSS selectors with fallback lists | Accessibility tree with ref= attributes |
| `--headless` / `--no-headless` flag | Always visible (headed) browser |
| `--state-file` for session persistence | Persistent browser profile at `~/.openclaw/browser/openclaw/user-data/` |
| `--account` flag for multi-account | Navigate to account picker manually |
| `storage_state` + profile dirs | Auth persists in browser profile, no state files needed |
| `page.wait_for_selector()` | `browser_wait_for` or poll with snapshot |
| `page.evaluate()` | `browser_evaluate` |
| Script returns JSON to stdout | Read results directly from snapshot |
