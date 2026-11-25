# PARA Project Manager — Claude Code Skill

A Claude Code skill for managing projects using the PARA method, with synchronized Obsidian notes, Google Drive folders, and Linear projects.

Akiflow is not written by this skill. Use Akiflow's Linear integration to import issues from selected Linear projects.

## Installation

### 1. Copy the skill to your Claude Code skills directory

```bash
mkdir -p ~/.claude/skills/para-projects
cp -r ./para-projects/* ~/.claude/skills/para-projects/
```

### 2. Get your Linear API key

1. Go to https://linear.app/settings/account/security/api-keys/new
2. Create a personal API key with permission to manage projects

### 3. Set the environment variable

Add to your `~/.zshrc`:
```bash
export LINEAR_API_KEY="lin_api_..."
```

Then reload: `source ~/.zshrc`

### 4. Run setup

```bash
cd ~/.claude/skills/para-projects
uv run scripts/setup.py
```

This will:
- Ensure `~/.../iCloud Drive/.project-registry/` exists (does not wipe `registry.json`)
- Merge Obsidian + Linear keys into `config.json`
- Resolve Linear team IDs (single team → both work and home; multiple teams → print list for you to set)
- Resolve Linear project status IDs for Not Started / In Progress / Done
- Ensure Obsidian vault, Archive, and Google Drive project/archive folders exist

### 5. Set default context per machine

Edit `~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/config.json`:
- Personal Mac: `"default_context": "home"`
- Work Mac: `"default_context": "work"`

Since config.json lives in iCloud, it syncs across devices. Override per-request by saying "create a home project" or "create a work project."

If you have multiple Linear teams, set `linear.teams.work.id` and `linear.teams.home.id`, then re-run setup.

### 6. Run tests (optional)

```bash
cd ~/.claude/skills/para-projects
uv sync
uv run pytest -v
```

### 7. Set up folder structure (optional)

```
> /para-projects setup folder structure
```

Ensures the Obsidian vault + Archive and Google Drive project/archive paths exist.

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

> /para-projects sync project W00002 to linear

> /para-projects setup folder structure
```

## File Locations

| File | Path |
|------|------|
| Skill | `~/.claude/skills/para-projects/SKILL.md` |
| Config | `~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/config.json` |
| Registry | `~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/registry.json` |
| Obsidian project notes | `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/projects/{id} - {name}/` |
| Obsidian archive | `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/projects/Archive/{id} - {name}/` |
| Google Drive project folders | `~/Library/CloudStorage/GoogleDrive-.../My Drive/1 🎯 Projects/{id} - {name}/` |
| Google Drive archive | `~/Library/CloudStorage/GoogleDrive-.../My Drive/4 🗃️ Archive/Projects/{id} - {name}/` |

## Project ID Format

- Work: `W00001`, `W00002`, ...
- Home: `H00001`, `H00002`, ...

Auto-incremented per context from the registry.

## Project Statuses

| Status | Meaning | Linear |
|--------|---------|--------|
| `Not Started` | Default on creation | planned / backlog status |
| `In Progress` | Actively being worked on | started status |
| `Done` | Closed via the Close Project action | completed status |

Closing a project moves folders to archive and sets the Linear project to Done. It does **not** archive the Linear project or delete issues (so Akiflow can keep importing them).

## Akiflow

After creating a Linear project, select it in Akiflow → Settings → Integrations → Linear → Filter by Project if you want its issues in Akiflow. This skill does not create Linear issues and does not call Akiflow.
