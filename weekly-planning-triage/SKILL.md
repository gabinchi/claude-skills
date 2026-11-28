---
name: "weekly-planning-triage"
description: "Run José's weekly planning: build the weekly review note in Obsidian from Linear, Akiflow, Habitify and Gmail, then triage the tools after his reflection."
---

# Weekly planning and triage

The session has two halves with a focus block between them. Half 1 builds the note. José reflects in the note with only Obsidian open. Half 2 triages the tools from what he wrote.

## Where things live

- Vault (general): `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/general`. Reach it through the desktop app's device tools. If the folder isn't connected, ask for access to it.
- Prompts: `2 🔁 Areas/Playbook/Components/Playbook – Weekly.md`. This page is the single source of the prompts. Read it fresh every session and never keep a copy of the prompts in this skill.
- 12-week direction: `2 🔁 Areas/Playbook/Components/Playbook – 12-Week.md`. If no current guiding sentence is set, write "Not set".
- Output: `Weekly/Weekly Review - YYYY-MM-DD.md` at the vault's top level, dated the day of the session. Create the `Weekly` folder if it's missing.

## Half 1: build the note

1. **Ask whether Linear and Habitify are updated.** Ask José whether he has marked what finished as Done in Linear and checked off the week's habits in Habitify. Wait for a clear yes on both before reading either tool. The "Done" and "Habitify week" prompts depend on them. If the Habitify connector has no summary or statistics tool, then ask him to paste a snapshot of Habitify's week summary.
2. **Gather the inputs:**
   - **Linear:** KPI line with points done vs. committed, open points, and days left in the cycle. Group open work by theme, one line per theme with its issue count and points. Don't list every issue: link to the cycle in Linear instead. Projects: only PARA projects (code starting with W), grouped by area (initiative). Leave out projects completed or canceled more than two weeks ago.
   - **Akiflow:** the schedule for the next 7–10 days, which holds the events from every calendar connected to Akiflow, plus the inbox and this week's recurring tasks. Fixed points are the busy events on his own calendars. List events from view-only calendars separately, as information only. Use Akiflow for the calendar, not Google Calendar. KPI line: free hours next week after the fixed points, as a starting estimate for Capacity. Also list one-off tasks left overdue from this week.
   - **Habitify:** the week's summary, from the connector if it offers one, otherwise from his snapshot. KPI line: overall completion % against his 70% target. List every habit, ranked weakest to strongest, each with its completion %.
   - **Gmail:** two inboxes, kept as separate lists. Threads from the past week that still need a reply or a decision. Treat expert-network solicitations as non-urgent. KPI line for each inbox: count of threads needing action and how long the oldest has waited.
     - gabinchi@gmail.com: read it through the Gmail connector.
     - jose@cintro.co: the connector can't reach it. Give José the prompt below to run in Gemini in Gmail, signed in as jose@cintro.co, and wait for him to paste the answer. Don't write the note until it arrives.

       ```
       Review my inbox for emails received in the past 7 days.

       List only threads where I still owe a reply or a decision. For each one, give:
       - sender and subject
       - date received
       - what I need to do, in one line

       Put solicitations from expert networks (GLG, Third Bridge, AlphaSights and similar) in a separate "Non-urgent" list.

       Then list newsletters, notifications and receipts I can archive, as one line each.

       Start with one line giving the number of threads that need action and how many days the oldest one has waited. Keep it short, with no commentary.
       ```
   - Readwise (Reader and highlights) and the Zettelkasten Inbox are out of scope. They belong to the Zettelkasten session.
3. **Write the note:**
   - Top: a **Summary** section with one short block per source. Each block opens with its KPI line. No commentary, no advice.
   - Below it: every prompt from the Weekly page, in the page's order and with its section headings. Leave an empty answer line under each one. Skip the page's pre-flight and closing lines.
4. **Hand off.** Give the note's path in one line and say the focus block can start. Then stop and wait.

## Half 2: triage

Start when José comes back and says the reflection is done.

1. Read the note again, including his answers.
2. Propose the changes one item at a time, one question per reply. Never send the whole list at once. Work tool by tool, in this order:
   - **Linear:** first check that the open points in the cycle fit the capacity he wrote for what is left of the cycle, and say plainly if they don't. Then the committed issues to move to Selected, kept within that capacity. Everything else in the cycle goes back to Backlog. Project statuses follow his continue/pause/cancel answers.
   - **Akiflow:** each inbox item gets scheduled, made recurring, or moved to Linear. Akiflow holds recurring tasks only. One-off work goes to Linear, filed under the area's project. Search Linear for an existing issue before creating one.
   - **Gmail:** what needs a reply this week, and what can be archived. Archive gabinchi@gmail.com threads through the connector. For jose@cintro.co, list what to archive and José archives it himself.
3. Apply a group only after José approves it. Never send an email.
4. Close with a short list of what changed in each tool.

## Rules

- Areas are shared across tools: Fraud Practice, Writing, Career, Career Education, Engagement, My Protocols, Health, Wellness, Family, Home, Admin, Leisure. Akiflow also keeps a Work project.
- Linear status flow: Backlog → Selected → Todo / In Progress / Review → Done.
- Keep replies short, and ask one question at a time.