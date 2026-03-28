#!/usr/bin/env bash
set -euo pipefail

# Refresh gog OAuth tokens for all accounts, one at a time.
# Guides the user through each browser-based re-auth flow.

ACCOUNTS=$(gog auth list --json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for a in data.get('accounts', []):
    print(a['email'])
")

TOTAL=$(echo "$ACCOUNTS" | wc -l | tr -d ' ')
CURRENT=0

echo ""
echo "============================================"
echo "  gog Token Refresh (${TOTAL} accounts)"
echo "============================================"
echo ""
echo "Your OAuth tokens expire every 7 days."
echo "This will open a browser window for each account."
echo "IMPORTANT: Make sure you sign in with the correct"
echo "Google account each time — check the account shown below."
echo ""

for EMAIL in $ACCOUNTS; do
    CURRENT=$((CURRENT + 1))
    echo "--------------------------------------------"
    echo "  Account ${CURRENT} of ${TOTAL}"
    echo ""
    echo "  >>> ${EMAIL} <<<"
    echo ""
    echo "  A browser window will open."
    echo "  Sign in with: ${EMAIL}"
    echo "--------------------------------------------"
    echo ""

    gog auth add "$EMAIL" --services user --force-consent

    echo ""
    echo "  Done: ${EMAIL}"
    echo ""
done

echo "============================================"
echo "  All ${TOTAL} accounts refreshed!"
echo "============================================"
echo ""
