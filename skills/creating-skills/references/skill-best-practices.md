# Skill Best Practices Reference

This document details best practices for creating effective Claude Code skills based on research and established patterns.

## What Are Skills?

**Skills** are specialized workflows that Claude Code can invoke to perform complex, multi-step tasks systematically.

**Key characteristics:**
- Self-contained with references and templates
- Systematic phase-based approach
- Use TodoWrite to track progress
- Follow established patterns
- Auto-discovered by Claude Code

---

## Skill Structure

### Directory Layout

**User-level skills** (`~/.claude/skills/`):
```
~/.claude/skills/
└── skill-name/
    ├── SKILL.md                    # Main skill file (REQUIRED)
    ├── references/                 # Supporting documentation
    │   ├── reference-1.md
    │   └── reference-2.md
    ├── templates/                  # Reusable templates
    │   └── template-1.md
    └── scripts/                    # Utility scripts (optional)
        └── script.py
```

**Project-level skills** (`.claude/skills/`):
```
.claude/skills/
└── skill-name/
    ├── SKILL.md                    # Main skill file (REQUIRED)
    ├── references/                 # Supporting documentation
    │   ├── reference-1.md
    │   └── reference-2.md
    └── templates/                  # Reusable templates
        └── template-1.md
```

**Critical rules:**
- Skills MUST be directly under their skills directory (user-level or project-level)
- Skills CANNOT be nested in subdirectories
- Main file MUST be named `SKILL.md`

**Wrong:**
```
~/.claude/skills/dev/skill-name/  ❌ Cannot nest in subdirectories
.claude/skills/dev/skill-name/    ❌ Cannot nest in subdirectories
```

**Right:**
```
~/.claude/skills/skill-name/      ✓ Directly under skills/
.claude/skills/skill-name/        ✓ Directly under skills/
```

---

## SKILL.md Format

### Frontmatter

**Required YAML frontmatter:**

```yaml
---
name: skill-name-without-prefix
description: When to use this skill in third person. Be specific about WHEN to invoke.
---
```

**Name guidelines:**
- Lowercase with hyphens
- Gerund form (ending in -ing)
- Do NOT include category prefix in name
- Examples: `fixing-bugs`, `planning-features`, `reviewing-code`

**Description guidelines:**
- Third person ("Performs...", "Creates...", "Reviews...")
- Specify WHEN to use (context triggers)
- Be specific (not vague)
- Mention key capabilities
- Length: 1-2 sentences, maximum 200 characters

**Good descriptions:**
```yaml
description: Performs comprehensive code review when evaluating pull requests or code changes. Reviews correctness, security, quality, testing, and standards compliance.

description: Improves code structure and quality when code becomes difficult to maintain, has duplication, or shows signs of technical debt. Uses incremental refactoring strategies.

description: Creates comprehensive, well-isolated unit tests when adding test coverage for new or existing code. Follows modern pytest best practices.
```

**Bad descriptions:**
```yaml
description: A skill for bugs  # Too vague

description: This skill helps you write code  # Too generic

description: Does testing  # Not specific enough
```

### Main Content Structure

**Standard structure:**

```markdown
# Skill Name

Brief introduction explaining what this skill does and why it's valuable.
Include research findings or statistics if relevant.

## Process Overview

Use the TodoWrite tool to track progress through these phases:

---

## Phase 1: [Phase Name]

Description of what this phase does.

### [Subsection]

Content...

### [Subsection]

Content...

---

## Phase 2: [Phase Name]

...

---

## Supporting Files Reference

This skill includes comprehensive reference materials:

### Skill-Specific
- `references/reference-1.md` - Description
- `templates/template-1.md` - Description

### Implementation Standards (Shared across all dev-* skills)
- `../dev-shared-references/coding-standards.md` - Description
- `../dev-shared-references/git-conventions.md` - Description

---

## Key Principles

- Principle 1
- Principle 2
- Principle 3

## Success Criteria

- Criterion 1
- Criterion 2
- Criterion 3

## Checklist

Before completing:
- [ ] Item 1
- [ ] Item 2
- [ ] Item 3

## When to Use This Skill

Use this skill:
- When X happens
- When Y is needed
- When Z is required

## Common Mistakes to Avoid

**❌ Don't:**
- Mistake 1
- Mistake 2

**✓ Do:**
- Best practice 1
- Best practice 2
```

---

## Skill Length Limits

**Critical rule: SKILL.md must be ≤ 500 lines**

**Why:**
- Easier to navigate
- Focused content
- Forces good organization
- References used for details

**If SKILL.md exceeds 500 lines:**
1. Extract detailed content to `references/`
2. Keep phases and structure in SKILL.md
3. Reference external files for details

**Example:**
```markdown
## Phase 3: Review Code Quality

Review code across multiple dimensions.

### Check for Code Smells

Look for common issues:
- Duplicate code
- Long functions
- Complex conditionals
- God objects

**Complete reference:** See `references/code-review-standards.md` for detailed examples and patterns.
```

**Use validation script:**
```bash
# From user-level skills directory
cd ~/.claude/skills/
python3 creating-skills/scripts/validate_skill.py skill-name

# From project-level skills directory
cd .claude/skills/
python3 ../path/to/validate_skill.py skill-name
```

---

## Naming Conventions

### Skill Naming

**Format:** `[category-]activity`

**Categories:**
- `dev-` - Development tasks (coding, testing, reviewing)
- `auditing-` - Audit and compliance tasks
- `creating-` - Creation tasks (skills, docs)
- No prefix - General purpose skills

**Activity naming:**
- Use gerund form (-ing)
- Be specific and descriptive
- Lowercase with hyphens

**Examples:**
```
dev-fixing-bugs          ✓
dev-planning-features    ✓
dev-reviewing-code       ✓
dev-refactoring          ✓
auditing-aws-security    ✓
creating-skills          ✓

FixBugs                  ❌ Not gerund, wrong case
dev-bug-fix              ❌ Not gerund
review                   ❌ Missing category, too vague
```

### File Naming

**References:** `kebab-case-description.md`
```
code-review-standards.md     ✓
refactoring-patterns.md      ✓
technical-debt-management.md ✓

CodeReviewStandards.md       ❌ Wrong case
standards.md                 ❌ Too vague
```

**Templates:** `kebab-case-template.md`
```
pr-review-template.md        ✓
bug-fix-report.md            ✓
feature-plan-template.md     ✓
```

**Scripts:** `snake_case_script.py`
```
validate_skill.py            ✓
check_duplication.py         ✓

validateSkill.py             ❌ Wrong case
validate-skill.py            ❌ Use underscores for Python
```

---

## Phase-Based Workflow

### Why Phases?

Phases provide:
- Clear structure
- Logical progression
- Progress tracking
- Systematic approach

### Number of Phases

**Typical: 5-8 phases**

**Too few (< 3):**
- Not enough structure
- Steps too large

**Too many (> 10):**
- Overwhelming
- Too granular

**Good examples:**
- Bug fixing: 6 phases
- Feature planning: 4 phases
- Code review: 7 phases
- Quality checks: 7 phases

### Phase Structure

**Each phase should have:**

```markdown
## Phase N: [Descriptive Phase Name]

Brief description of what this phase accomplishes.

### [Subsection 1]

Content...

### [Subsection 2]

Content...

### [Subsection 3]

Content...

---
```

**Phase naming:**
- Start with action verb
- Be specific
- Indicate outcome

**Good phase names:**
```
## Phase 1: Identify Refactoring Opportunities
## Phase 2: Prioritize Refactoring Work
## Phase 3: Ensure Test Coverage
## Phase 4: Refactor Incrementally
```

**Bad phase names:**
```
## Phase 1: Setup              ❌ Too vague
## Phase 2: Do Work            ❌ Not specific
## Phase 3: Finish             ❌ Not descriptive
```

---

## TodoWrite Integration

### Purpose

TodoWrite tool tracks progress through skill phases.

### Usage Pattern

**At skill start:**
```markdown
## Process Overview

Use the TodoWrite tool to track progress through these phases:

---

## Phase 1: [Name]
## Phase 2: [Name]
## Phase 3: [Name]
```

**In skill execution:**
Claude should use TodoWrite to:
1. Create todos for all phases at start
2. Mark current phase as in_progress
3. Mark phases as completed when done
4. Update activeForm for current task

**Example:**
```json
[
  {"content": "Identify refactoring opportunities", "status": "completed", "activeForm": "Identifying refactoring opportunities"},
  {"content": "Prioritize refactoring work", "status": "in_progress", "activeForm": "Prioritizing refactoring work"},
  {"content": "Ensure test coverage", "status": "pending", "activeForm": "Ensuring test coverage"}
]
```

---

## References Organization

### When to Use References

**Create reference file when:**
- Detailed explanations needed (> 200 lines)
- Complex patterns or examples
- Reference material (not workflow)
- Reusable knowledge

**Keep in SKILL.md when:**
- Core workflow steps
- Phase structure
- Quick reference
- < 100 lines of content

### Reference File Structure

```markdown
# Reference Topic

Brief introduction to topic.

## Section 1

Content...

## Section 2

Content...

## Summary

Key takeaways.
```

### Referencing Files

**In SKILL.md:**
```markdown
**Complete guide:** See `references/detailed-guide.md`

**For detailed patterns:** See `references/patterns.md` Section 3.

**Reference:** `references/standards.md` for complete standards.
```

---

## Templates Organization

### When to Create Templates

**Create template when:**
- Repeatable structure needed
- Standard format required
- User will fill in blanks

**Examples:**
- PR review template
- Bug fix report
- Feature plan template
- Documentation template

### Template Structure

```markdown
# Template Name

Brief description of when/how to use this template.

## Section 1

[Instructions for this section]

**Field name:**
[Description of what goes here]

## Section 2

...

## Example

[Complete example showing filled-in template]
```

---

## Shared References

### dev-shared-references/

**For ALL dev-* skills:**

```
dev-shared-references/
├── coding-standards.md      # Python, testing, FastAPI
├── git-conventions.md       # Commit format, branching
├── uv-guide.md             # Dependency management
└── aws-standards.md        # AWS infrastructure
```

**Reference from skills:**
```markdown
### Follow Implementation Standards

All code changes must follow standards in:
- `../dev-shared-references/coding-standards.md`
- `../dev-shared-references/git-conventions.md`
```

**Don't duplicate:**
- If standard applies to multiple skills → shared references
- If specific to one skill → skill references

---

## Code Examples

### Example Formatting

**Use triple backticks with language:**

```markdown
```python
def example_function():
    return "example"
```
```

**Show before/after:**

```markdown
**Before:**
```python
# Bad code
```

**After:**
```python
# Good code
```
```

**Label examples:**
```markdown
# ❌ BAD: Reason why it's bad
code...

# ✓ GOOD: Reason why it's good
code...
```

---

## Discovery and Invocation

### How Skills Are Discovered

1. **Startup:** Claude Code scans both `~/.claude/skills/` (user-level) and `.claude/skills/` (project-level)
2. **Description injection:** Skill descriptions added to system prompt
3. **Context matching:** Claude matches user request to skill description
4. **Priority:** Project-level skills can override user-level skills with the same name

### Invocation Methods

**1. Automatic (context-based):**
User says: "Fix this bug"
Claude recognizes: Matches `dev-fixing-bugs` description
Claude invokes: Automatically uses bug-fixing skill

**2. Explicit (user requests):**
User says: "Use the dev-reviewing-code skill to review PR #123"
Claude invokes: Explicitly uses code review skill

### Writing Good Descriptions for Discovery

**Include trigger keywords:**
```yaml
description: Performs comprehensive code review when evaluating pull requests or code changes.
# Triggers: "code review", "review PR", "review changes"

description: Improves code structure when code becomes difficult to maintain, has duplication, or shows signs of technical debt.
# Triggers: "refactor", "technical debt", "duplication", "code quality"
```

**Be specific about WHEN:**
```yaml
# ✓ GOOD: Clear when to use
description: Creates comprehensive integration tests when testing interactions between components, databases, APIs, or external services.

# ❌ BAD: Vague
description: Creates tests for code.
```

---

## Validation Checklist

Before considering skill complete:

### Structure
- [ ] SKILL.md exists with proper frontmatter
- [ ] Name follows conventions (gerund form, kebab-case)
- [ ] Description specifies WHEN to use
- [ ] Phases are logical and well-organized
- [ ] Supporting files in proper directories

### Length
- [ ] SKILL.md is ≤ 500 lines
- [ ] Detailed content extracted to references/
- [ ] Templates created for reusable structures

### Content Quality
- [ ] TodoWrite mentioned in Process Overview
- [ ] Each phase has clear purpose
- [ ] Examples are clear and correct
- [ ] Code follows standards
- [ ] References properly linked
- [ ] Success criteria defined
- [ ] Common mistakes documented

### Technical
- [ ] Markdown properly formatted
- [ ] Code blocks have language tags
- [ ] No broken links
- [ ] File references are correct
- [ ] Skill validated with validation script

---

## Common Patterns

### Research Citations

When applicable, include research findings:

```markdown
**Research finding:** 40% of developers spend 2-5 days/month on technical debt.

**Research shows:** Teams achieve 3x faster modernization with AI assistance.
```

### Warning Boxes

Use emoji for visual emphasis:

```markdown
**🚨 Critical:** Never push directly to main

**⚠️ Warning:** This operation cannot be undone

**💡 Tip:** Use early returns to reduce nesting
```

### Priority Indicators

```markdown
**HIGH Priority:**
- Critical items
- Must-fix issues

**MEDIUM Priority:**
- Important items
- Should-fix issues

**LOW Priority:**
- Nice-to-have items
- Optional improvements
```

---

## Testing Skills

### Manual Testing

**Test skill by:**
1. Creating test scenario
2. Invoking skill explicitly
3. Verifying TodoWrite used
4. Checking phases followed
5. Validating output quality

**Example test:**
```
"Use the dev-fixing-bugs skill to investigate the login error in auth.py:42"
```

**Verify:**
- Skill invoked correctly
- TodoWrite created for phases
- Systematic investigation
- Proper documentation

### Validation Script

**Run validation:**
```bash
# User-level skill
cd ~/.claude/skills/
python3 creating-skills/scripts/validate_skill.py skill-name

# Project-level skill
cd .claude/skills/
python3 ~/path/to/validate_skill.py skill-name
```

**Checks:**
- SKILL.md length ≤ 500 lines
- Frontmatter present
- Required sections exist
- File references valid

---

## Maintenance

### When to Update Skills

**Update skills when:**
- Code reviews reveal new patterns
- Common mistakes identified
- Better practices discovered
- User feedback received
- Standards change

**Example:**
"In code reviews, we keep seeing AI-generated duplication. Let's add a section to dev-refactoring about identifying and consolidating AI patterns."

### Version Control

**Track skill changes:**
```bash
# User-level skills
cd ~/.claude/skills/
git add skill-name/
git commit -m "feat(skill-name): add section on AI-generated duplication"

# Project-level skills
cd .claude/skills/
git add skill-name/
git commit -m "feat(skill-name): add section on [topic]"
```

**Document major changes:**
Update skill with note:
```markdown
**Updated 2025-01-15:** Added guidance on preventing AI-generated duplication
```

---

## Summary

**Key principles:**
- Skills in `~/.claude/skills/` (user-level) or `.claude/skills/` (project-level)
- No nesting in subdirectories
- SKILL.md ≤ 500 lines (extract to references)
- Phase-based workflow (5-8 phases typical)
- TodoWrite for progress tracking
- Gerund naming (fixing, planning, reviewing)
- Descriptive frontmatter for discovery
- Shared references for common standards
- Examples show before/after
- Validation before completion

**Skill anatomy:**
```
skill-name/
├── SKILL.md           # Main workflow (≤ 500 lines)
├── references/        # Detailed guides
├── templates/         # Reusable structures
└── scripts/           # Validation/utility scripts
```

**Quality checklist:**
- ✓ Clear WHEN to use (description)
- ✓ Systematic phases
- ✓ TodoWrite integration
- ✓ Proper length (≤ 500 lines)
- ✓ Supporting references
- ✓ Code examples
- ✓ Success criteria
- ✓ Validated with script
