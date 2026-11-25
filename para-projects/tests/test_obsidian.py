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
        folder = vault_env["vault"] / "H00001_kitchen_renovation"
        note = folder / "H00001_kitchen_renovation.md"
        assert folder.is_dir()
        assert note.is_file()
        assert result["folder_name"] == "H00001_kitchen_renovation"
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

    def test_folder_name_has_no_spaces_or_punctuation(self, vault_env):
        result = run(
            "create",
            "--id", "W00001",
            "--name", "Q&A Research - Phase 2",
            "--description", "notes",
            "--context", "work",
            registry_dir=vault_env["registry_dir"],
        )
        assert (vault_env["vault"] / "W00001_q_a_research_phase_2").is_dir()
        assert result["folder_name"] == "W00001_q_a_research_phase_2"


class TestRename:
    def test_rename_folder_and_note(self, vault_env):
        run(
            "create", "--id", "H00001", "--name", "Old Name",
            "--description", "body text", "--context", "home",
            registry_dir=vault_env["registry_dir"],
        )
        # Leave an extra file that should survive
        extra = vault_env["vault"] / "H00001_old_name" / "scratch.txt"
        extra.write_text("keep me")

        result = run(
            "rename",
            "--id", "H00001",
            "--old-name", "Old Name",
            "--new-name", "New Name",
            registry_dir=vault_env["registry_dir"],
        )
        new_dir = vault_env["vault"] / "H00001_new_name"
        assert new_dir.is_dir()
        assert not (vault_env["vault"] / "H00001_old_name").exists()
        assert (new_dir / "H00001_new_name.md").is_file()
        assert not (new_dir / "H00001_old_name.md").exists()
        assert (new_dir / "scratch.txt").read_text() == "keep me"
        text = (new_dir / "H00001_new_name.md").read_text()
        assert "name: New Name" in text
        assert "body text" in text
        assert result["folder_name"] == "H00001_new_name"

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
        new_dir = vault_env["vault"] / "W00005_move_me"
        assert new_dir.is_dir()
        text = (new_dir / "W00005_move_me.md").read_text()
        assert "id: W00005" in text
        assert "context: work" in text
        assert result["id"] == "W00005"

    def test_rename_without_project_note_keeps_other_notes(self, vault_env):
        folder = vault_env["vault"] / "W00001_loose_notes"
        folder.mkdir()
        other = folder / "Meeting with Greg.md"
        other.write_text("# Greg\n\nnotes")

        run(
            "rename", "--id", "W00001",
            "--old-name", "Loose Notes", "--new-name", "Renamed",
            registry_dir=vault_env["registry_dir"],
        )
        new_dir = vault_env["vault"] / "W00001_renamed"
        assert (new_dir / "Meeting with Greg.md").read_text() == "# Greg\n\nnotes"
        assert sorted(p.name for p in new_dir.iterdir()) == ["Meeting with Greg.md"]

    def test_migrates_legacy_folder_name(self, vault_env):
        legacy = vault_env["vault"] / "W00001 - Go to Market Plan"
        legacy.mkdir()
        (legacy / "W00001 - Go to Market Plan.md").write_text(
            "---\nid: W00001\nname: Go to Market Plan\nstatus: In Progress\ncontext: work\n"
            "linear_id: lin-1\nlinear_url:\n---\n\nThe plan\n"
        )
        (legacy / "Getting out There.md").write_text("keep")

        run(
            "rename", "--id", "W00001",
            "--old-name", "Go to Market Plan", "--new-name", "Go to Market Plan",
            registry_dir=vault_env["registry_dir"],
        )
        new_dir = vault_env["vault"] / "W00001_go_to_market_plan"
        assert not legacy.exists()
        assert sorted(p.name for p in new_dir.iterdir()) == [
            "Getting out There.md", "W00001_go_to_market_plan.md",
        ]
        text = (new_dir / "W00001_go_to_market_plan.md").read_text()
        assert "status: In Progress" in text
        assert "linear_id: lin-1" in text
        assert "The plan" in text
        assert (new_dir / "Getting out There.md").read_text() == "keep"


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
        assert result["created"] is False
        text = (vault_env["vault"] / "H00001_status_proj" / "H00001_status_proj.md").read_text()
        assert "status: In Progress" in text
        assert "linear_id: lin-1" in text
        assert "https://linear.app/p/lin-1" in text

    def test_update_without_project_note_creates_one_and_keeps_other_notes(self, vault_env):
        # Regression: update used to pick any .md as the project note, rewrite
        # it under the project-note name and delete the original.
        folder = vault_env["vault"] / "W00001_go_to_market_plan"
        folder.mkdir()
        other = folder / "Getting out There.md"
        original = "# Getting out there\n\nNotes I care about\n"
        other.write_text(original)

        result = run(
            "update", "--id", "W00001", "--name", "Go to Market Plan",
            "--status", "In Progress",
            registry_dir=vault_env["registry_dir"],
        )
        assert result["created"] is True
        assert other.read_text() == original
        note = folder / "W00001_go_to_market_plan.md"
        text = note.read_text()
        assert "status: In Progress" in text
        assert "Notes I care about" not in text

    def test_update_without_project_note_requires_name(self, vault_env):
        folder = vault_env["vault"] / "W00001_x"
        folder.mkdir()
        (folder / "other.md").write_text("keep")
        error = run(
            "update", "--id", "W00001", "--status", "Done",
            registry_dir=vault_env["registry_dir"], expect_error=True,
        )
        assert "--name" in error["error"]
        assert (folder / "other.md").read_text() == "keep"

    def test_update_finds_legacy_note(self, vault_env):
        legacy = vault_env["vault"] / "H00001 - Old Style"
        legacy.mkdir()
        (legacy / "H00001 - Old Style.md").write_text(
            "---\nid: H00001\nname: Old Style\nstatus: Not Started\ncontext: home\n"
            "linear_id:\nlinear_url:\n---\n\nbody\n"
        )
        result = run(
            "update", "--id", "H00001", "--status", "Done",
            registry_dir=vault_env["registry_dir"],
        )
        assert result["created"] is False
        notes = sorted(p.name for p in legacy.iterdir())
        assert notes == ["H00001_old_style.md"]
        assert "status: Done" in (legacy / "H00001_old_style.md").read_text()


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
        dest = vault_env["archive"] / "H00001_archive_me"
        assert dest.is_dir()
        assert not (vault_env["vault"] / "H00001_archive_me").exists()
        assert archived["path"] == str(dest)

        restored = run(
            "restore",
            "--id", "H00001",
            "--name", "Archive Me",
            registry_dir=vault_env["registry_dir"],
        )
        back = vault_env["vault"] / "H00001_archive_me"
        assert back.is_dir()
        assert not dest.exists()
        assert restored["path"] == str(back)

    def test_archive_legacy_folder(self, vault_env):
        legacy = vault_env["vault"] / "H00002 - Legacy"
        legacy.mkdir()
        run(
            "archive", "--id", "H00002", "--name", "Legacy",
            registry_dir=vault_env["registry_dir"],
        )
        assert (vault_env["archive"] / "H00002 - Legacy").is_dir()

    def test_archive_missing_errors(self, vault_env):
        error = run(
            "archive",
            "--id", "H00999",
            "--name", "Nope",
            registry_dir=vault_env["registry_dir"],
            expect_error=True,
        )
        assert "not found" in error["error"].lower()

    def test_id_prefix_does_not_match_longer_id(self, vault_env):
        (vault_env["vault"] / "H000010_other").mkdir()
        error = run(
            "archive", "--id", "H00001", "--name", "Nope",
            registry_dir=vault_env["registry_dir"], expect_error=True,
        )
        assert "not found" in error["error"].lower()
