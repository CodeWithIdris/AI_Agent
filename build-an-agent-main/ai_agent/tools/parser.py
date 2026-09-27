import ast
import json
from typing import Tuple, List, Any, Optional, Dict, Union


def parse_tool_call(text: str) -> Tuple[Optional[str], Union[List[Any], Dict[str, Any]]]:
    """
    Safely parse an LLM tool call response into a function name and arguments (list or dict).
    Supports:
      1. Python AST function call syntax: list_files('.') or run_terminal_command('git status')
      2. JSON tool call syntax: {"name": "list_files", "arguments": {"path": "."}}
      3. Markdown code fence wrapped calls: ```python list_files('.') ``` or ```json {...} ```
    """
    if not text:
        return None, []

    cleaned = text.strip()

    # Strip markdown code fencing if present
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # Strategy 1: Attempt JSON format parsing
    if (cleaned.startswith("{") and cleaned.endswith("}")) or (cleaned.startswith("[{") and cleaned.endswith("}]")):
        try:
            data = json.loads(cleaned)
            if isinstance(data, list) and len(data) > 0:
                data = data[0]

            if isinstance(data, dict):
                name = data.get("name") or data.get("tool") or data.get("function")
                raw_args = data.get("arguments") or data.get("args") or data.get("parameters")

                if name and isinstance(name, str):
                    if isinstance(raw_args, dict):
                        return name, raw_args
                    elif isinstance(raw_args, list):
                        return name, raw_args
                    elif raw_args is None or raw_args == "":
                        return name, []
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

    # Strategy 2: Attempt Python AST format parsing
    try:
        parsed_ast = ast.parse(cleaned, mode="eval")
        expression = parsed_ast.body
        if isinstance(expression, ast.Call) and isinstance(expression.func, ast.Name):
            args = [ast.literal_eval(arg) for arg in expression.args]
            kwargs = {keyword.arg: ast.literal_eval(keyword.value) for keyword in expression.keywords if keyword.arg}
            name = expression.func.id
            if kwargs:
                return name, kwargs
            return name, args
    except Exception:
        pass

    return None, []
