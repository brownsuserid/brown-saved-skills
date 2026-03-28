#!/bin/bash
# Unified Inbox Review - Airtable + Gmail + Beeper

set -e

echo "=== UNIFIED INBOX REVIEW ==="
echo ""

# Source env
source ~/.zshrc 2>/dev/null

echo "📊 1. AIRTABLE INBOX:"
python3 ~/.openclaw/skills/managing-projects/scripts/airtable-inbox-review/gather_inbox.py 2>&1
echo ""

echo "📧 2. GMAIL INBOX:"
python3 ~/.openclaw/skills/managing-projects/scripts/airtable-inbox-review/gather_emails.py --max 50 --since 3d 2>&1 | python3 -c "
import sys,json
d=json.load(sys.stdin)
for acct,emails in d.get('accounts',{}).items():
    if emails:
        print(f'  {acct}: {len(emails)} emails')
        for e in emails:
            print(f\"    - {e.get('subject','')[:50]}\")
    else:
        print(f'  {acct}: 0 emails')
"
echo ""

echo "💬 3. BEEPER INBOX:"
python3 ~/.openclaw/skills/managing-projects/scripts/airtable-inbox-review/gather_beeper.py --limit 30 2>&1
echo ""

echo "=== INBOX REVIEW COMPLETE ==="
echo "Next: Run routing-airtable-tasks skill for any items found above"
