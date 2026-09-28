import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Union


class MemoryManager:
    """Manages persistent JSON key-value memory for the AI Agent with atomic writes."""

    def __init__(self, memory_path: Union[str, Path]):
        self.memory_path = Path(memory_path)

    def load(self) -> Dict[str, Any]:
        """Load memories from the JSON file safely."""
        if not self.memory_path.exists():
            return {}
        try:
            return json.loads(self.memory_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def save(self, memory: Dict[str, Any]) -> None:
        """Save memories to the JSON file atomically to prevent file corruption."""
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(memory, indent=2, sort_keys=True)

        # Write to temporary file in the same directory and replace atomically
        tmp_file = self.memory_path.with_name(f"{self.memory_path.name}.tmp")
        try:
            tmp_file.write_text(content, encoding="utf-8")
            os.replace(tmp_file, self.memory_path)
        except Exception:
            # Fallback direct write if atomic replace encounters an issue
            self.memory_path.write_text(content, encoding="utf-8")
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass

    def remember(self, key: str, value: Any) -> str:
        """Store or update a memory value under key."""
        if not key or not str(key).strip():
            return "Error: Memory key cannot be empty."
        memory = self.load()
        memory[str(key).strip()] = value
        self.save(memory)
        return f"Remembered '{key}'"

    def recall(self, key: str = "") -> str:
        """Retrieve a specific memory by key, or dump all memories."""
        memory = self.load()
        if key:
            trimmed = str(key).strip()
            if trimmed in memory:
                val = memory[trimmed]
                if isinstance(val, (dict, list)):
                    return json.dumps(val, indent=2, sort_keys=True)
                return str(val)
            return f"No memory found for '{key}'"
        if not memory:
            return "No memories stored yet."
        return json.dumps(memory, indent=2, sort_keys=True)

    def forget(self, key: str) -> str:
        """Remove a memory entry by key."""
        trimmed = str(key).strip()
        memory = self.load()
        if trimmed not in memory:
            return f"No memory found for '{key}'"
        del memory[trimmed]
        self.save(memory)
        return f"Forgot '{key}'"

    def clear(self) -> str:
        """Clear all stored memories."""
        self.save({})
        return "All memories cleared."

