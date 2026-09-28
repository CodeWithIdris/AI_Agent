import pytest
from ai_agent.tools.parser import parse_tool_call


class TestToolParser:
    """Unit tests for AST and JSON tool call parser."""

    def test_empty_and_none_input(self):
        assert parse_tool_call("") == (None, [])
        assert parse_tool_call(None) == (None, [])
        assert parse_tool_call("   \n\t  ") == (None, [])

    def test_pure_ast_positional_args(self):
        name, args = parse_tool_call("list_files('.')")
        assert name == "list_files"
        assert args == ["."]

        name, args = parse_tool_call("run_terminal_command('git status')")
        assert name == "run_terminal_command"
        assert args == ["git status"]

    def test_pure_ast_keyword_args(self):
        name, args = parse_tool_call("list_files(path='src')")
        assert name == "list_files"
        assert isinstance(args, dict)
        assert args.get("path") == "src"

    def test_ast_mixed_positional_and_keyword_args(self):
        """Verify that positional arguments are NOT dropped when keyword arguments exist."""
        name, args = parse_tool_call("search_files('agent', path='ai_agent')")
        assert name == "search_files"
        assert isinstance(args, dict)
        assert args.get("__args__") == ["agent"]
        assert args.get("path") == "ai_agent"

    def test_markdown_code_fenced_call(self):
        text = "```python\nlist_files('.')\n```"
        name, args = parse_tool_call(text)
        assert name == "list_files"
        assert args == ["."]

        generic_fence = "```\nread_file('main.py')\n```"
        name, args = parse_tool_call(generic_fence)
        assert name == "read_file"
        assert args == ["main.py"]

    def test_embedded_call_in_conversational_text(self):
        text = "I will inspect the workspace files now:\nlist_files('.')\nLet me know if you need anything else."
        name, args = parse_tool_call(text)
        assert name == "list_files"
        assert args == ["."]

    def test_json_tool_call_exact(self):
        json_call = '{"name": "list_files", "arguments": {"path": "."}}'
        name, args = parse_tool_call(json_call)
        assert name == "list_files"
        assert args == {"path": "."}

    def test_json_tool_call_list_format(self):
        json_call = '[{"tool": "read_file", "args": ["main.py"]}]'
        name, args = parse_tool_call(json_call)
        assert name == "read_file"
        assert args == ["main.py"]

    def test_embedded_json_tool_call(self):
        text = 'Here is the tool call: {"name": "recall", "arguments": {"key": "pref"}}'
        name, args = parse_tool_call(text)
        assert name == "recall"
        assert args == {"key": "pref"}

    def test_invalid_syntax_returns_none(self):
        assert parse_tool_call("Hello world! Just a conversation.") == (None, [])
        assert parse_tool_call("def invalid_code(:") == (None, [])
