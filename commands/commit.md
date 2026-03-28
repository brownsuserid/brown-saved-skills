# Quality Check then Commit Changes

Create a to-do list for yourself. Follow these steps in sequence without skipping any.

## 1. Run Quality Checks

Follow the `dev-quality-checks` skill to run comprehensive quality validation (integration tests, security scanning, user validation). Do not proceed to commit until all checks pass.

## 2. Stage and Review Changes

```bash
git add .
git status
git diff --cached
```

Review staged changes to ensure no unintended files are included (especially `.env`, credentials, large binaries). If unsure, ask the user.

## 3. Commit

Follow commit format from `dev-shared-references/git-conventions.md`. End message with "-Agent Generated Commit Message".

## 4. Push

```bash
git push -u origin <branch-name>
```
