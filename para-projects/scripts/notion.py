#!/usr/bin/env python3
"""
PARA Projects — Notion CLI.

Usage:
    notion.py create-page --context work|home --id ID --name NAME --description DESC
                          --status STATUS [--todoist-url URL]
                          [--icloud-path PATH] [--gdrive-path PATH]
    notion.py update-page PAGE_ID --context work|home [--name NAME] [--status STATUS]
                                  [--description DESC] [--todoist-url URL]
                                  [--icloud-path PATH] [--gdrive-path PATH]
    notion.py archive-page PAGE_ID --context work|home
    notion.py unarchive-page PAGE_ID --context work|home

Requires: NOTION_API_KEY_WORK and/or NOTION_API_KEY_HOME env vars
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

def get_notion_creds(config, context):
    try:
        notion_cfg = config["notion"][context]
    except KeyError:
        err(f"Notion config for '{context}' not found in config.json")
    api_key_env = notion_cfg.get("api_key_env", f"NOTION_API_KEY_{context.upper()}")
    token = os.environ.get(api_key_env)
    if not token:
        err(f"{api_key_env} environment variable is not set")
    database_id = notion_cfg.get("database_id", "")
    if not database_id:
        err(f"notion.{context}.database_id is not set in config.json")
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
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if e.code == 403:
            err(
                f"HTTP 403: Integration not connected to this database. "
                f"Open the database in Notion → ··· → Connections and add the integration."
            )
        err(f"HTTP {e.code} from {path}: {body}")


def rich_text(content):
    return [{"text": {"content": content or ""}}]


def build_properties(args, include_created=False):
    props = {}
    if hasattr(args, "name") and args.name is not None:
        title = f"{args.id} — {args.name}" if hasattr(args, "id") else args.name
        props["Name"] = {"title": rich_text(title)}
    if hasattr(args, "id") and args.id is not None:
        props["Project ID"] = {"rich_text": rich_text(args.id)}
    if hasattr(args, "status") and args.status is not None:
        props["Status"] = {"select": {"name": args.status}}
    if hasattr(args, "description") and args.description is not None:
        props["Description"] = {"rich_text": rich_text(args.description)}
    if include_created:
        props["Created"] = {"date": {"start": datetime.now(timezone.utc).strftime("%Y-%m-%d")}}
    if hasattr(args, "todoist_url") and args.todoist_url is not None:
        props["Todoist"] = {"url": args.todoist_url}
    if hasattr(args, "icloud_path") and args.icloud_path is not None:
        props["iCloud Folder"] = {"rich_text": rich_text(args.icloud_path)}
    if hasattr(args, "gdrive_path") and args.gdrive_path is not None:
        props["Google Drive Folder"] = {"rich_text": rich_text(args.gdrive_path)}
    return props


def description_blocks(description):
    return [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": rich_text("Description")},
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": rich_text(description or "")},
        },
    ]


def page_url(page_id):
    return f"https://notion.so/{page_id.replace('-', '')}"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_create_page(args):
    config = load_config()
    token, database_id = get_notion_creds(config, args.context)

    body = {
        "parent": {"database_id": database_id},
        "properties": build_properties(args, include_created=True),
        "children": description_blocks(args.description),
    }
    result = request("POST", "/pages", token=token, body=body)
    print(json.dumps({"id": result["id"], "url": page_url(result["id"])}))


def cmd_update_page(args):
    config = load_config()
    token, _ = get_notion_creds(config, args.context)

    props = build_properties(args)
    if not props:
        err("No fields to update — provide at least one of: --name, --status, --description, --todoist-url, --icloud-path, --gdrive-path")

    result = request("PATCH", f"/pages/{args.page_id}", token=token, body={"properties": props})
    print(json.dumps({"id": result["id"], "url": page_url(result["id"])}))


def cmd_archive_page(args):
    config = load_config()
    token, _ = get_notion_creds(config, args.context)
    result = request(
        "PATCH",
        f"/pages/{args.page_id}",
        token=token,
        body={"archived": True, "properties": {"Status": {"select": {"name": "Done"}}}},
    )
    print(json.dumps({"id": result["id"], "archived": True}))


def cmd_unarchive_page(args):
    config = load_config()
    token, _ = get_notion_creds(config, args.context)
    result = request(
        "PATCH",
        f"/pages/{args.page_id}",
        token=token,
        body={"archived": False, "properties": {"Status": {"select": {"name": "In Progress"}}}},
    )
    print(json.dumps({"id": result["id"], "archived": False, "url": page_url(result["id"])}))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def add_page_fields(p):
    """Add optional page property flags shared across commands."""
    p.add_argument("--status")
    p.add_argument("--description")
    p.add_argument("--todoist-url", dest="todoist_url")
    p.add_argument("--icloud-path", dest="icloud_path")
    p.add_argument("--gdrive-path", dest="gdrive_path")


def main():
    parser = argparse.ArgumentParser(
        description="PARA Notion CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # create-page
    p = sub.add_parser("create-page", help="Create a project page in a Notion database")
    p.add_argument("--context", required=True, choices=["work", "home"])
    p.add_argument("--id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--description", required=True)
    add_page_fields(p)
    p.set_defaults(func=cmd_create_page)

    # update-page
    p = sub.add_parser("update-page", help="Update properties on a Notion page")
    p.add_argument("page_id")
    p.add_argument("--context", required=True, choices=["work", "home"])
    p.add_argument("--name")
    p.add_argument("--id")
    add_page_fields(p)
    p.set_defaults(func=cmd_update_page)

    # archive-page
    p = sub.add_parser("archive-page", help="Archive a Notion page and set status to Done")
    p.add_argument("page_id")
    p.add_argument("--context", required=True, choices=["work", "home"])
    p.set_defaults(func=cmd_archive_page)

    # unarchive-page
    p = sub.add_parser("unarchive-page", help="Unarchive a Notion page and set status to In Progress")
    p.add_argument("page_id")
    p.add_argument("--context", required=True, choices=["work", "home"])
    p.set_defaults(func=cmd_unarchive_page)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
