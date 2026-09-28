import os
from pathlib import Path
import pytest

from ai_agent.tools.file_ops import read_file, list_files, edit_file, delete_file
from ai_agent.tools.code_ops import create_file, search_files
from ai_agent.tools.system_ops import run_terminal_command


class TestFileOperations:
    """Tests for file system and code operations."""

    def test_create_and_read_file(self, tmp_path):
        test_file = tmp_path / "sample.txt"
        create_res = create_file(str(test_file), "Hello World\nLine 2\nLine 3")
        assert "Successfully created" in create_res
        assert test_file.exists()

        # Duplicate create check
        dup_res = create_file(str(test_file), "overwrite attempt")
        assert "already exists" in dup_res

        # Full read
        read_res = read_file(str(test_file))
        assert "Hello World\nLine 2\nLine 3" in read_res

    def test_read_file_pagination(self, tmp_path):
        test_file = tmp_path / "multiline.txt"
        content = "\n".join([f"Line {i}" for i in range(1, 11)])
        test_file.write_text(content, encoding="utf-8")

        # Read line range 3 to 5
        sliced = read_file(str(test_file), start_line=3, end_line=5)
        assert "Showing lines 3-5 of 10" in sliced
        assert "3: Line 3" in sliced
        assert "4: Line 4" in sliced
        assert "5: Line 5" in sliced
        assert "Line 1\n" not in sliced

    def test_edit_file_success_and_errors(self, tmp_path):
        test_file = tmp_path / "editable.txt"
        test_file.write_text("Hello Foo World", encoding="utf-8")

        # Successful edit
        edit_res = edit_file(str(test_file), "Foo", "Bar")
        assert "Successfully updated" in edit_res
        assert test_file.read_text(encoding="utf-8") == "Hello Bar World"

        # Missing target text error format
        missing_res = edit_file(str(test_file), "NonExistentString", "Baz")
        assert "Target text 'NonExistentString' not found" in missing_res

        # Empty old_str validation
        empty_res = edit_file(str(test_file), "", "Baz")
        assert "cannot be empty" in empty_res

    def test_delete_file(self, tmp_path):
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("temporary", encoding="utf-8")
        assert test_file.exists()

        del_res = delete_file(str(test_file))
        assert "Successfully deleted" in del_res
        assert not test_file.exists()

        # Delete non-existent file
        not_found = delete_file(str(test_file))
        assert "File not found" in not_found

    def test_list_files(self, tmp_path):
        (tmp_path / "subdir").mkdir()
        (tmp_path / "file_a.txt").write_text("a", encoding="utf-8")
        (tmp_path / "file_b.py").write_text("b", encoding="utf-8")

        listing = list_files(str(tmp_path))
        assert "[DIR]  subdir" in listing
        assert "[FILE] file_a.txt" in listing
        assert "[FILE] file_b.py" in listing

    def test_search_files(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "agent.py").write_text("class AIAgent:\n    pass\n", encoding="utf-8")
        (tmp_path / "README.md").write_text("# AIAgent Guide\n", encoding="utf-8")

        search_res = search_files("AIAgent", path=str(tmp_path))
        assert "Found 2 match(es)" in search_res
        assert "agent.py (Line 1): class AIAgent:" in search_res
        assert "README.md (Line 1): # AIAgent Guide" in search_res


class TestSystemOperations:
    """Tests for terminal command execution."""

    def test_run_simple_command(self):
        res = run_terminal_command("python -c \"print('system_test_ok')\"")
        assert "system_test_ok" in res

    def test_forbidden_command_protection(self):
        res = run_terminal_command("rm -rf /")
        assert "Command execution rejected for safety reasons" in res

        res2 = run_terminal_command("format C:")
        assert "Command execution rejected for safety reasons" in res2

    def test_empty_command(self):
        res = run_terminal_command("")
        assert "Empty command" in res
