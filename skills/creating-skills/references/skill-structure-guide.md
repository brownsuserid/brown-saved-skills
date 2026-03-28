# Skill Structure Guide

This document provides detailed guidance on structuring skill content, writing phases, and organizing supporting materials.

## SKILL.md Structure

### Complete Structure Template

```markdown
---
name: skill-name
description: When to use and key capabilities.
---

# Skill Name

Introduction with value proposition.

## Process Overview

Use the TodoWrite tool to track progress through these phases:

---

## Phase 1: [Name]

Phase content...

---

## Phase 2: [Name]

Phase content...

---

[Additional phases...]

---

## Supporting Files Reference

References and templates...

---

## Key Principles

Guiding principles...

## Success Criteria

Completion criteria...

## Checklist

Validation checklist...

## When to Use This Skill

Usage scenarios...

## Common Mistakes to Avoid

Anti-patterns and best practices...
```

---

## Phase Content Guidelines

### Phase Structure

Each phase should follow this structure:

```markdown
## Phase N: [Action Verb] [What]

Brief description of what this phase accomplishes (1-2 sentences).

### [Subsection 1]

Content...

### [Subsection 2]

Content...

### [Subsection 3]

Content...

---
```

### What to Include in Phases

**Do include:**
- Clear, actionable instructions
- Essential commands/code
- Expected outcomes
- Brief examples
- Common issues and quick fixes
- References to detailed docs

**Don't include:**
- Extensive explanations (use references)
- Long catalogs of patterns (use references)
- Detailed troubleshooting (use references)
- Multiple full examples (use references)

### Length Guidelines

**Per phase:**
- Target: 50-100 lines
- Maximum: 150 lines
- If longer: Extract to references

**Example of extracting:**

**Instead of (in SKILL.md):**
```markdown
## Phase 3: Identify Code Smells

### Duplicate Code

[50 lines of examples]

### Long Functions

[40 lines of examples]

### Complex Conditionals

[60 lines of examples]

[...continues for 200+ lines...]
```

**Do this (in SKILL.md):**
```markdown
## Phase 3: Identify Code Smells

Review code for common issues.

### Check for Code Smells

Look for:
- Duplicate code
- Long functions (> 50 lines)
- Complex conditionals
- God objects
- Feature envy
- Magic numbers

**Complete reference:** See `references/code-smells-catalog.md` for detailed examples and patterns.
```

---

## Reference File Organization

### When to Create References

Create reference file when content is:
- > 200 lines
- Detailed patterns catalog
- Extensive examples
- Reference material (not workflow)
- Troubleshooting guide

### Reference File Structure

```markdown
# Reference Topic

Brief introduction to topic.

## Overview

High-level summary.

---

## Section 1: [Topic]

Detailed content...

### Subsection

Content...

---

## Section 2: [Topic]

Detailed content...

### Subsection

Content...

---

## Summary

Key takeaways and quick reference.
```

### Common Reference Types

**Standards and Best Practices:**
- `code-review-standards.md`
- `refactoring-patterns.md`
- `documentation-standards.md`

**Detailed Guides:**
- `technical-debt-management.md`
- `root-cause-analysis.md`
- `integration-test-design.md`

**Pattern Catalogs:**
- `refactoring-patterns.md`
- `test-isolation.md`
- `architectural-principles.md`

---

## Template Organization

### When to Create Templates

Create template when:
- Repeatable structure needed
- Standard format required
- User fills in blanks

### Template Structure

```markdown
# Template Name

Brief description of when and how to use this template.

---

## Section 1: [Name]

[Instructions for completing this section]

**Field Name:**
[Description of what goes here]

**Example:**
[Example value]

---

## Section 2: [Name]

[Instructions]

---

## Complete Example

[Full example showing filled-in template]
```

### Common Template Types

**Reports:**
- `bug-fix-report.md`
- `pr-review-template.md`
- `security-audit-report.md`

**Plans:**
- `feature-plan-template.md`
- `refactoring-plan-template.md`

**Checklists:**
- `quality-checklist.md`
- `release-checklist.md`

---

## Code Examples Best Practices

### Formatting

Use language-tagged code blocks:

````markdown
```python
def example():
    return "value"
```
````

### Before/After Pattern

Show bad and good examples:

````markdown
**Before:**
```python
# Bad code with issues
x = calculate(data)
```

**After:**
```python
# Good code with improvements
result = calculate_total(order_data)
```
````

### Labeling Examples

Use consistent labels:

```markdown
# ❌ BAD: Reason why it's bad
code...

# ✓ GOOD: Reason why it's good
code...
```

### Working Examples

**Critical:** All examples must work!

Test examples:
- Run code examples
- Verify commands
- Check output matches

Update examples when code changes.

---

## Linking Between Files

### Reference from SKILL.md

**Format:**
```markdown
**Complete guide:** See `references/detailed-guide.md`

**For detailed examples:** See `references/patterns.md` Section 3

**Reference:** `references/standards.md` for complete standards
```

### Reference from One Reference to Another

**Format:**
```markdown
For more on code quality, see `code-review-standards.md` Section 2.

This builds on concepts from `refactoring-patterns.md`.
```

### Reference Shared Standards

**For dev-* skills:**
```markdown
**Follow implementation standards:**
- `../dev-shared-references/coding-standards.md`
- `../dev-shared-references/git-conventions.md`
```

---

## TodoWrite Integration

### Mention in Process Overview

```markdown
## Process Overview

Use the TodoWrite tool to track progress through these phases:

---

## Phase 1: [Name]
## Phase 2: [Name]
...
```

### Expected Usage

During skill execution, Claude should:

**1. Create todos at start:**
```json
[
  {"content": "Phase 1 description", "status": "pending", "activeForm": "Doing phase 1"},
  {"content": "Phase 2 description", "status": "pending", "activeForm": "Doing phase 2"},
  {"content": "Phase 3 description", "status": "pending", "activeForm": "Doing phase 3"}
]
```

**2. Update as phases progress:**
```json
[
  {"content": "Phase 1 description", "status": "completed", "activeForm": "Doing phase 1"},
  {"content": "Phase 2 description", "status": "in_progress", "activeForm": "Doing phase 2"},
  {"content": "Phase 3 description", "status": "pending", "activeForm": "Doing phase 3"}
]
```

**3. Complete when done:**
```json
[
  {"content": "Phase 1 description", "status": "completed", "activeForm": "Doing phase 1"},
  {"content": "Phase 2 description", "status": "completed", "activeForm": "Doing phase 2"},
  {"content": "Phase 3 description", "status": "completed", "activeForm": "Doing phase 3"}
]
```

---

## Supporting Sections

### Key Principles

List 5-8 core principles:

```markdown
## Key Principles

- **Principle 1:** Brief explanation
- **Principle 2:** Brief explanation
- **Principle 3:** Brief explanation
```

### Success Criteria

Define what "done" looks like:

```markdown
## Success Criteria

- Criterion 1 met
- Criterion 2 achieved
- Criterion 3 validated
- All quality gates passed
```

### Checklist

Provide validation checklist:

```markdown
## Checklist

Before completing:

**Planning:**
- [ ] Item 1
- [ ] Item 2

**Implementation:**
- [ ] Item 3
- [ ] Item 4

**Quality:**
- [ ] Item 5
- [ ] Item 6
```

### When to Use This Skill

Be specific about triggers:

```markdown
## When to Use This Skill

Use this skill:
- **When [condition 1]** - Specific scenario
- **When [condition 2]** - Specific scenario
- **When [condition 3]** - Specific scenario
```

### Common Mistakes to Avoid

Show anti-patterns and best practices:

```markdown
## Common Mistakes to Avoid

**❌ Don't:**
- Mistake 1 with explanation
- Mistake 2 with explanation

**✓ Do:**
- Best practice 1 with explanation
- Best practice 2 with explanation
```

---

## Validation

### Automated Checks

Run validation script:

```bash
python3 creating-skills/scripts/validate_skill.py skill-name
```

**Checks:**
- SKILL.md exists
- SKILL.md ≤ 500 lines
- Frontmatter present
- Required sections exist
- File references valid

### Manual Checks

**Quality:**
- [ ] Instructions are clear and actionable
- [ ] Examples are correct and working
- [ ] References are properly linked
- [ ] No broken links
- [ ] Markdown properly formatted

**Content:**
- [ ] Phases are logical and sequential
- [ ] Each phase has clear purpose
- [ ] TodoWrite integration mentioned
- [ ] Success criteria defined
- [ ] Common mistakes documented

---

## Maintenance

### When to Update

Update skill when:
- Code reviews reveal new patterns
- Better practices discovered
- User feedback received
- Standards change
- Tool capabilities change

### Versioning

Track changes:

```bash
git add skill-name/
git commit -m "feat(skill-name): add section on [topic]"
```

Document in skill:

```markdown
**Updated 2025-01-15:** Added guidance on [topic]
```

---

## Summary

**Key points:**
- SKILL.md ≤ 500 lines (extract to references)
- 5-8 phases with clear structure
- TodoWrite for progress tracking
- Code examples must work
- Proper linking between files
- Validation before completion
- Clear success criteria
- Anti-patterns documented
