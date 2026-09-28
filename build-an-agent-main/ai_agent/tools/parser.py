import ast
import json
import re
from typing import Tuple, List, Any, Optional, Dict, Union


def _extract_embedded_call(text: str) -> Optional[str]:
    """
    Look for a python function call pattern or code block in text when full text isn't a direct call.
    Example: 'I will run the command: run_terminal_command("git status")'
    """
    # 1. Check for markdown code blocks first
    code_block_match = re.search(r"```(?:python)?\s*([a-zA-Z_]\w*\s*\(.*?\))\s*```", text, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    # 2. Check for inline code snippet or standalone function call pattern
    call_match = re.search(r"([a-zA-Z_]\w*\s*\([^)]*\))", text)
    if call_match:
        candidate = call_match.group(1).strip()
        # Verify it parses as an AST call
        try:
            node = ast.parse(candidate, mode="eval").body
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                return candidate
        except Exception:
            pass

    return None


def parse_tool_call(text: str) -> Tuple[Optional[str], Union[List[Any], Dict[str, Any]]]:
    """
    Safely parse an LLM tool call response into a function name and arguments (list or dict).
    Supports:
      1. Python AST function call syntax: list_files('.') or search_files('kw', path='.')
      2. JSON tool call syntax: {"name": "list_files", "arguments": {"path": "."}}
      3. Markdown code fence wrapped calls: ```python list_files('.') ``` or ```json {...} ```
      4. Embedded calls inside conversational text
    """
    if not text:
        return None, []

    cleaned = text.strip()

    # Strip markdown code fencing if entire text is wrapped
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # Strategy 1: JSON format parsing (exact or embedded)
    json_candidate = None
    if (cleaned.startswith("{") and cleaned.endswith("}")) or (cleaned.startswith("[{") and cleaned.endswith("}]")):
        json_candidate = cleaned
    else:
        # Search for embedded JSON object in text
        json_match = re.search(r"(\{[\s\S]*\"name\"\s*:\s*\"[a-zA-Z_]\w*\"[\s\S]*\})", cleaned)
        if json_match:
            json_candidate = json_match.group(1)

    if json_candidate:
        try:
            data = json.loads(json_candidate)
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

    # Strategy 2: Python AST format parsing
    candidates_to_try = [cleaned]
    embedded = _extract_embedded_call(cleaned)
    if embedded and embedded != cleaned:
        candidates_to_try.append(embedded)

    for candidate in candidates_to_try:
        try:
            parsed_ast = ast.parse(candidate, mode="eval")
            expression = parsed_ast.body
            if isinstance(expression, ast.Call) and isinstance(expression.func, ast.Name):
                name = expression.func.id
                args = [ast.literal_eval(arg) for arg in expression.args]
                kwargs = {keyword.arg: ast.literal_eval(keyword.value) for keyword in expression.keywords if keyword.arg}

                # If both positional and keyword arguments are present, pack positional into __args__
                if args and kwargs:
                    combined = {"__args__": args, **kwargs}
                    return name, combined
                elif kwargs:
                    return name, kwargs
                return name, args
        except Exception:
            continue

    return None, []

