---
name: skill-overlap-checker
description: Analyzes a skill library for overlapping responsibilities, boundary confusion, and triggering ambiguity between skills. Use this skill whenever you want to audit skills for overlap, check if a new skill duplicates existing ones, identify skills that compete for the same triggers, find redundant or conflicting guidance across skills, or rationalize a growing skill library. Also triggers for "do any skills overlap", "which skills are redundant", "is this skill already covered", "audit my skills", "skill library health check", or when consolidating, merging, or retiring skills.
---

# Skill Overlap Checker

This skill systematically analyzes a collection of skills to find overlapping responsibilities, ambiguous boundaries, conflicting guidance, and triggering competition. The goal is to keep a skill library lean and well-partitioned so that each skill has a clear, non-competing purpose.

## When This Matters

As a skill library grows, several problems emerge:
- **Triggering competition**: Two skills match the same user prompt, causing unpredictable selection
- **Duplicated guidance**: The same advice appears in multiple skills, creating maintenance burden and drift risk
- **Boundary confusion**: It's unclear which skill should handle a request that touches two domains
- **Stale cross-references**: Skills reference other skills that have been retired or restructured

These problems compound — a user who gets the wrong skill loses trust in the whole system.

## Process

### Phase 1: Inventory

Scan the skill library to build a complete inventory.

```bash
# Run the inventory script to extract all skill metadata
python3 scripts/scan_skills.py <skill-library-path>
```

The script extracts from each SKILL.md:
- Name and description (from YAML frontmatter)
- Trigger phrases (from description and body)
- "Do NOT use" exclusions
- Cross-references to other skills
- Key topics and domains covered

If the script is not available or fails, do this manually:
1. Find all SKILL.md files in the library
2. Extract the name and description from each
3. Note any "Do NOT use for..." or "Use X instead" phrases
4. Note any references to sibling skills

### Phase 2: Overlap Detection

For each pair of skills, assess overlap across four dimensions:

#### 2a. Description Overlap
Compare skill descriptions for shared trigger language. Two skills whose descriptions would match the same user prompt are competing.

**Look for:**
- Shared keywords (e.g., both mention "testing", "deployment", "security")
- Overlapping trigger phrases (e.g., "run quality checks" could match both `quality-checks` and `evaluating-cdk-quality`)
- Vague descriptions that cast too wide a net

#### 2b. Content Overlap
Read the SKILL.md body of potentially overlapping skills. Look for:
- Identical or near-identical sections
- The same tools/commands recommended in both
- The same patterns or templates duplicated
- Conflicting advice on the same topic

#### 2c. Boundary Analysis
For each pair with detected overlap, determine if the boundary is:
- **Clear**: Each skill explicitly says when to use the other (e.g., "for unit tests use X, for integration tests use Y")
- **Implicit**: The skills cover different scopes but don't explicitly acknowledge each other
- **Confused**: A user prompt could reasonably trigger either skill with no clear winner

#### 2d. Cross-Reference Integrity
Check that:
- Skills referenced via relative paths (e.g., sibling skill directories) actually exist
- Referenced skills haven't been renamed or retired
- Cross-references are bidirectional where appropriate

### Phase 3: Report

Generate a structured report with findings organized by severity.

## Report Template

Use this exact structure:

```markdown
# Skill Overlap Analysis Report

**Library:** [path]
**Skills scanned:** [count]
**Date:** [date]

## Summary

| Severity | Count | Description |
|----------|-------|-------------|
| Critical | [N]   | Skills that actively compete for the same triggers |
| Warning  | [N]   | Partial overlap that could cause confusion |
| Info     | [N]   | Minor shared territory with clear boundaries |

## Critical: Triggering Competition

### [Skill A] vs [Skill B]
- **Overlap area:** [what they share]
- **Ambiguous prompts:** [example user prompts that could trigger either]
- **Recommendation:** [merge / split boundary / add exclusion / clarify descriptions]

## Warning: Partial Overlap

### [Skill A] vs [Skill B]
- **Shared content:** [what's duplicated]
- **Boundary status:** [clear / implicit / confused]
- **Recommendation:** [action]

## Info: Acknowledged Overlap

### [Skill A] vs [Skill B]
- **Shared territory:** [what]
- **Boundary mechanism:** [how they differentiate]

## Cross-Reference Issues

| Source Skill | Reference | Status |
|-------------|-----------|--------|
| [skill]     | [path]    | [OK / BROKEN / STALE] |

## Recommendations

1. [Prioritized action items]
```

### Phase 4: Targeted Analysis (Optional)

If the user asked about a specific skill (e.g., "does infra-cdk-quality overlap with anything?"), focus the analysis on that skill's relationships rather than doing an exhaustive all-pairs comparison.

For a single-skill check:
1. Read the target skill's SKILL.md fully
2. Identify its key topics, tools, and trigger phrases
3. Scan other skill descriptions for matches
4. Deep-read only the skills that look like potential overlaps
5. Report findings for just that skill

## Common Overlap Patterns

These are the patterns most frequently seen in skill libraries:

### Pattern 1: The Lifecycle Split Problem
Skills organized by lifecycle phase (plan → implement → test → deploy → monitor) often overlap at transitions. E.g., "implementing features" might include testing guidance that duplicates "writing unit tests."

**Fix:** Each phase skill should explicitly hand off to the next with "when done, use [next skill]" language, and avoid duplicating the next phase's content.

### Pattern 2: The Horizontal vs Vertical Conflict
A horizontal skill (e.g., "detecting anti-patterns") scans across all code, while vertical skills (e.g., "evaluating CDK quality") go deep in one domain. The horizontal skill may duplicate findings from the vertical one.

**Fix:** The horizontal skill should defer to vertical specialists for domains they cover, and focus on patterns the vertical skills don't address.

### Pattern 3: The Tool Overlap
Multiple skills recommend the same tool (e.g., Checkov, cdk-nag, pytest) with potentially different configurations or advice.

**Fix:** Designate one skill as the authority for each tool's configuration. Other skills can reference it but shouldn't duplicate setup instructions.

### Pattern 4: The Vague Description
A skill with a broad description (e.g., "improves code quality") competes with every specific quality skill. The description triggers on too many prompts.

**Fix:** Narrow the description to the skill's actual specialty. Add explicit "do NOT use for X" exclusions.

## Tips for Resolution

When recommending fixes for overlap:

1. **Prefer boundary clarification over merging.** Two focused skills with clear boundaries are usually better than one sprawling skill.

2. **Use "Do NOT use for..." exclusions.** These are cheap and effective. If skill A and skill B overlap, adding "Do NOT use for [B's domain]" to A's description immediately reduces triggering competition.

3. **Extract shared content to a reference file.** If two skills both need the same guidance (e.g., "how to run Checkov"), put it in one place and have both skills reference it.

4. **Check the description, not just the body.** Triggering is driven by the description field. Two skills can have totally different bodies but compete if their descriptions overlap.

5. **Test with ambiguous prompts.** The best way to verify a boundary is to write 3-4 prompts that sit on the boundary and check which skill triggers.
