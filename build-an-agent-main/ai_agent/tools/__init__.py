from typing import Callable, Dict, Any, Tuple, List
from .file_ops import read_file, list_files, edit_file
from .parser import parse_tool_call


class ToolRegistry:
    """Registry managing available tools for the AI Agent."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        # Register default toolsets
        self.register("read_file", read_file)
        self.register("list_files", list_files)
        self.register("edit_file", edit_file)

    def register(self, name: str, func: Callable) -> None:
        """Register a Python callable as a named tool."""
        self._tools[name] = func

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(name, None)

    def get_tool(self, name: str) -> Callable:
        """Retrieve tool function by name."""
        return self._tools.get(name)

    def is_registered(self, name: str) -> bool:
        """Check if tool exists in registry."""
        return name in self._tools

    def execute(self, name: str, *args, **kwargs) -> str:
        """Safely execute registered tool by name with exception handling."""
        tool_func = self.get_tool(name)
        if not tool_func:
            return f"Error: Tool '{name}' is not registered."
        try:
            return str(tool_func(*args, **kwargs))
        except Exception as error:
            return f"Tool '{name}' execution error: {error}"

    def get_prompt_signatures() -> str:
        """Return human-readable tool signatures for system prompt inclusion."""
        signatures = [
            "list_files(path='.')",
            "read_file(path)",
            "edit_file(path, old_str, new_str)",
            "remember(key, value)",
            "recall(key='')",
            "forget(key)",
        ]
        return ", ".join(signatures)


__all__ = ["ToolRegistry", "parse_tool_call", "read_file", "list_files", "edit_file"]
