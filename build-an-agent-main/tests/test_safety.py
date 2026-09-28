import pytest
from unittest.mock import patch, MagicMock
from ai_agent.agent import AIAgent
from ai_agent.config import Config
from ai_agent.memory import MemoryManager


class TestSafetyAndObservability:
    """Unit tests for Human-in-the-Loop Safety Mode and Cost Observability."""

    def test_default_autonomous_mode(self, tmp_path):
        mm = MemoryManager(tmp_path / "mem.json")
        agent = AIAgent(provider="ollama", memory_manager=mm)
        assert agent.safety_mode == "AUTONOMOUS"

    def test_safety_mode_initialization(self, tmp_path):
        mm = MemoryManager(tmp_path / "mem.json")
        agent = AIAgent(provider="ollama", safety_mode="CONFIRM_DANGEROUS", memory_manager=mm)
        assert agent.safety_mode == "CONFIRM_DANGEROUS"

    def test_dangerous_tool_rejection_in_confirm_dangerous_mode(self, tmp_path):
        mm = MemoryManager(tmp_path / "mem.json")
        agent = AIAgent(provider="ollama", safety_mode="CONFIRM_DANGEROUS", memory_manager=mm)

        # Hook returns False (user rejected)
        rejection_hook = MagicMock(return_value=False)
        res = agent._execute_tool_with_safety("run_terminal_command", ["git status"], approval_hook=rejection_hook)

        assert "REJECTED" in res
        assert rejection_hook.called

    def test_dangerous_tool_approval_in_confirm_dangerous_mode(self, tmp_path):
        mm = MemoryManager(tmp_path / "mem.json")
        agent = AIAgent(provider="ollama", safety_mode="CONFIRM_DANGEROUS", memory_manager=mm)

        # Hook returns True (user approved)
        approval_hook = MagicMock(return_value=True)
        with patch.object(agent.tools, "execute", return_value="command output") as mock_exec:
            res = agent._execute_tool_with_safety("run_terminal_command", ["git status"], approval_hook=approval_hook)
            assert res == "command output"
            mock_exec.assert_called_once_with("run_terminal_command", ["git status"])

    def test_safe_read_only_tool_runs_unhindered_in_confirm_dangerous_mode(self, tmp_path):
        mm = MemoryManager(tmp_path / "mem.json")
        agent = AIAgent(provider="ollama", safety_mode="CONFIRM_DANGEROUS", memory_manager=mm)

        hook = MagicMock(return_value=False)
        with patch.object(agent.tools, "execute", return_value="file contents") as mock_exec:
            res = agent._execute_tool_with_safety("read_file", ["README.md"], approval_hook=hook)
            assert res == "file contents"
            # Read-only tools should NOT trigger dangerous approval hook
            assert not hook.called

    def test_cost_calculation(self):
        # gpt-4o-mini is $0.15 / $0.60 per 1M tokens
        cost = Config.calculate_cost("gpt-4o-mini", 1_000_000, 1_000_000)
        assert cost == 0.75

        # gemini-2.5-flash is $0.075 / $0.30 per 1M tokens
        cost_gemini = Config.calculate_cost("gemini-2.5-flash", 2_000_000, 1_000_000)
        assert cost_gemini == 0.45
