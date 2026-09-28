import os
import re
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any


def parse_pytest_failures(output: str) -> List[Dict[str, Any]]:
    """Extract structured failure information from pytest or python traceback output."""
    failures = []

    # Split output by pytest failure headers: _________________ test_name _________________
    parts = re.split(r"(?:^|\n)\s*_{5,}\s*([^\s_]+)\s*_{5,}", output)

    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            test_name = parts[i]
            block = parts[i + 1] if i + 1 < len(parts) else ""
            # Strip short test summary info footer if in last block
            block = re.split(r"\n={5,}", block)[0]

            loc_match = re.search(r"([\w\\/\.\-]+\.py):(\d+):", block)
            error_match = re.search(r"E\s+([A-Za-z_]\w*(?:Error|Exception|AssertionError)?:.*?)(?:\n[^\sE]|\Z)", block, re.DOTALL)

            file_path = loc_match.group(1) if loc_match else "unknown"
            line_num = int(loc_match.group(2)) if loc_match else 0
            error_msg = error_match.group(1).strip() if error_match else "Test assertion failed."

            failures.append({
                "test_name": test_name,
                "file": file_path,
                "line": line_num,
                "error": error_msg,
                "details": block.strip(),
            })


    # Fallback to standard Python tracebacks if pytest failure blocks weren't found
    if not failures and "Traceback (most recent call last):" in output:
        traceback_matches = re.findall(
            r'File "([^"]+)", line (\d+), in (\w+)\n\s*(.*?)\n([A-Za-z_]\w*(?:Error|Exception)?:.*?)(?=\n\S|\Z)',
            output,
            re.DOTALL,
        )
        for fpath, lnum, func, code_line, err in traceback_matches:
            failures.append({
                "test_name": func,
                "file": fpath,
                "line": int(lnum),
                "error": err.strip(),
                "details": f"Line {lnum} in {func}: {code_line.strip()}",
            })

    return failures


def run_tests_with_diagnostics(command: str = "pytest", cwd: Optional[str] = None) -> str:
    """
    Execute test suite or script and extract high-level diagnostics, failing lines,
    and tracebacks for self-healing bug fixes.
    """
    working_dir = Path(cwd) if cwd else Path.cwd()
    if not working_dir.exists():
        return f"Error: Directory '{cwd}' does not exist."

    try:
        process = subprocess.run(
            command,
            shell=True,
            cwd=str(working_dir),
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )

        stdout = process.stdout or ""
        stderr = process.stderr or ""
        combined = f"{stdout}\n{stderr}".strip()

        if process.returncode == 0:
            # Tests passed
            summary_line = "All tests and scripts executed successfully (return code 0)."
            summary_match = re.search(r"(=+ .* passed.* =+)", stdout)
            if summary_match:
                summary_line = summary_match.group(1)
            return f"✅ SUCCESS: {summary_line}"

        # Tests failed - parse diagnostics
        failures = parse_pytest_failures(combined)

        report = [
            f"❌ TEST SUITE FAILED (Command: '{command}', Exit Code: {process.returncode})\n",
        ]

        if failures:
            report.append(f"Identified {len(failures)} Failure Point(s):")
            for i, fail in enumerate(failures, start=1):
                report.append(f"\n--- Failure #{i}: {fail['test_name']} ---")
                report.append(f"File: {fail['file']} (Line {fail['line']})")
                report.append(f"Error: {fail['error']}")

                # Attempt to extract surrounding source code
                target_file = working_dir / fail["file"]
                if target_file.exists() and target_file.is_file() and fail["line"] > 0:
                    try:
                        lines = target_file.read_text(encoding="utf-8").splitlines()
                        start_idx = max(0, fail["line"] - 4)
                        end_idx = min(len(lines), fail["line"] + 3)
                        context = []
                        for idx in range(start_idx, end_idx):
                            marker = " > " if idx == fail["line"] - 1 else "   "
                            context.append(f"{idx + 1:4d}{marker}{lines[idx]}")
                        report.append("Code Context:\n" + "\n".join(context))
                    except Exception:
                        pass
        else:
            # Truncated raw output if structured failure block couldn't be parsed
            report.append("Execution Output:\n" + combined[-1500:])

        report.append(
            "\n💡 Next Step: Inspect the failing file(s) with read_file, "
            "apply corrections using edit_file, and re-run run_tests_with_diagnostics."
        )

        return "\n".join(report)

    except subprocess.TimeoutExpired:
        return f"Error: Test command '{command}' timed out after 120 seconds."
    except Exception as err:
        return f"Error executing test diagnostics for '{command}': {err}"
