#!/usr/bin/env python3
"""
PARA Projects — First-run setup script.
Resolves Todoist parent project IDs and initializes directory structure.

Usage:
    export TODOIST_API_TOKEN="your-token-here"
    python3 setup.py
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

from utils import REGISTRY_DIR, CONFIG_PATH, REGISTRY_FILE, TODOIST_REST_BASE

REGISTRY_PATH = REGISTRY_FILE  # alias for clarity in setup output
TEMPLATE_PATH = Path(__file__).parent.parent / "config.template.json"

TODOIST_API_URL = f"{TODOIST_REST_BASE}/projects"


def get_todoist_token():
    token = os.environ.get("TODOIST_API_TOKEN")
    if not token:
        print("ERROR: TODOIST_API_TOKEN environment variable not set.")
        print("Get your token from: https://app.todoist.com/app/settings/integrations/developer")
        print('Then run: export TODOIST_API_TOKEN="your-token-here"')
        sys.exit(1)
    return token


def fetch_todoist_projects(token):
    req = urllib.request.Request(
        TODOIST_API_URL,
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        # API v1 may return {"results": [...]} instead of a plain array
        if isinstance(data, list):
            return data
        for key in ("results", "projects", "items"):
            if key in data and isinstance(data[key], list):
                return data[key]
        print(f"⚠ Unexpected Todoist response structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        return []
    except urllib.error.HTTPError as e:
        print(f"⚠ Todoist API error: HTTP {e.code} — {e.reason}")
        if e.code == 401:
            print("  Token may be invalid or expired. Check TODOIST_API_TOKEN.")
        elif e.code == 410:
            print("  Endpoint gone. The Todoist API may have changed.")
        print("  Skipping Todoist setup — add parent project IDs to config.json manually.")
        return []
    except urllib.error.URLError as e:
        print(f"⚠ Could not reach Todoist: {e.reason}. Skipping Todoist setup.")
        return []


def resolve_parent_ids(projects, config):
    # Build name→key mapping from config so it stays in sync with config.template.json
    parent_names = {
        v["name"]: k
        for k, v in config.get("todoist", {}).get("parent_projects", {}).items()
    }
    found = {}
    for p in projects:
        if p["name"] in parent_names:
            key = parent_names[p["name"]]
            found[key] = {"name": p["name"], "id": str(p["id"])}
    return found


def load_or_create_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)

    if not TEMPLATE_PATH.exists():
        print(f"ERROR: config.template.json not found at {TEMPLATE_PATH}")
        sys.exit(1)

    with open(TEMPLATE_PATH) as f:
        return json.load(f)


def main():
    print("=== PARA Projects Setup ===\n")

    # 1. Create registry directory
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Registry directory: {REGISTRY_DIR}")

    # 2. Initialize empty registry if needed
    if not REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "w") as f:
            json.dump([], f, indent=2)
        print(f"✓ Created empty registry: {REGISTRY_PATH}")
    else:
        print(f"✓ Registry exists: {REGISTRY_PATH}")

    # 3. Load or create config
    config = load_or_create_config()

    # 4. Create project and archive directories
    for key in ["icloud_projects_path", "icloud_archive_path", "gdrive_projects_path", "gdrive_archive_path"]:
        if key in config:
            path = Path(os.path.expanduser(config[key]))
            path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Directory: {path}")

    # 5. Resolve Todoist parent IDs
    token = os.environ.get("TODOIST_API_TOKEN")
    if not token:
        print("\n⚠ TODOIST_API_TOKEN not set — skipping Todoist setup.")
        print("  Add parent project IDs to config.json manually when ready.")
        parents = {}
    else:
        print("\nFetching Todoist projects...")
        projects = fetch_todoist_projects(token)
        parents = resolve_parent_ids(projects, config)

    if parents:
        for key in ["work", "home"]:
            if key in parents:
                config["todoist"]["parent_projects"][key] = parents[key]
                print(f'✓ Found "{parents[key]["name"]}" → ID: {parents[key]["id"]}')
            else:
                emoji = "💼" if key == "work" else "🏡"
                name = "Work" if key == "work" else "Home"
                print(f'⚠ Could not find "{emoji} {name}" in Todoist. Create it first, then re-run setup.')

    # 6. Write config
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"\n✓ Config saved: {CONFIG_PATH}")

    # 7. Summary
    print("\n=== Setup Complete ===")
    print(f"Default context:  {config['default_context']}")
    print(f"iCloud projects:  {config['icloud_projects_path']}")
    print(f"iCloud archive:   {config.get('icloud_archive_path', 'not set')}")
    print(f"GDrive projects:  {config['gdrive_projects_path']}")
    print(f"GDrive archive:   {config.get('gdrive_archive_path', 'not set')}")
    if token:
        print(f"\nAdd this to your ~/.zshrc to persist the token:")
        print(f'  export TODOIST_API_TOKEN="{token}"')
    else:
        print(f"\nWhen ready, set TODOIST_API_TOKEN in ~/.zshrc and re-run setup.")


if __name__ == "__main__":
    main()
