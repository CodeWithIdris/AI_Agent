from pathlib import Path


def read_file(path: str) -> str:
    """Return the text contents of a file at the given path."""
    file_path = Path(path)
    if not file_path.exists():
        return f"File not found: {path}"
    if file_path.is_dir():
        return f"'{path}' is a directory, not a file."
    try:
        return file_path.read_text(encoding="utf-8")
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
    file_path = Path(path)
    try:
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(new_str, encoding="utf-8")
            return f"Created new file: {path}"

        content = file_path.read_text(encoding="utf-8")
        if old_str not in content:
            return f"Target text 'old_str' not found in '{path}'"

        updated = content.replace(old_str, new_str, 1)
        file_path.write_text(updated, encoding="utf-8")
        return f"Successfully updated '{path}'"
    except Exception as err:
        return f"Error editing file '{path}': {err}"
