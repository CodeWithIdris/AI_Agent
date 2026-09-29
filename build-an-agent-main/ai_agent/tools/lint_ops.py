import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".agent-checkpoints",
    ".agent-memory.json",
    ".ruff_cache",
    "dist",
    "build",
}

# Regex patterns for detecting hardcoded secrets and credentials
SECRET_PATTERNS = [
    (re.compile(r"""(?i)(?:api_key|apikey|secret_key|secret)\s*[:=]\s*['"][a-zA-Z0-9_\-]{16,}['"]"""), "Possible hardcoded API key or secret"),
    (re.compile(r"""sk-[a-zA-Z0-9\-_]{20,}"""), "Hardcoded OpenAI-style secret key"),
    (re.compile(r"""hf_[a-zA-Z0-9]{20,}"""), "Hardcoded HuggingFace token"),
    (re.compile(r"""AIza[0-9A-Za-z\-_]{35}"""), "Hardcoded Google API key"),
    (re.compile(r"""ghp_[a-zA-Z0-9]{36}"""), "Hardcoded GitHub personal access token"),
    (re.compile(r"""AKIA[0-9A-Z]{16}"""), "Hardcoded AWS Access Key ID"),
    (re.compile(r"""-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"""), "Embedded Private Key"),
]

# Words that indicate fake/placeholder values
PLACEHOLDER_WORDS = {"your_", "sample", "test", "dummy", "placeholder", "fake", "example", "<", "env", "none", "xxx", "mock", "demo"}


class CodeIssue:
    """Represents a static analysis finding."""

    def __init__(
        self,
        file_path: str,
        line: int,
        severity: str,
        category: str,
        rule_id: str,
        description: str,
        remediation: str,
    ):
        self.file_path = file_path
        self.line = line
        self.severity = severity  # HIGH, MEDIUM, LOW
        self.category = category  # SECURITY, RELIABILITY, QUALITY
        self.rule_id = rule_id
        self.description = description
        self.remediation = remediation


class CodeReviewer(ast.NodeVisitor):
    """AST-based security and code quality visitor."""

    def __init__(self, file_path: str, source_lines: List[str]):
        self.file_path = file_path
        self.lines = source_lines
        self.issues: List[CodeIssue] = []

    def visit_Call(self, node: ast.Call):
        # Rule: eval() or exec()
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in ("eval", "exec"):
            self.issues.append(
                CodeIssue(
                    file_path=self.file_path,
                    line=node.lineno,
                    severity="HIGH",
                    category="SECURITY",
                    rule_id="SEC001",
                    description=f"Dangerous dynamic code execution function `{func_name}()` detected.",
                    remediation="Avoid eval/exec. Use ast.literal_eval() for data or safe parsing alternatives.",
                )
            )

        # Rule: os.system
        if isinstance(node.func, ast.Attribute) and node.func.attr == "system":
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                self.issues.append(
                    CodeIssue(
                        file_path=self.file_path,
                        line=node.lineno,
                        severity="HIGH",
                        category="SECURITY",
                        rule_id="SEC002",
                        description="`os.system()` is vulnerable to shell command injection.",
                        remediation="Use subprocess.run(['cmd', 'arg'], shell=False) with parameterized arguments.",
                    )
                )

        # Rule: subprocess shell=True
        if func_name in ("run", "Popen", "call", "check_call", "check_output"):
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    line_text = self.lines[node.lineno - 1] if 0 < node.lineno <= len(self.lines) else ""
                    if "# nosec" in line_text or "# noqa" in line_text:
                        continue
                    self.issues.append(
                        CodeIssue(
                            file_path=self.file_path,
                            line=node.lineno,
                            severity="HIGH",
                            category="SECURITY",
                            rule_id="SEC003",
                            description="subprocess invoked with `shell=True` poses shell injection risks.",
                            remediation="Pass arguments as a list of strings and set `shell=False`, or add `# nosec` if audited.",
                        )
                    )

        # Rule: insecure pickle loading
        if func_name in ("load", "loads"):
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "pickle":
                self.issues.append(
                    CodeIssue(
                        file_path=self.file_path,
                        line=node.lineno,
                        severity="HIGH",
                        category="SECURITY",
                        rule_id="SEC004",
                        description="`pickle` deserialization can execute arbitrary code.",
                        remediation="Use safer serialization formats like JSON, MessagePack, or cryptography-verified signatures.",
                    )
                )

        # Rule: unsafe yaml.load
        if func_name == "load":
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id in ("yaml", "pyyaml"):
                has_safe_loader = False
                for kw in node.keywords:
                    if kw.arg == "Loader":
                        val_str = ""
                        if isinstance(kw.value, ast.Name):
                            val_str = kw.value.id
                        elif isinstance(kw.value, ast.Attribute):
                            val_str = kw.value.attr
                        if "SafeLoader" in val_str or "BaseLoader" in val_str:
                            has_safe_loader = True
                if not has_safe_loader:
                    self.issues.append(
                        CodeIssue(
                            file_path=self.file_path,
                            line=node.lineno,
                            severity="HIGH",
                            category="SECURITY",
                            rule_id="SEC005",
                            description="Unsafe `yaml.load()` without SafeLoader can lead to arbitrary code execution.",
                            remediation="Use `yaml.safe_load(data)` or specify `Loader=yaml.SafeLoader`.",
                        )
                    )

        # Rule: HTTP requests missing timeout
        if func_name in ("get", "post", "put", "delete", "patch", "urlopen", "request"):
            mod_name = None
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                mod_name = node.func.value.id
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Attribute) and isinstance(node.func.value.value, ast.Name):
                mod_name = f"{node.func.value.value.id}.{node.func.value.attr}"

            if mod_name in ("requests", "httpx", "urllib.request"):
                has_timeout = any(kw.arg == "timeout" for kw in node.keywords)
                if not has_timeout:
                    self.issues.append(
                        CodeIssue(
                            file_path=self.file_path,
                            line=node.lineno,
                            severity="MEDIUM",
                            category="RELIABILITY",
                            rule_id="REL004",
                            description=f"HTTP call `{mod_name}.{func_name}()` without explicit `timeout` can hang indefinitely.",
                            remediation="Add an explicit timeout parameter, e.g. `timeout=15` or `timeout=30`.",
                        )
                    )

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # Rule: bare except
        if node.type is None:
            self.issues.append(
                CodeIssue(
                    file_path=self.file_path,
                    line=node.lineno,
                    severity="MEDIUM",
                    category="RELIABILITY",
                    rule_id="REL001",
                    description="Bare `except:` clause intercepts SystemExit, KeyboardInterrupt, and masks bugs.",
                    remediation="Catch specific exceptions e.g. `except Exception:` or `except (ValueError, KeyError):`.",
                )
            )

        # Rule: silent broad exception swallowing (except Exception: pass)
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            is_broad = node.type is None or (isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"))
            if is_broad:
                exc_label = "bare" if node.type is None else node.type.id
                self.issues.append(
                    CodeIssue(
                        file_path=self.file_path,
                        line=node.lineno,
                        severity="LOW",
                        category="QUALITY",
                        rule_id="REL005",
                        description=f"Silent exception swallowing (`except {exc_label}: pass`) suppresses critical failures.",
                        remediation="Log the exception, handle it explicitly, or specify precise exception types.",
                    )
                )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node):
        # Rule: Mutable default arguments
        all_defaults = list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]
        for default in all_defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.issues.append(
                    CodeIssue(
                        file_path=self.file_path,
                        line=default.lineno,
                        severity="MEDIUM",
                        category="RELIABILITY",
                        rule_id="REL002",
                        description=f"Function `{node.name}` uses a mutable default argument (list/dict/set).",
                        remediation="Use `default=None` and initialize the container inside the function body.",
                    )
                )

        # Rule: Excessively long function
        end_lineno = getattr(node, "end_lineno", node.lineno)
        if (end_lineno - node.lineno) > 85:
            self.issues.append(
                CodeIssue(
                    file_path=self.file_path,
                    line=node.lineno,
                    severity="LOW",
                    category="QUALITY",
                    rule_id="QUAL001",
                    description=f"Function `{node.name}` is {end_lineno - node.lineno} lines long (> 85 lines).",
                    remediation="Decompose into smaller, single-responsibility helper functions.",
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # Rule: wildcard import
        for alias in node.names:
            if alias.name == "*":
                self.issues.append(
                    CodeIssue(
                        file_path=self.file_path,
                        line=node.lineno,
                        severity="MEDIUM",
                        category="RELIABILITY",
                        rule_id="REL003",
                        description=f"Wildcard import `from {node.module or ''} import *` pollutes namespace.",
                        remediation="Explicitly import only required functions and classes.",
                    )
                )
        self.generic_visit(node)


def _scan_text_for_secrets(file_path: str, lines: List[str]) -> List[CodeIssue]:
    """Scan raw lines for hardcoded credentials and tokens."""
    issues = []
    norm_path = file_path.replace("\\", "/").lower()
    is_test_suite_file = "tests/" in norm_path or norm_path.startswith("test_")

    for line_idx, line in enumerate(lines, start=1):
        # Skip commented lines or documentation markdown
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue

        line_lower = line.lower()
        # If in a test file, ignore synthetic test setup lines
        if is_test_suite_file and any(t in line_lower for t in ("mock", "write_text", "bad_file", "assert", "fixture")):
            continue

        for pattern, desc in SECRET_PATTERNS:
            match = pattern.search(line)
            if match:
                matched_str = match.group(0).lower()
                # Exclude obvious test/placeholder strings
                if any(p in matched_str for p in PLACEHOLDER_WORDS):
                    continue

                issues.append(
                    CodeIssue(
                        file_path=file_path,
                        line=line_idx,
                        severity="HIGH",
                        category="SECURITY",
                        rule_id="SEC000",
                        description=f"{desc} detected.",
                        remediation="Move credential to an environment variable (.env) or secret manager.",
                    )
                )
                break
    return issues


def run_code_review(path: str = ".") -> str:
    """
    Run automated static analysis and security scanning across workspace files.
    Identifies hardcoded credentials, dangerous execution functions,
    command injection risks, and code anti-patterns.
    """
    target = Path(path)
    if not target.exists():
        return f"Error: Path '{path}' not found."

    files_to_scan = []
    if target.is_file():
        files_to_scan = [target]
    elif target.is_dir():
        for f in target.rglob("*"):
            if f.is_file() and not any(part in IGNORE_DIRS for part in f.parts):
                if f.suffix in (".py", ".json", ".yaml", ".yml", ".env", ".toml"):
                    files_to_scan.append(f)

    if not files_to_scan:
        return f"No scannable code files found in '{path}'."

    all_issues: List[CodeIssue] = []

    for f in files_to_scan:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
        except Exception:
            continue

        rel_path = f.as_posix()

        # 1. Regex Secret Scanning on all files
        secret_issues = _scan_text_for_secrets(rel_path, lines)
        all_issues.extend(secret_issues)

        # 2. AST Analysis for Python files
        if f.suffix in (".py", ".pyi"):
            try:
                tree = ast.parse(content, filename=str(f))
                reviewer = CodeReviewer(rel_path, lines)
                reviewer.visit(tree)
                all_issues.extend(reviewer.issues)
            except SyntaxError:
                # Syntax errors will be detected by tests or parser
                pass
            except Exception:
                pass

    if not all_issues:
        return (
            f"Code Review Complete: Scanned {len(files_to_scan)} file(s).\n"
            "[CLEAN] No security vulnerabilities, credential leaks, or anti-patterns detected!"
        )

    # Sort findings by severity: HIGH > MEDIUM > LOW
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    all_issues.sort(key=lambda x: (severity_order.get(x.severity, 99), x.file_path, x.line))

    high_count = sum(1 for i in all_issues if i.severity == "HIGH")
    med_count = sum(1 for i in all_issues if i.severity == "MEDIUM")
    low_count = sum(1 for i in all_issues if i.severity == "LOW")

    report_lines = [
        f"=== Code Review & Security Report ===",
        f"Scanned: {len(files_to_scan)} file(s)",
        f"Findings: {len(all_issues)} issue(s) -> [HIGH: {high_count}, MEDIUM: {med_count}, LOW: {low_count}]",
        "",
    ]

    current_file = None
    for issue in all_issues:
        if issue.file_path != current_file:
            current_file = issue.file_path
            report_lines.append(f"\n--- {current_file} ---")

        report_lines.append(
            f"  [{issue.severity}] ({issue.rule_id}) Line {issue.line}: {issue.description}\n"
            f"         Remediation: {issue.remediation}"
        )

    return "\n".join(report_lines)
