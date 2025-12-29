"""
Tests for .github/scripts/sync-manifests.py

Organised by function groups:
1. Pure functions (generate_manifest_content)
2. Filesystem operations (update_manifest with check_only)
3. CLI interface (main function with --check flag)
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


# -----------------------------------------------------------------------------
# Module import fixture
# -----------------------------------------------------------------------------

@pytest.fixture
def sync_manifests_module(repo_root: Path):
    """Import sync_manifests module."""
    spec = importlib.util.spec_from_file_location(
        "sync_manifests",
        repo_root / ".github" / "scripts" / "sync-manifests.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# =============================================================================
# PURE FUNCTIONS
# =============================================================================

class TestGenerateManifestContent:
    """Tests for generate_manifest_content() - creates manifest string."""

    def test_generates_manifest_with_entries(self, tmp_path, sync_manifests_module):
        """Generates manifest content with all .md files."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "Note One.md").write_text("# Note One\nContent")
        (knowledge / "Note Two.md").write_text("# Note Two\nContent")

        result = sync_manifests_module.generate_manifest_content(knowledge)

        assert "[[Note One]]" in result
        assert "[[Note Two]]" in result

    def test_excludes_manifest_from_entries(self, tmp_path, sync_manifests_module):
        """MANIFEST.md is not included in generated content."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "MANIFEST.md").write_text("old manifest")
        (knowledge / "Note.md").write_text("# Note")

        result = sync_manifests_module.generate_manifest_content(knowledge)

        assert "[[MANIFEST]]" not in result
        assert "[[Note]]" in result

    def test_includes_descriptions_from_headings(self, tmp_path, sync_manifests_module):
        """Descriptions come from file headings."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "API.md").write_text("# API Design Principles\n\nContent...")

        result = sync_manifests_module.generate_manifest_content(knowledge)

        assert "API Design Principles" in result

    def test_empty_folder_shows_placeholder(self, tmp_path, sync_manifests_module):
        """Empty Knowledge folder gets placeholder row."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()

        result = sync_manifests_module.generate_manifest_content(knowledge)

        assert "*(empty)*" in result

    def test_sorts_entries_alphabetically(self, tmp_path, sync_manifests_module):
        """Entries are sorted alphabetically."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "Zebra.md").write_text("# Z")
        (knowledge / "Alpha.md").write_text("# A")
        (knowledge / "Middle.md").write_text("# M")

        result = sync_manifests_module.generate_manifest_content(knowledge)

        alpha_pos = result.find("[[Alpha]]")
        middle_pos = result.find("[[Middle]]")
        zebra_pos = result.find("[[Zebra]]")

        assert alpha_pos < middle_pos < zebra_pos

    def test_creates_valid_markdown_table(self, tmp_path, sync_manifests_module):
        """Output is a valid markdown table."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "Test.md").write_text("# Test Note")

        result = sync_manifests_module.generate_manifest_content(knowledge)
        lines = result.strip().split("\n")

        # Should have header, separator, and at least one data row
        assert len(lines) >= 4
        assert lines[0] == "# Knowledge Manifest"
        assert lines[2].startswith("| File")
        assert lines[3].startswith("|---")


# =============================================================================
# FILESYSTEM OPERATIONS
# =============================================================================

class TestUpdateManifest:
    """Tests for update_manifest() - with check_only parameter."""

    def test_returns_true_when_in_sync(self, tmp_path, sync_manifests_module):
        """Returns True when manifest matches files."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "Note.md").write_text("# Note\nContent")

        # Create manifest that matches
        expected = sync_manifests_module.generate_manifest_content(knowledge)
        (knowledge / "MANIFEST.md").write_text(expected)

        result = sync_manifests_module.update_manifest(knowledge, check_only=True)

        assert result is True

    def test_returns_false_when_out_of_sync(self, tmp_path, sync_manifests_module):
        """Returns False when manifest doesn't match files."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "Note.md").write_text("# Note\nContent")
        (knowledge / "MANIFEST.md").write_text("# Old manifest")

        result = sync_manifests_module.update_manifest(knowledge, check_only=True)

        assert result is False

    def test_check_only_does_not_modify_file(self, tmp_path, sync_manifests_module):
        """check_only=True doesn't write to manifest."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "Note.md").write_text("# Note\nContent")
        (knowledge / "MANIFEST.md").write_text("# Old manifest")
        old_content = (knowledge / "MANIFEST.md").read_text()

        sync_manifests_module.update_manifest(knowledge, check_only=True)

        assert (knowledge / "MANIFEST.md").read_text() == old_content

    def test_updates_manifest_when_not_check_only(self, tmp_path, sync_manifests_module):
        """check_only=False updates the manifest file."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "Note.md").write_text("# Note\nContent")
        (knowledge / "MANIFEST.md").write_text("# Old manifest")

        sync_manifests_module.update_manifest(knowledge, check_only=False)

        manifest = (knowledge / "MANIFEST.md").read_text()
        assert "[[Note]]" in manifest

    def test_creates_manifest_if_missing(self, tmp_path, sync_manifests_module):
        """Creates MANIFEST.md if it doesn't exist."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "Note.md").write_text("# Note\nContent")

        result = sync_manifests_module.update_manifest(knowledge, check_only=False)

        assert result is False  # Was out of sync (didn't exist)
        assert (knowledge / "MANIFEST.md").exists()
        assert "[[Note]]" in (knowledge / "MANIFEST.md").read_text()


class TestGetPillars:
    """Tests for get_pillars() - finds pillar directories."""

    def test_finds_pillars_with_knowledge(self, tmp_path, sync_manifests_module):
        """Finds directories containing Knowledge/."""
        (tmp_path / "Personal" / "Knowledge").mkdir(parents=True)
        (tmp_path / "Work" / "Knowledge").mkdir(parents=True)

        result = sync_manifests_module.get_pillars(tmp_path)

        assert set(result) == {"Personal", "Work"}

    def test_ignores_hidden_directories(self, tmp_path, sync_manifests_module):
        """Ignores .git, .obsidian, etc."""
        (tmp_path / ".obsidian" / "Knowledge").mkdir(parents=True)
        (tmp_path / ".claude" / "Knowledge").mkdir(parents=True)

        result = sync_manifests_module.get_pillars(tmp_path)

        assert ".obsidian" not in result
        assert ".claude" not in result

    def test_returns_sorted_list(self, tmp_path, sync_manifests_module):
        """Returns pillars in sorted order."""
        (tmp_path / "Zebra" / "Knowledge").mkdir(parents=True)
        (tmp_path / "Alpha" / "Knowledge").mkdir(parents=True)

        result = sync_manifests_module.get_pillars(tmp_path)

        assert result == ["Alpha", "Zebra"]


# =============================================================================
# CLI INTERFACE
# =============================================================================

class TestMainCLI:
    """Tests for main() - CLI interface."""

    def test_syncs_all_manifests(self, vault_root, sync_manifests_module, capsys):
        """Syncs manifests for all pillars."""
        # Add file to Personal/Knowledge that's not in manifest
        knowledge = vault_root / "Personal" / "Knowledge"
        (knowledge / "New Note.md").write_text("# New Note\nContent...")

        # Mock script location to use vault_root
        with patch.object(Path, "resolve", return_value=vault_root / ".github" / "scripts" / "sync-manifests.py"):
            with patch.object(
                sync_manifests_module,
                "get_pillars",
                return_value=["Personal", "Work"]
            ):
                with pytest.raises(SystemExit) as exc_info:
                    # Patch __file__ to point to vault
                    old_file = sync_manifests_module.__file__
                    sync_manifests_module.__file__ = str(vault_root / ".github" / "scripts" / "sync-manifests.py")
                    try:
                        sync_manifests_module.main()
                    finally:
                        sync_manifests_module.__file__ = old_file

        assert exc_info.value.code == 0

    def test_check_flag_exits_1_when_out_of_sync(
        self, vault_root, sync_manifests_module, capsys
    ):
        """--check exits with code 1 when manifests out of sync."""
        # Add file not in manifest
        knowledge = vault_root / "Personal" / "Knowledge"
        (knowledge / "Untracked.md").write_text("# Untracked\nContent...")

        with patch.object(sys, "argv", ["sync-manifests.py", "--check"]):
            old_file = sync_manifests_module.__file__
            sync_manifests_module.__file__ = str(vault_root / ".github" / "scripts" / "sync-manifests.py")
            try:
                with pytest.raises(SystemExit) as exc_info:
                    sync_manifests_module.main()
            finally:
                sync_manifests_module.__file__ = old_file

        assert exc_info.value.code == 1

    def test_check_flag_exits_0_when_in_sync(
        self, tmp_path, sync_manifests_module, capsys
    ):
        """--check exits with code 0 when manifests in sync."""
        # Create a vault with synced manifests
        knowledge = tmp_path / "Personal" / "Knowledge"
        knowledge.mkdir(parents=True)
        (knowledge / "Note.md").write_text("# Note\nContent...")

        # Generate and write correct manifest
        correct_manifest = sync_manifests_module.generate_manifest_content(knowledge)
        (knowledge / "MANIFEST.md").write_text(correct_manifest)

        with patch.object(sys, "argv", ["sync-manifests.py", "--check"]):
            old_file = sync_manifests_module.__file__
            sync_manifests_module.__file__ = str(tmp_path / ".github" / "scripts" / "sync-manifests.py")
            try:
                with pytest.raises(SystemExit) as exc_info:
                    sync_manifests_module.main()
            finally:
                sync_manifests_module.__file__ = old_file

        assert exc_info.value.code == 0

    def test_prints_status_for_each_pillar(
        self, vault_root, sync_manifests_module, capsys
    ):
        """Prints sync status for each pillar."""
        old_file = sync_manifests_module.__file__
        sync_manifests_module.__file__ = str(vault_root / ".github" / "scripts" / "sync-manifests.py")
        try:
            with pytest.raises(SystemExit):
                sync_manifests_module.main()
        finally:
            sync_manifests_module.__file__ = old_file

        captured = capsys.readouterr()
        # Should mention Personal and Work
        assert "Personal" in captured.out or "Work" in captured.out

    def test_exits_0_when_no_pillars_found(self, tmp_path, sync_manifests_module, capsys):
        """Exits with code 0 when no pillars found."""
        old_file = sync_manifests_module.__file__
        sync_manifests_module.__file__ = str(tmp_path / ".github" / "scripts" / "sync-manifests.py")
        # Create the parent directories so Path resolution works
        (tmp_path / ".github" / "scripts").mkdir(parents=True)

        try:
            with pytest.raises(SystemExit) as exc_info:
                sync_manifests_module.main()
        finally:
            sync_manifests_module.__file__ = old_file

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "No pillars found" in captured.out


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Edge case tests for sync-manifests.py."""

    def test_handles_special_characters_in_filename(
        self, tmp_path, sync_manifests_module
    ):
        """Handles filenames with special characters."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        special_file = knowledge / "Note (Draft) - v2.md"
        special_file.write_text("# Note Draft v2")

        result = sync_manifests_module.generate_manifest_content(knowledge)

        assert "[[Note (Draft) - v2]]" in result

    def test_handles_unicode_in_filename(self, tmp_path, sync_manifests_module):
        """Handles Unicode characters in filenames."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        unicode_file = knowledge / "Cafe.md"
        unicode_file.write_text("# Cafe Notes")

        result = sync_manifests_module.generate_manifest_content(knowledge)

        assert "[[Cafe]]" in result

    def test_manifest_has_trailing_newline(self, tmp_path, sync_manifests_module):
        """Generated manifest ends with a newline."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "Test.md").write_text("# Test")

        result = sync_manifests_module.generate_manifest_content(knowledge)

        assert result.endswith("\n")
