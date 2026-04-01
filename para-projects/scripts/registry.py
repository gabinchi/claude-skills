#!/usr/bin/env python3
"""
PARA Projects — Registry CLI.

Usage:
    registry.py next-id <W|H>
    registry.py add --id ID --name NAME --description DESC [--todoist-id ID]
    registry.py find <id_or_name>
    registry.py update <id_or_name> [--name NAME] [--status STATUS] [--description DESC]
                                    [--todoist-id ID] [--closed-at now|ISO] [--clear-closed-at]
                                    [--new-id ID]
    registry.py list [--context work|home] [--status STATUS] [--sort created_at|status|id]
                     [--include-done] [--json]
    registry.py search <keyword> [--json]
    registry.py kebab <name>
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_DIR = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/.project-registry"
REGISTRY_FILE = REGISTRY_DIR / "registry.json"

VALID_STATUSES = ["Not Started", "In Progress", "Done"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load():
    if not REGISTRY_FILE.exists():
        return []
    with open(REGISTRY_FILE) as f:
        return json.load(f)


def save(projects):
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=REGISTRY_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(projects, f, indent=2)
        os.replace(tmp, REGISTRY_FILE)
    except Exception:
        os.unlink(tmp)
        raise


def to_kebab(name):
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    name = re.sub(r"\s+", "-", name.strip())
    return name


def find_one(projects, id_or_name):
    """Return (project, error_message). Exactly one of them will be None."""
    # Exact ID match
    for p in projects:
        if p["id"].upper() == id_or_name.upper():
            return p, None
    # Exact name match (case-insensitive)
    for p in projects:
        if p["name"].lower() == id_or_name.lower():
            return p, None
    # Partial name match
    matches = [p for p in projects if id_or_name.lower() in p["name"].lower()]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        ids = ", ".join(p["id"] for p in matches)
        return None, f"Ambiguous: '{id_or_name}' matches {ids}"
    return None, f"Not found: '{id_or_name}'"


def err(msg):
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(1)


def print_table(projects, extra_col=None):
    if not projects:
        print("No projects found.")
        return
    header = f"{'ID':<8} | {'Name':<30} | {'Status':<12} | {'Created':<10}"
    divider = f"{'-'*8}-+-{'-'*30}-+-{'-'*12}-+-{'-'*10}"
    if extra_col:
        header += f" | {extra_col[0]}"
        divider += f"-+-{'-'*10}"
    print(header)
    print(divider)
    for p in projects:
        row = (
            f"{p['id']:<8} | {p['name']:<30} | {p['status']:<12} | "
            f"{p.get('created_at', '')[:10]:<10}"
        )
        if extra_col:
            row += f" | {p.get(extra_col[1], '')}"
        print(row)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_next_id(args):
    projects = load()
    prefix = args.prefix.upper()
    max_num = 0
    for p in projects:
        if p["id"].startswith(prefix):
            try:
                max_num = max(max_num, int(p["id"][len(prefix):]))
            except ValueError:
                pass
    print(f"{prefix}{max_num + 1:05d}")


def cmd_add(args):
    projects = load()
    # Duplicate name check (active projects only)
    for p in projects:
        if p["name"].lower() == args.name.lower() and p.get("status") != "Done":
            err(f"Active project named '{args.name}' already exists: {p['id']}")
    entry = {
        "id": args.id,
        "name": args.name,
        "description": args.description,
        "status": "Not Started",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "closed_at": None,
        "todoist_project_id": args.todoist_id,
        "notion_page_id": args.notion_id,
    }
    projects.append(entry)
    save(projects)
    print(json.dumps(entry, indent=2))


def cmd_find(args):
    projects = load()
    project, error = find_one(projects, args.id_or_name)
    if error:
        err(error)
    print(json.dumps(project, indent=2))


def cmd_update(args):
    projects = load()
    project, error = find_one(projects, args.id)
    if error:
        err(error)

    if args.name is not None:
        for p in projects:
            if p["id"] != project["id"] and p["name"].lower() == args.name.lower() and p.get("status") != "Done":
                err(f"Active project named '{args.name}' already exists: {p['id']}")
        project["name"] = args.name

    if args.status is not None:
        if args.status not in VALID_STATUSES:
            err(f"Invalid status '{args.status}'. Valid values: {VALID_STATUSES}")
        project["status"] = args.status

    if args.description is not None:
        project["description"] = args.description

    if args.todoist_id is not None:
        project["todoist_project_id"] = args.todoist_id

    if args.notion_id is not None:
        project["notion_page_id"] = args.notion_id

    if args.closed_at is not None:
        project["closed_at"] = now_iso() if args.closed_at == "now" else args.closed_at

    if args.clear_closed_at:
        project["closed_at"] = None

    if args.new_id is not None:
        project["id"] = args.new_id

    project["updated_at"] = now_iso()
    save(projects)
    print(json.dumps(project, indent=2))


def cmd_list(args):
    projects = load()

    if args.context:
        prefix = "W" if args.context == "work" else "H"
        projects = [p for p in projects if p["id"].startswith(prefix)]
    if args.status:
        projects = [p for p in projects if p["status"] == args.status]
    if not args.include_done:
        projects = [p for p in projects if p["status"] != "Done"]

    sort_key = args.sort or "created_at"
    projects.sort(key=lambda p: p.get(sort_key, ""))

    if args.json:
        print(json.dumps(projects, indent=2))
    else:
        print_table(projects)


def cmd_search(args):
    projects = load()
    keyword = args.keyword.lower()
    results = []
    for p in projects:
        if keyword in p["name"].lower():
            results.append({**p, "_match": "name"})
        elif keyword in p.get("description", "").lower():
            results.append({**p, "_match": "description"})

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print(f"No projects matching '{args.keyword}'.")
        else:
            print_table(results, extra_col=("Match", "_match"))


def cmd_kebab(args):
    print(to_kebab(args.name))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PARA project registry CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # next-id
    p = sub.add_parser("next-id", help="Get the next available ID for a prefix")
    p.add_argument("prefix", help="W (work) or H (home)")
    p.set_defaults(func=cmd_next_id)

    # add
    p = sub.add_parser("add", help="Add a new project to the registry")
    p.add_argument("--id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--todoist-id", default=None, dest="todoist_id")
    p.add_argument("--notion-id", default=None, dest="notion_id")
    p.set_defaults(func=cmd_add)

    # find
    p = sub.add_parser("find", help="Find a project by ID or name")
    p.add_argument("id_or_name")
    p.set_defaults(func=cmd_find)

    # update
    p = sub.add_parser("update", help="Update fields on an existing project")
    p.add_argument("id", help="Project ID or name")
    p.add_argument("--name")
    p.add_argument("--status", choices=VALID_STATUSES)
    p.add_argument("--description")
    p.add_argument("--todoist-id", dest="todoist_id")
    p.add_argument("--notion-id", dest="notion_id")
    p.add_argument("--closed-at", dest="closed_at", help="ISO timestamp or 'now'")
    p.add_argument("--clear-closed-at", action="store_true", dest="clear_closed_at")
    p.add_argument("--new-id", dest="new_id", help="Reassign the project ID (used by Move)")
    p.set_defaults(func=cmd_update)

    # list
    p = sub.add_parser("list", help="List projects")
    p.add_argument("--context", choices=["work", "home"])
    p.add_argument("--status", choices=VALID_STATUSES)
    p.add_argument("--sort", choices=["created_at", "status", "id"], default="created_at")
    p.add_argument("--include-done", action="store_true", dest="include_done")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)

    # search
    p = sub.add_parser("search", help="Search projects by keyword in name or description")
    p.add_argument("keyword")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_search)

    # kebab
    p = sub.add_parser("kebab", help="Convert a name to kebab-case for folder naming")
    p.add_argument("name")
    p.set_defaults(func=cmd_kebab)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
