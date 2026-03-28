#!/usr/bin/env python3
"""Validate Claude Code skills for best practices compliance.

This script validates that skills follow best practices:
- SKILL.md exists and is ≤ 500 lines
- Proper frontmatter (name and description)
- Required sections present
- File references are valid
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


class SkillValidator:
    """Validate Claude Code skill structure and content."""

    def __init__(self, skill_path: Path, is_project_root: bool = False):
        """Initialize validator.

        Args:
            skill_path: Path to skill directory
            is_project_root: If True, skill is at project root (not under skills/)
        """
        self.skill_path = skill_path
        self.skill_md = skill_path / "SKILL.md"
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.is_project_root = is_project_root

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """Run all validations.

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self._check_skill_md_exists()

        if self.skill_md.exists():
            self._check_skill_md_length()
            self._check_frontmatter()
            self._check_required_sections()
            self._check_file_references()

        self._check_directory_structure(self.is_project_root)

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings

    def _check_skill_md_exists(self) -> None:
        """Check that SKILL.md file exists."""
        if not self.skill_md.exists():
            self.errors.append(f"❌ SKILL.md not found at {self.skill_md}")

    def _check_skill_md_length(self) -> None:
        """Check that SKILL.md is ≤ 500 lines."""
        with open(self.skill_md, "r", encoding="utf-8") as f:
            lines = f.readlines()
            line_count = len(lines)

        MAX_LINES = 500

        if line_count > MAX_LINES:
            self.errors.append(
                f"❌ SKILL.md is {line_count} lines (max: {MAX_LINES}). "
                f"Extract {line_count - MAX_LINES} lines to references/"
            )
        elif line_count > MAX_LINES * 0.9:  # Warning at 90%
            self.warnings.append(
                f"⚠️  SKILL.md is {line_count} lines (close to {MAX_LINES} limit)"
            )
        else:
            print(f"✓ SKILL.md length: {line_count} lines (within {MAX_LINES} limit)")

    def _check_frontmatter(self) -> None:
        """Check that frontmatter has required fields."""
        with open(self.skill_md, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for frontmatter
        if not content.startswith("---"):
            self.errors.append(
                "❌ SKILL.md missing frontmatter (should start with ---)"
            )
            return

        # Extract frontmatter
        match = re.match(r"---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            self.errors.append("❌ Invalid frontmatter format")
            return

        frontmatter = match.group(1)

        # Check for required fields
        if "name:" not in frontmatter:
            self.errors.append("❌ Frontmatter missing 'name' field")
        else:
            # Extract name
            name_match = re.search(r"name:\s*(.+)", frontmatter)
            if name_match:
                name = name_match.group(1).strip()
                # Check naming conventions
                if " " in name:
                    self.warnings.append(
                        f"⚠️  Skill name '{name}' contains spaces (use hyphens)"
                    )
                if name != name.lower():
                    self.warnings.append(f"⚠️  Skill name '{name}' not lowercase")
                if not name.endswith("ing") and name not in ["skills"]:
                    self.warnings.append(
                        f"⚠️  Skill name '{name}' should use gerund form (-ing)"
                    )
                print(f"✓ Skill name: {name}")

        if "description:" not in frontmatter:
            self.errors.append("❌ Frontmatter missing 'description' field")
        else:
            # Extract description
            desc_match = re.search(r"description:\s*(.+)", frontmatter)
            if desc_match:
                description = desc_match.group(1).strip()
                if len(description) < 50:
                    self.warnings.append(
                        f"⚠️  Description is short ({len(description)} chars). "
                        "Be more specific about WHEN to use."
                    )
                if len(description) > 250:
                    self.warnings.append(
                        f"⚠️  Description is long ({len(description)} chars). "
                        "Keep to 1-2 sentences."
                    )
                print(f"✓ Description: {len(description)} characters")

    def _check_required_sections(self) -> None:
        """Check that required sections are present."""
        with open(self.skill_md, "r", encoding="utf-8") as f:
            content = f.read()

        required_sections = [
            "# ",  # Title
            "## Process Overview",
            "## Phase",  # At least one phase
            "## Supporting Files Reference",
            "## Key Principles",
            "## Success Criteria",
        ]

        for section in required_sections:
            if section not in content:
                if section == "## Phase":
                    self.warnings.append(
                        "⚠️  No '## Phase' sections found. "
                        "Skills should use phase-based workflow."
                    )
                else:
                    self.warnings.append(f"⚠️  Missing section: {section}")

        # Check for TodoWrite mention
        if "TodoWrite" not in content:
            self.warnings.append(
                "⚠️  'TodoWrite' not mentioned. "
                "Skills should track progress with TodoWrite."
            )
        else:
            print("✓ TodoWrite integration mentioned")

    def _check_file_references(self) -> None:
        """Check that referenced files exist."""
        with open(self.skill_md, "r", encoding="utf-8") as f:
            content = f.read()

        # Find markdown links to local files
        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)

        for link_text, link_path in links:
            # Skip URLs
            if link_path.startswith(("http://", "https://", "#")):
                continue

            # Resolve relative paths
            referenced_file = self.skill_path / link_path
            if not referenced_file.exists():
                self.errors.append(
                    f"❌ Referenced file not found: {link_path} "
                    f"(mentioned as '{link_text}')"
                )

        # Find backtick references (e.g., `references/file.md`)
        backtick_refs = re.findall(r"`([^`]+\.md)`", content)

        for ref_path in backtick_refs:
            # Skip if it's a shared reference
            if ref_path.startswith("../"):
                continue

            referenced_file = self.skill_path / ref_path
            if not referenced_file.exists():
                self.warnings.append(f"⚠️  Referenced file may not exist: {ref_path}")

    def _check_directory_structure(self, is_project_root: bool = False) -> None:
        """Check directory structure follows conventions.

        Args:
            is_project_root: If True, skill is at project root (not under skills/)
        """
        has_references = (self.skill_path / "references").exists()
        has_templates = (self.skill_path / "templates").exists()

        if not has_references and not has_templates:
            self.warnings.append(
                "⚠️  No references/ or templates/ directories. "
                "Consider organizing supporting files."
            )

        # Check if skill is nested (should not be)
        # Project-level skills can be at root, user-level skills under skills/
        parent_name = self.skill_path.parent.name
        if not is_project_root and parent_name != "skills":
            self.errors.append(
                f"❌ Skill appears to be nested. "
                f"Skills must be directly under a skills/ directory, "
                f"not in {self.skill_path.parent}"
            )


def validate_skill(skill_name: str, base_path: Path = None) -> int:
    """Validate a skill by name.

    Args:
        skill_name: Name of skill to validate
        base_path: Base path to skills directory (defaults to ~/.claude/skills)

    Returns:
        Exit code (0 = success, 1 = validation failed)
    """
    if base_path is None:
        base_path = Path.home() / ".claude" / "skills"

    skill_path = base_path / skill_name

    if not skill_path.exists():
        print(f"❌ Error: Skill directory not found: {skill_path}")
        return 1

    print(f"\n🔍 Validating skill: {skill_name}")
    print(f"   Path: {skill_path}\n")

    # Detect if this is a project-level skill (not under skills/ directory)
    # Project-level skills are at the root of a repo (e.g., ./dev-notebooklm)
    is_project_root = base_path.name != "skills"

    validator = SkillValidator(skill_path, is_project_root=is_project_root)
    is_valid, errors, warnings = validator.validate()

    # Print results
    if errors:
        print("\n❌ ERRORS:")
        for error in errors:
            print(f"   {error}")

    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")

    if is_valid and not warnings:
        print("\n✅ Skill validation passed! No issues found.")
        return 0
    elif is_valid:
        print("\n✅ Skill validation passed (with warnings).")
        return 0
    else:
        print(f"\n❌ Skill validation failed with {len(errors)} error(s).")
        return 1


def validate_all_skills(base_path: Path = None) -> int:
    """Validate all skills in a skills directory.

    Args:
        base_path: Base path to skills directory (defaults to ~/.claude/skills)

    Returns:
        Exit code (0 = all valid, 1 = some failed)
    """
    if base_path is None:
        base_path = Path.home() / ".claude" / "skills"

    if not base_path.exists():
        print(f"❌ Skills directory not found: {base_path}")
        return 1

    # Find all skill directories (containing SKILL.md)
    skill_dirs = [
        d for d in base_path.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
    ]

    if not skill_dirs:
        print(f"No skills found in {base_path}")
        return 0

    print(f"\n🔍 Found {len(skill_dirs)} skills to validate in {base_path}\n")

    # Detect if this is a project-level skills directory (not under skills/)
    is_project_root = base_path.name != "skills"

    results = {}
    for skill_dir in sorted(skill_dirs):
        validator = SkillValidator(skill_dir, is_project_root=is_project_root)
        is_valid, errors, warnings = validator.validate()
        results[skill_dir.name] = (is_valid, errors, warnings)

    # Print summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    valid_count = sum(1 for is_valid, _, _ in results.values() if is_valid)
    invalid_count = len(results) - valid_count

    for skill_name, (is_valid, errors, warnings) in sorted(results.items()):
        status = "✅" if is_valid else "❌"
        warning_indicator = f" (⚠️  {len(warnings)} warnings)" if warnings else ""
        print(f"{status} {skill_name}{warning_indicator}")

        if errors:
            for error in errors:
                print(f"      {error}")

    print(f"\n✅ Valid: {valid_count}")
    if invalid_count > 0:
        print(f"❌ Invalid: {invalid_count}")

    return 0 if invalid_count == 0 else 1


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print(
            "  python validate_skill.py <skill-name>              # Validate single skill (user-level)"
        )
        print(
            "  python validate_skill.py <skill-name> --path <dir> # Validate single skill at custom path"
        )
        print(
            "  python validate_skill.py --all                     # Validate all user-level skills"
        )
        print(
            "  python validate_skill.py --all --path <dir>        # Validate all skills at custom path"
        )
        print("\nExamples:")
        print("  # User-level skill")
        print("  python validate_skill.py dev-fixing-bugs")
        print()
        print("  # Project-level skill")
        print("  python validate_skill.py my-skill --path .claude/skills")
        print()
        print("  # All user-level skills")
        print("  python validate_skill.py --all")
        print()
        print("  # All project-level skills")
        print("  python validate_skill.py --all --path .claude/skills")
        return 1

    # Parse arguments
    base_path = None
    if "--path" in sys.argv:
        path_idx = sys.argv.index("--path")
        if path_idx + 1 >= len(sys.argv):
            print("❌ Error: --path requires a directory argument")
            return 1
        base_path = Path(sys.argv[path_idx + 1])

    if sys.argv[1] == "--all":
        return validate_all_skills(base_path)
    else:
        skill_name = sys.argv[1]
        return validate_skill(skill_name, base_path)


if __name__ == "__main__":
    sys.exit(main())
