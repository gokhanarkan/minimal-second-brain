"""
Shared pytest fixtures for vault automation tests.
"""

import json
import os
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# -----------------------------------------------------------------------------
# Path fixtures - ensure scripts are importable
# -----------------------------------------------------------------------------

@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session", autouse=True)
def add_scripts_to_path(repo_root: Path):
    """Add script directories to Python path for imports."""
    scripts_path = repo_root / ".github" / "scripts"
    hooks_path = repo_root / ".claude" / "hooks"

    sys.path.insert(0, str(scripts_path))
    sys.path.insert(0, str(hooks_path))

    yield

    if str(scripts_path) in sys.path:
        sys.path.remove(str(scripts_path))
    if str(hooks_path) in sys.path:
        sys.path.remove(str(hooks_path))


# -----------------------------------------------------------------------------
# Vault structure fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def vault_root(tmp_path: Path) -> Path:
    """Create a minimal vault structure for testing."""
    # Create pillar directories
    for pillar in ["Personal", "Work"]:
        for folder in ["Inbox", "Projects", "Knowledge"]:
            (tmp_path / pillar / folder).mkdir(parents=True)

        # Create manifest file
        manifest = tmp_path / pillar / "Knowledge" / "MANIFEST.md"
        manifest.write_text(
            "# Knowledge Manifest\n\n"
            "| File | Description |\n"
            "|------|-------------|\n"
        )

    # Create root-level files that should exist
    (tmp_path / "CLAUDE.md").write_text("# CLAUDE.md")
    (tmp_path / "README.md").write_text("# README")
    (tmp_path / "AGENTS.md").write_text("# AGENTS.md")

    return tmp_path


@pytest.fixture
def vault_with_content(vault_root: Path) -> Path:
    """Vault with sample files in various states for testing."""
    # Knowledge files
    (vault_root / "Personal" / "Knowledge" / "API Design.md").write_text(
        "# API Design Principles\n\nSome content about API design..."
    )
    (vault_root / "Personal" / "Knowledge" / "Python Tips.md").write_text(
        "# Python Tips\n\nUseful Python patterns..."
    )

    # Update manifest to be in sync
    manifest = vault_root / "Personal" / "Knowledge" / "MANIFEST.md"
    manifest.write_text(
        "# Knowledge Manifest\n\n"
        "| File | Description |\n"
        "|------|-------------|\n"
        "| [[API Design]] | API Design Principles |\n"
        "| [[Python Tips]] | Python Tips |\n"
    )

    # Inbox files
    (vault_root / "Personal" / "Inbox" / "Quick Note.md").write_text(
        "# Quick Note\nTODO: process this"
    )

    # Project files
    (vault_root / "Work" / "Projects" / "Q1 Goals.md").write_text(
        "# Q1 Goals\n\nProject planning document with substantial content here..."
    )

    return vault_root


@pytest.fixture
def vault_with_issues(vault_root: Path) -> Path:
    """Vault with intentional issues for cleaner detection tests."""
    # File in Knowledge but not in manifest (out of sync)
    (vault_root / "Personal" / "Knowledge" / "Untracked.md").write_text(
        "# Untracked File\nContent..."
    )

    # File at vault root (should be in pillar)
    (vault_root / "Misplaced.md").write_text("# Misplaced File")

    # Empty/stub file
    (vault_root / "Work" / "Knowledge" / "Empty.md").write_text("# Title")

    return vault_root


@pytest.fixture
def synced_manifest_vault(vault_root: Path) -> Path:
    """Vault with manifest perfectly in sync with files."""
    knowledge_dir = vault_root / "Personal" / "Knowledge"

    # Create files with enough content (>50 chars after frontmatter)
    (knowledge_dir / "Note One.md").write_text(
        "# Note One\n\n"
        "This is the content for note one. It has enough text to pass the "
        "empty file check which requires at least 50 characters of content."
    )
    (knowledge_dir / "Note Two.md").write_text(
        "# Note Two\n\n"
        "This is the content for note two. It also has enough text to pass "
        "the empty file check which requires at least 50 characters."
    )

    # Create matching manifest
    (knowledge_dir / "MANIFEST.md").write_text(
        "# Knowledge Manifest\n\n"
        "| File | Description |\n"
        "|------|-------------|\n"
        "| [[Note One]] | Note One |\n"
        "| [[Note Two]] | Note Two |\n"
    )

    return vault_root


# -----------------------------------------------------------------------------
# Git mocking fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_git_log():
    """Mock subprocess.run for git log commands - returns 5 days ago."""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        # 5 days ago
        mock_result.stdout = str(int(datetime.now().timestamp() - (5 * 86400)))
        mock_run.return_value = mock_result

        yield mock_run


@pytest.fixture
def mock_git_log_old_files():
    """Mock git to return files modified 35 days ago (stale)."""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        # 35 days ago
        mock_result.stdout = str(int(datetime.now().timestamp() - (35 * 86400)))
        mock_run.return_value = mock_result

        yield mock_run


@pytest.fixture
def mock_git_log_failure():
    """Mock git log to fail (triggers mtime fallback)."""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        yield mock_run


# -----------------------------------------------------------------------------
# stdin mocking for hook tests
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_stdin():
    """Factory fixture for mocking stdin with JSON data."""
    def _mock_stdin(data: dict):
        return patch("sys.stdin", StringIO(json.dumps(data)))
    return _mock_stdin


@pytest.fixture
def write_tool_input(mock_stdin):
    """Pre-configured stdin for Write tool events."""
    def _write_input(file_path: str):
        return mock_stdin({
            "tool_name": "Write",
            "tool_input": {"file_path": file_path}
        })
    return _write_input


@pytest.fixture
def edit_tool_input(mock_stdin):
    """Pre-configured stdin for Edit tool events."""
    def _edit_input(file_path: str):
        return mock_stdin({
            "tool_name": "Edit",
            "tool_input": {"file_path": file_path}
        })
    return _edit_input


@pytest.fixture
def bash_tool_input(mock_stdin):
    """Pre-configured stdin for Bash tool events."""
    def _bash_input(command: str):
        return mock_stdin({
            "tool_name": "Bash",
            "tool_input": {"command": command}
        })
    return _bash_input


# -----------------------------------------------------------------------------
# Environment variable fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def github_output_file(tmp_path: Path):
    """Create a temporary file for GITHUB_OUTPUT."""
    output_file = tmp_path / "github_output"
    output_file.touch()

    with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_file)}):
        yield output_file


@pytest.fixture
def claude_project_dir(vault_root: Path):
    """Set CLAUDE_PROJECT_DIR environment variable."""
    with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(vault_root)}):
        yield vault_root
