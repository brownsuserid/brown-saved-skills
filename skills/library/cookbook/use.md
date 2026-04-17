# Use a Skill from the Library

## Context
Pull a skill, agent, or prompt from the catalog into the local environment. If already installed locally, overwrite with the latest from the source (refresh).

## Input
The user provides a skill name or description.

## Steps

### 1. Sync the Library Repo
Pull the latest catalog before reading:
```bash
cd <LIBRARY_SKILL_DIR>
git pull
```

### 2. Find the Entry
- Read `library.yaml`
- Search across `library.skills`, `library.agents`, and `library.prompts`
- Match by name (exact) or description (fuzzy/keyword match)
- If multiple matches, show them and ask the user to pick one
- If no match, tell the user and suggest `/library search`

### 3. Resolve Dependencies
If the entry has a `requires` field:
- For each typed reference (`skill:name`, `agent:name`, `prompt:name`):
  - Look it up in `library.yaml`
  - If found, recursively run the `use` workflow for that dependency first
  - If not found, warn the user: "Dependency <ref> not found in library catalog"
- For each `mcp:name` reference:
  - Look it up in `library.mcps` by name
  - If not found, warn: "MCP dependency `<name>` not found in library catalog"
  - If found, install the MCP config (see Step 3a below)
- Process all dependencies before the requested item

### 3a. Install MCP Server Config
For each `mcp:` dependency found in `library.mcps`:

1. **Determine target config** based on the same scope as the skill install:
   - Default (project): `.mcp.json` in the current working directory
   - Global: `~/.claude/settings.json` under `mcpServers`

2. **Read the target config file** (create `{}` if missing)
   - If the file exists but contains invalid JSON, warn: "Cannot merge MCP config — `<file>` has invalid JSON. Fix it manually or delete it." Do NOT overwrite. Still install the skill.

3. **Check if already configured**: if the MCP name already exists as a key, skip it and note: "MCP `<name>` already configured"

4. **Write the MCP config** based on the MCP entry's `type`:
   - **`type: stdio`** → add: `{ "<name>": { "command": "<command>", "args": [<args>] } }`
   - **`type: http`** → add: `{ "<name>": { "type": "http", "url": "<url>" } }`
   - For `.mcp.json`: add at the top level of the JSON object
   - For `settings.json`: add under `mcpServers` (create the key if it doesn't exist)
   - Resolve any `~` in path values to the actual home directory

5. **Write the updated config file**

### 4. Determine Target Directory
- Read `default_dirs` from `library.yaml`
- If user said "global" or "globally" → use the `global` path
- If user specified a custom path → use that path
- Otherwise → use the `default` path
- Select the correct section based on type (skills/agents/prompts)

### 5. Fetch from Source

**If source is a local path** (starts with `/` or `~`):
- Resolve `~` to the home directory
- Get the parent directory of the referenced file
- For skills: copy the entire parent directory to the target:
  ```bash
  cp -R <parent_directory>/ <target_directory>/<name>/
  ```
- For agents: copy just the agent file to the target:
  ```bash
  cp <agent_file> <target_directory>/<agent_name>.md
  ```
- For prompts: copy just the prompt file to the target:
  ```bash
  cp <prompt_file> <target_directory>/<prompt_name>.md
  ```
- If the agent or prompt is nested in a subdirectory under the `agents/` or `commands/` directories, copy the subdirectory to the target as well, creating the subdir if it doesn't exist. This is useful because it keeps the agents or commands grouped together.

**If source is a GitHub URL**:
- Parse the URL to extract: `org`, `repo`, `branch`, `file_path`
  - Browser URL pattern: `https://github.com/<org>/<repo>/blob/<branch>/<path>`
  - Raw URL pattern: `https://raw.githubusercontent.com/<org>/<repo>/<branch>/<path>`
- Determine the clone URL: `https://github.com/<org>/<repo>.git`
- Determine the parent directory path within the repo (everything before the filename)
- Clone into a temporary directory:
  ```bash
  tmp_dir=$(mktemp -d)
  git clone --depth 1 --branch <branch> https://github.com/<org>/<repo>.git "$tmp_dir"
  ```
- Copy the parent directory of the file to the target:
  ```bash
  cp -R "$tmp_dir/<parent_path>/" <target_directory>/<name>/
  ```
- Clean up:
  ```bash
  rm -rf "$tmp_dir"
  ```

**If clone fails (private repo)**, try SSH:
  ```bash
  git clone --depth 1 --branch <branch> git@github.com:<org>/<repo>.git "$tmp_dir"
  ```

### 6. Verify Installation
- Confirm the target directory exists
- Confirm the main file (SKILL.md, AGENT.md, or prompt file) exists in it
- Report success with the installed path

### 7. Confirm
Tell the user:
- What was installed and where
- Any dependencies that were also installed
- If this was a refresh (overwrite), mention that
- If any MCP servers were configured:
  - Which MCP servers were added and to which config file
  - Tell the user to run `/mcp` to verify the servers are working
  - If the MCP entry has a `note` field (e.g., prerequisites), show it
  - If the MCP entry has `env` vars with `${VAR}` patterns, warn: "Set `<VAR>` before using this skill"
