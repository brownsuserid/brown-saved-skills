#!/bin/bash
#
# check-cdk-dependencies.sh
#
# Synthesizes CDK stacks and checks for cross-stack dependencies (exports/imports).
# Returns non-zero exit code if problematic exports are found.
#
# Usage:
#   ./scripts/check-cdk-dependencies.sh
#
# Environment variables:
#   CDK_CMD - Override the CDK command (default: auto-detect)
#             Examples: "npx cdk", "uv run cdk", "yarn cdk"
#
# Exit codes:
#   0 - No exports found (clean)
#   1 - Exports found (dependency issues)
#   2 - Synthesis failed
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "CDK Cross-Stack Dependency Checker"
echo "=========================================="
echo ""

# Auto-detect CDK command if not specified
if [ -z "$CDK_CMD" ]; then
    if [ -f "uv.lock" ] || [ -f "pyproject.toml" ] && grep -q "\[tool.uv\]" pyproject.toml 2>/dev/null; then
        CDK_CMD="uv run cdk"
        echo "Detected: Python project with uv"
    elif [ -f "poetry.lock" ]; then
        CDK_CMD="poetry run cdk"
        echo "Detected: Python project with poetry"
    elif [ -f "package-lock.json" ]; then
        CDK_CMD="npx cdk"
        echo "Detected: TypeScript/JavaScript project with npm"
    elif [ -f "yarn.lock" ]; then
        CDK_CMD="yarn cdk"
        echo "Detected: TypeScript/JavaScript project with yarn"
    elif [ -f "pnpm-lock.yaml" ]; then
        CDK_CMD="pnpm cdk"
        echo "Detected: TypeScript/JavaScript project with pnpm"
    else
        CDK_CMD="npx cdk"
        echo "Defaulting to: npx cdk"
    fi
fi

echo "Using CDK command: $CDK_CMD"
echo ""

# Step 1: Synthesize all stacks
echo "Step 1: Synthesizing CDK stacks..."
echo "-----------------------------------"

if ! $CDK_CMD synth --all --quiet 2>&1; then
    echo -e "${RED}ERROR: CDK synthesis failed${NC}"
    exit 2
fi

echo -e "${GREEN}Synthesis complete${NC}"
echo ""

# Step 2: Check for exports
echo "Step 2: Scanning for CloudFormation exports..."
echo "-----------------------------------------------"

# Find all template files (including nested assemblies for CDK Stages)
TEMPLATES=$(find cdk.out -name "*.template.json" 2>/dev/null)

if [ -z "$TEMPLATES" ]; then
    echo -e "${YELLOW}WARNING: No templates found in cdk.out/${NC}"
    exit 0
fi

echo "Found templates:"
echo "$TEMPLATES" | while read -r template; do
    echo "  - $template"
done
echo ""

# Check for exports
EXPORTS_FOUND=0
EXPORT_DETAILS=""

for template in $TEMPLATES; do
    # Check for Export sections
    if grep -q '"Export"' "$template" 2>/dev/null; then
        EXPORTS_FOUND=1
        STACK_NAME=$(basename "$template" .template.json)
        EXPORT_NAMES=$(grep -o '"Export"[^}]*"Name"[^"]*"[^"]*"' "$template" 2>/dev/null | grep -o '"Name"[^"]*"[^"]*"' | cut -d'"' -f4 || echo "unknown")
        EXPORT_DETAILS="${EXPORT_DETAILS}\n  ${YELLOW}$STACK_NAME${NC}:"
        for name in $EXPORT_NAMES; do
            EXPORT_DETAILS="${EXPORT_DETAILS}\n    - $name"
        done
    fi
done

# Check for imports
IMPORTS_FOUND=0
IMPORT_DETAILS=""

for template in $TEMPLATES; do
    if grep -q 'Fn::ImportValue' "$template" 2>/dev/null; then
        IMPORTS_FOUND=1
        STACK_NAME=$(basename "$template" .template.json)
        IMPORT_NAMES=$(grep -o 'Fn::ImportValue[^}]*' "$template" 2>/dev/null | head -5 || echo "found")
        IMPORT_DETAILS="${IMPORT_DETAILS}\n  ${YELLOW}$STACK_NAME${NC}: Uses Fn::ImportValue"
    fi
done

echo ""
echo "Step 3: Results"
echo "---------------"

if [ $EXPORTS_FOUND -eq 1 ]; then
    echo -e "${RED}EXPORTS FOUND - Cross-stack dependencies detected!${NC}"
    echo -e "\nStacks with exports:$EXPORT_DETAILS"
    echo ""
fi

if [ $IMPORTS_FOUND -eq 1 ]; then
    echo -e "${RED}IMPORTS FOUND - Stacks consuming exports!${NC}"
    echo -e "\nStacks with imports:$IMPORT_DETAILS"
    echo ""
fi

if [ $EXPORTS_FOUND -eq 0 ] && [ $IMPORTS_FOUND -eq 0 ]; then
    echo -e "${GREEN}NO EXPORTS OR IMPORTS FOUND${NC}"
    echo "All stacks appear to be independent."
    echo ""
    exit 0
fi

# Provide remediation guidance
echo ""
echo "=========================================="
echo "Remediation Guidance"
echo "=========================================="
echo ""
echo "To fix cross-stack dependencies:"
echo ""
echo "1. Replace L2 constructs with plain strings in stack props"
echo "2. Use config files for known resource IDs"
echo "3. Use SSM Parameter Store for runtime lookups (not synthesis)"
echo "4. Use Secrets Manager for sensitive values"
echo ""
echo "See: references/cross-stack-dependencies.md for detailed patterns"
echo ""

exit 1
