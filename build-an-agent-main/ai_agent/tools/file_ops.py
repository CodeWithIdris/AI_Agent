from pathlib import Path
from typing import Optional


def read_file(path: str, start_line: int = 1, end_line: Optional[int] = None) -> str:
    """
    Return the text contents of a file at the given path.
    Supports optional line-level pagination via start_line (1-indexed) and end_line.
    """
    file_path = Path(path)
    if not file_path.exists():
        return f"File not found: {path}"
    if file_path.is_dir():
        return f"'{path}' is a directory, not a file."
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)

        if total_lines == 0:
            return "(Empty file)"

        if start_line is not None and start_line > 1 or end_line is not None:
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, end_line) if end_line is not None else total_lines
            selected = lines[start_idx:end_idx]
            formatted_lines = [
                f"{i}: {line}" for i, line in enumerate(selected, start=start_idx + 1)
            ]
            header = f"[File: {path} | Showing lines {start_idx + 1}-{end_idx} of {total_lines}]\n"
            return header + "".join(formatted_lines)

        return content
    except UnicodeDecodeError:
        return f"Cannot read binary file directly: {path}"
    except Exception as err:
        return f"Error reading file '{path}': {err}"


def list_files(path: str = ".") -> str:
    """Return a newline-separated listing of files and directories at path."""
    directory = Path(path)
    if not directory.exists():
        return f"Path not found: {path}"
    if not directory.is_dir():
        return f"'{path}' is not a directory."
    try:
        items = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        formatted = []
        for item in items:
            prefix = "[DIR] " if item.is_dir() else "[FILE]"
            formatted.append(f"{prefix} {item.name}")
        return "\n".join(formatted) if formatted else "(Empty directory)"
    except Exception as err:
        return f"Error listing directory '{path}': {err}"


def edit_file(path: str, old_str: str, new_str: str) -> str:
    """Replace the first occurrence of old_str with new_str in a file, or create it if missing."""
    if not old_str:
        return "Error: 'old_str' cannot be empty. Use create_file to create new content."

    file_path = Path(path)
    try:
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(new_str, encoding="utf-8")
            return f"Created new file: {path}"

        content = file_path.read_text(encoding="utf-8")
        if old_str not in content:
            return f"Target text {repr(old_str)} not found in '{path}'"

        updated = content.replace(old_str, new_str, 1)
        file_path.write_text(updated, encoding="utf-8")
        return f"Successfully updated '{path}'"
    except Exception as err:
        return f"Error editing file '{path}': {err}"


def delete_file(path: str) -> str:
    """Safely delete a file at the specified path."""
    file_path = Path(path)
    if not file_path.exists():
        return f"File not found: {path}"
    if file_path.is_dir():
        return f"Cannot delete '{path}' because it is a directory."
    try:
        file_path.unlink()
        return f"Successfully deleted file: {path}"
    except Exception as err:
        return f"Error deleting file '{path}': {err}"

