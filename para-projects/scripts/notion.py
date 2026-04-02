#!/usr/bin/env python3
"""
PARA Projects — Notion CLI.

Usage:
    notion.py create-page --context work|home --id ID --name NAME --description DESC
                          --status STATUS [--todoist-project-id ID]
                          [--icloud-path PATH] [--gdrive-path PATH]
    notion.py update-page PAGE_ID [--context work|home] [--name NAME] [--id ID]
                                  [--status STATUS] [--description DESC]
                                  [--todoist-project-id ID]
                                  [--icloud-path PATH] [--gdrive-path PATH]
    notion.py archive-page PAGE_ID [--context work|home]
    notion.py unarchive-page PAGE_ID [--context work|home]

Requires: NOTION_API_TOKEN env var (configurable via api_key_env in config.json)
Config:   ~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/config.json
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

from utils import err, load_config

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_notion_creds(config):
    notion_cfg = config.get("notion", {})
    if not notion_cfg:
        err("notion config not found in config.json")
    api_key_env = notion_cfg.get("api_key_env", "NOTION_API_TOKEN")
    token = os.environ.get(api_key_env)
    if not token:
        err(f"{api_key_env} environment variable is not set")
    database_id = notion_cfg.get("database_id", "")
    if not database_id:
        err("notion.database_id is not set in config.json")
    return token, database_id


def request(method, path, *, token, body=None):
    url = f"{NOTION_API}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        if e.code == 403:
            err(
                "HTTP 403: Integration not connected to this database. "
                "Open the database in Notion → ··· → Connections and add the integration."
            )
        err(f"HTTP {e.code} from {path}: {body_text}")


def rich_text(content):
    return [{"text": {"content": content or ""}}]


def build_properties(args, include_created=False):
    props = {}
    if hasattr(args, "name") and args.name is not None:
        title = f"{args.id} - {args.name}" if (hasattr(args, "id") and args.id) else args.name
        props["Name"] = {"title": rich_text(title)}
    if hasattr(args, "id") and args.id is not None:
        props["Project ID"] = {"rich_text": rich_text(args.id)}
    if hasattr(args, "description") and args.description is not None:
        props["Description"] = {"rich_text": rich_text(args.description)}
    if hasattr(args, "status") and args.status is not None:
        props["Status"] = {"select": {"name": args.status}}
    if hasattr(args, "context") and args.context is not None:
        context_label = "Work" if args.context == "work" else "Home"
        props["Context"] = {"select": {"name": context_label}}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if include_created:
        props["Created At"] = {"date": {"start": now}}
        props["Updated At"] = {"date": {"start": now}}
    return props


def folder_blocks(icloud_path=None, gdrive_path=None, todoist_project_id=None):
    """Build bulleted list blocks for folder/link paths."""
    items = []
    if icloud_path:
        items.append(f"iCloud: {icloud_path}")
    if gdrive_path:
        items.append(f"Google Drive: {gdrive_path}")
    if todoist_project_id:
        items.append(f"Todoist: https://app.todoist.com/app/project/{todoist_project_id}")
    return [
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": rich_text(item)},
        }
        for item in items
    ]


def replace_blocks(page_id, token, new_blocks):
    """Delete all existing body blocks and replace with new_blocks."""
    data = request("GET", f"/blocks/{page_id}/children", token=token)
    for block in data.get("results", []):
        request("DELETE", f"/blocks/{block['id']}", token=token)
    if new_blocks:
        request("PATCH", f"/blocks/{page_id}/children", token=token, body={"children": new_blocks})


def page_url(page_id):
    return f"https://notion.so/{page_id.replace('-', '')}"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_create_page(args):
    config = load_config()
    token, database_id = get_notion_creds(config)

    body = {
        "parent": {"database_id": database_id},
        "properties": build_properties(args, include_created=True),
        "children": folder_blocks(
            icloud_path=getattr(args, "icloud_path", None),
            gdrive_path=getattr(args, "gdrive_path", None),
            todoist_project_id=getattr(args, "todoist_project_id", None),
        ),
    }
    result = request("POST", "/pages", token=token, body=body)
    print(json.dumps({"id": result["id"], "url": page_url(result["id"])}))


def cmd_update_page(args):
    config = load_config()
    token, _ = get_notion_creds(config)

    has_folder_args = any(
        getattr(args, attr, None) is not None
        for attr in ("icloud_path", "gdrive_path", "todoist_project_id")
    )
    props = build_properties(args)

    if not props and not has_folder_args:
        err("No fields to update — provide at least one of: --name, --id, --status, --description, --context, --todoist-project-id, --icloud-path, --gdrive-path")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    props["Updated At"] = {"date": {"start": now}}

    result = request("PATCH", f"/pages/{args.page_id}", token=token, body={"properties": props})

    if has_folder_args:
        new_blocks = folder_blocks(
            icloud_path=getattr(args, "icloud_path", None),
            gdrive_path=getattr(args, "gdrive_path", None),
            todoist_project_id=getattr(args, "todoist_project_id", None),
        )
        replace_blocks(args.page_id, token, new_blocks)

    print(json.dumps({"id": result["id"], "url": page_url(result["id"])}))


def cmd_archive_page(args):
    config = load_config()
    token, _ = get_notion_creds(config)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = request(
        "PATCH",
        f"/pages/{args.page_id}",
        token=token,
        body={
            "archived": True,
            "properties": {
                "Status": {"select": {"name": "Done"}},
                "Closed At": {"date": {"start": now}},
                "Updated At": {"date": {"start": now}},
            },
        },
    )
    print(json.dumps({"id": result["id"], "archived": True}))


def cmd_unarchive_page(args):
    config = load_config()
    token, _ = get_notion_creds(config)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = request(
        "PATCH",
        f"/pages/{args.page_id}",
        token=token,
        body={
            "archived": False,
            "properties": {
                "Status": {"select": {"name": "In Progress"}},
                "Closed At": {"date": None},
                "Updated At": {"date": {"start": now}},
            },
        },
    )
    print(json.dumps({"id": result["id"], "archived": False, "url": page_url(result["id"])}))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def add_page_fields(p):
    """Add optional page property flags shared across commands."""
    p.add_argument("--status")
    p.add_argument("--todoist-project-id", dest="todoist_project_id")
    p.add_argument("--icloud-path", dest="icloud_path")
    p.add_argument("--gdrive-path", dest="gdrive_path")


def main():
    parser = argparse.ArgumentParser(
        description="PARA Notion CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # create-page
    p = sub.add_parser("create-page", help="Create a project page in the Notion database")
    p.add_argument("--context", required=True, choices=["work", "home"])
    p.add_argument("--id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--description", required=True)
    add_page_fields(p)
    p.set_defaults(func=cmd_create_page)

    # update-page
    p = sub.add_parser("update-page", help="Update properties on a Notion page")
    p.add_argument("page_id")
    p.add_argument("--context", choices=["work", "home"])
    p.add_argument("--name")
    p.add_argument("--id")
    p.add_argument("--description")
    add_page_fields(p)
    p.set_defaults(func=cmd_update_page)

    # archive-page
    p = sub.add_parser("archive-page", help="Archive a Notion page and set status to Done")
    p.add_argument("page_id")
    p.add_argument("--context", choices=["work", "home"])  # accepted for backward compat
    p.set_defaults(func=cmd_archive_page)

    # unarchive-page
    p = sub.add_parser("unarchive-page", help="Unarchive a Notion page and set status to In Progress")
    p.add_argument("page_id")
    p.add_argument("--context", choices=["work", "home"])  # accepted for backward compat
    p.set_defaults(func=cmd_unarchive_page)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
