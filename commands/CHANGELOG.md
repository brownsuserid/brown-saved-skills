# Changelog

All notable changes to AI SDLC will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## January 2026

### New Features

#### Infrastructure CDK Quality Skill
New skill for evaluating AWS CDK code quality. Identifies common issues before they cause deployment failures.

- **Cross-Stack Dependency Detection**: Finds circular references and deployment deadlocks between stacks
- **Security Scanning Integration**: Runs cdk-nag, Checkov, and cfn-lint with remediation guidance
- **Multi-Customer Deployment Scripts**: Includes production-ready deploy.sh patterns with AWS profile switching, stage name computation, and post-deployment validation
- **Best Practices Review**: Stack organization, IAM permissions, naming conventions, and construct patterns

**When to use:** "Review the CDK code for quality issues" or "Create a deploy.sh script"

#### Windows Support
Added Windows batch script (`setup.bat`) for Windows users who can't run bash scripts:
- Full feature parity with the bash setup script
- Uses file copies instead of symlinks (Windows symlinks require admin privileges)
- Supports all installation options: `--all`, `--claude`, `--status`, `--uninstall`

### Improvements

#### Enhanced AWS Secrets Utility
Added `--profile-override` option to `pull-env` for cases where the customer name differs from the AWS profile name.

#### Better PR Workflow
Updated PR creation workflow to analyze ALL commits on a branch (not just the most recent), ensuring PR descriptions capture the complete scope of work.

#### Documentation Updates
- README now documents Windows setup and the new infra-cdk-quality skill
- Clarified Antigravity file copying behavior (doesn't follow symlinks for security)
- Updated tool configuration table with accurate locations

---

## December 2025

### New Features

#### Automated Quality Checks with Claude Code Hooks
Your code quality checks now run automatically in the background. No more remembering to run formatters or linters - they happen after every edit.

- **Stop Hook**: After each Claude Code turn, automatically runs formatting (ruff), linting, type checking (mypy), and unit tests
- **Per-File Hooks**: Instant linting and formatting on every file save
- **Sample Configuration**: Ready-to-use `claude-settings.sample.json` included

#### Ralph Wiggum Plugin
Added Anthropic's official autonomous development loop technique. Claude can now iterate on complex tasks automatically until completion conditions are met.

#### Comprehensive Slash Commands
Added a full suite of slash commands for common workflows:

**Workflow Commands:**
- `/fix-bug` - Bug fix workflow with root cause analysis and TDD
- `/plan-feature` - Feature planning with architectural review
- `/quality-check` - Run integration tests, security scan, and user validation
- `/test` - Run all quality checks
- `/troubleshoot-01` and `/troubleshoot-02` - Two-phase troubleshooting

**Roadmap Commands:**
- `/roadmap-plan-01` - Create detailed implementation plans
- `/roadmap-plan-02-architect` - Architectural review of plans
- `/roadmap-plan-03-tests` - Generate test scenarios from plans
- `/roadmap-execute` - Execute plans with TDD

**Git Commands:**
- `/commit`, `/commit-only`, `/commit_push_pr` - Various commit workflows

#### Universal Multi-Tool Setup
Configure AI SDLC skills across all your AI coding assistants with a single command. Supports Claude Code, Cursor, Gemini CLI, and Antigravity with automatic tool detection.

#### AWS Secrets Manager Integration
New `pull-env` utility for pulling secrets from AWS Secrets Manager:
- Auto-discovers secrets by customer or application name
- Interactive selection mode
- Automatic JSON secret expansion into environment variables

#### Global Utility Scripts
All scripts now accessible from any project directory via `./setup-ai-sdlc.sh --utilities`.

### Improvements

#### Streamlined Quality Workflows
All skills and commands updated to leverage Stop hook automation:
- **Removed redundant checks**: No more manual formatting, linting, type checking, or unit test commands
- **Focus on what matters**: Workflows now only require integration tests, security scanning (bandit), and user validation
- **Clearer documentation**: Updated README with hooks documentation and commands table

#### Better Developer Experience
- **Simplified worktree workflow**: Updated docs to reference `wt` command
- **Cleaner repo structure**: Reorganized utility scripts into `scripts/` directory
- **Improved setup script**: Now handles hook installation, plugin setup, and comprehensive symlink creation

---

**Summary:** December 2025 was a major productivity release. Automated quality checks eliminate repetitive manual steps, new slash commands provide consistent workflows, and multi-tool support makes AI SDLC work across your entire toolkit.
