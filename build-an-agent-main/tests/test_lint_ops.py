import pytest
from pathlib import Path
from ai_agent.tools.lint_ops import run_code_review
from ai_agent.agent import AIAgent
from ai_agent.memory import MemoryManager
from ai_agent.tools import ToolRegistry


class TestLintOpsAndCodeReview:
    """Test suite for automated security linter and static code review."""

    def test_detect_hardcoded_secrets(self, tmp_path):
        bad_file = tmp_path / "config_bad.py"
        bad_file.write_text(
            'API_KEY = "sk-1234567890abcdef1234567890abcdef"\nHF_TOKEN = "hf_abcdefghijklmnopqrstuvwxyz123456"\n',
            encoding="utf-8",
        )

        report = run_code_review(str(tmp_path))
        assert "[HIGH]" in report
        assert "SEC000" in report
        assert "secret key" in report.lower() or "token" in report.lower()

    def test_detect_eval_and_exec(self, tmp_path):
        bad_file = tmp_path / "dynamic_exec.py"
        bad_file.write_text(
            "def run_custom(user_code):\n    eval(user_code)\n    exec(user_code)\n",
            encoding="utf-8",
        )

        report = run_code_review(str(tmp_path))
        assert "[HIGH]" in report
        assert "SEC001" in report
        assert "eval" in report
        assert "exec" in report

    def test_detect_os_system_and_subprocess_shell_true(self, tmp_path):
        bad_file = tmp_path / "command_injection.py"
        bad_file.write_text(
            "import os\nimport subprocess\n\ndef run_cmd(c):\n    os.system(c)\n    subprocess.run(c, shell=True)\n",
            encoding="utf-8",
        )

        report = run_code_review(str(tmp_path))
        assert "[HIGH]" in report
        assert "SEC002" in report
        assert "SEC003" in report
        assert "shell=True" in report

    def test_detect_insecure_pickle(self, tmp_path):
        bad_file = tmp_path / "deserializer.py"
        bad_file.write_text(
            "import pickle\n\ndef unpack(data):\n    return pickle.loads(data)\n",
            encoding="utf-8",
        )

        report = run_code_review(str(tmp_path))
        assert "[HIGH]" in report
        assert "SEC004" in report
        assert "pickle" in report

    def test_detect_mutable_default_and_bare_except(self, tmp_path):
        bad_file = tmp_path / "bad_patterns.py"
        bad_file.write_text(
            "def append_item(val, items=[]):\n    try:\n        items.append(val)\n    except:\n        pass\n    return items\n",
            encoding="utf-8",
        )

        report = run_code_review(str(tmp_path))
        assert "[MEDIUM]" in report
        assert "REL001" in report  # bare except
        assert "REL002" in report  # mutable default

    def test_detect_wildcard_import(self, tmp_path):
        bad_file = tmp_path / "wildcard.py"
        bad_file.write_text("from math import *\n\ndef calculate():\n    return sin(0)\n", encoding="utf-8")

        report = run_code_review(str(tmp_path))
        assert "[MEDIUM]" in report
        assert "REL003" in report

    def test_clean_code_passes(self, tmp_path):
        clean_file = tmp_path / "clean_module.py"
        clean_file.write_text(
            '''"""Safe mathematical helper module."""

def calculate_average(numbers: list) -> float:
    """Calculates arithmetic mean safely."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)
''',
            encoding="utf-8",
        )

        report = run_code_review(str(tmp_path))
        assert "[CLEAN]" in report
        assert "No security vulnerabilities" in report

    def test_agent_review_code_integration(self, tmp_path):
        mm = MemoryManager(tmp_path / "mem.json")
        agent = AIAgent(provider="ollama", memory_manager=mm)

        # Verify tool is registered
        assert agent.tools.is_registered("run_code_review")

        # Test agent review method
        clean_file = tmp_path / "helper.py"
        clean_file.write_text("def ping():\n    return 'pong'\n", encoding="utf-8")

        result = agent.review_code(str(tmp_path))
        assert "[CLEAN]" in result
