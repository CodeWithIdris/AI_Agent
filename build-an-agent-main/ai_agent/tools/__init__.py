import inspect
from typing import Callable, Dict, Any, Tuple, List, Optional, get_origin, get_args, Union
from .file_ops import read_file, list_files, edit_file, delete_file
from .code_ops import create_file, search_files
from .system_ops import run_terminal_command
from .parser import parse_tool_call


def _python_type_to_json_type(py_type: Any) -> str:
    """Map Python typing annotation to JSON schema type string."""
    origin = get_origin(py_type)
    if origin is Union:
        args = [a for a in get_args(py_type) if a is not type(None)]
        if args:
            py_type = args[0]

    if py_type in (str, Optional[str]):
        return "string"
    elif py_type in (int, Optional[int]):
        return "integer"
    elif py_type in (float, Optional[float]):
        return "number"
    elif py_type in (bool, Optional[bool]):
        return "boolean"
    elif py_type in (list, List, Optional[list], Optional[List]):
        return "array"
    elif py_type in (dict, Dict, Optional[dict], Optional[Dict]):
        return "object"
    return "string"


class ToolRegistry:
    """Registry managing available tools for the AI Agent."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        # Register default toolsets
        self.register("read_file", read_file)
        self.register("list_files", list_files)
        self.register("edit_file", edit_file)
        self.register("delete_file", delete_file)
        self.register("create_file", create_file)
        self.register("search_files", search_files)
        self.register("run_terminal_command", run_terminal_command)

    def register(self, name: str, func: Callable) -> None:
        """Register a Python callable as a named tool."""
        self._tools[name] = func

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(name, None)

    def get_tool(self, name: str) -> Optional[Callable]:
        """Retrieve tool function by name."""
        return self._tools.get(name)

    def is_registered(self, name: str) -> bool:
        """Check if tool exists in registry."""
        return name in self._tools

    @property
    def registered_tools(self) -> Dict[str, Callable]:
        """Return dict of all registered tools."""
        return self._tools.copy()

    def execute(self, name: str, *args, **kwargs) -> str:
        """Safely execute registered tool by name with flexible argument handling."""
        tool_func = self.get_tool(name)
        if not tool_func:
            return f"Error: Tool '{name}' is not registered."

        try:
            # Handle combined positional and keyword arguments packed into dictionary
            if len(args) == 1 and isinstance(args[0], dict):
                arg_dict = args[0]
                if "__args__" in arg_dict:
                    pos_args = arg_dict.get("__args__", [])
                    kw_args = {k: v for k, v in arg_dict.items() if k != "__args__"}
                    return str(tool_func(*pos_args, **kw_args))
                return str(tool_func(**arg_dict))

            if kwargs:
                if args:
                    return str(tool_func(*args, **kwargs))
                return str(tool_func(**kwargs))

            if args:
                if len(args) == 1 and isinstance(args[0], (list, tuple)):
                    return str(tool_func(*args[0]))
                return str(tool_func(*args))

            return str(tool_func())

        except TypeError as type_err:
            try:
                if args and isinstance(args[0], dict):
                    return str(tool_func(*list(args[0].values())))
                return f"Tool '{name}' argument mismatch: {type_err}"
            except Exception as err:
                return f"Tool '{name}' execution error: {err}"
        except Exception as error:
            return f"Tool '{name}' execution error: {error}"

    def get_openai_schemas(self) -> List[Dict[str, Any]]:
        """
        Dynamically generate OpenAI tools schema definitions
        for all currently registered tools based on their signatures and docstrings.
        """
        schemas = []
        for name, func in self._tools.items():
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or f"Execute {name} tool."
            description = doc.strip().split("\n\n")[0].replace("\n", " ").strip()

            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                    continue

                param_type = "string"
                if param.annotation != inspect.Parameter.empty:
                    param_type = _python_type_to_json_type(param.annotation)

                prop_def: Dict[str, Any] = {"type": param_type}
                if param.default != inspect.Parameter.empty:
                    prop_def["default"] = param.default
                else:
                    required.append(param_name)

                properties[param_name] = prop_def

            schema: Dict[str, Any] = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                    },
                },
            }
            if required:
                schema["function"]["parameters"]["required"] = required

            schemas.append(schema)

        return schemas

    def get_prompt_signatures(self) -> str:
        """Return human-readable tool signatures dynamically for system prompt inclusion."""
        signatures = []
        for name, func in self._tools.items():
            sig = inspect.signature(func)
            signatures.append(f"{name}{sig}")
        return ", ".join(signatures)


__all__ = [
    "ToolRegistry",
    "parse_tool_call",
    "read_file",
    "list_files",
    "edit_file",
    "delete_file",
    "create_file",
    "search_files",
    "run_terminal_command",
]

