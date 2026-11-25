---
name: para-projects
description: Creates and manages PARA-method projects with synchronized Obsidian notes, Google Drive folders, and Linear projects. Use when the user wants to create, list, search, rename, close, restore, or move projects, or set up PARA project folders.
---

# PARA Project Manager

Manages a registry of projects using the PARA method, with synchronized Obsidian notes, Google Drive folders, and Linear projects.

> **Invocation:** This skill must be called explicitly with `/para-projects`. It will not trigger automatically.

Akiflow is **not** written to by this skill. Akiflow imports Linear **issues** from projects you select under Settings → Integrations → Linear → Filter by Project. A newly created Linear project is not added to that filter automatically, and this skill does not create Linear issues.

## Dependencies

All scripts use Python 3 stdlib only (`argparse`, `json`, `os`, `pathlib`, `re`, `shutil`, `tempfile`, `urllib`). No external packages required. The project uses `uv` for environment management — run `uv sync` once after install to set up the dev environment (pytest).

## Scripts

Helper scripts live in `scripts/`:

- **`setup.py`** — first-run / upgrade. Creates the registry directory, merges Obsidian + Linear keys into `config.json`, resolves Linear team and project-status IDs. Does **not** rewrite `registry.json`.
- **`registry.py`** — registry CRUD CLI. All operations use this script instead of reading/writing `registry.json` directly.
- **`obsidian.py`** — Obsidian vault CLI. Creates/renames/updates/archives project folders and notes.
- **`linear.py`** — Linear GraphQL CLI. Creates and updates Linear projects (name, description, status, team).

Google Drive folder create/rename/move is done with plain filesystem commands in the skill steps (no Drive API script).

## Setup

Before first use:
1. Read `config.json` from `~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/`
2. If missing or missing Linear/Obsidian keys, run `python3 scripts/setup.py` from the skill directory
3. Verify `LINEAR_API_KEY` env var is set

If `linear.teams.work.id` or `.home.id` are empty and there are multiple Linear teams, setup prints the team list — set the IDs in `config.json` and re-run setup.

If `linear.statuses` entries are empty, re-run setup with a valid API key.

### Config Location

```
~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/
├── config.json
└── registry.json
```

### Config Structure

```json
{
  "default_context": "home",
  "obsidian_vault_path": "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/projects",
  "obsidian_archive_path": "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/projects/Archive",
  "gdrive_projects_path": "~/Library/CloudStorage/GoogleDrive-you@gmail.com/My Drive/1 🎯 Projects",
  "gdrive_archive_path": "~/Library/CloudStorage/GoogleDrive-you@gmail.com/My Drive/4 🗃️ Archive/Projects",
  "linear": {
    "api_key_env": "LINEAR_API_KEY",
    "teams": {
      "work": { "id": "", "name": "" },
      "home": { "id": "", "name": "" }
    },
    "statuses": {
      "Not Started": "",
      "In Progress": "",
      "Done": ""
    }
  }
}
```

Obsolete keys (`icloud_*`, `todoist`, `notion`) may remain in an upgraded config; ignore them.

---

## Registry Schema

`registry.json` is an array of project objects:

```json
[
  {
    "id": "W00001",
    "name": "Fraud Adjudication Agent",
    "description": "PydanticAI-based fraud case adjudication system for Nelo",
    "status": "In Progress",
    "created_at": "2026-04-01T10:00:00Z",
    "updated_at": "2026-04-01T10:00:00Z",
    "closed_at": null,
    "linear_project_id": "abc-uuid",
    "linear_url": "https://linear.app/team/project/..."
  }
]
```

Valid statuses: `Not Started` (default), `In Progress`, `Done`

`closed_at` is an optional ISO 8601 timestamp, set when the project is closed. `linear_project_id` / `linear_url` may be `null` if sync failed — use Sync Project to Linear (Op 10) to recover. Legacy records may still have `todoist_project_id` / `notion_page_id`; treat missing Linear fields as null.

---

## Operations

### 1. Create Project

**Intent:** "create a project", "new project", "add project"

**Inputs:** name (required), description (required), context: home | work (optional — fall back to `default_context`)

**Steps:**
1. `uv run scripts/registry.py check-name "{name}"` — abort immediately if name is already taken, before any external calls
2. Determine prefix (`W` = work, `H` = home); get next ID: `uv run scripts/registry.py next-id W`
3. Get sanitized name: `uv run scripts/registry.py folder-name "{name}"` → then folder name is `{id} - {sanitized}`
4. `uv run scripts/obsidian.py create --id {id} --name "{name}" --description "{desc}" --context {context}` — captures vault path
5. Create Google Drive folder at `{gdrive_projects_path}/{id} - {sanitized}`. If it already exists, warn and continue. If creation fails after Obsidian succeeded, warn and continue (Drive can be created later).
6. `uv run scripts/linear.py create-project --context {context} --id {id} --name "{name}" --description "{desc}" --status "Not Started"` — captures `linear_project_id` and URL. On failure: keep folders, store `linear_project_id: null`, instruct user to sync later.
7. If Linear succeeded: `uv run scripts/obsidian.py update --id {id} --name "{name}" --linear-id {linear_project_id} --linear-url "{linear_url}"`
8. `uv run scripts/registry.py add --id {id} --name "{name}" --description "{desc}" --linear-id {linear_project_id} --linear-url "{linear_url}"`
9. Confirm to user: show ID, Obsidian path, Google Drive path, Linear URL. Remind: add this Linear project to Akiflow's Linear import filter (Settings → Integrations → Linear → Filter by Project) if you want its issues in Akiflow. This skill does not create Linear issues.

**Example output:**
> ✅ Project created: **W00004 - Nelo Merchant Risk Model**
> - Obsidian: `projects/W00004 - Nelo Merchant Risk Model/`
> - Google Drive: `1 🎯 Projects/W00004 - Nelo Merchant Risk Model/`
> - Linear: https://linear.app/...
>
> Reminder: Akiflow only imports issues from Linear projects in your import filter. Select this project in Akiflow if you want its issues there.

---

### 2. Rename Project

**Intent:** "rename project", "change project name"

**Inputs:** project ID or current name, new name

**Steps:**
1. `uv run scripts/registry.py check-name "{new_name}"` — abort immediately if name contains `/` or `:`, or is already taken
2. Find project: `uv run scripts/registry.py find "{id_or_name}"`
3. Build old and new folder names: `{id} - {sanitized}`
4. `uv run scripts/obsidian.py rename --id {id} --old-name "{old_name}" --new-name "{new_name}"`
5. Rename Google Drive folder; if Drive fails, rename Obsidian folder back and abort
6. If `linear_project_id` is set: `uv run scripts/linear.py update-project {linear_project_id} --name "{id} - {new_name}"`; if it fails, warn but do not roll back — folders and registry are source of truth
7. `uv run scripts/registry.py update "{id}" --name "{new_name}"`
8. Confirm changes to user

---

### 3. Update Project Status

**Intent:** "update status", "mark project as", "project status"

**Inputs:** project ID or name, new status (`Not Started`, `In Progress`, or `Done`)

**Steps:**
1. Find project: `uv run scripts/registry.py find "{id_or_name}"`
2. `uv run scripts/obsidian.py update --id {id} --name "{name}" --status "{status}"`; if it fails, warn but continue
3. If `linear_project_id` is set: `uv run scripts/linear.py update-project {linear_project_id} --status "{status}"`; if it fails, warn but continue
4. `uv run scripts/registry.py update "{id}" --status "{status}"`
5. Confirm to user

---

### 4. List Projects

**Intent:** "list projects", "show projects", "my projects"

**Options:** filter by context (home/work), filter by status, sort by created_at (default), status, or id. By default excludes `Done` projects; pass `--include-done` if user asks.

Run: `uv run scripts/registry.py list [--context work|home] [--status "..."] [--sort ...] [--include-done]`

Output is a table. Use `--json` if you need structured data.

---

### 5. Show Project Detail

**Intent:** "show project {id}", "project details", "describe project"

Run: `uv run scripts/registry.py find "{id_or_name}"` and display all fields, plus derived folder paths:
- Obsidian: `{obsidian_vault_path}/{id} - {sanitized}/` (or under Archive if Done)
- Google Drive: `{gdrive_projects_path}/{id} - {sanitized}/` (or archive path if Done)
- Linear: `{linear_url}` if set

---

### 6. Close Project

**Intent:** "close project", "archive project", "finish project", "complete project"

**Inputs:** project ID or name

**Steps:**
1. Find project: `uv run scripts/registry.py find "{id_or_name}"`
2. Ask for written confirmation:
   > You are about to close project **{id} — {name}**. This will:
   > - Move its Obsidian folder to Archive/
   > - Move its Google Drive folder to the Drive archive
   > - Mark the Linear project as Done (completed status) — issues are **not** deleted; the Linear project is **not** archived
   >
   > Type **CLOSE {id}** to confirm.

   Do not proceed until the user responds with exactly `CLOSE {id}` (case-insensitive). Re-prompt once on mismatch, then cancel.

3. Create `{obsidian_archive_path}` and `{gdrive_archive_path}` if they don't exist
4. `uv run scripts/obsidian.py archive --id {id} --name "{name}"`
5. Move Google Drive folder to `{gdrive_archive_path}/{folder_name}`; if Drive fails, restore Obsidian (`obsidian.py restore`) and abort
6. If `linear_project_id` is set: `uv run scripts/linear.py update-project {linear_project_id} --status "Done"`; if it fails, warn but do not roll back folders
7. `uv run scripts/registry.py update "{id}" --status "Done" --closed-at now`
8. Confirm to user

---

### 7. Restore Project

**Intent:** "restore project", "unarchive project", "reopen project"

**Inputs:** project ID or name (searches `Done` projects in registry)

**Steps:**
1. Find project: `uv run scripts/registry.py find "{id_or_name}"` — confirm it has status `Done`
2. Ask for confirmation:
   > Restore **{id} — {name}**? This will move its folders back to Projects and set Linear to In Progress.
   > Reply **yes** to confirm.
3. `uv run scripts/obsidian.py restore --id {id} --name "{name}"`
4. Move Google Drive folder from archive back to `{gdrive_projects_path}/{folder_name}`; if Drive fails, re-archive Obsidian and abort
5. If `linear_project_id` is set: `uv run scripts/linear.py update-project {linear_project_id} --status "In Progress"`; if it fails, warn but continue
6. `uv run scripts/registry.py update "{id}" --status "In Progress" --clear-closed-at`
7. Confirm to user

---

### 8. Move Project

**Intent:** "move project to work", "move project to home", "change project context"

**Inputs:** project ID or name, target context (home | work)

**Steps:**
1. Find project: `uv run scripts/registry.py find "{id_or_name}"` — if already in target context, inform user and stop
2. Get new ID: `uv run scripts/registry.py next-id {target_prefix}`
3. Confirm:
   > Moving **{old_id} — {name}** to **{context}** will assign it a new ID (**{new_id}**). The old ID will no longer exist.
   > Reply **yes** to confirm.
4. `uv run scripts/obsidian.py rename --id {old_id} --old-name "{name}" --new-name "{name}" --new-id {new_id}`
5. Rename Google Drive folder `{old_id} - {name}` → `{new_id} - {name}`; if Drive fails, roll Obsidian back with `obsidian.py rename --id {new_id} --old-name "{name}" --new-name "{name}" --new-id {old_id}` and abort
6. If `linear_project_id` is set: `uv run scripts/linear.py update-project {linear_project_id} --name "{new_id} - {name}" --context {new_context}`; if team change fails, warn and leave on current team (still try name update without `--context`)
7. `uv run scripts/registry.py update "{old_id}" --new-id {new_id}`
8. Confirm to user with old and new IDs and Linear URL

---

### 9. Search Projects

**Intent:** "search projects", "find project", "look for project"

**Inputs:** keyword (searches name and description)

**Steps:**
1. `uv run scripts/registry.py search "{keyword}"`
2. Output includes a Match column showing whether the hit was in name or description

---

### 10. Sync Project to Linear

**Intent:** "sync project to linear", "fix linear sync", "retry linear"

**Inputs:** project ID or name

**Steps:**
1. Find project: `uv run scripts/registry.py find "{id_or_name}"` — if `linear_project_id` is already set, inform user and stop
2. Ensure Obsidian note exists; if missing: `uv run scripts/obsidian.py create ...`
3. Ensure Google Drive folder exists; create if missing
4. `uv run scripts/linear.py create-project --context {context} --id {id} --name "{name}" --description "{desc}" --status "{status}"` — captures ids
5. `uv run scripts/obsidian.py update --id {id} --name "{name}" --linear-id {linear_project_id} --linear-url "{url}"`
6. `uv run scripts/registry.py update "{id}" --linear-id {linear_project_id} --linear-url "{url}"`
7. Confirm to user with Linear URL and Akiflow filter reminder

Do **not** offer to bulk-sync the entire existing registry. Only sync projects the user names.

---

### 11. Sync Status Check

**Intent:** "sync status", "check sync", "show unsynced projects"

**Steps:**
1. `uv run scripts/registry.py list --json --include-done` — filter results where `linear_project_id` is null/missing
2. If none, confirm everything is in sync
3. If any found, display them and ask which ones to sync — if the user names projects, run Op 10 for each named project only

---

### 12. Setup Folder Structure

**Intent:** "setup folder structure", "initialize folders", "setup PARA folders"

**Steps:**
1. Ensure `{obsidian_vault_path}` and `{obsidian_archive_path}` exist
2. Ensure `{gdrive_projects_path}` and `{gdrive_archive_path}` exist
3. Confirm paths to the user. Do not create Inbox / Areas / Resources trees. Do not ask for iCloud PARA paths.

---

## Script Error Handling

All scripts write errors as JSON to stderr: `{"error": "message"}`. When a script exits non-zero:
1. Read the `error` field and surface it directly to the user: _"The operation failed: {error}"_
2. Do not proceed to subsequent steps unless noted otherwise
3. Suggest the recovery action if one is defined below

## Error Handling

- **Folder already exists:** Warn user, skip folder creation, continue with other steps
- **Linear API failure on Create:** Complete Obsidian/Drive/registry steps, store `linear_project_id: null`, flag sync as incomplete, instruct user to run `/para-projects sync project {id} to linear`
- **Google Drive failure on Create:** Keep Obsidian note, warn, continue with Linear/registry
- **Linear API failure on Rename/Status/Close:** Warn user, do not roll back folder/registry changes — instruct user to update manually
- **Partial folder failure on Rename/Close/Restore/Move:** Roll back the succeeded Obsidian operation before aborting (see individual ops)
- **Registry file missing:** Initialize with `[]`
- **Config missing:** Prompt user to run `python3 scripts/setup.py`
- **Duplicate project name:** Warn user, abort
- **Close — confirmation mismatch:** Re-prompt once, then cancel
- **Restore — archived folder not found:** Warn user, ask them to locate the folder manually and confirm its path before continuing
- **Linear team move failure:** Warn; leave project on its current team; still update name if possible

---

## Folder Name Convention

Pattern: `{id} - {name}` — original casing preserved, only `/` and `:` stripped (illegal on macOS filesystems)

Example: "Fraud Adjudication Agent" → `W00001 - Fraud Adjudication Agent`
Example: "Q&A Research" → `W00002 - Q&A Research`

Project names containing `/` or `:` are rejected at creation time by `check-name`.

Obsidian note path: `{vault}/{id} - {name}/{id} - {name}.md`
