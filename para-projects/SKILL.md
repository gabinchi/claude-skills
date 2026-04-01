---
name: para-projects
description: "Manage PARA-method projects with synced folders and Todoist integration. Use this skill whenever the user wants to create, list, modify, or manage projects. Triggers on: 'create a project', 'new project', 'list projects', 'rename project', 'project status', 'update project', or any reference to PARA project management. Also triggers when the user mentions project IDs like H0001 or W0001."
---

# PARA Project Manager

Manages a registry of projects using the PARA method, with synchronized folders in iCloud Drive, Google Drive, and Todoist.

## Setup

Before first use, ensure configuration exists:

1. Read `config.json` from the skill directory (see Config section below)
2. If missing, copy `config.template.json` and prompt user to fill in values
3. Verify paths exist and Todoist token is set

### Config Location

The config and registry live at:
```
~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/
├── config.json
└── registry.json
```

### Config Structure

```json
{
  "default_context": "work",
  "icloud_projects_path": "~/Library/Mobile Documents/com~apple~CloudDocs/Projects",
  "gdrive_projects_path": "~/Library/CloudStorage/GoogleDrive-gabinchi@gmail.com/My Drive/Projects",
  "todoist": {
    "parent_projects": {
      "work": { "name": "💼 Work", "id": "" },
      "home": { "name": "🏡 Home", "id": "" }
    }
  }
}
```

The Todoist API token must be set as environment variable `TODOIST_API_TOKEN`.

### First-Run: Resolve Todoist Parent Project IDs

If `todoist.parent_projects.work.id` or `todoist.parent_projects.home.id` are empty:

```bash
curl -s -X GET "https://api.todoist.com/rest/v2/projects" \
  -H "Authorization: Bearer $TODOIST_API_TOKEN" | python3 -c "
import json, sys
projects = json.load(sys.stdin)
for p in projects:
    if p['name'] in ['💼 Work', '🏡 Home']:
        print(f\"{p['name']}: {p['id']}\")
"
```

Write the IDs back to `config.json` and confirm with the user.

---

## Registry Schema

`registry.json` is an array of project objects:

```json
[
  {
    "id": "W0001",
    "name": "Fraud Adjudication Agent",
    "description": "PydanticAI-based fraud case adjudication system for Nelo",
    "status": "In Progress",
    "created_at": "2026-04-01T10:00:00Z",
    "updated_at": "2026-04-01T10:00:00Z",
    "todoist_project_id": "2349876123"
  }
]
```

Valid statuses: `Not Started` (default), `In Progress`, `Done`

---

## Operations

### 1. Create Project

**Trigger:** "create a project", "new project", "add project"

**Inputs:**
- Project name (required)
- Description (required)
- Context: home | work (optional — use `default_context` from config if not specified)

**Steps:**

1. **Load registry** from `registry.json`
2. **Generate ID:**
   - Determine prefix: `W` for work, `H` for home
   - Find highest existing number for that prefix in registry
   - Increment by 1, zero-pad to 4 digits
   - Example: if highest W project is W0003, next is W0004
3. **Build folder name:** `{id}-{name}` (spaces replaced with hyphens, lowercase)
   - Example: `W0004-nelo-merchant-risk-model`
4. **Create iCloud folder:**
   ```bash
   mkdir -p "{icloud_projects_path}/{folder_name}"
   ```
5. **Create Google Drive folder:**
   ```bash
   mkdir -p "{gdrive_projects_path}/{folder_name}"
   ```
6. **Create Todoist project** under the correct parent:
   ```bash
   curl -s -X POST "https://api.todoist.com/rest/v2/projects" \
     -H "Authorization: Bearer $TODOIST_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "{id}-{name}",
       "parent_id": "{parent_project_id}"
     }'
   ```
   Capture the returned `id` as `todoist_project_id`.
7. **Add to registry:**
   ```json
   {
     "id": "{id}",
     "name": "{name}",
     "description": "{description}",
     "status": "Not Started",
     "created_at": "{ISO 8601 now}",
     "updated_at": "{ISO 8601 now}",
     "todoist_project_id": "{todoist_project_id}"
   }
   ```
8. **Write registry** back to `registry.json`
9. **Confirm** to user: show ID, folder paths, and Todoist link

### 2. Rename Project

**Trigger:** "rename project", "change project name", "modify project name"

**Inputs:**
- Project ID or current name
- New name

**Steps:**

1. **Load registry**, find the project
2. **Build old and new folder names**
3. **Rename iCloud folder:**
   ```bash
   mv "{icloud_projects_path}/{old_folder}" "{icloud_projects_path}/{new_folder}"
   ```
4. **Rename Google Drive folder:**
   ```bash
   mv "{gdrive_projects_path}/{old_folder}" "{gdrive_projects_path}/{new_folder}"
   ```
5. **Update Todoist project:**
   ```bash
   curl -s -X POST "https://api.todoist.com/rest/v2/projects/{todoist_project_id}" \
     -H "Authorization: Bearer $TODOIST_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name": "{new_id}-{new_name}"}'
   ```
6. **Update registry** entry: name, updated_at
7. **Write registry**
8. **Confirm** changes to user

### 3. Update Project Status

**Trigger:** "update status", "mark project as", "project status"

**Inputs:**
- Project ID or name
- New status: `Not Started`, `In Progress`, or `Done`

**Steps:**

1. Load registry, find project
2. Update `status` and `updated_at`
3. Write registry
4. Confirm to user

### 4. List Projects

**Trigger:** "list projects", "show projects", "my projects"

**Options:**
- Filter by context (home/work) — default: show all
- Filter by status — default: show all
- Sort by: created_at (default), status, id

**Output format:**

```
ID      | Name                        | Status       | Created
--------|-----------------------------|--------------|-----------
W0001   | Fraud Adjudication Agent    | In Progress  | 2026-04-01
W0002   | Merchant Risk Model         | Not Started  | 2026-04-02
H0001   | Kitchen Renovation          | In Progress  | 2026-03-15
```

### 5. Show Project Detail

**Trigger:** "show project {id}", "project details", "describe project"

Show all fields for the specified project, including folder paths and Todoist link:
- Todoist link: `https://app.todoist.com/app/project/{todoist_project_id}`

---

## Error Handling

- **Folder already exists:** Warn user, skip folder creation, continue with other steps
- **Todoist API failure:** Log error, complete folder creation, flag that Todoist sync is incomplete. Store `todoist_project_id: null` and instruct user to retry with "sync project {id} to todoist"
- **Registry file missing:** Initialize with empty array `[]`
- **Config missing:** Walk user through setup flow
- **Duplicate project name:** Warn user, ask for confirmation before proceeding (IDs will still be unique)

## Folder Name Convention

Folder names follow the pattern: `{id}-{kebab-case-name}`
- Convert name to lowercase
- Replace spaces with hyphens
- Strip special characters except hyphens
- Example: "Fraud Adjudication Agent" → `W0001-fraud-adjudication-agent`
