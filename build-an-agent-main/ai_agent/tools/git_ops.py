import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

CHECKPOINT_DIR = Path(".agent-checkpoints")


def is_git_repo(path: str = ".") -> bool:
    """Check if the target directory is inside a Git repository."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return res.returncode == 0 and res.stdout.strip() == "true"
    except Exception:
        return False


def get_git_diff(path: str = ".") -> str:
    """
    Get current unstaged and staged Git diffs for the workspace.
    Returns clear message if clean or not a git repository.
    """
    if not is_git_repo(path):
        return "Workspace is not a Git repository or Git is not installed."

    try:
        # Check status first
        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if not status.stdout.strip():
            return "✅ Workspace is clean (no uncommitted or modified files)."

        # Get diff of tracked modifications
        diff = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        diff_output = diff.stdout.strip()

        # If diff is empty (e.g. untracked new files only), show git status summary
        if not diff_output:
            return f"🌿 Workspace changes (untracked files):\n{status.stdout.strip()}"

        return f"🌿 Current Git Diff (HEAD):\n\n{diff_output}\n\nSummary:\n{status.stdout.strip()}"

    except Exception as err:
        return f"Error reading Git diff: {err}"


def create_checkpoint(target_file: Optional[str] = None, description: str = "auto-checkpoint", workspace: str = ".") -> str:
    """
    Creates a rollback checkpoint before file modifications.
    If target_file is provided, backs up that specific file.
    If target_file is None, snapshots git state or modified files.
    """
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    timestamp = int(time.time() * 1000)
    cp_id = f"cp_{timestamp}"

    checkpoint_meta = {
        "id": cp_id,
        "timestamp": timestamp,
        "description": description,
        "files": [],
    }

    try:
        cp_path = CHECKPOINT_DIR / cp_id
        cp_path.mkdir(exist_ok=True)

        if target_file:
            tf = Path(target_file)
            if tf.exists() and tf.is_file():
                dest = cp_path / tf.name
                shutil.copy2(tf, dest)
                checkpoint_meta["files"].append({
                    "original": str(tf),
                    "backup": str(dest),
                    "existed": True,
                })
            else:
                checkpoint_meta["files"].append({
                    "original": str(tf),
                    "backup": "",
                    "existed": False,
                })

        # Save metadata entry
        import json
        meta_file = cp_path / "metadata.json"
        meta_file.write_text(json.dumps(checkpoint_meta, indent=2), encoding="utf-8")

        # Keep checkpoint stack index
        index_file = CHECKPOINT_DIR / "stack.json"
        stack = []
        if index_file.exists():
            try:
                stack = json.loads(index_file.read_text(encoding="utf-8"))
            except Exception:
                stack = []
        stack.append(cp_id)
        index_file.write_text(json.dumps(stack, indent=2), encoding="utf-8")

        return f"Checkpoint `{cp_id}` created: {description}"

    except Exception as err:
        return f"Failed to create checkpoint: {err}"


def undo_last_change(workspace: str = ".") -> str:
    """
    Reverts the workspace to the most recent checkpoint snapshot.
    """
    index_file = CHECKPOINT_DIR / "stack.json"
    if not index_file.exists():
        # Fallback to git checkout if git repo
        if is_git_repo(workspace):
            try:
                subprocess.run(["git", "restore", "."], cwd=workspace, check=True)
                return "✅ Reverted workspace changes using Git restore."
            except Exception as e:
                return f"No checkpoints found, and git restore failed: {e}"
        return "No checkpoints available to undo."

    import json
    try:
        stack = json.loads(index_file.read_text(encoding="utf-8"))
    except Exception:
        return "Corrupted checkpoint stack."

    if not stack:
        return "No further checkpoints available to undo."

    cp_id = stack.pop()
    index_file.write_text(json.dumps(stack, indent=2), encoding="utf-8")

    cp_path = CHECKPOINT_DIR / cp_id
    meta_file = cp_path / "metadata.json"
    if not meta_file.exists():
        return f"Checkpoint `{cp_id}` metadata missing."

    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        restored_files = []

        for item in meta.get("files", []):
            orig_path = Path(item["original"])
            if item.get("existed", True):
                b_path = Path(item["backup"])
                if b_path.exists():
                    shutil.copy2(b_path, orig_path)
                    restored_files.append(f"Restored: {orig_path.name}")
            else:
                # File was newly created in this step, delete on rollback
                if orig_path.exists():
                    orig_path.unlink()
                    restored_files.append(f"Removed created file: {orig_path.name}")

        # Clean up this checkpoint directory
        shutil.rmtree(cp_path, ignore_errors=True)

        summary = ", ".join(restored_files) if restored_files else "Workspace state restored"
        return f"↩️ Successfully reverted checkpoint `{cp_id}` ({meta.get('description', '')}). {summary}."

    except Exception as err:
        return f"Error while undoing checkpoint `{cp_id}`: {err}"
