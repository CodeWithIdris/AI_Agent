import subprocess
import sys


def run_terminal_command(command: str) -> str:
    """
    Execute a shell command locally in the workspace directory with timeout safeguards.
    Returns stdout or stderr output.
    """
    if not command or not command.strip():
        return "Error: Empty command string provided."

    # Prevent extremely dangerous commands if needed
    forbidden_substrings = ["rm -rf /", "mkfs", "format C:"]
    for forbidden in forbidden_substrings:
        if forbidden.lower() in command.lower():
            return f"Command execution rejected for safety reasons: {forbidden}"

    try:
        process = subprocess.run(
            command,
            shell=True,
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
