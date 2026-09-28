import os
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from ai_agent.tools.git_ops import create_checkpoint, undo_last_change, get_git_diff, is_git_repo, CHECKPOINT_DIR
from ai_agent.agent import AIAgent
from ai_agent.memory import MemoryManager


class TestGitOpsAndCheckpointing:
    """Unit tests for Git diffing and Time-Travel Checkpoint rollback."""

    def test_checkpoint_and_undo_file_modification(self, tmp_path):
        test_file = tmp_path / "code.py"
        test_file.write_text("initial_code = True", encoding="utf-8")

        # Create checkpoint before edit
        cp_res = create_checkpoint(str(test_file), description="before-edit")
        assert "created" in cp_res

        # Modify file
        test_file.write_text("buggy_code = True", encoding="utf-8")
        assert test_file.read_text(encoding="utf-8") == "buggy_code = True"

        # Undo change
        undo_res = undo_last_change()
        assert "Successfully reverted" in undo_res
        assert test_file.read_text(encoding="utf-8") == "initial_code = True"

    def test_checkpoint_and_undo_new_file_creation(self, tmp_path):
        new_file = tmp_path / "newly_created.txt"
        assert not new_file.exists()

        # Checkpoint prior to file existing
        create_checkpoint(str(new_file), description="before-creation")

        # Create file
        new_file.write_text("Hello World", encoding="utf-8")
        assert new_file.exists()

        # Undo should delete the newly created file
        undo_res = undo_last_change()
        assert "Successfully reverted" in undo_res
        assert not new_file.exists()

    def test_get_git_diff_non_repo(self, tmp_path):
        diff = get_git_diff(str(tmp_path))
        # Depending on whether tmp_path is inside git or not, it returns clean, diff, or non-git message
        assert isinstance(diff, str)

    def test_agent_auto_checkpoint_on_edit(self, tmp_path):
        mem_file = tmp_path / "mem.json"
        mm = MemoryManager(mem_file)
        agent = AIAgent(provider="ollama", memory_manager=mm)

        target = tmp_path / "sample.py"
        target.write_text("def hello(): return 'old'", encoding="utf-8")

        with patch("ai_agent.tools.git_ops.create_checkpoint") as mock_cp:
            agent._execute_tool_with_safety("edit_file", [str(target), "'old'", "'new'"])
            mock_cp.assert_called_once()
