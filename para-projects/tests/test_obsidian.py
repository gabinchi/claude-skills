"""
Unit tests for scripts/obsidian.py

Run with:
    python3 -m pytest tests/test_obsidian.py -v
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

OBSIDIAN_SCRIPT = Path(__file__).parent.parent / "scripts" / "obsidian.py"


def run(*args, registry_dir=None, expect_error=False):
    env = os.environ.copy()
    if registry_dir:
        env["_PARA_REGISTRY_DIR_OVERRIDE"] = str(registry_dir)
    result = subprocess.run(
        [sys.executable, str(OBSIDIAN_SCRIPT)] + list(args),
        capture_output=True,
        text=True,
        env=env,
    )
    if expect_error:
        assert result.returncode != 0, f"Expected non-zero exit, got 0. stdout: {result.stdout}"
        return json.loads(result.stderr)
    assert result.returncode == 0, f"Exit {result.returncode}. stderr: {result.stderr}\nstdout: {result.stdout}"
    return json.loads(result.stdout) if result.stdout.strip() else {}


@pytest.fixture
def vault_env(tmp_path, monkeypatch):
    """Temp registry config pointing Obsidian paths at a temp vault."""
    registry_dir = tmp_path / ".project-registry"
    registry_dir.mkdir()
    vault = tmp_path / "projects"
    archive = vault / "Archive"
    vault.mkdir()
    config = {
        "default_context": "home",
        "obsidian_vault_path": str(vault),
        "obsidian_archive_path": str(archive),
        "gdrive_projects_path": str(tmp_path / "gdrive"),
        "gdrive_archive_path": str(tmp_path / "gdrive-archive"),
        "linear": {
            "api_key_env": "LINEAR_API_KEY",
            "teams": {"work": {"id": "w", "name": "W"}, "home": {"id": "h", "name": "H"}},
            "statuses": {"Not Started": "s1", "In Progress": "s2", "Done": "s3"},
        },
    }
    (registry_dir / "config.json").write_text(json.dumps(config))
    (registry_dir / "registry.json").write_text("[]")
    monkeypatch.setenv("_PARA_REGISTRY_DIR_OVERRIDE", str(registry_dir))
    return {"registry_dir": registry_dir, "vault": vault, "archive": archive}


class TestCreate:
    def test_creates_folder_and_note(self, vault_env):
        result = run(
            "create",
            "--id", "H00001",
            "--name", "Kitchen Renovation",
            "--description", "Full remodel",
            "--context", "home",
            registry_dir=vault_env["registry_dir"],
        )
        folder = vault_env["vault"] / "H00001 - Kitchen Renovation"
        note = folder / "H00001 - Kitchen Renovation.md"
        assert folder.is_dir()
        assert note.is_file()
        assert result["folder_name"] == "H00001 - Kitchen Renovation"
        text = note.read_text()
        assert "id: H00001" in text
        assert "name: Kitchen Renovation" in text
        assert "status: Not Started" in text
        assert "Full remodel" in text

    def test_rejects_duplicate_folder(self, vault_env):
        args = [
            "create", "--id", "H00001", "--name", "Dup",
            "--description", "d", "--context", "home",
        ]
        run(*args, registry_dir=vault_env["registry_dir"])
        error = run(*args, registry_dir=vault_env["registry_dir"], expect_error=True)
        assert "already exists" in error["error"]

    def test_strips_illegal_chars_in_folder(self, vault_env):
        # Name with chars that would be illegal if not stripped — create uses sanitize
        # check-name rejects / and : at registry level; sanitize still strips if passed
        result = run(
            "create",
            "--id", "W00001",
            "--name", "Q&A Research",
            "--description", "notes",
            "--context", "work",
            registry_dir=vault_env["registry_dir"],
        )
        assert (vault_env["vault"] / "W00001 - Q&A Research").is_dir()
        assert result["folder_name"] == "W00001 - Q&A Research"


class TestRename:
    def test_rename_folder_and_note(self, vault_env):
        run(
            "create", "--id", "H00001", "--name", "Old Name",
            "--description", "body text", "--context", "home",
            registry_dir=vault_env["registry_dir"],
        )
        # Leave an extra file that should survive
        extra = vault_env["vault"] / "H00001 - Old Name" / "scratch.txt"
        extra.write_text("keep me")

        result = run(
            "rename",
            "--id", "H00001",
            "--old-name", "Old Name",
            "--new-name", "New Name",
            registry_dir=vault_env["registry_dir"],
        )
        new_dir = vault_env["vault"] / "H00001 - New Name"
        assert new_dir.is_dir()
        assert not (vault_env["vault"] / "H00001 - Old Name").exists()
        assert (new_dir / "H00001 - New Name.md").is_file()
        assert (new_dir / "scratch.txt").read_text() == "keep me"
        text = (new_dir / "H00001 - New Name.md").read_text()
        assert "name: New Name" in text
        assert "body text" in text
        assert result["folder_name"] == "H00001 - New Name"

    def test_rename_with_new_id(self, vault_env):
        run(
            "create", "--id", "H00001", "--name", "Move Me",
            "--description", "d", "--context", "home",
            registry_dir=vault_env["registry_dir"],
        )
        result = run(
            "rename",
            "--id", "H00001",
            "--old-name", "Move Me",
            "--new-name", "Move Me",
            "--new-id", "W00005",
            registry_dir=vault_env["registry_dir"],
        )
        new_dir = vault_env["vault"] / "W00005 - Move Me"
        assert new_dir.is_dir()
        text = (new_dir / "W00005 - Move Me.md").read_text()
        assert "id: W00005" in text
        assert "context: work" in text
        assert result["id"] == "W00005"


class TestUpdate:
    def test_update_status_and_linear(self, vault_env):
        run(
            "create", "--id", "H00001", "--name", "Status Proj",
            "--description", "d", "--context", "home",
            registry_dir=vault_env["registry_dir"],
        )
        result = run(
            "update",
            "--id", "H00001",
            "--name", "Status Proj",
            "--status", "In Progress",
            "--linear-id", "lin-1",
            "--linear-url", "https://linear.app/p/lin-1",
            registry_dir=vault_env["registry_dir"],
        )
        assert result["status"] == "In Progress"
        text = (vault_env["vault"] / "H00001 - Status Proj" / "H00001 - Status Proj.md").read_text()
        assert "status: In Progress" in text
        assert "linear_id: lin-1" in text
        assert "https://linear.app/p/lin-1" in text


class TestArchiveRestore:
    def test_archive_and_restore(self, vault_env):
        run(
            "create", "--id", "H00001", "--name", "Archive Me",
            "--description", "d", "--context", "home",
            registry_dir=vault_env["registry_dir"],
        )
        archived = run(
            "archive",
            "--id", "H00001",
            "--name", "Archive Me",
            registry_dir=vault_env["registry_dir"],
        )
        dest = vault_env["archive"] / "H00001 - Archive Me"
        assert dest.is_dir()
        assert not (vault_env["vault"] / "H00001 - Archive Me").exists()
        assert archived["path"] == str(dest)

        restored = run(
            "restore",
            "--id", "H00001",
            "--name", "Archive Me",
            registry_dir=vault_env["registry_dir"],
        )
        back = vault_env["vault"] / "H00001 - Archive Me"
        assert back.is_dir()
        assert not dest.exists()
        assert restored["path"] == str(back)

    def test_archive_missing_errors(self, vault_env):
        error = run(
            "archive",
            "--id", "H00999",
            "--name", "Nope",
            registry_dir=vault_env["registry_dir"],
            expect_error=True,
        )
        assert "not found" in error["error"].lower()
