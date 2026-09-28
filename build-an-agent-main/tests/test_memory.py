import json
from pathlib import Path
import pytest

from ai_agent.memory import MemoryManager


class TestMemoryManager:
    """Unit tests for MemoryManager persistence and operations."""

    def test_remember_and_recall_string(self, tmp_path):
        mem_file = tmp_path / "memory.json"
        mm = MemoryManager(mem_file)

        res = mm.remember("language", "Python")
        assert "Remembered 'language'" in res

        # Recall specific key
        val = mm.recall("language")
        assert val == "Python"

        # Recall non-existent key
        missing = mm.recall("unknown_key")
        assert "No memory found" in missing

    def test_remember_structured_data(self, tmp_path):
        mem_file = tmp_path / "memory.json"
        mm = MemoryManager(mem_file)

        data = {"model": "Qwen", "tokens": 4096, "active": True}
        mm.remember("config", data)

        recalled = mm.recall("config")
        parsed = json.loads(recalled)
        assert parsed == data

    def test_forget_and_clear(self, tmp_path):
        mem_file = tmp_path / "memory.json"
        mm = MemoryManager(mem_file)

        mm.remember("k1", "v1")
        mm.remember("k2", "v2")

        forget_res = mm.forget("k1")
        assert "Forgot 'k1'" in forget_res
        assert "No memory found" in mm.recall("k1")

        clear_res = mm.clear()
        assert "All memories cleared" in clear_res
        assert mm.recall() == "No memories stored yet."

    def test_atomic_persistence(self, tmp_path):
        mem_file = tmp_path / "atomic_memory.json"
        mm = MemoryManager(mem_file)

        mm.remember("key", "val")
        assert mem_file.exists()
        # Ensure temporary file is cleaned up after atomic replacement
        assert not mem_file.with_name(f"{mem_file.name}.tmp").exists()

        # Reload in a new manager instance
        mm2 = MemoryManager(mem_file)
        assert mm2.recall("key") == "val"

    def test_corrupt_file_handling(self, tmp_path):
        mem_file = tmp_path / "corrupt.json"
        mem_file.write_text("{invalid_json: 123", encoding="utf-8")

        mm = MemoryManager(mem_file)
        assert mm.load() == {}
        assert mm.recall() == "No memories stored yet."
