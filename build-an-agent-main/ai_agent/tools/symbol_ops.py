import ast
from pathlib import Path
from typing import List, Dict, Any, Optional

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".agent-checkpoints",
    ".agent-memory.json",
    ".ruff_cache",
    "dist",
    "build",
}


def _format_args(args_node: ast.arguments) -> str:
    """Format AST arguments into a readable string including default values."""
    params = []
    # Positional args and their defaults
    non_default_count = len(args_node.args) - len(args_node.defaults)
    for i, arg in enumerate(args_node.args):
        ann = f": {ast.unparse(arg.annotation)}" if arg.annotation else ""
        def_str = ""
        if i >= non_default_count:
            default_val = args_node.defaults[i - non_default_count]
            def_str = f" = {ast.unparse(default_val)}"
        params.append(f"{arg.arg}{ann}{def_str}")

    if args_node.vararg:
        params.append(f"*{args_node.vararg.arg}")

    # Keyword-only args and their defaults
    for i, arg in enumerate(args_node.kwonlyargs):
        ann = f": {ast.unparse(arg.annotation)}" if arg.annotation else ""
        def_str = ""
        if i < len(args_node.kw_defaults) and args_node.kw_defaults[i] is not None:
            def_str = f" = {ast.unparse(args_node.kw_defaults[i])}"
        params.append(f"{arg.arg}{ann}{def_str}")

    if args_node.kwarg:
        params.append(f"**{args_node.kwarg.arg}")
    return ", ".join(params)


def get_code_outline(file_path: str) -> str:
    """
    Generate an AST-based hierarchical code outline of classes, methods, functions,
    and docstrings with exact line numbers for the specified file.
    """
    p = Path(file_path)
    if not p.exists():
        return f"Error: File not found at '{file_path}'."
    if not p.is_file():
        return f"Error: '{file_path}' is not a file."

    try:
        source = p.read_text(encoding="utf-8", errors="ignore")
    except Exception as err:
        return f"Error reading file '{file_path}': {err}"

    # Non-python fallback outlines
    if p.suffix.lower() == ".md":
        lines = source.splitlines()
        headings = []
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                headings.append(f"Line {idx:4d} | {stripped}")
        if not headings:
            return f"Markdown outline for '{file_path}': No headings found."
        return f"Markdown Outline for '{file_path}':\n" + "\n".join(headings)

    if p.suffix.lower() not in (".py", ".pyi"):
        lines = source.splitlines()
        return f"Outline for '{file_path}' ({len(lines)} lines, {len(source)} bytes)."

    # Python AST Outline
    try:
        tree = ast.parse(source, filename=str(p))
    except SyntaxError as syn_err:
        return f"SyntaxError parsing '{file_path}' at line {syn_err.lineno}: {syn_err.msg}"
    except Exception as parse_err:
        return f"Error parsing AST for '{file_path}': {parse_err}"

    outline_entries: List[str] = [f"Code Outline for `{p.as_posix()}`:"]
    found_symbols = 0

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            found_symbols += 1
            bases = [ast.unparse(b) for b in node.bases]
            bases_str = f"({', '.join(bases)})" if bases else ""
            end_line = getattr(node, "end_lineno", node.lineno)
            doc = ast.get_docstring(node)
            doc_str = f" - \"{doc.splitlines()[0]}\"" if doc else ""
            outline_entries.append(
                f"\n  class {node.name}{bases_str} [Lines {node.lineno}-{end_line}]{doc_str}"
            )

            # Class methods & attributes
            for subnode in node.body:
                if isinstance(subnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    prefix = "async def" if isinstance(subnode, ast.AsyncFunctionDef) else "def"
                    m_args = _format_args(subnode.args)
                    m_end = getattr(subnode, "end_lineno", subnode.lineno)
                    m_doc = ast.get_docstring(subnode)
                    m_doc_str = f" - \"{m_doc.splitlines()[0]}\"" if m_doc else ""
                    ret = f" -> {ast.unparse(subnode.returns)}" if subnode.returns else ""
                    outline_entries.append(
                        f"    |-- {prefix} {subnode.name}({m_args}){ret} [Lines {subnode.lineno}-{m_end}]{m_doc_str}"
                    )

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found_symbols += 1
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            f_args = _format_args(node.args)
            f_end = getattr(node, "end_lineno", node.lineno)
            doc = ast.get_docstring(node)
            doc_str = f" - \"{doc.splitlines()[0]}\"" if doc else ""
            ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
            outline_entries.append(
                f"  {prefix} {node.name}({f_args}){ret} [Lines {node.lineno}-{f_end}]{doc_str}"
            )

        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            # Record significant module-level constants (e.g. ALL_CAPS or __all__)
            target_names = []
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        target_names.append(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                target_names.append(node.target.id)

            for t_name in target_names:
                if t_name.isupper() or t_name.startswith("__"):
                    found_symbols += 1
                    outline_entries.append(f"  const {t_name} [Line {node.lineno}]")

    if found_symbols == 0:
        return f"File '{file_path}' parsed successfully, but contains no top-level classes or functions."

    return "\n".join(outline_entries)


def find_symbol(symbol_name: str, path: str = ".") -> str:
    """
    Search workspace Python files for definitions of classes, functions,
    methods, and constants matching symbol_name via AST indexing.
    """
    if not symbol_name or not symbol_name.strip():
        return "Error: Empty symbol name provided."

    target_dir = Path(path)
    if not target_dir.exists():
        return f"Path not found: '{path}'."

    query = symbol_name.strip()
    matches: List[str] = []
    max_matches = 30

    py_files = []
    if target_dir.is_file() and target_dir.suffix in (".py", ".pyi"):
        py_files = [target_dir]
    elif target_dir.is_dir():
        for f in target_dir.rglob("*.py"):
            if not any(part in IGNORE_DIRS for part in f.parts):
                py_files.append(f)

    for py_file in py_files:
        if len(matches) >= max_matches:
            break
        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(py_file))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if query.lower() in node.name.lower():
                    end_line = getattr(node, "end_lineno", node.lineno)
                    doc = ast.get_docstring(node)
                    doc_prev = f" - \"{doc.splitlines()[0]}\"" if doc else ""
                    rel_p = py_file.as_posix()
                    matches.append(
                        f"class `{node.name}` in {rel_p}:{node.lineno}-{end_line}{doc_prev}"
                    )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if query.lower() in node.name.lower():
                    end_line = getattr(node, "end_lineno", node.lineno)
                    doc = ast.get_docstring(node)
                    doc_prev = f" - \"{doc.splitlines()[0]}\"" if doc else ""
                    kind = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                    rel_p = py_file.as_posix()
                    args_s = _format_args(node.args)
                    matches.append(
                        f"{kind} `{node.name}({args_s})` in {rel_p}:{node.lineno}-{end_line}{doc_prev}"
                    )

    if not matches:
        return f"No symbol definitions matching '{symbol_name}' found in '{path}'."

    header = f"Found {len(matches)} symbol definition(s) for '{symbol_name}':\n"
    res = header + "\n".join(f"- {m}" for m in matches)
    if len(matches) >= max_matches:
        res += f"\n\n(Capped at {max_matches} results)"
    return res


def find_references(symbol_name: str, path: str = ".") -> str:
    """
    Search workspace Python files for all references, calls, and imports
    of symbol_name using AST node inspection.
    """
    if not symbol_name or not symbol_name.strip():
        return "Error: Empty symbol name provided."

    target_dir = Path(path)
    if not target_dir.exists():
        return f"Path not found: '{path}'."

    query = symbol_name.strip()
    references: List[str] = []
    max_refs = 50

    py_files = []
    if target_dir.is_file() and target_dir.suffix in (".py", ".pyi"):
        py_files = [target_dir]
    elif target_dir.is_dir():
        for f in target_dir.rglob("*.py"):
            if not any(part in IGNORE_DIRS for part in f.parts):
                py_files.append(f)

    for py_file in py_files:
        if len(references) >= max_refs:
            break
        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
            lines = source.splitlines()
            tree = ast.parse(source, filename=str(py_file))
        except Exception:
            continue

        for node in ast.walk(tree):
            match_lineno = None
            ref_kind = "reference"

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == query:
                match_lineno = node.lineno
                ref_kind = "definition"
            elif isinstance(node, ast.ClassDef) and node.name == query:
                match_lineno = node.lineno
                ref_kind = "definition"
            elif isinstance(node, ast.Name) and node.id == query:
                match_lineno = node.lineno
                ref_kind = "variable/identifier"
            elif isinstance(node, ast.Attribute) and node.attr == query:
                match_lineno = node.lineno
                ref_kind = "attribute access"
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if alias.name == query or alias.asname == query:
                        match_lineno = node.lineno
                        ref_kind = "import"
                        break

            if match_lineno:
                snippet = lines[match_lineno - 1].strip() if 0 < match_lineno <= len(lines) else ""
                ref_entry = f"{py_file.as_posix()}:{match_lineno} [{ref_kind}] `{snippet}`"
                if ref_entry not in references:
                    references.append(ref_entry)
                    if len(references) >= max_refs:
                        break

    if not references:
        return f"No references to symbol '{symbol_name}' found in '{path}'."

    header = f"Found {len(references)} reference(s) to '{symbol_name}':\n"
    res = header + "\n".join(f"- {r}" for r in references)
    if len(references) >= max_refs:
        res += f"\n\n(Capped at {max_refs} results)"
    return res
