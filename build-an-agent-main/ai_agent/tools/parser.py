import ast
from typing import Tuple, List, Any, Optional


def parse_tool_call(text: str) -> Tuple[Optional[str], List[Any]]:
    """
    Safely parse an LLM tool call response into a function name and argument list.
    Supports clean function calls as well as responses wrapped in markdown code fences.
    """
    cleaned = text.strip()
    
    # Strip markdown code fencing if present
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        parsed_ast = ast.parse(cleaned, mode="eval")
        expression = parsed_ast.body
    except SyntaxError:
        return None, []

    if not isinstance(expression, ast.Call) or not isinstance(expression.func, ast.Name):
        return None, []

    try:
        args = [ast.literal_eval(arg) for arg in expression.args]
        args.extend(ast.literal_eval(keyword.value) for keyword in expression.keywords)
    except Exception:
        return None, []

    name = expression.func.id
    return name, args
