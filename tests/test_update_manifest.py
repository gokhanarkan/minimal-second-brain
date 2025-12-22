"""
Tests for .claude/hooks/update-manifest.py

Organised by function groups:
1. Pure functions (get_first_heading)
2. Filesystem operations (update_manifest, find_knowledge_dir)
3. stdin/JSON interface (main function)
"""

import importlib.util
import json
import os
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest


# -----------------------------------------------------------------------------
# Module import fixture
# -----------------------------------------------------------------------------

@pytest.fixture
def update_manifest_module(repo_root: Path):
    """Import update_manifest module."""
    spec = importlib.util.spec_from_file_location(
        "update_manifest",
        repo_root / ".claude" / "hooks" / "update-manifest.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# =============================================================================
# PURE FUNCTIONS
# =============================================================================

class TestGetFirstHeading:
    """Tests for get_first_heading() - extracts description from markdown."""

    def test_extracts_h1_heading(self, tmp_path, update_manifest_module):
        """Extracts # heading text."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# My Title\n\nSome content...")

        result = update_manifest_module.get_first_heading(md_file)

        assert result == "My Title"

    def test_extracts_h2_heading(self, tmp_path, update_manifest_module):
        """Extracts ## heading text."""
        md_file = tmp_path / "test.md"
        md_file.write_text("## Secondary Heading\n\nContent")

        result = update_manifest_module.get_first_heading(md_file)

        assert result == "Secondary Heading"

    def test_strips_multiple_hashes(self, tmp_path, update_manifest_module):
        """Strips all leading # characters."""
        md_file = tmp_path / "test.md"
        md_file.write_text("### Deep Heading")

        result = update_manifest_module.get_first_heading(md_file)

        assert result == "Deep Heading"

    def test_uses_first_line_if_no_heading(self, tmp_path, update_manifest_module):
        """Falls back to first non-empty line if no heading."""
        md_file = tmp_path / "test.md"
        md_file.write_text("This is a note without a heading.\n\nMore content.")

        result = update_manifest_module.get_first_heading(md_file)

        assert result == "This is a note without a heading."

    def test_truncates_long_lines(self, tmp_path, update_manifest_module):
        """Truncates first line to 80 chars with ellipsis."""
        md_file = tmp_path / "test.md"
        long_line = "A" * 100
        md_file.write_text(long_line)

        result = update_manifest_module.get_first_heading(md_file)

        assert len(result) == 83  # 80 + "..."
        assert result.endswith("...")

    def test_skips_empty_lines(self, tmp_path, update_manifest_module):
        """Skips empty lines to find first content."""
        md_file = tmp_path / "test.md"
        md_file.write_text("\n\n\n# After Empty Lines")

        result = update_manifest_module.get_first_heading(md_file)

        assert result == "After Empty Lines"

    def test_returns_default_for_empty_file(self, tmp_path, update_manifest_module):
        """Returns 'No description' for empty file."""
        md_file = tmp_path / "test.md"
        md_file.write_text("")

        result = update_manifest_module.get_first_heading(md_file)

        assert result == "No description"

    def test_returns_default_for_nonexistent_file(
        self, tmp_path, update_manifest_module
    ):
        """Returns 'No description' for missing file."""
        md_file = tmp_path / "nonexistent.md"

        result = update_manifest_module.get_first_heading(md_file)

        assert result == "No description"

    def test_handles_file_with_only_whitespace(
        self, tmp_path, update_manifest_module
    ):
        """Returns 'No description' for whitespace-only file."""
        md_file = tmp_path / "test.md"
        md_file.write_text("   \n\n   \n")

        result = update_manifest_module.get_first_heading(md_file)

        assert result == "No description"


# =============================================================================
# FILESYSTEM OPERATIONS
# =============================================================================

class TestUpdateManifest:
    """Tests for update_manifest() - regenerates MANIFEST.md."""

    def test_creates_manifest_with_entries(self, tmp_path, update_manifest_module):
        """Creates manifest with all .md files listed."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "Note One.md").write_text("# Note One\nContent")
        (knowledge / "Note Two.md").write_text("# Note Two\nContent")

        update_manifest_module.update_manifest(knowledge)

        manifest = (knowledge / "MANIFEST.md").read_text()
        assert "[[Note One]]" in manifest
        assert "[[Note Two]]" in manifest

    def test_excludes_manifest_from_entries(self, tmp_path, update_manifest_module):
        """MANIFEST.md is not listed as an entry."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "MANIFEST.md").write_text("old manifest")
        (knowledge / "Note.md").write_text("# Note")

        update_manifest_module.update_manifest(knowledge)

        manifest = (knowledge / "MANIFEST.md").read_text()
        assert "[[MANIFEST]]" not in manifest
        assert "[[Note]]" in manifest

    def test_includes_descriptions_from_headings(
        self, tmp_path, update_manifest_module
    ):
        """Descriptions come from file headings."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "API.md").write_text("# API Design Principles\n\nContent...")

        update_manifest_module.update_manifest(knowledge)

        manifest = (knowledge / "MANIFEST.md").read_text()
        assert "API Design Principles" in manifest

    def test_empty_folder_shows_placeholder(self, tmp_path, update_manifest_module):
        """Empty Knowledge folder gets placeholder row."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()

        update_manifest_module.update_manifest(knowledge)

        manifest = (knowledge / "MANIFEST.md").read_text()
        assert "*(empty)*" in manifest

    def test_sorts_entries_alphabetically(self, tmp_path, update_manifest_module):
        """Entries are sorted alphabetically."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "Zebra.md").write_text("# Z")
        (knowledge / "Alpha.md").write_text("# A")
        (knowledge / "Middle.md").write_text("# M")

        update_manifest_module.update_manifest(knowledge)

        manifest = (knowledge / "MANIFEST.md").read_text()
        alpha_pos = manifest.find("[[Alpha]]")
        middle_pos = manifest.find("[[Middle]]")
        zebra_pos = manifest.find("[[Zebra]]")

        assert alpha_pos < middle_pos < zebra_pos

    def test_overwrites_existing_manifest(self, tmp_path, update_manifest_module):
        """Completely regenerates manifest, not appending."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "MANIFEST.md").write_text("| [[Old Entry]] | Should be gone |")
        (knowledge / "New.md").write_text("# New Note")

        update_manifest_module.update_manifest(knowledge)

        manifest = (knowledge / "MANIFEST.md").read_text()
        assert "[[Old Entry]]" not in manifest
        assert "[[New]]" in manifest

    def test_creates_valid_markdown_table(self, tmp_path, update_manifest_module):
        """Output is a valid markdown table."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "Test.md").write_text("# Test Note")

        update_manifest_module.update_manifest(knowledge)

        manifest = (knowledge / "MANIFEST.md").read_text()
        lines = manifest.strip().split("\n")

        # Should have header, separator, and at least one data row
        assert len(lines) >= 4
        assert lines[0] == "# Knowledge Manifest"
        assert lines[2].startswith("| File")
        assert lines[3].startswith("|---")


class TestFindKnowledgeDir:
    """Tests for find_knowledge_dir() - locates parent Knowledge/ folder."""

    def test_finds_knowledge_for_direct_child(
        self, tmp_path, update_manifest_module
    ):
        """Finds Knowledge/ when file is directly inside."""
        knowledge = tmp_path / "Personal" / "Knowledge"
        knowledge.mkdir(parents=True)
        file_path = knowledge / "Note.md"
        file_path.write_text("content")

        result = update_manifest_module.find_knowledge_dir(str(file_path))

        assert result == knowledge

    def test_finds_knowledge_for_nested_file(
        self, tmp_path, update_manifest_module
    ):
        """Finds Knowledge/ for file in subdirectory."""
        knowledge = tmp_path / "Personal" / "Knowledge"
        subdir = knowledge / "subfolder"
        subdir.mkdir(parents=True)
        file_path = subdir / "Note.md"
        file_path.write_text("content")

        result = update_manifest_module.find_knowledge_dir(str(file_path))

        assert result == knowledge

    def test_returns_none_for_inbox_file(self, tmp_path, update_manifest_module):
        """Returns None for files not in Knowledge/."""
        inbox = tmp_path / "Personal" / "Inbox"
        inbox.mkdir(parents=True)
        file_path = inbox / "Note.md"
        file_path.write_text("content")

        result = update_manifest_module.find_knowledge_dir(str(file_path))

        assert result is None

    def test_returns_none_for_root_file(self, tmp_path, update_manifest_module):
        """Returns None for files at vault root."""
        file_path = tmp_path / "README.md"
        file_path.write_text("content")

        result = update_manifest_module.find_knowledge_dir(str(file_path))

        assert result is None

    def test_returns_none_for_projects_file(self, tmp_path, update_manifest_module):
        """Returns None for files in Projects/."""
        projects = tmp_path / "Personal" / "Projects"
        projects.mkdir(parents=True)
        file_path = projects / "Project.md"
        file_path.write_text("content")

        result = update_manifest_module.find_knowledge_dir(str(file_path))

        assert result is None


class TestGetPillars:
    """Tests for get_pillars() - finds pillar directories."""

    def test_finds_pillars_with_knowledge(self, tmp_path, update_manifest_module):
        """Finds directories containing Knowledge/."""
        (tmp_path / "Personal" / "Knowledge").mkdir(parents=True)
        (tmp_path / "Work" / "Knowledge").mkdir(parents=True)

        result = update_manifest_module.get_pillars(tmp_path)

        assert set(result) == {"Personal", "Work"}

    def test_ignores_hidden_directories(self, tmp_path, update_manifest_module):
        """Ignores .git, .obsidian, etc."""
        (tmp_path / ".obsidian" / "Knowledge").mkdir(parents=True)
        (tmp_path / ".claude" / "Knowledge").mkdir(parents=True)

        result = update_manifest_module.get_pillars(tmp_path)

        assert ".obsidian" not in result
        assert ".claude" not in result

    def test_ignores_directories_without_knowledge(
        self, tmp_path, update_manifest_module
    ):
        """Ignores directories that don't have Knowledge/ subfolder."""
        (tmp_path / "Random" / "Inbox").mkdir(parents=True)
        (tmp_path / "Another").mkdir(parents=True)

        result = update_manifest_module.get_pillars(tmp_path)

        assert "Random" not in result
        assert "Another" not in result

    def test_returns_sorted_list(self, tmp_path, update_manifest_module):
        """Returns pillars in sorted order."""
        (tmp_path / "Zebra" / "Knowledge").mkdir(parents=True)
        (tmp_path / "Alpha" / "Knowledge").mkdir(parents=True)

        result = update_manifest_module.get_pillars(tmp_path)

        assert result == ["Alpha", "Zebra"]


# =============================================================================
# STDIN/JSON INTERFACE
# =============================================================================

class TestMainStdinInterface:
    """Tests for main() - JSON stdin interface."""

    def test_exits_silently_on_invalid_json(self, update_manifest_module):
        """Invalid JSON input exits with code 0."""
        with patch("sys.stdin", StringIO("not valid json")):
            with pytest.raises(SystemExit) as exc_info:
                update_manifest_module.main()

        assert exc_info.value.code == 0

    def test_exits_silently_on_empty_input(self, update_manifest_module):
        """Empty stdin exits with code 0."""
        with patch("sys.stdin", StringIO("")):
            with pytest.raises(SystemExit) as exc_info:
                update_manifest_module.main()

        assert exc_info.value.code == 0

    def test_handles_write_tool_for_knowledge_file(
        self, vault_root, claude_project_dir, update_manifest_module
    ):
        """Write tool to Knowledge/ file triggers manifest update."""
        knowledge = vault_root / "Personal" / "Knowledge"
        new_file = knowledge / "New Note.md"
        new_file.write_text("# New Note\nContent here...")

        input_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(new_file)}
        }

        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with pytest.raises(SystemExit) as exc_info:
                update_manifest_module.main()

        assert exc_info.value.code == 0

        manifest = (knowledge / "MANIFEST.md").read_text()
        assert "[[New Note]]" in manifest

    def test_handles_edit_tool_for_knowledge_file(
        self, vault_root, claude_project_dir, update_manifest_module
    ):
        """Edit tool to Knowledge/ file triggers manifest update."""
        knowledge = vault_root / "Personal" / "Knowledge"
        existing_file = knowledge / "Existing.md"
        existing_file.write_text("# Updated Title\nNew content")

        input_data = {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(existing_file)}
        }

        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with pytest.raises(SystemExit) as exc_info:
                update_manifest_module.main()

        assert exc_info.value.code == 0

        manifest = (knowledge / "MANIFEST.md").read_text()
        assert "[[Existing]]" in manifest

    def test_ignores_non_knowledge_files(
        self, vault_root, claude_project_dir, update_manifest_module
    ):
        """Write to Inbox/ does not update manifest incorrectly."""
        inbox = vault_root / "Personal" / "Inbox"
        inbox_file = inbox / "Todo.md"
        inbox_file.write_text("# Todo")

        # Record manifest state before
        manifest_path = vault_root / "Personal" / "Knowledge" / "MANIFEST.md"
        manifest_before = manifest_path.read_text()

        input_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(inbox_file)}
        }

        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with pytest.raises(SystemExit):
                update_manifest_module.main()

        # Manifest should be unchanged
        assert manifest_path.read_text() == manifest_before

    def test_bash_tool_with_knowledge_in_command(
        self, vault_root, claude_project_dir, update_manifest_module
    ):
        """Bash command mentioning Knowledge/ triggers all manifest updates."""
        # Create file in Knowledge
        knowledge = vault_root / "Personal" / "Knowledge"
        (knowledge / "Bash Created.md").write_text("# Created by Bash")

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "cp something.md Knowledge/"}
        }

        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with pytest.raises(SystemExit) as exc_info:
                update_manifest_module.main()

        assert exc_info.value.code == 0

        manifest = (knowledge / "MANIFEST.md").read_text()
        assert "[[Bash Created]]" in manifest

    def test_bash_tool_without_knowledge_exits_early(
        self, vault_root, claude_project_dir, update_manifest_module
    ):
        """Bash command not mentioning Knowledge/ exits without action."""
        manifest_path = vault_root / "Personal" / "Knowledge" / "MANIFEST.md"
        manifest_before = manifest_path.read_text()

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"}
        }

        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with pytest.raises(SystemExit) as exc_info:
                update_manifest_module.main()

        assert exc_info.value.code == 0
        # Manifest should be unchanged
        assert manifest_path.read_text() == manifest_before

    def test_unknown_tool_exits_silently(self, update_manifest_module):
        """Unknown tool name exits with code 0."""
        input_data = {
            "tool_name": "UnknownTool",
            "tool_input": {}
        }

        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with pytest.raises(SystemExit) as exc_info:
                update_manifest_module.main()

        assert exc_info.value.code == 0

    def test_missing_file_path_exits_silently(self, update_manifest_module):
        """Write tool without file_path exits with code 0."""
        input_data = {
            "tool_name": "Write",
            "tool_input": {}
        }

        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with pytest.raises(SystemExit) as exc_info:
                update_manifest_module.main()

        assert exc_info.value.code == 0

    def test_missing_tool_input_exits_silently(self, update_manifest_module):
        """Missing tool_input object exits with code 0."""
        input_data = {
            "tool_name": "Write"
        }

        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with pytest.raises(SystemExit) as exc_info:
                update_manifest_module.main()

        assert exc_info.value.code == 0


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Edge case tests for update-manifest.py."""

    def test_handles_special_characters_in_filename(
        self, tmp_path, update_manifest_module
    ):
        """Handles filenames with special characters."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        special_file = knowledge / "Note (Draft) - v2.md"
        special_file.write_text("# Note Draft v2")

        update_manifest_module.update_manifest(knowledge)

        manifest = (knowledge / "MANIFEST.md").read_text()
        assert "[[Note (Draft) - v2]]" in manifest

    def test_handles_unicode_in_filename(self, tmp_path, update_manifest_module):
        """Handles Unicode characters in filenames."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        unicode_file = knowledge / "Cafe.md"
        unicode_file.write_text("# Cafe Notes")

        update_manifest_module.update_manifest(knowledge)

        manifest = (knowledge / "MANIFEST.md").read_text()
        assert "[[Cafe]]" in manifest

    def test_handles_numbers_in_filename(self, tmp_path, update_manifest_module):
        """Handles numbers in filenames."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "2025-01-15 Meeting Notes.md").write_text("# Meeting Notes")

        update_manifest_module.update_manifest(knowledge)

        manifest = (knowledge / "MANIFEST.md").read_text()
        assert "[[2025-01-15 Meeting Notes]]" in manifest

    def test_handles_very_long_heading(self, tmp_path, update_manifest_module):
        """Long headings are NOT truncated (only non-heading first lines are)."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        # Heading with # prefix is handled differently than plain text
        long_heading = "# " + "A" * 100
        (knowledge / "Long.md").write_text(long_heading)

        update_manifest_module.update_manifest(knowledge)

        manifest = (knowledge / "MANIFEST.md").read_text()
        # Headings are not truncated, only plain text first lines are
        assert "A" * 100 in manifest

    def test_manifest_has_trailing_newline(self, tmp_path, update_manifest_module):
        """Manifest ends with a newline."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "Test.md").write_text("# Test")

        update_manifest_module.update_manifest(knowledge)

        manifest = (knowledge / "MANIFEST.md").read_text()
        assert manifest.endswith("\n")
