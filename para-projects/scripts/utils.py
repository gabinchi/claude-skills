"""
PARA Projects — Shared utilities.

Imported by registry.py, linear.py, obsidian.py, and setup.py.
"""

import json
import os
import re
import sys
import unicodedata
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

LINEAR_API = "https://api.linear.app/graphql"


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


def expand_path(path_str):
    """Expand ~ in a config path string and return a Path."""
    return Path(os.path.expanduser(path_str))


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------

def slugify(name):
    """Lowercase ASCII slug: each run of characters other than a-z/0-9 becomes one underscore."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")


def folder_name(project_id, name):
    """Project folder name, e.g. 'W00001_go_to_market_plan'."""
    return f"{project_id}_{slugify(name)}"
