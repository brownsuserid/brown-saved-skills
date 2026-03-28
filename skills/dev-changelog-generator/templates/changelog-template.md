# Changelog Templates

Pick the template that matches the project's conventions, or adapt as needed.

---

## Standard Template (Recommended)

```markdown
# v[X.Y.Z] - [YYYY-MM-DD]

## Features
- feat(scope): Description of feature and its impact (#PR)

## Improvements
- perf(scope): Description of improvement with quantified impact (#PR)

## Bug Fixes
- fix(scope): Description of what was broken and what's fixed (#PR)

## Breaking Changes

### [Change Name]
**What changed**: Description
**What breaks**: Impact on existing behavior
**Migration**: Step-by-step instructions

## Security
- fix(deps): Update [package] to patch [vulnerability type] (#PR)

---

**Full Changelog**: https://github.com/org/repo/compare/vPREV...vX.Y.Z
```

---

## Minimal Template

For patch releases, hotfixes, or weekly updates where brevity matters.

```markdown
# v[X.Y.Z] - [YYYY-MM-DD]

- fix(scope): Description (#PR)
- fix(scope): Description (#PR)
- chore(deps): Description (#PR)
```

---

## Detailed Template

For major releases or when communicating to a broader audience.

```markdown
# v[X.Y.Z] - [YYYY-MM-DD]

[1-2 sentence summary of the release theme]

## Features

### [Major Feature Name]
[2-3 sentences on what it does and why it matters]
- Key capability one
- Key capability two
(#PR)

## Improvements
- perf(scope): Specific improvement with numbers (#PR)
- refactor(scope): What's better and why (#PR)

## Bug Fixes
- fix(scope): What was broken, now fixed (#PR)

## Breaking Changes
[Detailed migration guidance — see breaking changes template in best-practices reference]

---

**Full Changelog**: https://github.com/org/repo/compare/vPREV...vX.Y.Z

## Contributors
Thanks to @contributor1, @contributor2 for their contributions!
```

---

## Keep a Changelog Format

Based on [keepachangelog.com](https://keepachangelog.com/en/1.0.0/).

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New feature description

### Changed
- Changed behavior description

### Deprecated
- Deprecated feature (removal planned in vX.Y.Z)

### Removed
- Removed feature description

### Fixed
- Bug fix description

### Security
- Security fix description

[X.Y.Z]: https://github.com/org/repo/compare/vPREV...vX.Y.Z
```
