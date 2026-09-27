from pathlib import Path


def create_file(path: str, content: str) -> str:
    """Create a new file at the specified path with content."""
    file_path = Path(path)
    try:
        if file_path.exists():
            return f"File '{path}' already exists. Use edit_file to replace or modify content."
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully created file '{path}'"
    except Exception as err:
        return f"Error creating file '{path}': {err}"


def search_files(keyword: str, path: str = ".") -> str:
    """Search for a keyword or string pattern across files in the target directory (grep capability)."""
    search_dir = Path(path)
    if not search_dir.exists():
        return f"Path not found: {path}"
    if not search_dir.is_dir():
        return f"'{path}' is not a directory."

    if not keyword or not keyword.strip():
        return "Error: Empty search keyword provided."

    matches = []
    max_matches = 50  # Cap results to avoid overwhelming context window

    # Directories to ignore
    ignore_dirs = {".git", "__pycache__", ".venv", "node_modules", ".agent-memory.json"}

    try:
        for file_path in search_dir.rglob("*"):
            if file_path.is_file():
                if any(part in ignore_dirs for part in file_path.parts):
                    continue
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                    for line_num, line in enumerate(text.splitlines(), start=1):
                        if keyword.lower() in line.lower():
                            matches.append(f"{file_path} (Line {line_num}): {line.strip()}")
                            if len(matches) >= max_matches:
                                break
                except Exception:
                    continue

            if len(matches) >= max_matches:
                break

        if not matches:
            return f"No matches found for keyword '{keyword}' in directory '{path}'."

        result = f"Found {len(matches)} match(es) for '{keyword}':\n" + "\n".join(matches)
        if len(matches) >= max_matches:
            result += f"\n\n(Search capped at {max_matches} matches)"
        return result

    except Exception as err:
        return f"Error searching files in '{path}': {err}"
