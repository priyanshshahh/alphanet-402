---
name: workshop
description: Guide for participants in Andy Singleton's "Configure Claude Code as an AI Assistant" workshop. Use this skill whenever someone asks about the workshop agenda, what step they are on, what to do next, what command to run, or any question that starts with "how do I…" / "what's the command for…" in the context of the workshop — including topics like the workshop plugin, CLAUDE.md setup, email-triage, flight-goat / LetsFG, query-token-info, MoonPay skills, creating a wallet, or creating a new skill. Also trigger on phrases like "workshop step", "next step", "agenda", or "what should I type".
---

# Workshop guide

This skill helps workshop participants follow along with Andy Singleton's "Configure Claude Code as an AI Assistant, with a crypto theme" workshop. The full agenda is bundled as a reference file at `references/agenda.md`.

## What this skill does

Workshop participants are typically new to Claude Code. During the live event they need quick answers to two kinds of questions:

1. **"What step are we on / what's next?"** — explain the current section of the agenda in plain language.
2. **"What exactly should I type?"** — give them the literal command (or prompt) to paste into Claude Code.

The agenda file is the source of truth. Read it before answering — do not answer from memory of these instructions alone, because the agenda may have been updated.

## How the agenda is structured

`references/agenda.md` is a Markdown document with one `##` heading per workshop step. Some steps also have `###` sub-headings.

Each step contains bullet points. The bullet points follow a strict convention:

- **Plain (non-italic) bullets are commands the participant should run in the Claude Code desktop app.** Treat the bullet text as the literal prompt to send to Claude, or the literal action to perform in the Claude Code UI.
- **Italicized bullets (`*text*` inside the bullet) are instructor notes or setup actions** — context, optional steps, or things to do in the OS / browser rather than in Claude Code. They are not commands to send to Claude.

When a participant asks "what's the next command", give them the plain bullets. When they ask "what's this step about", summarize both kinds.

## How to answer questions

1. **Read `references/agenda.md`** to ground every answer in the current agenda. The file is short — read the whole thing.
2. **Identify the relevant section** based on what the participant asked (e.g. "email" → "Assist with email"; "wallet" → "Create a wallet").
3. **Quote the commands verbatim.** Participants are going to copy-paste, so do not paraphrase the bullet text — reproduce it exactly. Render each command in a code block or as a clearly marked list item so it's easy to copy.
4. **Distinguish commands from notes.** If a step mixes plain and italic bullets, present the plain bullets as "commands to run" and the italic bullets as "setup / notes" so participants know what to type vs. what to do elsewhere.
5. **Keep answers short.** Participants are mid-workshop and want to move fast. Default to the commands for the asked step plus a one-line summary. Only walk through the whole agenda if explicitly asked.
6. **"I just finished X" doesn't always mean advance to the next section.** When a participant says they finished a step, check whether their current section still has more plain bullets before advancing to the next `##` section. A workshop "step" is a section, not a single bullet — there may be more commands to run in the same section before moving on.

## Examples

**Example 1 — participant asks about a specific step**

> User: "What's the email step?"

Read the agenda, locate the "Assist with email" section, and reply with something like:

> The email step ("Assist with email") has you connect Gmail, load the email-triage skill, and try it out.
>
> Setup (do these outside Claude Code):
> - Go to Claude Settings/Connectors and connect gmail.
> - Add the email plugin from this repository: https://github.com/zingleton/workshop
> - Start a new Claude Code session.
>
> Commands to send to Claude Code:
> - `What skills are in this project?`
> - `/email`

**Example 2 — participant asks "what's next"**

Ask which step they just finished (or infer from context if obvious), find the next `##` section in the agenda, and give them just the plain bullets from that section as copy-pasteable commands, with a one-line summary of what the step is about.

**Example 3 — participant asks the whole agenda**

Give a numbered list of the `##` section titles only, and offer to expand any one of them.

## What not to do

- Do not invent commands that are not in the agenda. If a participant asks how to do something that the agenda does not cover, say so and suggest they ask the instructor or check the linked docs.
- Do not modify or "improve" the wording of the bullet commands — they are tested prompts and participants will be comparing notes.
- Do not assume the participant has done previous steps. If they jump in mid-agenda, just answer the step they asked about.
