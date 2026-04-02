"""
Unit tests for scripts/registry.py

Run with:
    python3 -m pytest tests/test_registry.py -v
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REGISTRY_SCRIPT = Path(__file__).parent.parent / "scripts" / "registry.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(*args, registry_dir=None, expect_error=False):
    """Run registry.py with the given args, optionally overriding REGISTRY_DIR via env."""
    import os
    env = os.environ.copy()
    if registry_dir:
        # Patch the registry path by monkeypatching the module-level constant via env
        env["_PARA_REGISTRY_DIR_OVERRIDE"] = str(registry_dir)

    result = subprocess.run(
        [sys.executable, str(REGISTRY_SCRIPT)] + list(args),
        capture_output=True,
        text=True,
        env=env,
    )
    if expect_error:
        assert result.returncode != 0, f"Expected non-zero exit, got 0. stdout: {result.stdout}"
        return json.loads(result.stderr)
    else:
        assert result.returncode == 0, f"Exit {result.returncode}. stderr: {result.stderr}"
        return json.loads(result.stdout) if result.stdout.strip() and result.stdout.strip()[0] in "{[" else result.stdout.strip()


@pytest.fixture
def reg_dir(tmp_path, monkeypatch):
    """Provide a temp registry dir and patch the script to use it."""
    registry_dir = tmp_path / ".project-registry"
    registry_dir.mkdir()
    registry_file = registry_dir / "registry.json"
    registry_file.write_text("[]")
    monkeypatch.setenv("_PARA_REGISTRY_DIR_OVERRIDE", str(registry_dir))
    return registry_dir


@pytest.fixture
def reg_dir_with_projects(reg_dir):
    """Pre-populate registry with a set of projects."""
    projects = [
        {
            "id": "W00001",
            "name": "Fraud Adjudication Agent",
            "description": "PydanticAI fraud case system",
            "status": "In Progress",
            "created_at": "2026-04-01T10:00:00Z",
            "updated_at": "2026-04-01T10:00:00Z",
            "closed_at": None,
            "todoist_project_id": "111",
            "notion_page_id": "aaa",
        },
        {
            "id": "W00002",
            "name": "Merchant Risk Model",
            "description": "Credit risk scoring for Nelo",
            "status": "Not Started",
            "created_at": "2026-04-02T10:00:00Z",
            "updated_at": "2026-04-02T10:00:00Z",
            "closed_at": None,
            "todoist_project_id": "222",
            "notion_page_id": "bbb",
        },
        {
            "id": "H00001",
            "name": "Kitchen Renovation",
            "description": "Full kitchen remodel",
            "status": "In Progress",
            "created_at": "2026-03-15T10:00:00Z",
            "updated_at": "2026-03-15T10:00:00Z",
            "closed_at": None,
            "todoist_project_id": "333",
            "notion_page_id": "ccc",
        },
        {
            "id": "W00003",
            "name": "Old Closed Project",
            "description": "Already done",
            "status": "Done",
            "created_at": "2026-01-01T10:00:00Z",
            "updated_at": "2026-03-01T10:00:00Z",
            "closed_at": "2026-03-01T10:00:00Z",
            "todoist_project_id": "444",
            "notion_page_id": "ddd",
        },
    ]
    (reg_dir / "registry.json").write_text(json.dumps(projects))
    return reg_dir


# ---------------------------------------------------------------------------
# check-name
# ---------------------------------------------------------------------------

class TestCheckName:
    def test_available_name(self, reg_dir_with_projects):
        result = run("check-name", "Brand New Project")
        assert result["available"] is True

    def test_rejects_duplicate_active_name(self, reg_dir_with_projects):
        error = run("check-name", "Fraud Adjudication Agent", expect_error=True)
        assert "already exists" in error["error"]

    def test_case_insensitive(self, reg_dir_with_projects):
        error = run("check-name", "fraud adjudication agent", expect_error=True)
        assert "already exists" in error["error"]

    def test_allows_name_of_done_project(self, reg_dir_with_projects):
        result = run("check-name", "Old Closed Project")
        assert result["available"] is True


# ---------------------------------------------------------------------------
# next-id
# ---------------------------------------------------------------------------

class TestNextId:
    def test_empty_registry_returns_00001(self, reg_dir):
        result = run("next-id", "W")
        assert result == "W00001"

    def test_increments_from_existing(self, reg_dir_with_projects):
        result = run("next-id", "W")
        assert result == "W00004"

    def test_home_prefix(self, reg_dir_with_projects):
        result = run("next-id", "H")
        assert result == "H00002"

    def test_independent_per_prefix(self, reg_dir_with_projects):
        w = run("next-id", "W")
        h = run("next-id", "H")
        assert w == "W00004"
        assert h == "H00002"

    def test_zero_pads_to_five_digits(self, reg_dir):
        # Manually insert a project with a high number
        projects = [{
            "id": "W00099", "name": "X", "description": "d", "status": "Not Started",
            "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
            "closed_at": None, "todoist_project_id": None, "notion_page_id": None,
        }]
        (reg_dir / "registry.json").write_text(json.dumps(projects))
        result = run("next-id", "W")
        assert result == "W00100"


# ---------------------------------------------------------------------------
# kebab
# ---------------------------------------------------------------------------

class TestFolderName:
    def test_basic(self, reg_dir):
        assert run("folder-name", "Fraud Adjudication Agent") == "Fraud Adjudication Agent"

    def test_preserves_casing(self, reg_dir):
        assert run("folder-name", "My Project") == "My Project"

    def test_preserves_special_chars(self, reg_dir):
        assert run("folder-name", "Q&A Research") == "Q&A Research"

    def test_strips_slash(self, reg_dir):
        assert run("folder-name", "Work/Home") == "WorkHome"

    def test_strips_colon(self, reg_dir):
        assert run("folder-name", "Phase: Alpha") == "Phase Alpha"

    def test_strips_both(self, reg_dir):
        assert run("folder-name", "A/B: Test") == "AB Test"

    def test_numbers_preserved(self, reg_dir):
        assert run("folder-name", "Project 42") == "Project 42"


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

class TestAdd:
    def test_adds_project(self, reg_dir):
        result = run(
            "add", "--id", "W00001", "--name", "Test Project",
            "--description", "A test", "--todoist-id", "999", "--notion-id", "xyz",
        )
        assert result["id"] == "W00001"
        assert result["name"] == "Test Project"
        assert result["status"] == "Not Started"
        assert result["todoist_project_id"] == "999"
        assert result["notion_page_id"] == "xyz"
        assert result["closed_at"] is None

    def test_persists_to_registry(self, reg_dir):
        run("add", "--id", "W00001", "--name", "Test", "--description", "desc")
        data = json.loads((reg_dir / "registry.json").read_text())
        assert len(data) == 1
        assert data[0]["id"] == "W00001"

    def test_rejects_duplicate_active_name(self, reg_dir_with_projects):
        error = run(
            "add", "--id", "W00004", "--name", "Fraud Adjudication Agent",
            "--description", "dupe", expect_error=True,
        )
        assert "already exists" in error["error"]

    def test_allows_duplicate_name_if_existing_is_done(self, reg_dir_with_projects):
        # "Old Closed Project" has status Done — should be allowed
        result = run(
            "add", "--id", "W00004", "--name", "Old Closed Project",
            "--description", "new version",
        )
        assert result["id"] == "W00004"

    def test_null_todoist_and_notion_by_default(self, reg_dir):
        result = run("add", "--id", "W00001", "--name", "X", "--description", "y")
        assert result["todoist_project_id"] is None
        assert result["notion_page_id"] is None


# ---------------------------------------------------------------------------
# find
# ---------------------------------------------------------------------------

class TestFind:
    def test_find_by_exact_id(self, reg_dir_with_projects):
        result = run("find", "W00001")
        assert result["name"] == "Fraud Adjudication Agent"

    def test_find_by_exact_name(self, reg_dir_with_projects):
        result = run("find", "Kitchen Renovation")
        assert result["id"] == "H00001"

    def test_find_by_partial_name(self, reg_dir_with_projects):
        result = run("find", "Merchant")
        assert result["id"] == "W00002"

    def test_find_case_insensitive_id(self, reg_dir_with_projects):
        result = run("find", "w00001")
        assert result["id"] == "W00001"

    def test_find_not_found(self, reg_dir_with_projects):
        error = run("find", "Nonexistent Project", expect_error=True)
        assert "Not found" in error["error"]

    def test_find_ambiguous(self, reg_dir_with_projects):
        # "Project" matches both "Fraud Adjudication Agent" description and "Merchant Risk Model" — but search is name/desc only in find
        # Add two projects with similar names to force ambiguity
        run("add", "--id", "W00010", "--name", "Risk Alpha", "--description", "d")
        run("add", "--id", "W00011", "--name", "Risk Beta", "--description", "d")
        error = run("find", "Risk", expect_error=True)
        assert "Ambiguous" in error["error"]


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestUpdate:
    def test_update_name(self, reg_dir_with_projects):
        result = run("update", "W00001", "--name", "Fraud Agent v2")
        assert result["name"] == "Fraud Agent v2"

    def test_update_status(self, reg_dir_with_projects):
        result = run("update", "W00001", "--status", "Done")
        assert result["status"] == "Done"

    def test_update_description(self, reg_dir_with_projects):
        result = run("update", "W00001", "--description", "New desc")
        assert result["description"] == "New desc"

    def test_update_todoist_id(self, reg_dir_with_projects):
        result = run("update", "W00001", "--todoist-id", "newid")
        assert result["todoist_project_id"] == "newid"

    def test_update_notion_id(self, reg_dir_with_projects):
        result = run("update", "W00001", "--notion-id", "newnotion")
        assert result["notion_page_id"] == "newnotion"

    def test_set_closed_at_now(self, reg_dir_with_projects):
        result = run("update", "W00001", "--closed-at", "now")
        assert result["closed_at"] is not None
        assert result["closed_at"].endswith("Z")

    def test_clear_closed_at(self, reg_dir_with_projects):
        run("update", "W00003", "--closed-at", "now")
        result = run("update", "W00003", "--clear-closed-at")
        assert result["closed_at"] is None

    def test_update_new_id(self, reg_dir_with_projects):
        result = run("update", "W00001", "--new-id", "H00010")
        assert result["id"] == "H00010"

    def test_rejects_invalid_status(self, reg_dir_with_projects):
        import subprocess, os
        env = os.environ.copy()
        env["_PARA_REGISTRY_DIR_OVERRIDE"] = str(reg_dir_with_projects)
        result = subprocess.run(
            [sys.executable, str(REGISTRY_SCRIPT), "update", "W00001", "--status", "Bogus"],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode != 0
        assert "Bogus" in result.stderr

    def test_rejects_duplicate_name(self, reg_dir_with_projects):
        error = run("update", "W00001", "--name", "Merchant Risk Model", expect_error=True)
        assert "already exists" in error["error"]

    def test_updated_at_changes(self, reg_dir_with_projects):
        original = run("find", "W00001")
        result = run("update", "W00001", "--status", "Done")
        assert result["updated_at"] >= original["updated_at"]

    def test_update_persists(self, reg_dir_with_projects):
        run("update", "W00001", "--name", "Persisted Name")
        data = json.loads((reg_dir_with_projects / "registry.json").read_text())
        w1 = next(p for p in data if p["id"] == "W00001")
        assert w1["name"] == "Persisted Name"


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

class TestList:
    def test_excludes_done_by_default(self, reg_dir_with_projects):
        result = run("list", "--json")
        ids = [p["id"] for p in result]
        assert "W00003" not in ids

    def test_includes_done_with_flag(self, reg_dir_with_projects):
        result = run("list", "--json", "--include-done")
        ids = [p["id"] for p in result]
        assert "W00003" in ids

    def test_filter_by_work_context(self, reg_dir_with_projects):
        result = run("list", "--json", "--context", "work")
        assert all(p["id"].startswith("W") for p in result)

    def test_filter_by_home_context(self, reg_dir_with_projects):
        result = run("list", "--json", "--context", "home")
        assert all(p["id"].startswith("H") for p in result)

    def test_filter_by_status(self, reg_dir_with_projects):
        result = run("list", "--json", "--status", "Not Started")
        assert all(p["status"] == "Not Started" for p in result)

    def test_sort_by_id(self, reg_dir_with_projects):
        result = run("list", "--json", "--sort", "id")
        ids = [p["id"] for p in result]
        assert ids == sorted(ids)

    def test_empty_result(self, reg_dir):
        result = run("list", "--json")
        assert result == []


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_by_name(self, reg_dir_with_projects):
        result = run("search", "Fraud", "--json")
        assert len(result) == 1
        assert result[0]["id"] == "W00001"
        assert result[0]["_match"] == "name"

    def test_search_by_description(self, reg_dir_with_projects):
        result = run("search", "Nelo", "--json")
        assert any(p["_match"] == "description" for p in result)

    def test_search_case_insensitive(self, reg_dir_with_projects):
        result = run("search", "fraud", "--json")
        assert len(result) == 1

    def test_search_no_results(self, reg_dir_with_projects):
        result = run("search", "xyzzy123", "--json")
        assert result == []

    def test_search_multiple_results(self, reg_dir_with_projects):
        # "risk" matches W00002 by name and W00001 by description ("fraud" → add a risk keyword)
        run("add", "--id", "H00002", "--name", "Home Risk Audit", "--description", "risk assessment")
        result = run("search", "risk", "--json")
        assert len(result) >= 2
