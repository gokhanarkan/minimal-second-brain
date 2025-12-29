"""
Tests for .github/scripts/vault-cleaner.py

Organised by function groups:
1. Pure utility functions (no mocking needed)
2. Filesystem operations (tmp_path fixtures)
3. Git-dependent functions (mock subprocess)
4. Integration tests (full workflow)
"""

import importlib.util
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# -----------------------------------------------------------------------------
# Module import fixture
# -----------------------------------------------------------------------------

@pytest.fixture
def vault_cleaner(repo_root: Path):
    """Import vault_cleaner module."""
    spec = importlib.util.spec_from_file_location(
        "vault_cleaner",
        repo_root / ".github" / "scripts" / "vault-cleaner.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# =============================================================================
# PURE UTILITY FUNCTIONS - No mocking required
# =============================================================================

class TestDaysSince:
    """Tests for days_since() - pure function."""

    def test_days_since_today(self, vault_cleaner):
        """Same day returns 0."""
        frozen_now = datetime(2025, 1, 15, 12, 0, 0)
        dt = datetime(2025, 1, 15, 10, 0, 0)
        with patch.object(vault_cleaner, "datetime") as mock_dt:
            mock_dt.now.return_value = frozen_now
            assert vault_cleaner.days_since(dt) == 0

    def test_days_since_yesterday(self, vault_cleaner):
        """Yesterday returns 1."""
        frozen_now = datetime(2025, 1, 15, 12, 0, 0)
        dt = datetime(2025, 1, 14, 12, 0, 0)
        with patch.object(vault_cleaner, "datetime") as mock_dt:
            mock_dt.now.return_value = frozen_now
            assert vault_cleaner.days_since(dt) == 1

    def test_days_since_week_ago(self, vault_cleaner):
        """7 days ago returns 7."""
        frozen_now = datetime(2025, 1, 15, 12, 0, 0)
        dt = datetime(2025, 1, 8, 12, 0, 0)
        with patch.object(vault_cleaner, "datetime") as mock_dt:
            mock_dt.now.return_value = frozen_now
            assert vault_cleaner.days_since(dt) == 7

    def test_days_since_future_returns_negative(self, vault_cleaner):
        """Future date returns negative days."""
        frozen_now = datetime(2025, 1, 15, 12, 0, 0)
        dt = datetime(2025, 1, 16, 12, 0, 0)
        with patch.object(vault_cleaner, "datetime") as mock_dt:
            mock_dt.now.return_value = frozen_now
            assert vault_cleaner.days_since(dt) == -1


class TestParseManifest:
    """Tests for parse_manifest() - parses MANIFEST.md files."""

    def test_parse_valid_manifest(self, tmp_path, vault_cleaner):
        """Parse manifest with multiple entries."""
        manifest = tmp_path / "MANIFEST.md"
        manifest.write_text(
            "# Knowledge Manifest\n\n"
            "| File | Description |\n"
            "|------|-------------|\n"
            "| [[Note One]] | Description one |\n"
            "| [[Note Two]] | Description two |\n"
        )

        result = vault_cleaner.parse_manifest(manifest)

        assert result == {"Note One", "Note Two"}

    def test_parse_empty_manifest(self, tmp_path, vault_cleaner):
        """Parse manifest with no entries."""
        manifest = tmp_path / "MANIFEST.md"
        manifest.write_text(
            "# Knowledge Manifest\n\n"
            "| File | Description |\n"
            "|------|-------------|\n"
        )

        result = vault_cleaner.parse_manifest(manifest)

        assert result == set()

    def test_parse_nonexistent_manifest(self, tmp_path, vault_cleaner):
        """Missing manifest returns empty set."""
        manifest = tmp_path / "nonexistent.md"

        result = vault_cleaner.parse_manifest(manifest)

        assert result == set()

    def test_parse_manifest_with_spaces_in_name(self, tmp_path, vault_cleaner):
        """Parse entries with spaces in filenames."""
        manifest = tmp_path / "MANIFEST.md"
        manifest.write_text("| [[My Long Note Name]] | Description |")

        result = vault_cleaner.parse_manifest(manifest)

        assert "My Long Note Name" in result


class TestGetActualFiles:
    """Tests for get_actual_files() - lists .md files in Knowledge/."""

    def test_get_files_excludes_manifest(self, tmp_path, vault_cleaner):
        """MANIFEST.md should be excluded from results."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "MANIFEST.md").write_text("manifest content")
        (knowledge / "Note.md").write_text("note content")

        result = vault_cleaner.get_actual_files(knowledge)

        assert result == {"Note"}
        assert "MANIFEST" not in result

    def test_get_files_returns_stems(self, tmp_path, vault_cleaner):
        """Returns filenames without .md extension."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()
        (knowledge / "API Design.md").write_text("content")

        result = vault_cleaner.get_actual_files(knowledge)

        assert result == {"API Design"}

    def test_get_files_empty_directory(self, tmp_path, vault_cleaner):
        """Empty Knowledge directory returns empty set."""
        knowledge = tmp_path / "Knowledge"
        knowledge.mkdir()

        result = vault_cleaner.get_actual_files(knowledge)

        assert result == set()

    def test_get_files_nonexistent_directory(self, tmp_path, vault_cleaner):
        """Nonexistent directory returns empty set."""
        knowledge = tmp_path / "nonexistent"

        result = vault_cleaner.get_actual_files(knowledge)

        assert result == set()


class TestGenerateIssueBody:
    """Tests for generate_issue_body() - pure function generating markdown."""

    def test_empty_inputs_generates_minimal_body(self, vault_cleaner):
        """No issues generates header only."""
        result = vault_cleaner.generate_issue_body({}, {}, {}, [], {})

        assert "# Vault Cleaning Tasks" in result
        assert "## 1." not in result  # No task sections

    def test_manifest_issues_section(self, vault_cleaner):
        """Manifest issues create proper section."""
        manifest_issues = {
            "Personal": {"add": ["New Note"], "remove": ["Old Note"]}
        }

        result = vault_cleaner.generate_issue_body(manifest_issues, {}, {}, [], {})

        assert "## 1. Fix Manifest Files" in result
        assert "Personal/Knowledge/MANIFEST.md" in result
        assert "Add: `[[New Note]]`" in result
        assert "Remove: `[[Old Note]]`" in result

    def test_inbox_items_section(self, vault_cleaner):
        """Inbox items create proper section."""
        inbox_items = {
            "Personal": [{"name": "todo.md", "age_days": 5}]
        }

        result = vault_cleaner.generate_issue_body({}, inbox_items, {}, [], {})

        assert "Process Inbox Items" in result
        assert "Personal/Inbox/" in result
        assert "`todo.md` (5 days)" in result

    def test_stale_projects_section(self, vault_cleaner):
        """Stale projects create proper section."""
        stale_projects = {
            "Work": [{"name": "old-project.md", "age_days": 45}]
        }

        result = vault_cleaner.generate_issue_body({}, {}, stale_projects, [], {})

        assert "Archive Stale Projects" in result
        assert "`old-project.md` (45 days)" in result

    def test_root_files_section(self, vault_cleaner):
        """Root files create proper section."""
        root_files = ["misplaced.md", "another.md"]

        result = vault_cleaner.generate_issue_body({}, {}, {}, root_files, {})

        assert "Move Files from Vault Root" in result
        assert "`misplaced.md`" in result

    def test_empty_files_section(self, vault_cleaner):
        """Empty files create proper section."""
        empty_files = {
            "Personal": ["Knowledge/stub.md"]
        }

        result = vault_cleaner.generate_issue_body({}, {}, {}, [], empty_files)

        assert "Review Empty/Stub Files" in result
        assert "`Knowledge/stub.md`" in result

    def test_task_numbering_increments(self, vault_cleaner):
        """Multiple sections have sequential task numbers."""
        result = vault_cleaner.generate_issue_body(
            {"P": {"add": ["x"], "remove": []}},
            {"P": [{"name": "x.md", "age_days": 5}]},
            {"P": [{"name": "y.md", "age_days": 35}]},
            ["z.md"],
            {"P": ["Knowledge/stub.md"]}
        )

        assert "## 1." in result
        assert "## 2." in result
        assert "## 3." in result
        assert "## 4." in result
        assert "## 5." in result


# =============================================================================
# FILESYSTEM OPERATIONS - Using tmp_path fixtures
# =============================================================================

class TestGetPillars:
    """Tests for get_pillars() - auto-detects pillar directories."""

    def test_detects_pillars_with_inbox(self, tmp_path, vault_cleaner):
        """Detects folders containing Inbox/."""
        (tmp_path / "Personal" / "Inbox").mkdir(parents=True)

        result = vault_cleaner.get_pillars(tmp_path)

        assert "Personal" in result

    def test_detects_pillars_with_knowledge(self, tmp_path, vault_cleaner):
        """Detects folders containing Knowledge/."""
        (tmp_path / "Work" / "Knowledge").mkdir(parents=True)

        result = vault_cleaner.get_pillars(tmp_path)

        assert "Work" in result

    def test_ignores_hidden_directories(self, tmp_path, vault_cleaner):
        """Ignores .git, .obsidian, etc."""
        (tmp_path / ".git" / "Inbox").mkdir(parents=True)
        (tmp_path / ".obsidian" / "Knowledge").mkdir(parents=True)

        result = vault_cleaner.get_pillars(tmp_path)

        assert ".git" not in result
        assert ".obsidian" not in result

    def test_ignores_regular_directories(self, tmp_path, vault_cleaner):
        """Ignores directories without pillar structure."""
        (tmp_path / "random_folder").mkdir()

        result = vault_cleaner.get_pillars(tmp_path)

        assert "random_folder" not in result

    def test_returns_sorted_list(self, tmp_path, vault_cleaner):
        """Returns pillars in sorted order."""
        (tmp_path / "Zebra" / "Inbox").mkdir(parents=True)
        (tmp_path / "Alpha" / "Knowledge").mkdir(parents=True)

        result = vault_cleaner.get_pillars(tmp_path)

        assert result == ["Alpha", "Zebra"]


class TestCheckManifestSync:
    """Tests for check_manifest_sync() - compares manifest to actual files."""

    def test_detects_missing_from_manifest(self, vault_root, vault_cleaner):
        """Detects files in Knowledge/ not listed in manifest."""
        (vault_root / "Personal" / "Knowledge" / "Untracked.md").write_text(
            "# Untracked"
        )

        result = vault_cleaner.check_manifest_sync(vault_root)

        assert "Personal" in result
        assert "Untracked" in result["Personal"]["add"]

    def test_detects_extra_in_manifest(self, vault_root, vault_cleaner):
        """Detects entries in manifest with no matching file."""
        manifest = vault_root / "Personal" / "Knowledge" / "MANIFEST.md"
        manifest.write_text(
            "# Manifest\n| [[Ghost Note]] | Does not exist |"
        )

        result = vault_cleaner.check_manifest_sync(vault_root)

        assert "Personal" in result
        assert "Ghost Note" in result["Personal"]["remove"]

    def test_no_issues_when_synced(self, synced_manifest_vault, vault_cleaner):
        """Returns empty dict when manifest is in sync."""
        result = vault_cleaner.check_manifest_sync(synced_manifest_vault)

        assert result == {}


class TestCheckRootFiles:
    """Tests for check_root_files() - finds .md files at vault root."""

    def test_detects_misplaced_files(self, vault_root, vault_cleaner):
        """Finds .md files that should be in pillars."""
        (vault_root / "misplaced.md").write_text("content")

        result = vault_cleaner.check_root_files(vault_root)

        assert "misplaced.md" in result

    def test_ignores_allowed_root_files(self, vault_root, vault_cleaner):
        """Ignores README.md, CLAUDE.md, AGENTS.md."""
        result = vault_cleaner.check_root_files(vault_root)

        assert "README.md" not in result
        assert "CLAUDE.md" not in result
        assert "AGENTS.md" not in result

    def test_returns_sorted_list(self, vault_root, vault_cleaner):
        """Returns files in sorted order."""
        (vault_root / "zebra.md").write_text("z")
        (vault_root / "alpha.md").write_text("a")

        result = vault_cleaner.check_root_files(vault_root)

        assert result == ["alpha.md", "zebra.md"]


class TestCheckEmptyFiles:
    """Tests for check_empty_files() - finds stub files."""

    def test_detects_empty_file(self, vault_root, vault_cleaner):
        """Files with <50 chars are detected."""
        (vault_root / "Personal" / "Knowledge" / "stub.md").write_text("# Title")

        result = vault_cleaner.check_empty_files(vault_root)

        assert "Personal" in result
        assert "Knowledge/stub.md" in result["Personal"]

    def test_ignores_files_with_content(self, vault_root, vault_cleaner):
        """Files with sufficient content are ignored."""
        content = "# Title\n\n" + "x" * 100
        (vault_root / "Personal" / "Knowledge" / "full.md").write_text(content)

        result = vault_cleaner.check_empty_files(vault_root)

        assert "Personal" not in result or \
               "Knowledge/full.md" not in result.get("Personal", [])

    def test_strips_frontmatter_before_counting(self, vault_root, vault_cleaner):
        """YAML frontmatter is not counted toward content length."""
        content = "---\ntags: [test]\n---\n# Title"  # <50 chars after frontmatter
        (vault_root / "Personal" / "Knowledge" / "frontmatter.md").write_text(content)

        result = vault_cleaner.check_empty_files(vault_root)

        assert "Personal" in result
        assert "Knowledge/frontmatter.md" in result["Personal"]

    def test_ignores_manifest_files(self, vault_root, vault_cleaner):
        """MANIFEST.md is never flagged as empty."""
        result = vault_cleaner.check_empty_files(vault_root)

        for pillar_files in result.values():
            assert not any("MANIFEST.md" in f for f in pillar_files)


# =============================================================================
# GIT-DEPENDENT FUNCTIONS - Mock subprocess
# =============================================================================

class TestGetFileLastModified:
    """Tests for get_file_last_modified() - git log with mtime fallback."""

    def test_uses_git_timestamp_when_available(
        self, vault_root, vault_cleaner
    ):
        """Uses git log timestamp when git succeeds."""
        test_file = vault_root / "test.md"
        test_file.write_text("content")

        frozen_now = datetime(2025, 1, 15, 12, 0, 0)
        five_days_ago_ts = int(frozen_now.timestamp() - (5 * 86400))

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = str(five_days_ago_ts)
            mock_run.return_value = mock_result

            with patch.object(vault_cleaner, "datetime") as mock_dt:
                mock_dt.now.return_value = frozen_now
                mock_dt.fromtimestamp = datetime.fromtimestamp
                result = vault_cleaner.get_file_last_modified(test_file, vault_root)

                # Should be ~5 days ago
                assert vault_cleaner.days_since(result) == 5

    def test_falls_back_to_mtime_on_git_failure(
        self, vault_root, vault_cleaner
    ):
        """Falls back to filesystem mtime when git fails."""
        test_file = vault_root / "test.md"
        test_file.write_text("content")

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            result = vault_cleaner.get_file_last_modified(test_file, vault_root)

            # Should return a datetime close to now (file was just created)
            # Using real datetime.now() since we're testing mtime fallback
            assert isinstance(result, datetime)
            # File was just created, so days_since should be 0
            assert vault_cleaner.days_since(result) == 0


class TestCheckInboxItems:
    """Tests for check_inbox_items() - finds old inbox items."""

    def test_detects_old_inbox_items(
        self, vault_root, vault_cleaner
    ):
        """Files >3 days old are detected."""
        inbox_file = vault_root / "Personal" / "Inbox" / "old.md"
        inbox_file.write_text("old content")

        frozen_now = datetime(2025, 1, 15, 12, 0, 0)
        five_days_ago_ts = int(frozen_now.timestamp() - (5 * 86400))

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = str(five_days_ago_ts)
            mock_run.return_value = mock_result

            with patch.object(vault_cleaner, "datetime") as mock_dt:
                mock_dt.now.return_value = frozen_now
                mock_dt.fromtimestamp = datetime.fromtimestamp
                result = vault_cleaner.check_inbox_items(vault_root)

        assert "Personal" in result
        assert any(item["name"] == "old.md" for item in result["Personal"])

    def test_ignores_recent_inbox_items(self, vault_root, vault_cleaner):
        """Files <3 days old are ignored."""
        inbox_file = vault_root / "Personal" / "Inbox" / "new.md"
        inbox_file.write_text("new content")

        frozen_now = datetime(2025, 1, 15, 12, 0, 0)

        # Mock git to return 1 day ago and mock datetime.now()
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            # 1 day before frozen_now
            mock_result.stdout = str(int(frozen_now.timestamp() - 86400))
            mock_run.return_value = mock_result

            with patch.object(vault_cleaner, "datetime") as mock_dt:
                mock_dt.now.return_value = frozen_now
                mock_dt.fromtimestamp = datetime.fromtimestamp
                result = vault_cleaner.check_inbox_items(vault_root)

        assert "Personal" not in result or not any(
            item["name"] == "new.md" for item in result.get("Personal", [])
        )


class TestCheckStaleProjects:
    """Tests for check_stale_projects() - finds old projects."""

    def test_detects_stale_projects(
        self, vault_root, vault_cleaner
    ):
        """Projects >30 days old are detected."""
        project = vault_root / "Personal" / "Projects" / "stale.md"
        project.write_text("# Old Project")

        frozen_now = datetime(2025, 1, 15, 12, 0, 0)
        thirty_five_days_ago_ts = int(frozen_now.timestamp() - (35 * 86400))

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = str(thirty_five_days_ago_ts)
            mock_run.return_value = mock_result

            with patch.object(vault_cleaner, "datetime") as mock_dt:
                mock_dt.now.return_value = frozen_now
                mock_dt.fromtimestamp = datetime.fromtimestamp
                result = vault_cleaner.check_stale_projects(vault_root)

        assert "Personal" in result
        assert any(p["name"] == "stale.md" for p in result["Personal"])

    def test_ignores_active_projects(
        self, vault_root, vault_cleaner
    ):
        """Projects <30 days old are ignored."""
        project = vault_root / "Personal" / "Projects" / "active.md"
        project.write_text("# Active Project")

        frozen_now = datetime(2025, 1, 15, 12, 0, 0)
        five_days_ago_ts = int(frozen_now.timestamp() - (5 * 86400))

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = str(five_days_ago_ts)
            mock_run.return_value = mock_result

            with patch.object(vault_cleaner, "datetime") as mock_dt:
                mock_dt.now.return_value = frozen_now
                mock_dt.fromtimestamp = datetime.fromtimestamp
                result = vault_cleaner.check_stale_projects(vault_root)

        assert "Personal" not in result or not any(
            p["name"] == "active.md" for p in result.get("Personal", [])
        )


# =============================================================================
# GITHUB OUTPUT - Environment variable handling
# =============================================================================

class TestSetGithubOutput:
    """Tests for set_github_output() - writes to GITHUB_OUTPUT file."""

    def test_writes_to_github_output_file(
        self, github_output_file, vault_cleaner
    ):
        """Writes name=value to GITHUB_OUTPUT file."""
        vault_cleaner.set_github_output("has_tasks", "true")

        content = github_output_file.read_text()
        assert "has_tasks=true" in content

    def test_appends_multiple_outputs(
        self, github_output_file, vault_cleaner
    ):
        """Multiple calls append to the file."""
        vault_cleaner.set_github_output("foo", "bar")
        vault_cleaner.set_github_output("baz", "qux")

        content = github_output_file.read_text()
        assert "foo=bar" in content
        assert "baz=qux" in content

    def test_prints_when_no_github_output(self, capsys, vault_cleaner):
        """Prints to stdout when GITHUB_OUTPUT not set."""
        with patch.dict(os.environ, {}, clear=True):
            vault_cleaner.set_github_output("test", "value")

        captured = capsys.readouterr()
        assert "test=value" in captured.out


# =============================================================================
# INTEGRATION TESTS - Full workflow
# =============================================================================

class TestMainIntegration:
    """Integration tests for main() orchestrator."""

    def test_main_with_clean_vault(
        self, synced_manifest_vault, github_output_file, vault_cleaner, capsys
    ):
        """Clean vault produces no tasks."""
        frozen_now = datetime(2025, 1, 15, 12, 0, 0)

        with patch.object(
            vault_cleaner, "get_vault_root", return_value=synced_manifest_vault
        ):
            with patch.object(vault_cleaner, "datetime") as mock_dt:
                mock_dt.now.return_value = frozen_now
                mock_dt.fromtimestamp = datetime.fromtimestamp
                # Mock git to return recent files (not stale)
                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    # 1 day ago - recent enough to not trigger stale checks
                    mock_result.stdout = str(int(frozen_now.timestamp() - 86400))
                    mock_run.return_value = mock_result

                    vault_cleaner.main()

        output = github_output_file.read_text()
        assert "has_tasks=false" in output

        captured = capsys.readouterr()
        assert "Vault is tidy" in captured.out

    def test_main_with_issues_creates_file(
        self, vault_with_issues, github_output_file, vault_cleaner
    ):
        """Vault with issues produces cleaning-tasks.md."""
        frozen_now = datetime(2025, 1, 15, 12, 0, 0)

        with patch.object(
            vault_cleaner, "get_vault_root", return_value=vault_with_issues
        ):
            with patch.object(vault_cleaner, "datetime") as mock_dt:
                mock_dt.now.return_value = frozen_now
                mock_dt.fromtimestamp = datetime.fromtimestamp
                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 1
                    mock_result.stdout = ""
                    mock_run.return_value = mock_result

                    vault_cleaner.main()

        output = github_output_file.read_text()
        assert "has_tasks=true" in output

        tasks_file = vault_with_issues / "cleaning-tasks.md"
        assert tasks_file.exists()
        assert "# Vault Cleaning Tasks" in tasks_file.read_text()
