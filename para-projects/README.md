# PARA Project Manager — Claude Code Skill

A Claude Code skill for managing projects using the PARA method, with synchronized folders across iCloud Drive, Google Drive, and Todoist.

## Installation

### 1. Copy the skill to your Claude Code skills directory

```bash
# Create the skill directory
mkdir -p ~/.claude/skills/para-projects

# Copy files (adjust source path as needed)
cp -r ./para-projects/* ~/.claude/skills/para-projects/
```

Alternatively, if you manage skills in a repo or another location, place the `para-projects/` folder wherever your Claude Code instance reads skills from.

### 2. Get your Todoist API token

1. Go to https://app.todoist.com/app/settings/integrations/developer
2. Copy the API token

### 3. Set the environment variable

Add to your `~/.zshrc`:
```bash
export TODOIST_API_TOKEN="your-token-here"
```

Then reload: `source ~/.zshrc`

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
- Create project folders in iCloud and Google Drive if they don't exist
- Resolve Todoist parent project IDs automatically

### 6. Set default context per machine

Edit `~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/config.json`:
- Personal Mac: `"default_context": "home"`
- Work Mac: `"default_context": "work"`

Since config.json lives in iCloud, you'll share it across devices. If you need different defaults per machine, you can override by telling Claude Code: "create a home project" or "create a work project."

## Usage (in Claude Code)

```
> create a project called "Merchant Risk Model" — it's a credit risk scoring model for Nelo merchants

> list my work projects

> rename W0003 to "Merchant Risk Scoring v2"

> mark H0002 as done

> show project W0001
```

## File Locations

| File | Path |
|------|------|
| Skill | `~/.claude/skills/para-projects/SKILL.md` |
| Config | `~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/config.json` |
| Registry | `~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/registry.json` |
| iCloud folders | `~/Library/Mobile Documents/com~apple~CloudDocs/Projects/{id}-{name}/` |
| Google Drive folders | `~/Library/CloudStorage/GoogleDrive-gabinchi@gmail.com/My Drive/Projects/{id}-{name}/` |

## Project ID Format

- Work: `W0001`, `W0002`, ...
- Home: `H0001`, `H0002`, ...

Auto-incremented per context from the registry.
