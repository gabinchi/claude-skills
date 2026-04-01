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

REGISTRY_DIR = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/.project-registry"
CONFIG_PATH = REGISTRY_DIR / "config.json"
REGISTRY_PATH = REGISTRY_DIR / "registry.json"

TODOIST_API_URL = "https://api.todoist.com/rest/v2/projects"
PARENT_NAMES = {"💼 Work": "work", "🏡 Home": "home"}


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
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def resolve_parent_ids(projects):
    found = {}
    for p in projects:
        if p["name"] in PARENT_NAMES:
            key = PARENT_NAMES[p["name"]]
            found[key] = {"name": p["name"], "id": str(p["id"])}
    return found


def load_or_create_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)

    # Default config
    icloud_base = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs"
    gdrive_base = Path.home() / "Library/CloudStorage"
    # Find the first Google Drive folder if present
    gdrive_roots = list(gdrive_base.glob("GoogleDrive-*")) if gdrive_base.exists() else []
    gdrive_root = str(gdrive_roots[0] / "My Drive") if gdrive_roots else str(gdrive_base / "GoogleDrive-you@gmail.com/My Drive")
    return {
        "default_context": "work",
        "icloud_projects_path": str(icloud_base / "1 🎯 Projects"),
        "icloud_archive_path": str(icloud_base / "4 🗃️ Archive/Projects"),
        "gdrive_projects_path": str(Path(gdrive_root) / "1 🎯 Projects"),
        "gdrive_archive_path": str(Path(gdrive_root) / "4 🗃️ Archive/Projects"),
        "todoist": {
            "parent_projects": {
                "work": {"name": "💼 Work", "id": ""},
                "home": {"name": "🏡 Home", "id": ""},
            }
        },
    }


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
    token = get_todoist_token()
    print("\nFetching Todoist projects...")
    projects = fetch_todoist_projects(token)
    parents = resolve_parent_ids(projects)

    if "work" in parents:
        config["todoist"]["parent_projects"]["work"] = parents["work"]
        print(f'✓ Found "{parents["work"]["name"]}" → ID: {parents["work"]["id"]}')
    else:
        print('⚠ Could not find "💼 Work" project in Todoist. Create it first.')

    if "home" in parents:
        config["todoist"]["parent_projects"]["home"] = parents["home"]
        print(f'✓ Found "{parents["home"]["name"]}" → ID: {parents["home"]["id"]}')
    else:
        print('⚠ Could not find "🏡 Home" project in Todoist. Create it first.')

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
    print(f"\nAdd this to your ~/.zshrc to persist the token:")
    print(f'  export TODOIST_API_TOKEN="{token}"')


if __name__ == "__main__":
    main()
