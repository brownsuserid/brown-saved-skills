---
name: creating-skills
description: Creates new Claude Code skills (user-level or project-level) when a systematic workflow needs to be defined for a complex task. Ensures skills follow best practices including proper structure, naming conventions, phase-based workflows, and 500-line limit validation.
---

# Creating Skills Skill

This skill provides a systematic approach to creating high-quality Claude Code skills that follow established best practices and conventions.

## Process Overview

Use the TodoWrite tool to track progress through these phases:

---

## Phase 0: Determine Skill Scope

Choose whether this skill should be user-level or project-level, then set `$SKILL_PATH` for all subsequent commands.

**User-level** (`~/.claude/skills/`): Cross-project, general workflows, language-agnostic (e.g., `dev-fixing-bugs`, `dev-reviewing-code`)
**Project-level** (`.claude/skills/`): Project-specific tooling, deployment, conventions (e.g., `deploying-to-production`, `running-migration-tests`)

**Set path variable:**
```bash
# User-level
SKILL_PATH=~/.claude/skills

# Project-level
SKILL_PATH=.claude/skills
```

---

## Phase 1: Define Skill Purpose

Clearly identify what the skill should do and when it should be used.

### Identify the Need

**Good candidates for skills:**
- Development workflows (implementing, testing, reviewing)
- Quality assurance processes
- Documentation creation
- Multi-phase investigations
- Desire to have Claude agents be able to execute

**Not good candidates:**
- One-time tasks
- Simple, single-step operations
- Highly context-specific tasks
- Tasks that should be run by the human operator

### Draft Description

Write 1-2 sentences (max 200 characters) that:
- Uses third person ("Performs...", "Creates...", "Reviews...")
- Specifies WHEN to use (trigger conditions)
- Lists key capabilities

**Template:**
```
[Action] [what] when [trigger condition]. [Key features].
```

**Example:**
```
Performs comprehensive code review when evaluating pull requests. Reviews correctness, security, quality, and testing.
```

---

## Phase 2: Research Best Practices

Gather information about best practices for the task.

### Search for Industry Standards

```bash
# Web search patterns
"[task] best practices 2025"
"[task] systematic approach"
"[task] workflow process"
```

### Review Existing Skills

```bash
ls $SKILL_PATH/
cat $SKILL_PATH/[similar-skill]/SKILL.md
```

**Note patterns:**
- How many phases?
- What structure?
- How is TodoWrite used?
- What references included?

**Complete research guidance:** See `references/skill-best-practices.md`

---

## Phase 3: Design Phase Structure

Break the task into logical, sequential phases.

### Target 5-8 Phases

**Common patterns:**

**Investigation:** Collect → Generate hypotheses → Validate → Implement → Verify

**Creation:** Analyze requirements → Design → Implement → Test → Document → Review

**Review:** Fetch info → Quick scan → Detailed review → Provide feedback → Decide → Follow-up

### Name Phases Descriptively

**Format:** `Phase N: [Action Verb] [What]`

**Good:**
- Phase 1: Identify Refactoring Opportunities
- Phase 2: Prioritize Refactoring Work

**Bad:**
- Phase 1: Setup (too vague)
- Phase 2: Work (not descriptive)

**Complete phase design guide:** See `references/skill-structure-guide.md`

---

## Phase 4: Create Directory Structure

Set up skill directory with proper organization.

### Create Skill Directory

```bash
cd $SKILL_PATH/
mkdir -p skill-name/{references,templates,scripts}
```

**Naming rules:**
- Gerund form (-ing): `fixing`, `planning`, `reviewing`
- Lowercase with hyphens: `fixing-bugs`, `reviewing-code`
- Include a short and relevant category prefix: `dev-`, `fs-`, `pm-`

**Examples:**
```bash
mkdir -p dev-fixing-bugs/{references,templates}
mkdir -p dev-reviewing-code/{references,templates}
```

---

## Phase 5: Write Main SKILL.md

Create the main skill file with proper structure.

### Create Frontmatter

```yaml
---
name: skill-name-without-category-prefix
description: When to use. Key capabilities.
---
```

### Write Structure

```markdown
# Skill Name

Introduction with value proposition.

## Process Overview

Use the TodoWrite tool to track progress through these phases:

---

## Phase 1: [Name]

Content...

---

## Phase 2: [Name]

Content...

---

[Additional phases...]

---

## Supporting Files Reference

List references and templates...

---

## Key Principles

Core principles...

## Success Criteria

Completion criteria...

## Checklist

Validation items...

## When to Use This Skill

Usage scenarios...

## Common Mistakes to Avoid

Anti-patterns and best practices...
```

### Keep Phases Focused

**In each phase include:** Clear instructions, essential commands, expected outcomes, brief examples, references to detailed docs

**Extract to references if:** > 200 lines of detail, complex patterns catalog, extensive examples

**IMPORTANT: Avoid redundancy - Use shared references:**
- Git/PR → `../dev-shared-references/git-and-pr-workflow.md`
- Testing → `../dev-writing-unit-tests/SKILL.md`
- Quality checks → `../dev-quality-checks/SKILL.md`
- Coding standards → `../dev-shared-references/coding-standards.md`

**Critical: SKILL.md must be ≤ 500 lines**

```bash
wc -l $SKILL_PATH/skill-name/SKILL.md
```

**Complete structure guide:** See `references/skill-structure-guide.md`

---

## Phase 6: Create Reference Files

Write detailed supporting documentation.

### Identify Reference Topics

**Common topics:**
- Best practices and standards
- Patterns and anti-patterns
- Detailed examples
- Troubleshooting guides

### Create Files

**Structure:**
```markdown
# Reference Topic

Introduction.

## Section 1

Content...

## Section 2

Content...

## Summary

Key takeaways.
```

**File naming:**
- `kebab-case-description.md`
- Examples: `code-review-standards.md`, `refactoring-patterns.md`

### Link from SKILL.md

```markdown
**Complete guide:** See `references/detailed-guide.md`
```

**Complete reference organization:** See `references/skill-structure-guide.md`

---

## Phase 7: Create Templates

Provide reusable structures for outputs.

### Create Template Files

**Structure:**
```markdown
# Template Name

Description of when/how to use.

## Section 1

[Instructions]

**Field:** [What goes here]

## Example

[Complete example]
```

**File naming:**
- `kebab-case-template.md`
- Examples: `pr-review-template.md`, `bug-fix-report.md`

---

## Phase 8: Validate Skill

Ensure skill meets quality standards.

### Run Validation Script

```bash
cd $SKILL_PATH/
python3 creating-skills/scripts/validate_skill.py skill-name
```

**Note:** For project-level skills, ensure the validation script is available or copy it from your user-level skills directory.

**Checks:**
- SKILL.md exists
- SKILL.md ≤ 500 lines
- Proper frontmatter
- Required sections
- File references valid

**Fix any errors before proceeding.**

### Manual Review Checklist

**Structure:**
- [ ] SKILL.md with frontmatter
- [ ] Name follows conventions
- [ ] Description specifies WHEN
- [ ] 5-8 phases
- [ ] TodoWrite mentioned

**Content:**
- [ ] Clear instructions
- [ ] Working examples
- [ ] Proper references
- [ ] Success criteria
- [ ] Common mistakes

**Length:**
- [ ] SKILL.md ≤ 500 lines
- [ ] Details in references
- [ ] Templates created

**Complete validation checklist:** See `references/skill-best-practices.md`

---

## Phase 9: Document and Communicate

Finalize skill and make it discoverable.

### Create Commit

```bash
cd $SKILL_PATH/
git add skill-name/
git commit -m "$(cat <<'EOF'
feat(skills): add [skill-name] skill

Created [user-level/project-specific] skill for [task]:
- [Phase count] phases, [Reference count] references, [Template count] templates

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Test Skill

**Manually test:**
```
"Use the [skill-name] skill to [scenario]"
```

**Verify:**
- Skill invoked correctly
- TodoWrite creates phases
- Workflow followed
- Output quality good

---

## Supporting Files Reference

This skill includes comprehensive reference materials:

### Skill Creation Specific
- `references/skill-best-practices.md` - Complete best practices guide with naming, structure, discovery
- `references/skill-structure-guide.md` - Detailed guidance on phases, references, templates, and validation
- `scripts/validate_skill.py` - Validation script for checking compliance

---

## Key Principles

- **Systematic workflow:** 5-8 phases for clear structure
- **Length limit:** SKILL.md ≤ 500 lines (extract to references)
- **Clear triggers:** Description specifies WHEN to use
- **TodoWrite integration:** Track progress through phases
- **Proper naming:** Gerund form, kebab-case, descriptive
- **Validation:** Use script to check compliance
- **Examples:** Show correct usage with code
- **Research-based:** Include best practices

## Success Criteria

- SKILL.md created with proper frontmatter
- Name follows conventions (gerund, kebab-case)
- Description is specific about WHEN
- 5-8 clearly defined phases
- SKILL.md ≤ 500 lines
- References for detailed content
- Templates for reusable structures
- Validation script passes
- Manually tested and working
- Committed to version control

## Skill Creation Checklist

**Planning:**
- [ ] Purpose defined
- [ ] Triggers identified
- [ ] Research completed
- [ ] Phases designed (5-8)

**Implementation:**
- [ ] Directory created
- [ ] SKILL.md with frontmatter
- [ ] Phases with instructions
- [ ] References created
- [ ] Templates created

**Quality:**
- [ ] SKILL.md ≤ 500 lines
- [ ] Markdown formatted
- [ ] Code examples correct
- [ ] File references valid
- [ ] Validation passes
- [ ] Manually tested

**Finalization:**
- [ ] Committed
- [ ] Documentation updated
- [ ] Team notified

## When to Use This Skill

Use this skill:
- **When creating new skills** - Systematic approach needed
- **When updating skills** - Ensure best practices
- **When skill too long** - Split into references
- **When validating** - Check compliance

## Common Mistakes to Avoid

**❌ Don't:**
- Create skills for one-time tasks
- Write vague descriptions
- Skip research
- Exceed 500 lines in SKILL.md
- Forget TodoWrite
- Skip validation
- Use non-gerund names
- **Duplicate content from shared references** (git, testing, quality checks)
- Include redundant commit/PR instructions

**✓ Do:**
- Create for repeated tasks
- Write specific descriptions
- Research first
- Extract to references
- Integrate TodoWrite
- Validate before commit
- Follow naming conventions
- **Reference shared documentation** (../dev-shared-references/, other skills)
- Keep examples concise, defer to comprehensive guides
