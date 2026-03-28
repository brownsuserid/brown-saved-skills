---
name: documenting
description: Creates and updates project documentation — README files, docstrings, API docs, usage examples, and architecture documentation. Use this skill whenever code is undocumented, documentation is outdated, or new features need explanation. Triggers for requests like "add docs", "write a README", "document this module", "add docstrings", "write API docs", "this code needs documentation", "make this easier to understand for new developers", "create onboarding docs", "generate API reference", "update the README", "add usage examples", "document the public API", "write migration guide", or "our docs are out of date". Also use when asked to review documentation quality, check for missing docstrings, or prepare documentation before a release, deployment, or going to production.
---

# Documenting Skill

Every function is an agent tool. Every docstring is a tool definition. Write all documentation as if an AI agent with zero prior context will use it to decide how to call your code correctly on the first try. This is the default — not a special mode. Agents read docstrings the way humans read APIs: they need concrete examples, explicit constraints, return structures, and error recovery guidance. Documentation that works for agents works better for humans too.

## Process Overview

Use the TodoWrite tool to track progress through these phases:

---

## Phase 0: Understand the Project

Before documenting anything, understand what you're documenting and who it's for. Documentation written without this context tends to be generic and unhelpful.

### Assess the Project

- **Purpose**: What does this project do? Read existing README, package metadata, or ask the user.
- **Audience**: Who reads these docs? Always include AI agents — they are the primary consumer. Also consider: end users, developers integrating with an API, internal team members.
- **Language & conventions**: What language(s) is the project in? Use the appropriate docstring convention (Google-style for Python, JSDoc/TSDoc for TypeScript, GoDoc for Go, etc.).
- **Existing doc tooling**: Is there Sphinx, MkDocs, Storybook, TypeDoc, or similar already configured? Work with it rather than creating parallel documentation.

### Prioritize by Audience Impact

Documentation that agents and users see first matters most:
1. Public API docstrings — the tool definitions agents use to call your code. This is the highest priority
2. README — first impression for human users and agents discovering the project
3. Usage examples — reduces support questions and shows agents correct calling patterns
4. Architecture docs — helps new team members and agents understand system boundaries

---

## Phase 1: Identify Documentation Needs

Determine what documentation is missing or outdated.

### Check for Missing README

```bash
ls -la README.md
```

**README is essential** - it's the first thing users see.

### Find Undocumented Functions (Missing Tool Definitions)

```bash
# Find Python functions without docstrings — these are tools with no definition
rg "^\s*def\s+\w+\([^)]*\):" --type py -A 1 | rg -v '"""' | rg "def " -B 1
```

**Priority:**
- Public functions without docstrings — CRITICAL: agents cannot use tools without definitions
- Complex functions without docstrings (HIGH)
- Private functions without docstrings (MEDIUM)

### Find Undocumented Classes

```bash
rg "^\s*class\s+\w+" --type py -A 1 | rg -v '"""' | rg "class " -B 1
```

### Prioritize Findings

Focus on high-impact gaps first: missing README, undocumented public APIs, broken examples. Architecture docs and private function docstrings come after the public-facing documentation is solid.

Check `docs/architecture/` for existing Mermaid diagrams — see `../dev-shared-references/architecture-diagrams.md` for standards.

---

## Phase 2: Write Tool Definitions (Docstrings)

Every docstring is a tool definition. An agent reading this docstring must be able to call the function correctly without reading the implementation. Use the convention identified in Phase 0 (Google-style for Python, JSDoc/TSDoc for TypeScript, etc.).

### Required Elements for Every Docstring

These are not optional. Every public function docstring MUST include:

1. **Concrete example values for every parameter** — not just types. `rate: Discount as decimal between 0.0 and 1.0 (e.g., 0.2 for 20% off)` not `rate: The discount rate`
2. **Explicit constraints** — min/max values, valid ranges, required formats, what happens at boundaries
3. **Return structure** — for dicts/complex types, list every key and its meaning. For lists, describe the element structure
4. **Error recovery guidance** — not just what raises, but what the caller should do about it. `ValueError: If rate > 1.0. Pass as decimal, not percentage (0.05 not 5)`
5. **Use/don't-use hints** — when this function is the right choice vs. a similar one

### Docstring Format

**Google-style template (tool definition):**

```python
def function_name(param1: type1, param2: type2) -> return_type:
    """Brief one-line summary stating what this tool does (< 80 chars).

    What this function does, when to use it, and when NOT to use it.

    Args:
        param1: What this is + constraint + example value
                (e.g., "user_123". Must be non-empty string)
        param2: What this is + valid range + example
                (between 0.0 and 1.0, where 0.2 means 20%. Default: 0.0)

    Returns:
        Description of return value. For complex types, list structure:
        - key1: Description of field
        - key2: Description of field

    Raises:
        ExceptionType: When this occurs. Recovery: [what to do]

    Examples:
        >>> function_name(value1, value2)
        expected_result

    Note:
        Important caveats or warnings.
    """
    # implementation
```

### Write Tool Definitions

For each undocumented function:

1. Read implementation — understand the full contract (inputs, outputs, side effects, edge cases)
2. Write docstring as a tool definition — an agent must be able to call this correctly from the docstring alone
3. Include concrete example values for EVERY parameter — no exceptions
4. Document return structure completely — every dict key, every list element type
5. Add error recovery guidance to every Raises entry
6. Run doctests to verify examples produce correct results: `python -m doctest module.py`

**Complete examples:** See `references/docstring-examples.md`

---

## Phase 3: Create/Update README

Ensure the project has a comprehensive README. The README is the first thing users see — it shapes their entire perception of the project.

For README structure, templates, and best practices, see `references/documentation-standards.md`.

### Key Principles

- Start with what the project does and why it matters, not installation steps
- Include a Quick Start with a minimal working example
- Keep examples realistic but concise — link to full docs for depth
- Broken examples erode trust in the entire doc set. Always verify examples run successfully before committing

---

## Phase 4: Generate API Documentation (Tool Catalog)

Create comprehensive API reference documentation — this is the tool catalog that agents and developers use to discover and use your code.

For API documentation formats and examples, see `references/documentation-standards.md` and `references/docstring-examples.md`.

### Approach

- Document modules with a summary of what tools they provide and a usage example
- Document classes with their purpose, attributes, and construction examples — classes are tool collections
- Focus on the public interface — internal implementation details belong in code comments, not docstrings
- For each function: what it does, when to use it vs alternatives, complete input/output contract

---

## Phase 5: Create Usage Examples (Tool Calling Patterns)

Provide practical examples showing how to call each tool correctly. Good examples show agents and developers the exact calling pattern, expected inputs, and expected outputs.

### Identify What to Cover

- What are the most common tool calling patterns?
- What parameter combinations are confusing without examples?
- What error scenarios should callers know how to handle?
- What's the correct sequence when tools must be called in order?

### Write and Test Examples

For usage example structure and patterns, see `references/docstring-examples.md`.

Every example must be tested and working. Run examples before committing — a broken example teaches users the wrong thing and wastes their time debugging documentation instead of their own code.

---

## Phase 6: Validate Documentation

Ensure documentation is accurate, complete, and helpful.

### Validation Checklist

**Tool Definition Quality (primary — every docstring must pass):**
- [ ] Every parameter has a concrete example value (not just a type description)
- [ ] Every parameter has explicit constraints (ranges, formats, valid values, required vs optional)
- [ ] Return structures fully documented (every dict key, every list element type)
- [ ] Every Raises entry includes recovery guidance (what to do, not just what went wrong)
- [ ] Docstring alone is sufficient to call the function correctly without reading the implementation

**Completeness:**
- [ ] README exists
- [ ] All public functions have tool definitions (docstrings)
- [ ] All public classes have tool definitions (docstrings)
- [ ] Examples for common calling patterns
- [ ] Configuration documented

**Accuracy:**
- [ ] Signatures match docstrings
- [ ] Doctests pass: `python -m doctest module.py` (MUST run this, not just check manually)
- [ ] Parameters accurate
- [ ] Returns accurate
- [ ] Exceptions correct

**Quality:**
- [ ] Google style docstrings
- [ ] Realistic examples with real-world values
- [ ] Clear language
- [ ] WHY explained — when to use vs. not use

### Test Examples

```bash
# Run all examples
python -m doctest module.py
```

### Check Links

```bash
# Find markdown links
rg "\[.*\]\(.*\)" --type md
```

**Complete validation guide:** See `references/documentation-standards.md`

---

## Phase 7: Create Commit and PR

Follow the standard git workflow in `../dev-shared-references/git-and-pr-workflow.md`.

Use the `docs:` prefix for commit messages. Summarize what was documented (README, docstrings, examples, API reference) and note that examples were tested.

---

## Supporting Files Reference

This skill includes comprehensive reference materials:

### Documentation Specific
- `references/documentation-standards.md` - Complete guide for READMEs, API docs, architecture docs
- `references/docstring-examples.md` - Google-style docstring examples for functions, classes, modules

### Implementation Standards (Shared across all dev-* skills)
- `../dev-shared-references/coding-standards.md` - Python best practices, Google-style docstrings
- `../dev-shared-references/git-conventions.md` - Commit message format and workflow
- `../dev-shared-references/architecture-diagrams.md` - Mermaid diagram standards and templates

---

## Key Principles

- **Every function is a tool:** Docstrings are tool definitions. An agent with zero context must be able to call the function correctly from the docstring alone. This is the default assumption, not a special case
- **Concrete over abstract:** `rate: Discount as decimal between 0.0 and 1.0 (e.g., 0.2 for 20% off)` beats `rate: The discount rate`. Every parameter gets an example value, every constraint gets stated explicitly
- **Accuracy first:** Documentation that contradicts the code is worse than no documentation — it actively misleads agents and humans alike
- **Verify with doctests:** Always run `python -m doctest module.py` — never skip this. Broken examples cause agents to generate incorrect calling patterns
- **Complete return contracts:** For dicts, list every key. For lists, describe element structure. For complex types, document the full shape. Agents can't inspect return values at definition time
- **Error recovery, not just error names:** `ValueError: If rate > 1.0` is incomplete. `ValueError: If rate > 1.0. Pass as decimal, not percentage (0.05 not 5)` tells the agent how to fix it
- **Keep updated:** Documentation should be updated in the same PR as code changes
