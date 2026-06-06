---
name: email-triage
description: >
  This skill should be used when the user asks to "check email", "triage my inbox",
  "check my email", "morning email", "inbox summary", or invokes /email or /summary.
  Scans the inbox for recent emails, classifies by priority tier, and offers reply drafting.
---

# Email Triage Skill

## Overview

Scan Gmail for recent messages, classify them into three priority tiers, and offer to draft replies for urgent items.

## Step 0 — Load Context (optional)

If you use a family-assistant skill or maintain reference files with contact and alias data, load them here before scanning. This gives the triage engine context about who matters and which aliases map to which priority.

Example reference files (if available):

| File | What it provides |
|------|-----------------|
| `family-members.md` | Names, relationships, emails — always Tier 1 |
| `email-aliases.md` | Alias routing & default priority tiers |
| `household.md` | Schools, services — helps classify household emails |

> **Tip:** The [family-assistant-skill](https://github.com/ericporres/family-assistant-skill) template is a good companion for this plugin. It provides the contact and household context that makes triage smarter.

If you don't have reference files yet, the skill still works — it just classifies based on content and sender patterns instead of alias routing.

## Step 1 — Scan Inbox

Use Gmail MCP tools to search:

```
Query: in:inbox newer_than:1d
```

Add exclusions for any labels you handle separately (e.g., `-label:AI` if you have an AI newsletter digest).

**Why not `is:unread`:** Many people casually browse emails on their phone without intending to act on them. Read status is unreliable as a triage signal. Use time-based windowing instead.

**Time window options:**
- Default: `newer_than:1d` (last 24 hours — good for daily morning triage)
- "Just today": `newer_than:12h`
- "Catch me up" or "this week": `newer_than:3d`

**Snippet-first approach:** The search results include subjects, senders, and snippets. Classify from these first. Only call `read_gmail_message` for:
- All Tier 1 emails (need full context for reply drafting)
- Ambiguous Tier 2 emails where the snippet isn't enough to classify

This avoids token blowout on high-volume days.

## Step 2 — Classify into Tiers

### Tier 1 — Reply Needed

Emails with a direct question, request, or action aimed at you. Each gets:
- One-line summary of what the sender needs
- Suggested action: Reply / Schedule / Forward to [person]

**Urgency signals (auto-promote to Tier 1):**
- From family members or emergency contacts
- From your work domain (e.g., `@yourcompany.com`)
- Time-sensitive language: "by EOD", "deadline", "RSVP", "urgent", "asap", "tomorrow", "today"
- Replies in threads you started
- Financial: bills, invoices, payment due, bank alerts, fraud alerts
- School emails: any school-related domains your kids attend
- Medical: doctor's office, appointment confirmations, prescription alerts

### Tier 2 — Review / Decide

Needs your eyes but not necessarily a reply:
- Order/shipping confirmations
- Calendar invites
- Shared documents
- Travel itinerary changes
- Receipts and transaction confirmations
- Newsletters you actively read

### Tier 3 — Noise

Marketing, bulk newsletters, automated notifications, social media alerts, promotional offers. Summarize as counts by category.

### Alias-aware routing (customize this section)

If you use email aliases (e.g., `shopping@yourdomain.com`, `travel@yourdomain.com`), map them to default tiers here. This is the most powerful part of the triage — a well-configured alias map means most emails get classified instantly without needing to read content.

Example alias routing:

```
Primary (you@domain.com)          → Evaluate on content
Family/kids aliases                → Default Tier 1
Financial aliases (bank@, 401k@)   → Default Tier 1
Health/medical aliases             → Default Tier 1
Household/utilities aliases        → Default Tier 2
Travel aliases                     → Default Tier 2
Shopping aliases                   → Default Tier 3 (unless delivery update → Tier 2, fraud → Tier 1)
Subscription/media aliases         → Default Tier 3
```

> **Tip:** If you use the family-assistant-skill's `email-aliases.md`, you can list 100+ aliases with per-alias tier routing. The triage skill reads it at runtime and applies the mapping automatically.

When an alias isn't recognized, fall back to content-based classification.

## Step 3 — Present Results

Format output as:

```markdown
# Inbox Triage — [Today's Date]
[X emails scanned from last 24h]

## Reply Needed (X)

1. **[Sender Name]** — [Subject]
   [One-line summary of what they need]
   → Suggested: [Reply / Schedule / Forward to X]

2. ...

## Review (X)

- **[Sender]** — [Subject] — [One-line summary]
- ...

## Noise (X)
[X] marketing, [X] social, [X] automated, [X] promotional
→ Want me to archive these?
```

**Numbering matters.** Tier 1 items are numbered so you can say "draft a reply to #3."

## Step 4 — Reply Drafting (conversational)

When asked to draft a reply (e.g., "draft a reply to #3"):

1. Read the full message with `read_gmail_message` if not already loaded
2. Read the full thread with `read_gmail_thread` for conversation context
3. Draft a reply matching the user's voice (see guidelines below)
4. Present the draft for review
5. **Never auto-send.** Always require explicit confirmation before sending.

### Email voice guidelines (customize these)

Describe how you write emails so Claude can match your style:

```
- Direct and concise — no filler
- Warm but professional
- Uses first names
- Signs off with "[Your Name]" or "Best, [Your Name]"
- Doesn't over-explain or over-apologize
```

## Step 5 — Archive Offer

If there are Tier 3 (noise) emails and the user confirms archival:
- List the specific emails that will be archived
- Require explicit confirmation
- Archive only after confirmation
- Report what was archived

**Never auto-archive. Never permanently delete.**

## Edge Cases

- **Empty inbox:** "Nothing new in the last 24 hours — inbox is clean."
- **All noise:** Skip to Tier 3 summary, note no action items.
- **Very high volume (50+):** Warn the user, offer to scan in batches or filter by alias/sender.
- **Thread context:** For Tier 1 thread replies, read the full thread to understand context before suggesting a response.

## What This Skill Does NOT Do

- Does not maintain its own contact list (optionally reads from family-assistant or similar)
- Does not save output to files (ephemeral conversation view)
- Does not send emails without explicit confirmation
- Does not modify labels or filters
- Does not permanently delete anything
