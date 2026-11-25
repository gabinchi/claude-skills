#!/usr/bin/env python3
"""
PARA Projects — First-run / upgrade setup script.
Merges Obsidian + Linear config into an existing registry config,
resolves Linear team and project-status IDs, and ensures folders exist.

Usage:
    export LINEAR_API_KEY="lin_api_..."
    python3 setup.py
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

from utils import REGISTRY_DIR, CONFIG_PATH, REGISTRY_FILE, LINEAR_API, expand_path

REGISTRY_PATH = REGISTRY_FILE
TEMPLATE_PATH = Path(__file__).parent.parent / "config.template.json"


def load_template():
    if not TEMPLATE_PATH.exists():
        print(f"ERROR: config.template.json not found at {TEMPLATE_PATH}")
        sys.exit(1)
    with open(TEMPLATE_PATH) as f:
        return json.load(f)


def load_or_create_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return load_template()


def deep_merge_defaults(config, template):
    """Add missing keys from template without overwriting existing values.
    Does not rewrite registry.json. Leaves obsolete keys (todoist, notion, icloud_*) in place.
    """
    for key, value in template.items():
        if key not in config:
            config[key] = value
        elif isinstance(value, dict) and isinstance(config.get(key), dict):
            deep_merge_defaults(config[key], value)
    return config


def get_linear_token(config):
    env_name = config.get("linear", {}).get("api_key_env", "LINEAR_API_KEY")
    return os.environ.get(env_name), env_name


def linear_graphql(token, query, variables=None):
    body = {"query": query}
    if variables is not None:
        body["variables"] = variables
    req = urllib.request.Request(
        LINEAR_API,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": token,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.loads(resp.read().decode())
    if "errors" in payload:
        messages = "; ".join(e.get("message", str(e)) for e in payload["errors"])
        raise RuntimeError(messages)
    return payload.get("data", {})


def resolve_linear_teams(token, config):
    data = linear_graphql(
        token,
        """
        query {
          teams {
            nodes { id name key }
          }
        }
        """,
    )
    teams = data.get("teams", {}).get("nodes", [])
    if not teams:
        print("⚠ No Linear teams found for this API key.")
        return False

    linear = config.setdefault("linear", {})
    team_cfg = linear.setdefault("teams", {})
    work = team_cfg.setdefault("work", {"id": "", "name": ""})
    home = team_cfg.setdefault("home", {"id": "", "name": ""})

    if len(teams) == 1:
        t = teams[0]
        for ctx in ("work", "home"):
            team_cfg[ctx] = {"id": t["id"], "name": t["name"]}
        print(f'✓ Single Linear team "{t["name"]}" → work and home')
        return True

    # Multiple teams: fill only if ids already set; otherwise print and stop filling
    if work.get("id") and home.get("id"):
        print(f'✓ Linear work team: {work.get("name") or work["id"]}')
        print(f'✓ Linear home team: {home.get("name") or home["id"]}')
        return True

    print("\nMultiple Linear teams found. Set linear.teams.work.id and")
    print("linear.teams.home.id in config.json, then re-run setup:\n")
    for t in teams:
        print(f'  {t["id"]}  {t.get("key", ""):<8}  {t["name"]}')
    print()
    return False


def pick_status_id(statuses, preferred_types):
    by_type = {}
    for s in statuses:
        by_type.setdefault(s.get("type"), []).append(s)
    for t in preferred_types:
        if t in by_type:
            return by_type[t][0]["id"], by_type[t][0]["name"]
    if statuses:
        return statuses[0]["id"], statuses[0]["name"]
    return "", ""


def resolve_linear_statuses(token, config):
    data = linear_graphql(
        token,
        """
        query {
          projectStatuses {
            nodes { id name type }
          }
        }
        """,
    )
    statuses = data.get("projectStatuses", {}).get("nodes", [])
    if not statuses:
        print("⚠ No Linear project statuses found.")
        return

    linear = config.setdefault("linear", {})
    status_map = linear.setdefault("statuses", {})

    mapping = {
        "Not Started": ["planned", "backlog"],
        "In Progress": ["started"],
        "Done": ["completed"],
    }
    for para_status, types in mapping.items():
        sid, sname = pick_status_id(statuses, types)
        status_map[para_status] = sid
        print(f'✓ Linear status "{para_status}" → {sname} ({sid})')


def ensure_dirs(config):
    for key in [
        "obsidian_vault_path",
        "obsidian_archive_path",
        "gdrive_projects_path",
        "gdrive_archive_path",
    ]:
        path_str = config.get(key)
        if not path_str:
            print(f"⚠ {key} not set in config")
            continue
        path = expand_path(path_str)
        if path.exists():
            print(f"✓ Directory exists: {path}")
        else:
            path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created directory: {path}")


def main():
    print("=== PARA Projects Setup ===\n")

    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Registry directory: {REGISTRY_DIR}")

    if not REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "w") as f:
            json.dump([], f, indent=2)
        print(f"✓ Created empty registry: {REGISTRY_PATH}")
    else:
        print(f"✓ Registry exists (not rewritten): {REGISTRY_PATH}")

    template = load_template()
    config = load_or_create_config()
    deep_merge_defaults(config, template)

    # Preserve default_context if already set
    if "default_context" not in config:
        config["default_context"] = template.get("default_context", "work")

    ensure_dirs(config)

    token, env_name = get_linear_token(config)
    if not token:
        print(f"\n⚠ {env_name} not set — Linear sync will be unavailable.")
        print(f'  Set it in ~/.zshrc: export {env_name}="lin_api_..."')
        print("  Create a key at: https://linear.app/settings/account/security/api-keys/new")
    else:
        print(f"✓ {env_name} is set")
        try:
            print("\nResolving Linear teams...")
            resolve_linear_teams(token, config)
            print("\nResolving Linear project statuses...")
            resolve_linear_statuses(token, config)
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"⚠ Linear API error: HTTP {e.code} — {body}")
        except Exception as e:
            print(f"⚠ Linear setup failed: {e}")

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"\n✓ Config saved: {CONFIG_PATH}")

    print("\n=== Setup Complete ===")
    print(f"Default context:     {config.get('default_context')}")
    print(f"Obsidian vault:      {config.get('obsidian_vault_path')}")
    print(f"Obsidian archive:    {config.get('obsidian_archive_path')}")
    print(f"GDrive projects:     {config.get('gdrive_projects_path')}")
    print(f"GDrive archive:      {config.get('gdrive_archive_path')}")
    if not token:
        print(f"\n⚠ When ready, set {env_name} in ~/.zshrc and re-run setup.")


if __name__ == "__main__":
    main()
