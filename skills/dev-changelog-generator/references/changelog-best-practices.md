# Changelog Best Practices

Detailed reference for writing high-quality changelog entries. The SKILL.md covers the workflow; this file goes deeper on translation patterns and style choices.

---

## Translation Patterns

When converting commits to changelog entries, the goal is to add context that makes the change understandable without reading the diff.

### API / Backend Changes

**Commit:** `feat: add pagination to GET /api/v2/items endpoint`
**Entry:** `feat(api): Add pagination to items endpoint — large result sets no longer timeout (#234)`

**Commit:** `fix: resolve N+1 query in relationships endpoint`
**Entry:** `fix(api): Eliminate N+1 query in relationships endpoint — reduces response time from ~2s to ~50ms for linked records`

### Performance Changes

**Commit:** `perf: implement Redis caching layer for user sessions`
**Entry:** `perf(sessions): Add Redis caching for session lookups — page loads ~3x faster for authenticated users`

**Commit:** `chore: upgrade from PostgreSQL 14 to 16`
**Entry:** `chore(deps): Upgrade PostgreSQL 14 to 16 — enables parallel query execution and improved JSON performance`

### Bug Fixes

**Commit:** `fix: prevent race condition in websocket message handler`
**Entry:** `fix(websocket): Prevent race condition in message handler — resolves intermittent connection drops under concurrent load`

**Commit:** `fix: correct timezone offset calculation in date picker`
**Entry:** `fix(dates): Correct timezone offset calculation — scheduled events now display in the user's local timezone`

---

## Writing Guidelines

**Be specific about impact.** "Fixed a bug" is useless. "Fixed duplicate webhook deliveries when retry logic triggered during partial failures" tells the reader exactly what was wrong and whether it affected them.

**Include scope when the project has multiple areas.** `fix(auth):` vs `fix(billing):` helps developers quickly find changes relevant to their work.

**Quantify when possible.** "~2x faster" or "reduces memory usage by 40%" is more useful than "improved performance."

**Explain breaking changes thoroughly.** Developers need to know: what changed, why, what breaks, and how to migrate. A one-liner isn't enough.

---

## Changelog Styles

Choose based on project conventions and audience.

### Standard (most projects)
```markdown
# v2.5.0 - 2024-03-15

## Features
- feat(workspaces): Add team workspaces with role-based access (#234)
- feat(shortcuts): Add keyboard shortcuts — press ? to view all (#245)

## Fixes
- fix(upload): Handle files >10MB correctly (#267)
- fix(tz): Use IANA timezone database for all date calculations (#278)

## Breaking Changes
- **API auth required**: All endpoints now require Bearer token auth (see migration guide in #290)

**Full Changelog**: https://github.com/org/repo/compare/v2.4.0...v2.5.0
```

### Keep a Changelog (keepachangelog.com)
```markdown
## [2.5.0] - 2024-03-15

### Added
- Team workspaces with role-based access

### Changed
- API endpoints now require authentication

### Fixed
- File upload handling for files >10MB
- Timezone calculations using IANA database

[2.5.0]: https://github.com/org/repo/compare/v2.4.0...v2.5.0
```

### Minimal (weekly updates, patch releases)
```markdown
# v2.5.1 - 2024-03-18

- fix(upload): Retry failed multipart uploads (#271)
- fix(ui): Correct sidebar width on narrow viewports (#272)
- chore(deps): Update lodash to 4.17.21 (security) (#273)
```

---

## Breaking Changes Template

For significant breaking changes, provide enough detail for developers to migrate:

```markdown
### API Authentication Required

**What changed**: All API endpoints now require a Bearer token in the Authorization header.

**Why**: Unauthenticated access created security and rate-limiting issues.

**What breaks**: API calls without auth will receive 401 responses.

**Migration**:
1. Generate an API key in Settings > API
2. Add `Authorization: Bearer <key>` to all requests
3. Deadline: April 1, 2024 (unauthenticated access disabled)

See full migration guide: docs.example.com/api-migration (#290)
```

---

## Filtering Guidance

**Always include**: Features, bug fixes, breaking changes, security patches, significant performance improvements, deprecation notices.

**Always exclude**: Test-only changes, CI/CD config, code formatting, build tooling, internal refactors with no behavior change.

**Judgment call**: Dependency updates (include if security-related or if they change behavior), documentation changes (include if they reflect API/behavior changes), refactors (include if they improve reliability/performance users will notice).
