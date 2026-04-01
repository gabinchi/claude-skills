"""
PARA Projects — Shared utilities.

Imported by registry.py, todoist.py, notion.py, and setup.py.
"""

import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_override = os.environ.get("_PARA_REGISTRY_DIR_OVERRIDE")
REGISTRY_DIR = (
    Path(_override)
    if _override
    else Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/.project-registry"
)
CONFIG_PATH = REGISTRY_DIR / "config.json"
REGISTRY_FILE = REGISTRY_DIR / "registry.json"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

TODOIST_REST_BASE = "https://api.todoist.com/api/v1"
TODOIST_SYNC_BASE = "https://api.todoist.com/sync/v9"


def err(msg):
    """Print a JSON error to stderr and exit non-zero."""
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(1)


def load_config():
    """Load config.json from the registry directory."""
    if not CONFIG_PATH.exists():
        err(f"Config not found at {CONFIG_PATH}. Run setup.py first.")
    with open(CONFIG_PATH) as f:
        return json.load(f)


def unwrap_list(data):
    """Unwrap an API response that may be a plain list or a dict wrapping one."""
    if isinstance(data, list):
        return data
    for key in ("results", "projects", "tasks", "items"):
        if key in data and isinstance(data[key], list):
            return data[key]
    return []
