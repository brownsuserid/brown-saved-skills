# Semantic Versioning Guide

Comprehensive guide for versioning software using Semantic Versioning (SemVer) specification.

## Overview

Semantic Versioning provides a simple set of rules and requirements that dictate how version numbers are assigned and incremented. This guide covers how to apply SemVer to your projects, when to bump versions, and how to integrate with git workflows.

---

## SemVer Format

### Basic Format

```
MAJOR.MINOR.PATCH
```

**Examples:**
- `1.0.0` - Initial stable release
- `1.2.3` - MAJOR version 1, MINOR version 2, PATCH version 3
- `2.0.0` - MAJOR version bump (breaking change)

### Pre-release Versions

```
MAJOR.MINOR.PATCH-PRERELEASE
```

**Examples:**
- `1.0.0-alpha.1` - Alpha release
- `1.0.0-beta.2` - Beta release
- `1.0.0-rc.1` - Release candidate
- `2.0.0-dev` - Development version

### Build Metadata

```
MAJOR.MINOR.PATCH+BUILD
```

**Examples:**
- `1.0.0+20250106` - Build with date
- `1.0.0+build.123` - Build number
- `1.0.0-beta.1+exp.sha.5114f85` - Pre-release with build metadata

---

## Version Bumping Rules

### When to Increment MAJOR (X.0.0)

Increment MAJOR version when you make **incompatible API changes** or **breaking changes**.

**Breaking changes include:**
- Removing public APIs, functions, or classes
- Changing function signatures (parameters, return types)
- Changing behavior in backward-incompatible ways
- Removing or renaming configuration options
- Changing data formats that break existing clients
- Removing support for older versions

**Examples:**

```python
# BEFORE: Version 1.5.2
def get_user(user_id: int) -> dict:
    return {"id": user_id, "name": "..."}

# AFTER: Version 2.0.0 (breaking change)
def get_user(user_id: int) -> User:  # Changed return type
    return User(id=user_id, name="...")
```

```python
# BEFORE: Version 1.5.2
class Config:
    database_url: str

# AFTER: Version 2.0.0 (breaking change)
class Config:
    db_connection: DatabaseConnection  # Changed field name and type
```

**Commit message format:**
```bash
feat!: migrate to new authentication system

BREAKING CHANGE: Removed legacy token-based auth in favor of OAuth2.
All clients must update to use OAuth2 authentication flow.

Migration guide: docs/migration-v2.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### When to Increment MINOR (x.Y.0)

Increment MINOR version when you add **new functionality** in a **backward-compatible manner**.

**Minor changes include:**
- Adding new public APIs, functions, or classes
- Adding optional parameters to existing functions
- Adding new features that don't break existing code
- Deprecating functionality (but not removing it yet)
- Performance improvements without API changes

**Examples:**

```python
# Version 1.5.2 → 1.6.0 (new feature)
def get_user(user_id: int, include_metadata: bool = False) -> dict:
    """Added optional parameter - backward compatible."""
    data = {"id": user_id, "name": "..."}
    if include_metadata:
        data["metadata"] = load_metadata(user_id)
    return data
```

```python
# Version 1.5.2 → 1.6.0 (new class)
class UserCache:  # New feature added
    """New caching functionality for users."""
    def get(self, user_id: int) -> dict:
        ...
```

**Commit message format:**
```bash
feat: add user caching functionality

Added UserCache class for caching user data with configurable TTL.
This is fully backward compatible and optional.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### When to Increment PATCH (x.y.Z)

Increment PATCH version when you make **backward-compatible bug fixes**.

**Patch changes include:**
- Fixing bugs without changing API
- Security patches
- Performance improvements without API changes
- Documentation updates (if packaged with code)
- Internal refactoring that doesn't affect public API

**Examples:**

```python
# Version 1.5.2 → 1.5.3 (bug fix)
def calculate_discount(price: float, rate: float) -> float:
    # BEFORE: Incorrect calculation
    # return price * rate

    # AFTER: Fixed calculation
    return price * (1 - rate)
```

**Commit message format:**
```bash
fix: correct discount calculation formula

Fixed bug where discount was multiplied instead of subtracted.
Now correctly calculates: price * (1 - rate)

Fixes #123

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Decision Tree

Use this decision tree to determine which version number to increment:

```
Did you make breaking changes?
├─ YES → Increment MAJOR (2.0.0)
└─ NO
   ├─ Did you add new features (backward-compatible)?
   │  ├─ YES → Increment MINOR (1.6.0)
   │  └─ NO
   │     └─ Did you fix bugs or make patches?
   │        ├─ YES → Increment PATCH (1.5.3)
   │        └─ NO → No version change needed
```

**Examples:**

| Change | Current | New Version | Reason |
|--------|---------|-------------|---------|
| Remove deprecated function | 1.5.2 | 2.0.0 | Breaking change |
| Add new optional parameter | 1.5.2 | 1.6.0 | New feature |
| Fix security vulnerability | 1.5.2 | 1.5.3 | Bug fix |
| Add new class | 1.5.2 | 1.6.0 | New feature |
| Change function return type | 1.5.2 | 2.0.0 | Breaking change |
| Update documentation | 1.5.2 | 1.5.3 | Patch (if versioned with code) |
| Refactor internals | 1.5.2 | 1.5.3 | Patch (no API change) |

---

## Pre-release Versions

### Alpha Releases

Early testing versions, API may change frequently.

```
1.0.0-alpha.1
1.0.0-alpha.2
```

**When to use:**
- Early development
- API not stable
- Breaking changes expected
- Internal testing only

**Example workflow:**
```bash
# Initial alpha
git tag v1.0.0-alpha.1

# Bug fixes in alpha
git tag v1.0.0-alpha.2

# More changes
git tag v1.0.0-alpha.3
```

### Beta Releases

Feature-complete, API mostly stable, bug fixes expected.

```
1.0.0-beta.1
1.0.0-beta.2
```

**When to use:**
- Features complete
- API frozen or nearly frozen
- External testing needed
- Collecting feedback

**Example workflow:**
```bash
# First beta after alpha phase
git tag v1.0.0-beta.1

# Bug fixes
git tag v1.0.0-beta.2
```

### Release Candidates

Final testing before stable release.

```
1.0.0-rc.1
1.0.0-rc.2
```

**When to use:**
- No known critical bugs
- Ready for production testing
- Final validation needed
- Last step before stable

**Example workflow:**
```bash
# First release candidate
git tag v1.0.0-rc.1

# Critical bug found, fixed
git tag v1.0.0-rc.2

# No more issues, release stable
git tag v1.0.0
```

### Pre-release Precedence

Versions are ordered by precedence:

```
1.0.0-alpha.1 < 1.0.0-alpha.2 < 1.0.0-beta.1 < 1.0.0-beta.2 < 1.0.0-rc.1 < 1.0.0
```

---

## Changelog Management

### Keep a Changelog Format

Use [Keep a Changelog](https://keepachangelog.com/) format for CHANGELOG.md.

**Structure:**
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New feature description

### Changed
- Changed behavior description

### Deprecated
- Deprecated feature (will be removed in next MAJOR)

### Removed
- Removed feature (BREAKING CHANGE)

### Fixed
- Bug fix description

### Security
- Security fix description

## [1.5.3] - 2025-01-06

### Fixed
- Fixed discount calculation formula (#123)

## [1.5.2] - 2025-01-05

### Added
- Added user caching functionality
- Added optional metadata parameter to get_user

### Fixed
- Fixed race condition in database connection pool

## [1.5.1] - 2025-01-04

### Security
- Patched SQL injection vulnerability in user search

[Unreleased]: https://github.com/user/repo/compare/v1.5.3...HEAD
[1.5.3]: https://github.com/user/repo/compare/v1.5.2...v1.5.3
[1.5.2]: https://github.com/user/repo/compare/v1.5.1...v1.5.2
[1.5.1]: https://github.com/user/repo/releases/tag/v1.5.1
```

### Changelog Sections

**Added** - New features
```markdown
### Added
- New `UserCache` class for caching user data
- Support for OAuth2 authentication
```

**Changed** - Changes in existing functionality
```markdown
### Changed
- Improved performance of database queries by 50%
- Updated error messages to be more descriptive
```

**Deprecated** - Soon-to-be removed features
```markdown
### Deprecated
- `get_user_legacy()` function - use `get_user()` instead (will be removed in v2.0.0)
```

**Removed** - Removed features (BREAKING CHANGE)
```markdown
### Removed
- **BREAKING:** Removed legacy token-based authentication
- **BREAKING:** Removed deprecated `process_sync()` method
```

**Fixed** - Bug fixes
```markdown
### Fixed
- Fixed memory leak in connection pool
- Corrected calculation in discount formula (#123)
```

**Security** - Security fixes
```markdown
### Security
- Patched SQL injection vulnerability (CVE-2025-1234)
- Fixed XSS vulnerability in user profile page
```

---

## Git Integration

### Tagging Releases

**Create annotated tags for releases:**

```bash
# Stable release
git tag -a v1.5.3 -m "Release version 1.5.3"

# Pre-release
git tag -a v1.0.0-beta.1 -m "Beta release 1.0.0-beta.1"

# Push tags
git push origin v1.5.3
git push origin --tags  # Push all tags
```

### Release Workflow

**Complete release workflow:**

```bash
# 1. Update version in code (pyproject.toml, __version__, etc.)
# 2. Update CHANGELOG.md
# 3. Commit changes
git add .
git commit -m "chore: prepare release v1.5.3

Updated version to 1.5.3 and finalized changelog.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 4. Create tag
git tag -a v1.5.3 -m "Release version 1.5.3"

# 5. Push
git push origin main
git push origin v1.5.3
```

### Version Branches

**For maintaining multiple versions:**

```bash
# Main development (future 2.0.0)
main

# Maintenance branch for 1.x
git checkout -b maintenance/1.x v1.5.3

# Apply patch to 1.x
git checkout maintenance/1.x
# Fix bug
git commit -m "fix: security patch for 1.x"
git tag -a v1.5.4 -m "Release version 1.5.4"
git push origin maintenance/1.x
git push origin v1.5.4
```

---

## Python Integration

### pyproject.toml

**Version specification:**

```toml
[project]
name = "myproject"
version = "1.5.3"
description = "My project description"
requires-python = ">=3.11"

[tool.setuptools.dynamic]
# Or use dynamic versioning
version = {attr = "myproject.__version__"}
```

### __init__.py

**Version constant:**

```python
"""MyProject package."""

__version__ = "1.5.3"
```

### Dependency Versioning

**Specify dependencies with SemVer:**

```toml
[project]
dependencies = [
    "fastapi>=0.100.0,<1.0.0",  # Allow MINOR/PATCH updates
    "pydantic>=2.0.0,<3.0.0",   # Pin to MAJOR version 2
    "pytest>=7.4.0",            # Minimum version (dev)
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0,<8.0.0",     # Pin to MAJOR version 7
    "ruff>=0.1.0,<0.2.0",       # Pin to MINOR version 0.1
]
```

**Version constraints:**
- `>=1.5.0,<2.0.0` - Compatible with MINOR/PATCH updates (recommended)
- `~=1.5.0` - Compatible with PATCH updates only (`>=1.5.0,<1.6.0`)
- `==1.5.3` - Exact version (use sparingly, blocks updates)
- `>=1.5.0` - Minimum version (allows all future versions)

---

## Special Cases

### Version 0.x.x (Initial Development)

**Before 1.0.0, anything may change:**

```
0.1.0 - Initial development
0.2.0 - Added features (may break things)
0.3.0 - More changes (breaking allowed)
1.0.0 - First stable release
```

**Rules for 0.x.x:**
- MINOR version bump can include breaking changes
- PATCH version for backward-compatible fixes
- No guarantees about stability
- Use for initial development only

### Version 1.0.0 (First Stable Release)

**Criteria for 1.0.0:**
- API is stable and production-ready
- Documentation complete
- Test coverage adequate
- Breaking changes will increment MAJOR going forward

### Migration Guides

**For MAJOR version bumps, provide migration guide:**

**`docs/migration-v2.md`:**
```markdown
# Migration Guide: v1.x to v2.0

## Overview

Version 2.0 introduces breaking changes. This guide helps migrate from 1.x.

## Breaking Changes

### Authentication System

**Before (v1.x):**
```python
from myproject.auth import TokenAuth

auth = TokenAuth(token="...")
client = Client(auth=auth)
```

**After (v2.0):**
```python
from myproject.auth import OAuth2Auth

auth = OAuth2Auth(client_id="...", client_secret="...")
client = Client(auth=auth)
```

### Configuration

**Before (v1.x):**
```python
config = Config(database_url="...")
```

**After (v2.0):**
```python
config = Config(db_connection=DatabaseConnection(...))
```

## Deprecated Features

The following were deprecated in v1.5.0 and removed in v2.0.0:
- `get_user_legacy()` → Use `get_user()`
- `process_sync()` → Use async `process()`

## Step-by-Step Migration

1. Update dependencies: `uv add myproject>=2.0.0,<3.0.0`
2. Replace authentication code (see above)
3. Update configuration (see above)
4. Run tests to identify issues
5. Review changelog for additional changes
```

---

## Quick Reference

### Version Format
```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
```

### Incrementing
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward-compatible)
- **PATCH**: Bug fixes (backward-compatible)

### Pre-release Order
```
alpha → beta → rc → stable
```

### Git Tags
```bash
git tag -a v1.5.3 -m "Release 1.5.3"
git push origin v1.5.3
```

### Changelog Sections
```
Added, Changed, Deprecated, Removed, Fixed, Security
```

### Python Dependencies
```toml
"package>=1.5.0,<2.0.0"  # Allow MINOR/PATCH
"package~=1.5.0"         # Allow PATCH only
```

---

## Best Practices

**Do:**
- ✓ Use SemVer consistently across all projects
- ✓ Update CHANGELOG.md with every release
- ✓ Create annotated git tags for releases
- ✓ Provide migration guides for MAJOR bumps
- ✓ Deprecate before removing (one MAJOR version notice)
- ✓ Use pre-release versions for testing
- ✓ Document breaking changes clearly
- ✓ Pin MAJOR versions in dependencies

**Don't:**
- ✗ Skip versions (1.5.2 → 1.5.4)
- ✗ Re-use version numbers
- ✗ Make breaking changes in MINOR/PATCH
- ✗ Release without updating changelog
- ✗ Use custom version schemes
- ✗ Remove features without deprecation notice
- ✗ Tag releases without testing
- ✗ Use exact version pins unnecessarily

---

## Common Scenarios

### Scenario 1: Security Patch

**Situation:** Critical security vulnerability found in stable release.

**Action:**
```bash
# Fix vulnerability
git checkout main
git commit -m "fix: patch SQL injection vulnerability

Security fix for user search functionality.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Increment PATCH version
# 1.5.2 → 1.5.3
git tag -a v1.5.3 -m "Security release 1.5.3"
git push origin v1.5.3
```

### Scenario 2: New Feature

**Situation:** Add optional caching functionality.

**Action:**
```bash
# Implement feature
git commit -m "feat: add user caching functionality

Added UserCache class with configurable TTL. Fully backward compatible.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Increment MINOR version
# 1.5.3 → 1.6.0
git tag -a v1.6.0 -m "Release 1.6.0"
git push origin v1.6.0
```

### Scenario 3: Breaking Change

**Situation:** Migrate to new authentication system.

**Action:**
```bash
# Implement breaking change
git commit -m "feat!: migrate to OAuth2 authentication

BREAKING CHANGE: Removed legacy token-based auth.
See docs/migration-v2.md for upgrade guide.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Increment MAJOR version
# 1.6.0 → 2.0.0
git tag -a v2.0.0 -m "Release 2.0.0"
git push origin v2.0.0
```

---

## Further Reading

- [Semantic Versioning 2.0.0 Specification](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [PEP 440 - Version Identification](https://peps.python.org/pep-0440/)
