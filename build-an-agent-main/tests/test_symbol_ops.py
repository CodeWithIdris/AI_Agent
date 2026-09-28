import pytest
from pathlib import Path
from ai_agent.tools.symbol_ops import get_code_outline, find_symbol, find_references
from ai_agent.tools import ToolRegistry


class TestSymbolOps:
    """Test suite for AST symbol indexing, code outlining, and reference tracking."""

    def test_get_code_outline_python(self, tmp_path):
        sample_code = '''"""Module docstring."""

GLOBAL_VERSION = "1.0.0"

class DataPipeline:
    """Processes stream data."""

    def __init__(self, name: str):
        self.name = name

    def process(self, batch_size: int = 10) -> bool:
        """Executes a processing batch."""
        return True


def helper_function(x: int) -> int:
    """Calculates square."""
    return x * x
'''
        test_file = tmp_path / "pipeline.py"
        test_file.write_text(sample_code, encoding="utf-8")

        outline = get_code_outline(str(test_file))
        assert "DataPipeline" in outline
        assert "process(self, batch_size: int = 10) -> bool" in outline
        assert "helper_function(x: int) -> int" in outline
        assert "GLOBAL_VERSION" in outline
        assert "Processes stream data." in outline

    def test_get_code_outline_markdown(self, tmp_path):
        sample_md = """# Architecture Guide

## System Components
### Tool Registry
"""
        test_file = tmp_path / "docs.md"
        test_file.write_text(sample_md, encoding="utf-8")

        outline = get_code_outline(str(test_file))
        assert "Architecture Guide" in outline
        assert "System Components" in outline
        assert "Tool Registry" in outline

    def test_get_code_outline_syntax_error(self, tmp_path):
        bad_code = "def broken_func(\n  print('missing paren'"
        test_file = tmp_path / "broken.py"
        test_file.write_text(bad_code, encoding="utf-8")

        outline = get_code_outline(str(test_file))
        assert "SyntaxError" in outline

    def test_get_code_outline_missing_file(self):
        outline = get_code_outline("non_existent_file_xyz.py")
        assert "Error: File not found" in outline

    def test_find_symbol(self, tmp_path):
        f1 = tmp_path / "service.py"
        f1.write_text(
            "class PaymentService:\n    '''Handles billing.'''\n    pass\n\ndef process_refund(amount: float):\n    pass\n",
            encoding="utf-8",
        )

        res_class = find_symbol("PaymentService", str(tmp_path))
        assert "class `PaymentService`" in res_class
        assert "service.py" in res_class

        res_func = find_symbol("process_refund", str(tmp_path))
        assert "def `process_refund" in res_func

        res_not_found = find_symbol("NonExistentSymbol", str(tmp_path))
        assert "No symbol definitions matching" in res_not_found

    def test_find_references(self, tmp_path):
        f_def = tmp_path / "calculator.py"
        f_def.write_text("def compute_sum(a, b):\n    return a + b\n", encoding="utf-8")

        f_call = tmp_path / "app_main.py"
        f_call.write_text(
            "from calculator import compute_sum\n\nval = compute_sum(10, 20)\n",
            encoding="utf-8",
        )

        refs = find_references("compute_sum", str(tmp_path))
        assert "app_main.py" in refs
        assert "calculator.py" in refs
        assert "compute_sum" in refs

    def test_registry_integration(self):
        reg = ToolRegistry()
        assert reg.is_registered("get_code_outline")
        assert reg.is_registered("find_symbol")
        assert reg.is_registered("find_references")

        schemas = reg.get_openai_schemas()
        schema_names = [s["function"]["name"] for s in schemas]
        assert "get_code_outline" in schema_names
        assert "find_symbol" in schema_names
        assert "find_references" in schema_names
