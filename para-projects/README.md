# PARA Project Manager — Claude Code Skill

A Claude Code skill for managing projects using the PARA method, with synchronized folders across iCloud Drive, Google Drive, and Todoist.

## Installation

### 1. Copy the skill to your Claude Code skills directory

```bash
mkdir -p ~/.claude/skills/para-projects
cp -r ./para-projects/* ~/.claude/skills/para-projects/
```

### 2. Get your Todoist API token

1. Go to https://app.todoist.com/app/settings/integrations/developer
2. Copy the API token

### 3. Set the environment variables

Add to your `~/.zshrc`:
```bash
export TODOIST_API_TOKEN="your-token-here"
export NOTION_API_KEY_WORK="your-work-notion-token"
export NOTION_API_KEY_HOME="your-home-notion-token"
```

Then reload: `source ~/.zshrc`

To get Notion API keys: go to https://www.notion.so/my-integrations, create an integration per account, and copy the token. Then share each target database with its integration (open the database in Notion → ··· → Connections).

### 4. Ensure Todoist parent projects exist

In Todoist, make sure you have two top-level projects:
- `💼 Work`
- `🏡 Home`

### 5. Run setup

```bash
cd ~/.claude/skills/para-projects
python3 scripts/setup.py
```

This will:
- Create `~/.../iCloud Drive/.project-registry/` with config and registry
- Resolve Todoist parent project IDs automatically

### 6. Set default context per machine

Edit `~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/config.json`:
- Personal Mac: `"default_context": "home"`
- Work Mac: `"default_context": "work"`

Since config.json lives in iCloud, it syncs across devices. Override per-request by saying "create a home project" or "create a work project."

### 7. Set up folder structure (optional)

If starting fresh, let the skill create your PARA folders:
```
> /para-projects setup folder structure
```

After setup, update `icloud_projects_path`, `icloud_archive_path`, `gdrive_projects_path`, and `gdrive_archive_path` in `config.json` to point to the new folders.

## Usage (in Claude Code)

This skill must be invoked explicitly using `/para-projects`:

```
> /para-projects create a project called "Merchant Risk Model" — it's a credit risk scoring model for Nelo merchants

> /para-projects list my work projects

> /para-projects search projects "risk"

> /para-projects rename W00003 to "Merchant Risk Scoring v2"

> /para-projects move W00003 to home

> /para-projects mark H00002 as done

> /para-projects show project W00001

> /para-projects close project W00001

> /para-projects restore project W00001

> /para-projects sync status

> /para-projects sync project W00002 to todoist

> /para-projects sync project W00002 to notion

> /para-projects setup folder structure
```

## File Locations

| File | Path |
|------|------|
| Skill | `~/.claude/skills/para-projects/SKILL.md` |
| Config | `~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/config.json` |
| Registry | `~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/registry.json` |
| iCloud project folders | `~/Library/Mobile Documents/com~apple~CloudDocs/1 🎯 Projects/{id}-{name}/` |
| iCloud archive | `~/Library/Mobile Documents/com~apple~CloudDocs/4 🗃️ Archive/Projects/{id}-{name}/` |
| Google Drive project folders | `~/Library/CloudStorage/GoogleDrive-you@gmail.com/My Drive/1 🎯 Projects/{id}-{name}/` |
| Google Drive archive | `~/Library/CloudStorage/GoogleDrive-you@gmail.com/My Drive/4 🗃️ Archive/Projects/{id}-{name}/` |

## Project ID Format

- Work: `W00001`, `W00002`, ...
- Home: `H00001`, `H00002`, ...

Auto-incremented per context from the registry.

## Project Statuses

| Status | Meaning |
|--------|---------|
| `Not Started` | Default on creation |
| `In Progress` | Actively being worked on |
| `Done` | Closed via the Close Project action |