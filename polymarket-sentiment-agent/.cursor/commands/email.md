---
description: Triage today's inbox — prioritized summary with reply drafting
---

Invoke the `email-triage` skill to scan the inbox and produce a prioritized triage.

1. Load the email-triage skill
2. Execute the full triage workflow
3. Present results in the standard three-tier format
4. Offer reply drafting for Tier 1 items

If the user provides an argument, filter accordingly:
- `$ARGUMENTS` = "work" → only work-domain emails
- `$ARGUMENTS` = "personal" → exclude work-domain emails
- No argument → full inbox triage
