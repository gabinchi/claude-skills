#!/usr/bin/env python3
"""
PARA Projects — Obsidian vault CLI.

Usage:
    obsidian.py create --id ID --name NAME --description DESC [--context work|home]
                       [--status STATUS] [--linear-id ID] [--linear-url URL]
    obsidian.py rename --id ID --old-name OLD --new-name NEW [--new-id ID]
    obsidian.py update --id ID --name NAME [--status STATUS]
                       [--linear-id ID] [--linear-url URL] [--description DESC]
    obsidian.py archive --id ID --name NAME
    obsidian.py restore --id ID --name NAME

Config:   ~/Library/Mobile Documents/com~apple~CloudDocs/.project-registry/config.json
"""

import argparse
import json
import shutil
from pathlib import Path

from utils import err, load_config, expand_path, folder_name


def id_prefixes(project_id):
    """Folder/note name prefixes for a project: current '{id}_' and legacy '{id} - '."""
    return (f"{project_id}_", f"{project_id} - ")


def note_filename(project_id, name):
    return f"{folder_name(project_id, name)}.md"


def vault_paths(config):
    vault = expand_path(config["obsidian_vault_path"])
    archive = expand_path(
        config.get("obsidian_archive_path")
        or str(Path(config["obsidian_vault_path"]) / "Archive")
    )
    return vault, archive


def frontmatter(**fields):
    lines = ["---"]
    for key, value in fields.items():
        if value is None or value == "":
            lines.append(f"{key}:")
        else:
            # Quote values that need it
            text = str(value)
            if any(c in text for c in (":", "#", "{", "}", "[", "]", ",", "&", "*", "!", "|", ">", "'", '"', "%", "@", "`")) or text != text.strip():
                text = json.dumps(text)
            lines.append(f"{key}: {text}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def write_note(path, *, project_id, name, status, context, description, linear_id=None, linear_url=None):
    body = (description or "").rstrip() + "\n"
    content = frontmatter(
        id=project_id,
        name=name,
        status=status,
        context=context,
        linear_id=linear_id or "",
        linear_url=linear_url or "",
    ) + "\n" + body
    path.write_text(content, encoding="utf-8")


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        value = raw.strip()
        if value.startswith('"') and value.endswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        meta[key.strip()] = value
    return meta, parts[2].lstrip("\n")


def find_project_dir(root, project_id):
    """Find a project folder under root named '{id}_...' (or legacy '{id} - ...')."""
    if not root.exists():
        return None
    prefixes = id_prefixes(project_id)
    matches = [p for p in root.iterdir() if p.is_dir() and p.name.startswith(prefixes)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        err(f"Ambiguous Obsidian folders for {project_id}: {[m.name for m in matches]}")
    return None


def find_note(project_dir, project_id):
    """Find the project note '{id}_....md' (or legacy '{id} - ....md') inside the folder.

    Returns None when there is no project note. Never falls back to another
    note: callers rewrite and delete the note they get back.
    """
    prefixes = id_prefixes(project_id)
    notes = sorted(
        p for p in project_dir.glob("*.md") if p.is_file() and p.name.startswith(prefixes)
    )
    return notes[0] if notes else None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_create(args):
    config = load_config()
    vault, _ = vault_paths(config)
    vault.mkdir(parents=True, exist_ok=True)

    fname = folder_name(args.id, args.name)
    project_dir = vault / fname
    if project_dir.exists():
        err(f"Obsidian folder already exists: {project_dir}")

    project_dir.mkdir(parents=True)
    note_path = project_dir / note_filename(args.id, args.name)
    context = args.context or ("work" if args.id.upper().startswith("W") else "home")
    write_note(
        note_path,
        project_id=args.id,
        name=args.name,
        status=args.status or "Not Started",
        context=context,
        description=args.description,
        linear_id=args.linear_id,
        linear_url=args.linear_url,
    )
    print(json.dumps({
        "path": str(project_dir),
        "note": str(note_path),
        "folder_name": fname,
    }))


def cmd_rename(args):
    config = load_config()
    vault, archive = vault_paths(config)
    new_id = args.new_id or args.id

    # Prefer vault; fall back to archive for closed projects
    old_dir = find_project_dir(vault, args.id) or find_project_dir(archive, args.id)
    if old_dir is None:
        # Try exact old name
        candidate = vault / folder_name(args.id, args.old_name)
        if not candidate.exists():
            candidate = archive / folder_name(args.id, args.old_name)
        old_dir = candidate if candidate.exists() else None
    if old_dir is None:
        err(f"Obsidian folder not found for {args.id}")

    new_fname = folder_name(new_id, args.new_name)
    new_dir = old_dir.parent / new_fname
    if new_dir.exists() and new_dir.resolve() != old_dir.resolve():
        err(f"Target Obsidian folder already exists: {new_dir}")

    old_note = find_note(old_dir, args.id)
    if old_dir.resolve() != new_dir.resolve():
        old_dir.rename(new_dir)

    # Rename note file and update frontmatter
    if old_note is not None:
        note_in_new = new_dir / old_note.name
        meta, body = parse_frontmatter(note_in_new.read_text(encoding="utf-8"))
        new_note_path = new_dir / note_filename(new_id, args.new_name)
        context = meta.get("context") or ("work" if new_id.upper().startswith("W") else "home")
        if args.new_id:
            context = "work" if new_id.upper().startswith("W") else "home"
        write_note(
            new_note_path,
            project_id=new_id,
            name=args.new_name,
            status=meta.get("status") or "Not Started",
            context=context,
            description=body.rstrip("\n"),
            linear_id=meta.get("linear_id") or "",
            linear_url=meta.get("linear_url") or "",
        )
        if new_note_path.resolve() != note_in_new.resolve() and note_in_new.exists():
            note_in_new.unlink()

    print(json.dumps({
        "path": str(new_dir),
        "folder_name": new_fname,
        "old_path": str(old_dir),
        "id": new_id,
    }))


def cmd_update(args):
    config = load_config()
    vault, archive = vault_paths(config)

    project_dir = find_project_dir(vault, args.id) or find_project_dir(archive, args.id)
    if project_dir is None and args.name:
        for root in (vault, archive):
            candidate = root / folder_name(args.id, args.name)
            if candidate.exists():
                project_dir = candidate
                break
    if project_dir is None:
        err(f"Obsidian folder not found for {args.id}")

    # No project note yet (e.g. a folder of loose notes): create one and leave
    # the other files alone.
    note = find_note(project_dir, args.id)
    if note is None and not args.name:
        err(f"No project note in {project_dir}; pass --name to create one")
    meta, body = parse_frontmatter(note.read_text(encoding="utf-8")) if note else ({}, "")
    name = args.name or meta.get("name") or ""
    status = args.status if args.status is not None else (meta.get("status") or "Not Started")
    context = meta.get("context") or ("work" if args.id.upper().startswith("W") else "home")
    linear_id = args.linear_id if args.linear_id is not None else meta.get("linear_id", "")
    linear_url = args.linear_url if args.linear_url is not None else meta.get("linear_url", "")
    description = args.description if args.description is not None else body.rstrip("\n")

    # If name changed relative to note filename, rename note
    target_note = project_dir / note_filename(args.id, name)
    write_note(
        target_note,
        project_id=args.id,
        name=name,
        status=status,
        context=context,
        description=description,
        linear_id=linear_id,
        linear_url=linear_url,
    )
    if note is not None and target_note != note and note.exists():
        note.unlink()

    print(json.dumps({
        "path": str(project_dir),
        "note": str(target_note),
        "status": status,
        "created": note is None,
    }))


def cmd_archive(args):
    config = load_config()
    vault, archive = vault_paths(config)
    archive.mkdir(parents=True, exist_ok=True)

    project_dir = find_project_dir(vault, args.id)
    if project_dir is None:
        candidate = vault / folder_name(args.id, args.name)
        project_dir = candidate if candidate.exists() else None
    if project_dir is None:
        err(f"Obsidian folder not found for {args.id}")

    dest = archive / project_dir.name
    if dest.exists():
        err(f"Archive destination already exists: {dest}")
    shutil.move(str(project_dir), str(dest))
    print(json.dumps({"path": str(dest), "from": str(project_dir)}))


def cmd_restore(args):
    config = load_config()
    vault, archive = vault_paths(config)
    vault.mkdir(parents=True, exist_ok=True)

    project_dir = find_project_dir(archive, args.id)
    if project_dir is None:
        candidate = archive / folder_name(args.id, args.name)
        project_dir = candidate if candidate.exists() else None
    if project_dir is None:
        err(f"Archived Obsidian folder not found for {args.id}")

    dest = vault / project_dir.name
    if dest.exists():
        err(f"Vault destination already exists: {dest}")
    shutil.move(str(project_dir), str(dest))
    print(json.dumps({"path": str(dest), "from": str(project_dir)}))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PARA Obsidian vault CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create", help="Create a project folder and note in the vault")
    p.add_argument("--id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--context", choices=["work", "home"])
    p.add_argument("--status", default="Not Started",
                   choices=["Not Started", "In Progress", "Done"])
    p.add_argument("--linear-id", dest="linear_id")
    p.add_argument("--linear-url", dest="linear_url")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("rename", help="Rename project folder and note (optional --new-id for context move)")
    p.add_argument("--id", required=True)
    p.add_argument("--old-name", required=True, dest="old_name")
    p.add_argument("--new-name", required=True, dest="new_name")
    p.add_argument("--new-id", dest="new_id", help="New project ID (used by Move)")
    p.set_defaults(func=cmd_rename)

    p = sub.add_parser("update", help="Update note frontmatter / body")
    p.add_argument("--id", required=True)
    p.add_argument("--name")
    p.add_argument("--status", choices=["Not Started", "In Progress", "Done"])
    p.add_argument("--description")
    p.add_argument("--linear-id", dest="linear_id")
    p.add_argument("--linear-url", dest="linear_url")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("archive", help="Move project folder to Archive/")
    p.add_argument("--id", required=True)
    p.add_argument("--name", required=True)
    p.set_defaults(func=cmd_archive)

    p = sub.add_parser("restore", help="Move project folder from Archive/ back to vault")
    p.add_argument("--id", required=True)
    p.add_argument("--name", required=True)
    p.set_defaults(func=cmd_restore)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
