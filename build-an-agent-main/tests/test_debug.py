import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from ai_agent.tools.debug_ops import parse_pytest_failures, run_tests_with_diagnostics
from ai_agent.agent import AIAgent
from ai_agent.memory import MemoryManager


class TestDebugOps:
    """Unit tests for diagnostic extraction and self-healing test runner."""

    def test_parse_pytest_failures(self):
        sample_output = """
============================= FAILURES =============================
___________________________ test_divide ___________________________

    def test_divide():
        calc = Calculator()
>       assert calc.divide(10, 0) == 0
E       ZeroDivisionError: division by zero

tests/test_calc.py:15: ZeroDivisionError
===================== short test summary info =====================
FAILED tests/test_calc.py::test_divide - ZeroDivisionError: division by zero
1 failed in 0.05s
"""
        failures = parse_pytest_failures(sample_output)
        assert len(failures) == 1
        assert failures[0]["test_name"] == "test_divide"
        assert "ZeroDivisionError" in failures[0]["error"]
        assert failures[0]["line"] == 15
        assert "tests/test_calc.py" in failures[0]["file"]

    def test_run_tests_with_diagnostics_passing(self, tmp_path):
        # Run a python one-liner that exits with 0
        cmd = 'python -c "print(\'OK\')"'
        result = run_tests_with_diagnostics(cmd, cwd=str(tmp_path))
        assert "✅ SUCCESS" in result

    def test_run_tests_with_diagnostics_failing(self, tmp_path):
        # Create a failing python file
        test_py = tmp_path / "fail_script.py"
        test_py.write_text("assert 1 == 2, 'Value mismatch!'", encoding="utf-8")

        result = run_tests_with_diagnostics(f"python {test_py.name}", cwd=str(tmp_path))
        assert "❌ TEST SUITE FAILED" in result
        assert "AssertionError" in result or "Value mismatch!" in result
        assert "Next Step" in result

    def test_auto_debug_success_when_already_passing(self, tmp_path):
        mem_file = tmp_path / "test_mem.json"
        mm = MemoryManager(mem_file)
        agent = AIAgent(provider="ollama", memory_manager=mm)

        with patch("ai_agent.tools.debug_ops.run_tests_with_diagnostics", return_value="✅ SUCCESS: 5 passed"):
            report = agent.auto_debug("pytest")
            assert "already passing" in report

    def test_auto_debug_healing_flow(self, tmp_path):
        mem_file = tmp_path / "test_mem.json"
        mm = MemoryManager(mem_file)
        agent = AIAgent(provider="ollama", memory_manager=mm)

        diag_sequence = [
            "❌ TEST SUITE FAILED\nFailure: test_math.py:10",
            "✅ SUCCESS: 1 passed in 0.1s",
        ]

        with patch("ai_agent.tools.debug_ops.run_tests_with_diagnostics", side_effect=diag_sequence):
            with patch.object(agent, "process_turn", return_value="Fixed bug using edit_file."):
                report = agent.auto_debug("pytest")
                assert "Self-Healing Succeeded on Attempt 1" in report
