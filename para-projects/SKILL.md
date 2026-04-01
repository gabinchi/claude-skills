---
name: para-projects
description: "Manage PARA-method projects with synced folders and Todoist integration. Only invoke this skill when explicitly called with /para-projects."
---

# PARA Project Manager

Manages a registry of projects using the PARA method, with synchronized folders in iCloud Drive, Google Drive, and Todoist.

## Scripts

Two helper scripts live in `scripts/`:

- **`setup.py`** — first-run only. Creates the registry directory, initializes `config.json` with correct PARA paths, and resolves Todoist parent project IDs.
- **`registry.py`** — registry CRUD CLI. All operations use this script instead of reading/writing `registry.json` directly.
- **`todoist.py`** — Todoist API CLI. Handles project creation, rename, task deletion, and archiving.
- **`notion.py`** — Notion API CLI. Handles page creation, updates, archiving, and unarchiving across separate work/home accounts.

## Setup

Before first use:
1. Read `config.json` from `~/.../iCloud Drive/.project-registry/`
2. If missing, run `python3 scripts/setup.py` from the skill directory
3. Verify `TODOIST_API_TOKEN`, `NOTION_API_KEY_WORK`, and `NOTION_API_KEY_HOME` env vars are set

If `todoist.parent_projects.work.id` or `.home.id` are empty, fetch all projects from `GET /rest/v2/projects`, filter by name (`💼 Work`, `🏡 Home`), write the IDs back to `config.json`, and confirm with the user.

If `notion.work.database_id` or `notion.home.database_id` are empty, ask the user to provide them. Each database must belong to the corresponding Notion account and must have the integration connected (Settings → Connections in Notion).

### Config Location

```
~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/
├── config.json
└── registry.json
```

### Config Structure

```json
{
  "default_context": "work",
  "icloud_projects_path": "~/Library/Mobile Documents/com~apple~CloudDocs/1 🎯 Projects",
  "icloud_archive_path": "~/Library/Mobile Documents/com~apple~CloudDocs/4 🗃️ Archive/Projects",
  "gdrive_projects_path": "~/Library/CloudStorage/GoogleDrive-you@gmail.com/My Drive/1 🎯 Projects",
  "gdrive_archive_path": "~/Library/CloudStorage/GoogleDrive-you@gmail.com/My Drive/4 🗃️ Archive/Projects",
  "todoist": {
    "parent_projects": {
      "work": { "name": "💼 Work", "id": "" },
      "home": { "name": "🏡 Home", "id": "" }
    }
  },
  "notion": {
    "work": { "database_id": "", "api_key_env": "NOTION_API_KEY_WORK" },
    "home": { "database_id": "", "api_key_env": "NOTION_API_KEY_HOME" }
  }
}
```

The archive paths must point to the `Projects/` subfolder inside `4 🗃️ Archive/`, matching what Setup Folder Structure creates.

Work and home use separate Notion accounts and API keys. Set `NOTION_API_KEY_WORK` and `NOTION_API_KEY_HOME` as environment variables. Each `database_id` must belong to the respective account's workspace.

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
    "todoist_project_id": "2349876123",
    "notion_page_id": "abc123def456"
  }
]
```

Valid statuses: `Not Started` (default), `In Progress`, `Done`

`closed_at` is an optional ISO 8601 timestamp, set when the project is closed. `todoist_project_id` and `notion_page_id` may be `null` if sync failed — use Sync Project to Todoist (Op 10) or Sync Project to Notion (Op 11) to recover.

---

## Operations

### 1. Create Project

**Trigger:** "create a project", "new project", "add project"

**Inputs:** name (required), description (required), context: home | work (optional — fall back to `default_context`)

**Steps:**
1. Determine prefix (`W` = work, `H` = home); get next ID: `python3 scripts/registry.py next-id W`
2. Get kebab folder name: `python3 scripts/registry.py kebab "{name}"` → `{id}-{kebab}` (e.g. `W00004-nelo-merchant-risk-model`)
3. Create folders at `{icloud_projects_path}/{folder_name}` and `{gdrive_projects_path}/{folder_name}`
4. `python3 scripts/todoist.py create-project --context {context} --id {id} --name "{name}"` — captures `todoist_project_id` and Todoist URL from output
5. `python3 scripts/notion.py create-page --context {context} --id {id} --name "{name}" --description "{desc}" --status "Not Started" --todoist-url {todoist_url} --icloud-path "{icloud_projects_path}/{folder_name}" --gdrive-path "{gdrive_projects_path}/{folder_name}"` — captures `notion_page_id` and Notion URL from output
6. `python3 scripts/registry.py add --id {id} --name "{name}" --description "{desc}" --todoist-id {todoist_project_id} --notion-id {notion_page_id}` — errors if name is a duplicate
7. Confirm to user: show ID, folder paths, Todoist link, and Notion URL

---

### 2. Rename Project

**Trigger:** "rename project", "change project name"

**Inputs:** project ID or current name, new name

**Steps:**
1. Find project: `python3 scripts/registry.py find "{id_or_name}"` — captures current name, id, todoist_project_id
2. Build old and new folder names using `registry.py kebab`
3. Rename iCloud folder; if that succeeds, rename Google Drive folder; if Google Drive fails, rename iCloud folder back and abort
4. `python3 scripts/todoist.py update-project {todoist_project_id} --name "{id}-{new_name}"`; if it fails, warn but do not roll back — folders and registry are source of truth
5. `python3 scripts/notion.py update-page {notion_page_id} --context {context} --name "{new_name}" --id {id}`; if it fails, warn but do not roll back
6. `python3 scripts/registry.py update "{id}" --name "{new_name}"` — errors if new name is a duplicate
7. Confirm changes to user

---

### 3. Update Project Status

**Trigger:** "update status", "mark project as", "project status"

**Inputs:** project ID or name, new status (`Not Started`, `In Progress`, or `Done`)

**Steps:**
1. Find project: `python3 scripts/registry.py find "{id_or_name}"`
2. `python3 scripts/notion.py update-page {notion_page_id} --context {context} --status "{status}"`; if it fails, warn but continue
3. `python3 scripts/registry.py update "{id}" --status "{status}"`
4. Confirm to user

---

### 4. List Projects

**Trigger:** "list projects", "show projects", "my projects"

**Options:** filter by context (home/work), filter by status, sort by created_at (default), status, or id. By default excludes `Done` projects; pass `--include-done` if user asks.

Run: `python3 scripts/registry.py list [--context work|home] [--status "..."] [--sort ...] [--include-done]`

Output is a table. Use `--json` if you need structured data.

---

### 5. Show Project Detail

**Trigger:** "show project {id}", "project details", "describe project"

Run: `python3 scripts/registry.py find "{id_or_name}"` and display all fields, plus derived folder paths and Todoist link (`https://app.todoist.com/app/project/{todoist_project_id}`).

---

### 6. Close Project

**Trigger:** "close project", "archive project", "finish project", "complete project"

**Inputs:** project ID or name

**Steps:**
1. Find project: `python3 scripts/registry.py find "{id_or_name}"`
2. `python3 scripts/todoist.py get-tasks {todoist_project_id}` — count the results for the confirmation message
3. Ask for written confirmation:
   > You are about to close project **{id} — {name}**. This will:
   > - Move its folders to the archive in iCloud and Google Drive
   > - Delete **{N} incomplete task(s)** in Todoist and archive the project
   >
   > Type **CLOSE {id}** to confirm.

   Do not proceed until the user responds with exactly `CLOSE {id}` (case-insensitive). Re-prompt once on mismatch, then cancel.

4. Create `{icloud_archive_path}` and `{gdrive_archive_path}` if they don't exist
5. Move iCloud project folder to `{icloud_archive_path}/{folder_name}`; if that succeeds, move Google Drive folder; if Google Drive fails, move iCloud folder back and abort
6. `python3 scripts/todoist.py delete-incomplete-tasks {todoist_project_id}`
7. `python3 scripts/todoist.py archive-project {todoist_project_id}`
8. `python3 scripts/notion.py archive-page {notion_page_id} --context {context}`
9. `python3 scripts/registry.py update "{id}" --status "Done" --closed-at now`
10. Confirm to user: folders moved, Todoist archived, Notion archived, registry updated

---

### 7. Restore Project

**Trigger:** "restore project", "unarchive project", "reopen project"

**Inputs:** project ID or name (searches `Done` projects in registry)

**Steps:**
1. Find project: `python3 scripts/registry.py find "{id_or_name}"` — confirm it has status `Done`
2. Ask for confirmation:
   > Restore **{id} — {name}**? This will move its folders back to Projects and create a new Todoist project.
   > Reply **yes** to confirm.
3. Move iCloud folder from `{icloud_archive_path}/{folder_name}` back to `{icloud_projects_path}/{folder_name}`; if that succeeds, move Google Drive folder; if Google Drive fails, move iCloud folder back and abort
4. `python3 scripts/todoist.py create-project --context {context} --id {id} --name "{name}"` — captures new `todoist_project_id`
5. `python3 scripts/notion.py unarchive-page {notion_page_id} --context {context}`
6. `python3 scripts/registry.py update "{id}" --status "In Progress" --clear-closed-at --todoist-id {todoist_project_id}`
7. Confirm to user: folders restored, Todoist project created, Notion page restored

---

### 8. Move Project

**Trigger:** "move project to work", "move project to home", "change project context"

**Inputs:** project ID or name, target context (home | work)

**Steps:**
1. Find project: `python3 scripts/registry.py find "{id_or_name}"` — if already in target context, inform user and stop
2. Get new ID: `python3 scripts/registry.py next-id {target_prefix}`
3. Confirm:
   > Moving **{old_id} — {name}** to **{context}** will assign it a new ID (**{new_id}**). The old ID will no longer exist.
   > Reply **yes** to confirm.
4. Build old and new folder names using `registry.py kebab`
5. Rename iCloud folder (old → new); if succeeds, rename Google Drive folder; if Google Drive fails, rename iCloud back and abort
6. `python3 scripts/todoist.py update-project {todoist_project_id} --name "{new_id}-{name}"`; also update parent via Todoist REST API if needed
7. Since work and home use separate Notion accounts, the page cannot be moved cross-account:
   - `python3 scripts/notion.py create-page --context {target_context} --id {new_id} --name "{name}" --description "{desc}" --status "{status}" --todoist-url {todoist_url} --icloud-path "{new_icloud_path}" --gdrive-path "{new_gdrive_path}"` — captures new `notion_page_id`
   - `python3 scripts/notion.py archive-page {old_notion_page_id} --context {old_context}`
8. `python3 scripts/registry.py update "{old_id}" --new-id {new_id} --notion-id {notion_page_id}`
9. Confirm to user with old and new IDs and new Notion URL

---

### 9. Search Projects

**Trigger:** "search projects", "find project", "look for project"

**Inputs:** keyword (searches name and description)

**Steps:**
1. `python3 scripts/registry.py search "{keyword}"`
2. Output includes a Match column showing whether the hit was in name or description

---

### 10. Sync Project to Todoist

**Trigger:** "sync project to todoist", "fix todoist sync", "retry todoist"

**Inputs:** project ID or name

**Steps:**
1. Find project: `python3 scripts/registry.py find "{id_or_name}"` — if `todoist_project_id` is already set, inform user and stop
2. `python3 scripts/todoist.py create-project --context {context} --id {id} --name "{name}"` — captures `todoist_project_id`
3. `python3 scripts/registry.py update "{id}" --todoist-id {todoist_project_id}`
4. Confirm to user with Todoist link

---

### 11. Sync Project to Notion

**Trigger:** "sync project to notion", "fix notion sync", "retry notion"

**Inputs:** project ID or name

**Steps:**
1. Find project: `python3 scripts/registry.py find "{id_or_name}"` — if `notion_page_id` is already set, inform user and stop
2. `python3 scripts/notion.py create-page --context {context} --id {id} --name "{name}" --description "{desc}" --status "{status}" --todoist-url {todoist_url} --icloud-path "{icloud_path}" --gdrive-path "{gdrive_path}"` — captures `notion_page_id`
3. `python3 scripts/registry.py update "{id}" --notion-id {notion_page_id}`
4. Confirm to user with Notion URL

---

### 12. Sync Status Check

**Trigger:** "sync status", "check sync", "show unsynced projects"

**Steps:**
1. `python3 scripts/registry.py list --json` — filter results where `todoist_project_id` is null or `notion_page_id` is null
2. If none, confirm everything is in sync
3. If any found, display them grouped by what's missing (Todoist / Notion / both) and offer to sync them now — if yes, run Op 10 and/or Op 11 for each as needed

---

### 13. Setup Folder Structure

**Trigger:** "setup folder structure", "initialize folders", "setup PARA folders", "create PARA structure"

**Steps:**
1. Ask the user:
   > Which parent folders would you like to build the PARA directory structure in? Please list the full paths, one per line.

   Do not ask about Todoist.

2. For each provided path, create:
   ```
   0 📥 Inbox/
   1 🎯 Projects/
   2 🔁 Areas/
   3 🧰 Resources/
   4 🗃️ Archive/
   └── Projects/
   ```

3. Confirm to user with the structure created per parent folder. Remind user to update `icloud_projects_path`, `icloud_archive_path`, `gdrive_projects_path`, and `gdrive_archive_path` in `config.json` to point to the new folders if they haven't already.

---

## Error Handling

- **Folder already exists:** Warn user, skip folder creation, continue with other steps
- **Todoist API failure on Create:** Complete folder/registry/Notion steps, store `todoist_project_id: null`, flag sync as incomplete, instruct user to run `/para-projects sync project {id} to todoist`
- **Notion API failure on Create:** Complete folder/registry/Todoist steps, store `notion_page_id: null`, flag sync as incomplete, instruct user to run `/para-projects sync project {id} to notion`
- **Todoist or Notion API failure on Rename/Status Update/Close:** Warn user, do not roll back folder/registry changes — instruct user to update manually
- **Notion — database not connected:** If API returns 403, remind user to share the database with the integration in Notion (Settings → Connections)
- **Partial folder failure on Rename/Close/Restore/Move:** Roll back the succeeded folder operation before aborting (see individual ops for details)
- **Registry file missing:** Initialize with `[]`
- **Config missing:** Prompt user to run `python3 scripts/setup.py`
- **Duplicate project name:** Warn user, ask for confirmation before proceeding
- **Close — Todoist archive failure:** Warn user; instruct to archive manually at `https://app.todoist.com/app/project/{todoist_project_id}`
- **Close — confirmation mismatch:** Re-prompt once, then cancel
- **Restore — archived folder not found:** Warn user, ask them to locate the folder manually and confirm its path before continuing

---

## Folder Name Convention

Pattern: `{id}-{kebab-case-name}` — lowercase, spaces to hyphens, strip special characters except hyphens

Example: "Fraud Adjudication Agent" → `W00001-fraud-adjudication-agent`