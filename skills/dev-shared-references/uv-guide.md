# UV Dependency Management Guide

uv replaces virtualenv, pip-tools, pyenv, pipx, poetry, and even simple script runners in one Rust binary. You'll create a project with `uv init`, declare packages with `uv add`, freeze them with `uv lock`, materialize the environment with `uv sync`, and execute code or CLIs with `uv run` — all 10-100× faster than the classic toolchain.


## 1. Create or Import a Project

```bash
# New package or app
$ uv init myapp            # writes pyproject.toml
$ cd myapp
```

uv init scaffolds `pyproject.toml`; the `.venv` and `uv.lock` are created lazily at first sync.

Already have a repo? Just drop in a `pyproject.toml` and let the next steps handle the rest.

## 2. Add & Remove Dependencies

```bash
$ uv add fastapi psycopg[binary]        # add runtime deps
$ uv add -D black ruff pytest           # add dev-only deps
$ uv remove psycopg                     # yank a dep
```

**Flags:** `-D/--dev`, `--group analytics`, `--extras ui` mirror Poetry's grouping semantics.

Git, path and URL requirements are equally valid:
```bash
$ uv add git+https://github.com/encode/httpx --tag 0.27.0
```

## 3. Locking for Reproducibility

```bash
$ uv lock                  # solves & writes uv.lock
$ uv lock --upgrade        # full refresh
$ uv lock -P fastapi       # upgrade just FastAPI
```

Locking captures exact versions & hashes across all platforms for deterministic CI/CD.

## 4. Syncing the Environment

```bash
$ uv sync                  # create .venv & install deps
$ uv sync --inexact        # keep stray packages
$ uv sync --frozen         # error if lock & deps diverge
```

`uv sync` guarantees the venv mirrors `uv.lock`; it also removes junk packages unless you opt out.

## 5. Running Code & CLIs

### 5.1 Run any command in the project env

```bash
$ uv run python manage.py migrate
$ uv run pytest -q
```

`uv run` automatically spawns the venv (or re-uses the active one) before executing the command.

### 5.2 Ad-hoc scripts

```bash
$ uv run script.py                       # local file
$ uv run https://bit.ly/strptime_demo.py # remote URL
```

## 6. Virtual Environments & Python Versions

```bash
# Create a fresh venv anywhere
$ uv venv .venv

# See available interpreters & install one
$ uv python list
$ uv python install 3.12

# Pin a project-local Python
$ echo "3.11" > .python-version
$ uv sync          # venv now uses 3.11
```

uv downloads missing CPython builds on demand and keeps them under `~/Library/Caches/uv/python` on macOS.

## 7. Tool-centric Workflow (pipx replacement)

```bash
# Install Black globally, isolated from projects
$ uv tool install black

# Run it anywhere
$ uv tool run black .

# Upgrade or list
$ uv tool upgrade --all
$ uv tool list
```

Tools are cached once and re-used across projects, saving both time and disk space.

## 8. Inspect, Export, Troubleshoot

| Need | Command |
|------|---------|
| Visualize deps | `uv tree` |
| Produce requirements.txt | `uv export --format requirements-txt > req.txt` |
| Show cache dir | `uv cache dir` |
| Clean cache | `uv cache prune` |
| Update uv itself | `uv self update` |

All commands are instant; the resolver never touches your venv for read-only queries.

## 9. Day-zero Startup Script

```bash
# clone repo & prep
git clone https://github.com/your-org/awesome.git
cd awesome

# first-time setup
uv sync                # resolves, locks, installs
uv run pytest          # green tests in the fresh venv
uv run fastapi dev     # start the app
```

From zero to running server in seconds, no manual `python -m venv`, no `pip install -r` loops.

## 10. Migration Tip

If muscle memory still types `pip`, remember you can optionally use `uv pip …` as a bridge—yet the native commands above give you the full deterministic, project-aware power of uv.

## Best Practices

- **Always use `uv sync`** after pulling changes to keep your environment in sync
- **Commit `uv.lock`** to version control for reproducible builds
- **Use `uv add -D`** for development dependencies (testing, linting, etc.)
- **Pin Python version** with `.python-version` file for consistency across team
- **Use `uv run`** instead of activating venv manually for better reproducibility
- **Leverage `uv tool`** for global tools like black, ruff, pytest to avoid polluting project environments
