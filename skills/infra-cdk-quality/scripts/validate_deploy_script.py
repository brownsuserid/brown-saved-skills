#!/usr/bin/env python3
"""Validate deploy scripts for best practices compliance.

This script validates that deploy scripts follow best practices:
- Has proper shebang line
- Includes help text and usage examples
- Has environment validation
- Has AWS profile handling
- Has pre-flight validation
- Has secrets management (.env -> Secrets Manager)
- Has CDK deploy command
- Has proper error handling
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


class DeployScriptValidator:
    """Validate deploy script structure and content."""

    def __init__(self, script_path: Path):
        """Initialize validator.

        Args:
            script_path: Path to deploy script
        """
        self.script_path = script_path
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.content: str = ""

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """Run all validations.

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self._check_file_exists()

        if self.script_path.exists():
            with open(self.script_path, "r", encoding="utf-8") as f:
                self.content = f.read()

            self._check_shebang()
            self._check_help_text()
            self._check_environment_validation()
            self._check_aws_profile_handling()
            self._check_preflight_validation()
            self._check_secrets_management()
            self._check_cdk_deploy()
            self._check_error_handling()
            self._check_user_feedback()

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings

    def _check_file_exists(self) -> None:
        """Check that deploy script file exists."""
        if not self.script_path.exists():
            self.errors.append(f"❌ Deploy script not found at {self.script_path}")

    def _check_shebang(self) -> None:
        """Check for proper shebang line."""
        if not self.content.startswith("#!/"):
            self.errors.append("❌ Missing shebang line. Add #!/bin/bash or #!/usr/bin/env bash")
            return

        first_line = self.content.split("\n")[0]
        if "bash" in first_line:
            print(f"✓ Shebang: {first_line}")
        elif "sh" in first_line:
            self.warnings.append(
                f"⚠️  Shebang uses sh ({first_line}). Consider using bash for more features."
            )
        else:
            self.warnings.append(f"⚠️  Non-standard shebang: {first_line}")

    def _check_help_text(self) -> None:
        """Check for help text and usage information."""
        help_patterns = [
            r"-h\|--help",
            r"--help\)",
            r"show_help",
            r"usage\(\)",
            r"Usage:",
            r"USAGE:",
        ]

        has_help_flag = any(
            re.search(pattern, self.content, re.IGNORECASE) for pattern in help_patterns
        )

        if not has_help_flag:
            self.errors.append(
                "❌ Missing help flag (-h|--help). Deploy scripts should include usage information."
            )
        else:
            print("✓ Help text/usage present")

        # Check for examples in help
        if "example" in self.content.lower() or "Example:" in self.content:
            print("✓ Examples included in help")
        else:
            self.warnings.append(
                "⚠️  No examples found in help text. Add examples to improve usability."
            )

    def _check_environment_validation(self) -> None:
        """Check for environment validation."""
        env_patterns = [
            r"-e\|--environment",
            r"--environment\)",
            r"ENVIRONMENT=",
            r"\$ENVIRONMENT",
            r"dev\|prod\|staging",
            r"validate.*environment",
        ]

        has_env_handling = any(
            re.search(pattern, self.content, re.IGNORECASE) for pattern in env_patterns
        )

        if not has_env_handling:
            self.warnings.append(
                "⚠️  No environment validation found. Consider adding "
                "-e|--environment flag for multi-environment support."
            )
        else:
            print("✓ Environment validation present")

        # Check for environment-specific validation
        if "dev" in self.content and "prod" in self.content:
            print("✓ Multiple environments supported (dev/prod)")
        else:
            self.warnings.append("⚠️  Consider supporting multiple environments (dev/prod/staging).")

    def _check_aws_profile_handling(self) -> None:
        """Check for AWS profile management."""
        profile_patterns = [
            r"AWS_PROFILE",
            r"aws.*profile",
            r"set_aws_profile",
            r"--profile",
            r"aws sts get-caller-identity",
        ]

        has_profile_handling = any(
            re.search(pattern, self.content, re.IGNORECASE) for pattern in profile_patterns
        )

        if not has_profile_handling:
            self.errors.append(
                "❌ No AWS profile handling found. Deploy scripts should manage "
                "AWS_PROFILE for multi-account deployments."
            )
        else:
            print("✓ AWS profile handling present")

        # Check for credential verification
        if "get-caller-identity" in self.content:
            print("✓ AWS credential verification present")
        else:
            self.warnings.append(
                "⚠️  No credential verification found. Consider using "
                "'aws sts get-caller-identity' to verify credentials."
            )

    def _check_preflight_validation(self) -> None:
        """Check for pre-flight validation section."""
        preflight_patterns = [
            r"pre.?flight",
            r"validate_config",
            r"check_dependencies",
            r"validate_prerequisites",
            r"# Validation",
            r"# Pre-deployment",
        ]

        has_preflight = any(
            re.search(pattern, self.content, re.IGNORECASE) for pattern in preflight_patterns
        )

        if not has_preflight:
            self.warnings.append(
                "⚠️  No pre-flight validation section found. Consider adding "
                "configuration and dependency checks before deployment."
            )
        else:
            print("✓ Pre-flight validation present")

        # Check for specific validations
        validations = {
            "file existence check": r"test -f|-e\s+\$|if \[ -f",
            "required variable check": r'\[ -z "\$|test -z|if \[ -n',
            "command availability": r"command -v|which|type ",
        }

        found_validations = []
        for name, pattern in validations.items():
            if re.search(pattern, self.content):
                found_validations.append(name)

        if found_validations:
            print(f"✓ Validations found: {', '.join(found_validations)}")

    def _check_secrets_management(self) -> None:
        """Check for secrets management (pushing .env secrets to Secrets Manager)."""
        secrets_patterns = [
            r"secretsmanager",
            r"setup.?secrets",
            r"push.?secrets",
            r"Secrets Manager",
            r"Secrets Management",
        ]

        has_secrets_handling = any(
            re.search(pattern, self.content, re.IGNORECASE) for pattern in secrets_patterns
        )

        if not has_secrets_handling:
            self.warnings.append(
                "⚠️  No secrets management found. Deploy scripts should push "
                "credentials from .env files to AWS Secrets Manager before CDK deploy. "
                "See Phase 6 in the deploy skill."
            )
        else:
            print("✓ Secrets management present (Secrets Manager integration)")

        # Check for .env file loading
        env_file_patterns = [
            r"\.env\.\$",
            r"\.env\.\{",
            r"source.*\.env",
            r"env_file",
            r"CUSTOMER_ENV_FILE",
        ]

        has_env_loading = any(re.search(pattern, self.content) for pattern in env_file_patterns)

        if has_env_loading:
            print("✓ Customer .env file loading present")
        else:
            self.warnings.append(
                "⚠️  No .env file loading pattern found. Deploy scripts should "
                "load customer-specific .env files for credentials."
            )

    def _check_cdk_deploy(self) -> None:
        """Check for CDK deploy command."""
        cdk_patterns = [
            r"cdk deploy",
            r"npx cdk deploy",
            r"CDK_DEPLOY",
        ]

        has_cdk_deploy = any(
            re.search(pattern, self.content, re.IGNORECASE) for pattern in cdk_patterns
        )

        if not has_cdk_deploy:
            self.errors.append(
                "❌ No CDK deploy command found. Deploy scripts should include "
                "'cdk deploy' or 'npx cdk deploy'."
            )
        else:
            print("✓ CDK deploy command present")

        # Check for context flags
        if "-c " in self.content or "--context" in self.content:
            print("✓ CDK context flags present")
        else:
            self.warnings.append(
                "⚠️  No CDK context flags found. Consider using -c flags "
                "to pass environment-specific configuration."
            )

        # Check for stack filtering
        if "--stack" in self.content or "-s " in self.content:
            print("✓ Stack filtering option present")

    def _check_error_handling(self) -> None:
        """Check for proper error handling."""
        error_patterns = [
            r"set -e",
            r"exit 1",
            r"trap.*ERR",
            r"trap.*EXIT",
            r"\|\| exit",
            r"\|\| \{",
        ]

        has_error_handling = any(re.search(pattern, self.content) for pattern in error_patterns)

        if not has_error_handling:
            self.errors.append(
                "❌ No error handling found. Add 'set -e' or explicit error checking with 'exit 1'."
            )
        else:
            print("✓ Error handling present")

        # Check for set -e at the beginning
        if "set -e" in self.content:
            # Check if it's near the top (within first 50 lines)
            lines = self.content.split("\n")[:50]
            if any("set -e" in line for line in lines):
                print("✓ 'set -e' found near script start")
            else:
                self.warnings.append(
                    "⚠️  'set -e' found but not near script start. Consider moving it earlier."
                )

        # Check for trap cleanup
        if "trap" in self.content:
            print("✓ Trap handler present for cleanup")
        else:
            self.warnings.append("⚠️  No trap handler found. Consider adding cleanup on exit.")

    def _check_user_feedback(self) -> None:
        """Check for user feedback patterns."""
        # Check for emoji feedback
        emoji_patterns = ["✅", "❌", "⚠️", "💡", "🔧", "📋"]
        has_emoji = any(emoji in self.content for emoji in emoji_patterns)

        if has_emoji:
            print("✓ Emoji feedback present for visual scanning")
        else:
            self.warnings.append(
                "⚠️  No emoji feedback found. Consider using emoji prefixes "
                "(✅ ❌ ⚠️ ) for better visual feedback."
            )

        # Check for progress indicators
        progress_patterns = [
            r"echo.*deploying",
            r"echo.*starting",
            r"echo.*complete",
            r"echo.*finished",
            r"echo.*success",
        ]

        has_progress = any(
            re.search(pattern, self.content, re.IGNORECASE) for pattern in progress_patterns
        )

        if has_progress:
            print("✓ Progress indicators present")
        else:
            self.warnings.append(
                "⚠️  Limited progress indicators. Add echo statements to show deployment progress."
            )


def validate_deploy_script(script_path: str) -> int:
    """Validate a deploy script.

    Args:
        script_path: Path to the deploy script

    Returns:
        Exit code (0 = success, 1 = validation failed)
    """
    path = Path(script_path)

    if not path.exists():
        print(f"❌ Error: Deploy script not found: {path}")
        return 1

    print(f"\n🔍 Validating deploy script: {path.name}")
    print(f"   Path: {path}\n")

    validator = DeployScriptValidator(path)
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
        print("\n✅ Deploy script validation passed! No issues found.")
        return 0
    elif is_valid:
        print("\n✅ Deploy script validation passed (with warnings).")
        return 0
    else:
        print(f"\n❌ Deploy script validation failed with {len(errors)} error(s).")
        return 1


def validate_all_scripts(directory: str) -> int:
    """Validate all deploy scripts in a directory.

    Args:
        directory: Directory to search for deploy scripts

    Returns:
        Exit code (0 = all valid, 1 = some failed)
    """
    path = Path(directory)

    if not path.exists():
        print(f"❌ Directory not found: {path}")
        return 1

    # Find all deploy scripts
    scripts = list(path.glob("**/deploy*.sh"))

    if not scripts:
        print(f"No deploy scripts found in {path}")
        return 0

    print(f"\n🔍 Found {len(scripts)} deploy script(s) to validate\n")

    results = {}
    for script in sorted(scripts):
        validator = DeployScriptValidator(script)
        is_valid, errors, warnings = validator.validate()
        results[script] = (is_valid, errors, warnings)

    # Print summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    valid_count = sum(1 for is_valid, _, _ in results.values() if is_valid)
    invalid_count = len(results) - valid_count

    for script, (is_valid, errors, warnings) in sorted(results.items()):
        status = "✅" if is_valid else "❌"
        warning_indicator = f" (⚠️  {len(warnings)} warnings)" if warnings else ""
        print(f"{status} {script.name}{warning_indicator}")

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
        print("  python validate_deploy_script.py <script.sh>  # Validate single script")
        print("  python validate_deploy_script.py --all <dir>  # Validate all in directory")
        print("\nExamples:")
        print("  python validate_deploy_script.py deploy.sh")
        print("  python validate_deploy_script.py ./scripts/deploy.sh")
        print("  python validate_deploy_script.py --all ./projects/")
        return 1

    if sys.argv[1] == "--all":
        if len(sys.argv) < 3:
            print("❌ Error: --all requires a directory argument")
            return 1
        return validate_all_scripts(sys.argv[2])
    else:
        return validate_deploy_script(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
