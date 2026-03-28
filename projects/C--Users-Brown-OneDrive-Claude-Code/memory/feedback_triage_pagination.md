---
name: Triage must paginate all inbox results
description: During inbox triage, always paginate through ALL results from all 4 inbox labels to avoid missing older emails
type: feedback
---

During inbox triage, always paginate through ALL search results for each of the 4 inbox labels (INBOX, Check-Brown, Urgent-Brown, Read-Brown). The initial search may return a nextPageToken indicating more results exist. Follow ALL pagination tokens to get the complete inbox.

**Why:** In the March 25, 2026 triage session, several emails were missed because the initial INBOX search returned 50 results with a nextPageToken, but pagination was not followed. This caused emails from Mar 17-22 to be skipped entirely, including active replies from Jeremy Jordan (Lillian Project), Sonia Vohnout, Andrew (Secret Sauce Society), and a significant business decision email from Daniel Lee about AI Verde.

**How to apply:**
1. When any gmail_search returns a nextPageToken, ALWAYS make follow-up calls with that token until all results are retrieved.
2. After deduplication, verify coverage by checking the date range. If the oldest email is recent (e.g., only going back 2 days), there are likely more results to fetch.
3. Cross-reference: after building the thread list from INBOX, check if Urgent-Brown or Check-Brown contain threads NOT already in the INBOX list. These may point to older items that fell off the first page.
