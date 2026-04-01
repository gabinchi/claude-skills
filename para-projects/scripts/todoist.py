#!/usr/bin/env python3
"""
PARA Projects — Todoist CLI.

Usage:
    todoist.py create-project --context work|home --id ID --name NAME
    todoist.py update-project PROJECT_ID --name NAME
    todoist.py get-tasks PROJECT_ID
    todoist.py delete-task TASK_ID
    todoist.py delete-incomplete-tasks PROJECT_ID
    todoist.py archive-project PROJECT_ID

Requires: TODOIST_API_TOKEN env var
Config:   ~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/config.json
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path

CONFIG_PATH = (
    Path.home()
    / "Library/Mobile Documents/com~apple~CloudDocs/.project-registry/config.json"
)

REST_BASE = "https://api.todoist.com/rest/v2"
SYNC_BASE = "https://api.todoist.com/sync/v9"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_token():
    token = os.environ.get("TODOIST_API_TOKEN")
    if not token:
        err("TODOIST_API_TOKEN environment variable is not set")
    return token


def load_config():
    if not CONFIG_PATH.exists():
        err(f"Config not found at {CONFIG_PATH}. Run setup.py first.")
    with open(CONFIG_PATH) as f:
        return json.load(f)


def err(msg):
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(1)


def request(method, url, *, token, body=None, form=None):
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    elif form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        err(f"HTTP {e.code} from {url}: {body}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_create_project(args):
    token = get_token()
    config = load_config()
    context = args.context
    try:
        parent_id = config["todoist"]["parent_projects"][context]["id"]
    except KeyError:
        err(f"Todoist parent project ID for '{context}' not set in config")
    if not parent_id:
        err(f"Todoist parent project ID for '{context}' is empty — run setup.py")

    result = request(
        "POST",
        f"{REST_BASE}/projects",
        token=token,
        body={"name": f"{args.id}-{args.name}", "parent_id": parent_id},
    )
    print(json.dumps({"id": result["id"], "name": result["name"], "url": f"https://app.todoist.com/app/project/{result['id']}"}))


def cmd_update_project(args):
    token = get_token()
    result = request(
        "POST",
        f"{REST_BASE}/projects/{args.project_id}",
        token=token,
        body={"name": args.name},
    )
    print(json.dumps({"id": result["id"], "name": result["name"]}))


def cmd_get_tasks(args):
    token = get_token()
    tasks = request(
        "GET",
        f"{REST_BASE}/tasks?project_id={args.project_id}",
        token=token,
    )
    print(json.dumps(tasks))


def cmd_delete_task(args):
    token = get_token()
    request("DELETE", f"{REST_BASE}/tasks/{args.task_id}", token=token)
    print(json.dumps({"deleted": args.task_id}))


def cmd_delete_incomplete_tasks(args):
    token = get_token()
    tasks = request(
        "GET",
        f"{REST_BASE}/tasks?project_id={args.project_id}",
        token=token,
    )
    deleted = []
    for task in tasks:
        request("DELETE", f"{REST_BASE}/tasks/{task['id']}", token=token)
        deleted.append(task["id"])
    print(json.dumps({"deleted_count": len(deleted), "deleted_ids": deleted}))


def cmd_archive_project(args):
    token = get_token()
    request(
        "POST",
        f"{SYNC_BASE}/projects/archive",
        token=token,
        form={"id": args.project_id},
    )
    print(json.dumps({"archived": args.project_id}))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PARA Todoist CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # create-project
    p = sub.add_parser("create-project", help="Create a Todoist project under the context parent")
    p.add_argument("--context", required=True, choices=["work", "home"])
    p.add_argument("--id", required=True)
    p.add_argument("--name", required=True)
    p.set_defaults(func=cmd_create_project)

    # update-project
    p = sub.add_parser("update-project", help="Rename a Todoist project")
    p.add_argument("project_id")
    p.add_argument("--name", required=True)
    p.set_defaults(func=cmd_update_project)

    # get-tasks
    p = sub.add_parser("get-tasks", help="List active tasks in a project")
    p.add_argument("project_id")
    p.set_defaults(func=cmd_get_tasks)

    # delete-task
    p = sub.add_parser("delete-task", help="Delete a single task")
    p.add_argument("task_id")
    p.set_defaults(func=cmd_delete_task)

    # delete-incomplete-tasks
    p = sub.add_parser("delete-incomplete-tasks", help="Delete all active tasks in a project")
    p.add_argument("project_id")
    p.set_defaults(func=cmd_delete_incomplete_tasks)

    # archive-project
    p = sub.add_parser("archive-project", help="Archive a Todoist project")
    p.add_argument("project_id")
    p.set_defaults(func=cmd_archive_project)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
