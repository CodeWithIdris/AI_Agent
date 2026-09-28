import os
import pytest
from unittest.mock import MagicMock, patch

from ai_agent.tools import ToolRegistry
from ai_agent.agent import AIAgent
from ai_agent.memory import MemoryManager
from ai_agent.config import Config


class TestToolRegistry:
    """Unit tests for dynamic ToolRegistry and schema generation."""

    def test_default_tools_registered(self):
        registry = ToolRegistry()
        tools = registry.registered_tools
        assert "read_file" in tools
        assert "list_files" in tools
        assert "edit_file" in tools
        assert "delete_file" in tools
        assert "create_file" in tools
        assert "search_files" in tools
        assert "run_terminal_command" in tools
        assert len(tools) >= 7

    def test_dynamic_openai_schemas(self):
        registry = ToolRegistry()
        schemas = registry.get_openai_schemas()
        assert isinstance(schemas, list)

        schema_map = {s["function"]["name"]: s["function"] for s in schemas}
        assert "read_file" in schema_map
        read_func = schema_map["read_file"]
        assert "path" in read_func["parameters"]["properties"]
        assert read_func["parameters"]["required"] == ["path"]
        assert read_func["parameters"]["properties"]["path"]["type"] == "string"

    def test_dynamic_prompt_signatures(self):
        registry = ToolRegistry()
        signatures = registry.get_prompt_signatures()
        assert "read_file" in signatures
        assert "list_files" in signatures
        assert "delete_file" in signatures

    def test_custom_tool_registration_and_execution(self):
        registry = ToolRegistry()

        def custom_adder(a: int, b: int = 10) -> int:
            """Add two numbers together."""
            return a + b

        registry.register("custom_adder", custom_adder)
        assert registry.is_registered("custom_adder")

        # Positional execution
        assert registry.execute("custom_adder", 5, 15) == "20"
        # Keyword execution
        assert registry.execute("custom_adder", {"a": 20, "b": 30}) == "50"
        # Mixed execution via __args__
        assert registry.execute("custom_adder", {"__args__": [100], "b": 50}) == "150"

        # Schema generated for custom tool
        schemas = registry.get_openai_schemas()
        custom_schema = next(s for s in schemas if s["function"]["name"] == "custom_adder")
        assert custom_schema["function"]["parameters"]["properties"]["a"]["type"] == "integer"
        assert custom_schema["function"]["parameters"]["required"] == ["a"]


class TestAgentExecution:
    """Unit tests for AIAgent orchestrator."""

    def test_agent_initialization_and_system_prompt(self, tmp_path):
        mem_file = tmp_path / "test_mem.json"
        mm = MemoryManager(mem_file)
        mm.remember("user_name", "Idris")

        with patch.dict(os.environ, {"HF_TOKEN": "mock-token", "AGENT_MODEL": "test-model"}):
            Config.API_KEY = "mock-token"
            agent = AIAgent(memory_manager=mm)

            prompt = agent.build_system_prompt()
            assert "Idris" in prompt
            assert "system tools" in prompt
            assert "delete_file" in prompt

    def test_agent_fallback_tool_execution(self, tmp_path):
        """Verify Strategy C fallback execution when user prompt directly requests a tool."""
        mem_file = tmp_path / "test_mem.json"
        mm = MemoryManager(mem_file)

        with patch.dict(os.environ, {"HF_TOKEN": "mock-token", "AGENT_MODEL": "test-model"}):
            Config.API_KEY = "mock-token"
            agent = AIAgent(memory_manager=mm)

            # Mock run_inference to simulate a model that forgot to call tool
            with patch.object(agent, "run_inference", return_value=("I cannot do that.", [])):
                callback_calls = []

                def callback(resp, tool_name, args, result):
                    callback_calls.append((tool_name, result))

                # Pass explicit tool call prompt
                response = agent.process_turn("remember('city', 'Casablanca')", callback=callback)
                assert "Remembered 'city'" in response or len(callback_calls) > 0
                assert mm.recall("city") == "Casablanca"
