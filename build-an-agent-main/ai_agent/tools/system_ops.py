import os
import subprocess
from pathlib import Path
from typing import Optional


def run_terminal_command(command: str, cwd: Optional[str] = None) -> str:
    """
    Execute a shell command locally in the workspace directory with timeout safeguards.
    Returns stdout or stderr output.
    """
    if not command or not command.strip():
        return "Error: Empty command string provided."

    # Prevent extremely dangerous commands across OS environments
    forbidden_substrings = [
        "rm -rf /",
        "rm -rf /*",
        "mkfs",
        "format c:",
        "format-volume",
        "del /s /q c:\\",
        "rmdir /s /q c:\\",
        ":(){ :|:& };:",
    ]
    command_lower = command.lower()
    for forbidden in forbidden_substrings:
        if forbidden in command_lower:
            return f"Command execution rejected for safety reasons: {forbidden}"

    working_dir = Path(cwd) if cwd else Path.cwd()
    if not working_dir.exists():
        return f"Error: Working directory does not exist: {cwd}"

    try:
        process = subprocess.run(  # nosec: B602 - audited system terminal command executor
            command,
            shell=True,
            cwd=str(working_dir),
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout limit
            encoding="utf-8",
            errors="replace",
        )

        output = []
        if process.stdout and process.stdout.strip():
            output.append(f"STDOUT:\n{process.stdout.strip()}")
        if process.stderr and process.stderr.strip():
            output.append(f"STDERR:\n{process.stderr.strip()}")

        if not output:
            return f"Command executed successfully with return code {process.returncode} (No output)."

        return "\n\n".join(output)

    except subprocess.TimeoutExpired:
        return f"Error: Command '{command}' timed out after 60 seconds."
    except Exception as err:
        return f"Error executing command '{command}': {err}"

