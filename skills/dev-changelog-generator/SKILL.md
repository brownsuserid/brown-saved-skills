---
name: dev-changelog-generator
description: Generates changelogs and release notes from git commit history. Use this skill whenever a developer is creating a PR, publishing a release, tagging a version, preparing release notes, or asking to summarize what changed between branches, tags, or time periods. Also triggers for "what's new", "write a changelog", "generate release notes", or any workflow that involves communicating code changes to the team.
---

# Changelog Generator

Transforms git commit history into well-structured, developer-friendly changelogs and release notes.

## Process

### 1. Determine Scope

Establish which commits to include. Ask the user if unclear.

```bash
# Between tags
git log v2.4.0..v2.5.0 --oneline

# Since last tag
git log $(git describe --tags --abbrev=0)..HEAD --oneline

# Time-based
git log --since="7 days ago" --oneline
```

Check for existing changelog conventions (`CHANGELOG.md`, `CHANGELOG_STYLE.md`, `.changelog.yml`) and follow them if present.

### 2. Analyze and Categorize Commits

Retrieve full commit details and group by type:

```bash
git log <range> --format="%H|%s|%b|%an|%ae|%ad" --date=short
```

**Categories** (based on conventional commit prefixes):
- **Features** — `feat:` commits, new functionality
- **Improvements** — `chore:`, `refactor:`, `perf:` with user-visible impact
- **Bug Fixes** — `fix:` commits
- **Breaking Changes** — `BREAKING CHANGE:` or `!` in type
- **Security** — vulnerability fixes, dependency security patches
- **Documentation** — `docs:` (user-facing only)

**Filter out noise** — exclude commits that don't affect the codebase's behavior: test-only changes, CI/CD config, formatting, build system tweaks, internal tooling, and dependency bumps (unless security-related). These clutter changelogs and make the important changes harder to find.

### 3. Write Changelog Entries

The audience is developers working in the codebase. Write entries that are clear, specific, and technically accurate — but focus on *what changed and why it matters* rather than implementation minutiae.

**Good entries explain impact:**
```
- feat(auth): Add OAuth2 token refresh with sliding expiration — sessions no longer expire during active use
- fix(websocket): Resolve race condition in message handler that caused dropped connections under load
- perf(db): Add composite index to queries table — dashboard loads ~2x faster for large datasets
```

**Weak entries just restate the commit:**
```
- Updated auth code
- Fixed bug
- Performance improvement
```

Each entry should give a developer enough context to understand the change without reading the diff. Include the scope prefix when the project uses conventional commits.

### 4. Format the Changelog

Use the format from `templates/changelog-template.md` as a starting point. Key structural decisions:

- **Version header**: Include version number (or date range) and date
- **Category groupings**: Group by type (features, fixes, etc.)
- **PR/issue links**: Include `(#123)` references where available
- **Breaking changes**: Call out prominently with migration guidance
- **Comparison link**: Add a GitHub compare URL at the bottom

For detailed formatting options and alternative styles, see `references/changelog-best-practices.md`.

### 5. Review and Output

Present the changelog to the user for review before saving. Offer to:
- Adjust entries or categories
- Prepend to existing `CHANGELOG.md`
- Create a GitHub release (`gh release create`)
- Copy to clipboard

## Quality Checklist

Before finalizing:
- [ ] All user-facing commits included
- [ ] Internal/noise commits excluded
- [ ] Entries are specific (not vague "improvements")
- [ ] Breaking changes highlighted with migration steps
- [ ] Security updates mentioned
- [ ] PR/commit links included where available
- [ ] Consistent formatting throughout
- [ ] Matches existing project conventions if any

## Common Mistakes

- **Restating commit messages verbatim** — commits are written for the author in the moment; changelog entries should be readable by any team member weeks later
- **Including every commit** — filter noise aggressively; a changelog with 50 entries is harder to scan than one with 15 meaningful ones
- **Vague descriptions** — "various bug fixes" tells the reader nothing; be specific about what was fixed
- **Forgetting breaking changes** — these need migration guidance, not just a mention
- **Missing scope context** — when the project has multiple modules/services, include which area was affected
