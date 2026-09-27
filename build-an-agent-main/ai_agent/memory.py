import json
from pathlib import Path
from typing import Any, Dict


class MemoryManager:
    """Manages persistent JSON key-value memory for the AI Agent."""

    def __init__(self, memory_path: Path):
        self.memory_path = Path(memory_path)

    def load(self) -> Dict[str, Any]:
        """Load memories from the JSON file."""
        if not self.memory_path.exists():
            return {}
        try:
            return json.loads(self.memory_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def save(self, memory: Dict[str, Any]) -> None:
        """Save memories to the JSON file with pretty formatting."""
        self.memory_path.write_text(
            json.dumps(memory, indent=2, sort_keys=True),
            encoding="utf-8"
        )

    def remember(self, key: str, value: Any) -> str:
        """Store or update a memory value under key."""
        memory = self.load()
        memory[key] = value
        self.save(memory)
        return f"Remembered '{key}'"

    def recall(self, key: str = "") -> str:
        """Retrieve a specific memory by key, or dump all memories."""
        memory = self.load()
        if key:
            if key in memory:
                return str(memory[key])
            return f"No memory found for '{key}'"
        if not memory:
            return "No memories stored yet."
        return json.dumps(memory, indent=2, sort_keys=True)

    def forget(self, key: str) -> str:
        """Remove a memory entry by key."""
        memory = self.load()
        if key not in memory:
            return f"No memory found for '{key}'"
        del memory[key]
        self.save(memory)
        return f"Forgot '{key}'"

    def clear(self) -> str:
        """Clear all stored memories."""
        self.save({})
        return "All memories cleared."
