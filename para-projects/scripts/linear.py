#!/usr/bin/env python3
"""
PARA Projects — Linear CLI.

Usage:
    linear.py create-project --context work|home --id ID --name NAME [--description DESC] [--status STATUS]
    linear.py update-project PROJECT_ID [--name NAME] [--description DESC] [--status STATUS]
                                       [--context work|home]

Requires: LINEAR_API_KEY env var (configurable via linear.api_key_env in config.json)
Config:   ~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/config.json
"""

import argparse
import json
import os
import urllib.request

from utils import err, load_config, LINEAR_API


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_token(config):
    env_name = config.get("linear", {}).get("api_key_env", "LINEAR_API_KEY")
    token = os.environ.get(env_name)
    if not token:
        err(f"{env_name} environment variable is not set")
    return token


def graphql(token, query, variables=None):
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
    try:
        with urllib.request.urlopen(req) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err(f"HTTP {e.code} from Linear: {e.read().decode()}")
    if "errors" in payload:
        messages = "; ".join(e.get("message", str(e)) for e in payload["errors"])
        err(f"Linear GraphQL error: {messages}")
    return payload.get("data", {})


def team_id_for_context(config, context):
    try:
        tid = config["linear"]["teams"][context]["id"]
    except KeyError:
        err(f"Linear team for '{context}' not set in config — run setup.py")
    if not tid:
        err(f"Linear team ID for '{context}' is empty — run setup.py")
    return tid


def status_id_for(config, para_status):
    if not para_status:
        return None
    statuses = config.get("linear", {}).get("statuses", {})
    sid = statuses.get(para_status)
    if not sid:
        err(
            f"Linear status ID for '{para_status}' not set in config — run setup.py"
        )
    return sid


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_create_project(args):
    config = load_config()
    token = get_token(config)
    team_id = team_id_for_context(config, args.context)

    project_input = {
        "name": f"{args.id} - {args.name}",
        "teamIds": [team_id],
    }
    if args.description:
        project_input["description"] = args.description
    status = args.status or "Not Started"
    project_input["statusId"] = status_id_for(config, status)

    data = graphql(
        token,
        """
        mutation ProjectCreate($input: ProjectCreateInput!) {
          projectCreate(input: $input) {
            success
            project {
              id
              name
              url
            }
          }
        }
        """,
        {"input": project_input},
    )
    result = data.get("projectCreate", {})
    if not result.get("success"):
        err("Linear projectCreate reported success=false")
    project = result["project"]
    print(json.dumps({
        "id": project["id"],
        "name": project["name"],
        "url": project["url"],
    }))


def cmd_update_project(args):
    config = load_config()
    token = get_token(config)

    project_input = {}
    if args.name is not None:
        project_input["name"] = args.name
    if args.description is not None:
        project_input["description"] = args.description
    if args.status is not None:
        project_input["statusId"] = status_id_for(config, args.status)
    if args.context is not None:
        project_input["teamIds"] = [team_id_for_context(config, args.context)]

    if not project_input:
        err(
            "No fields to update — provide at least one of: "
            "--name, --description, --status, --context"
        )

    data = graphql(
        token,
        """
        mutation ProjectUpdate($id: String!, $input: ProjectUpdateInput!) {
          projectUpdate(id: $id, input: $input) {
            success
            project {
              id
              name
              url
            }
          }
        }
        """,
        {"id": args.project_id, "input": project_input},
    )
    result = data.get("projectUpdate", {})
    if not result.get("success"):
        err("Linear projectUpdate reported success=false")
    project = result["project"]
    print(json.dumps({
        "id": project["id"],
        "name": project["name"],
        "url": project["url"],
    }))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PARA Linear CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-project", help="Create a Linear project for a context team")
    p.add_argument("--context", required=True, choices=["work", "home"])
    p.add_argument("--id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--status", default="Not Started",
                   choices=["Not Started", "In Progress", "Done"])
    p.set_defaults(func=cmd_create_project)

    p = sub.add_parser("update-project", help="Update a Linear project")
    p.add_argument("project_id")
    p.add_argument("--name")
    p.add_argument("--description")
    p.add_argument("--status", choices=["Not Started", "In Progress", "Done"])
    p.add_argument("--context", choices=["work", "home"],
                   help="Move the project to this context's team")
    p.set_defaults(func=cmd_update_project)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
