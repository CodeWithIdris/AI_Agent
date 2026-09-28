import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO

from ai_agent.tools.web_ops import fetch_webpage, web_search
from ai_agent.agent import AIAgent
from ai_agent.memory import MemoryManager


class TestWebOpsAndPlanning:
    """Unit tests for web search, URL fetching, planning, and session exporting."""

    def test_fetch_webpage_invalid_url(self):
        res = fetch_webpage("not_a_url")
        assert "Invalid URL" in res

    def test_fetch_webpage_clean_html(self):
        sample_html = b"""
        <html>
            <head><style>body { color: red; }</style></head>
            <body>
                <script>alert('bad');</script>
                <h1>Python 3.13 Released</h1>
                <p>Python 3.13 introduces experimental free-threading.</p>
            </body>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.headers.get.return_value = "text/html"
        mock_resp.headers.get_content_charset.return_value = "utf-8"
        mock_resp.read.return_value = sample_html

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = fetch_webpage("https://docs.python.org/release.html")
            assert "Python 3.13 Released" in res
            assert "experimental free-threading" in res
            assert "alert" not in res
            assert "color: red" not in res

    def test_web_search_empty_query(self):
        res = web_search("")
        assert "Empty search query" in res

    def test_web_search_mock_results(self):
        mock_html = b"""
        <div class="result__body">
            <a class="result__url" href="https://example.com/doc">https://example.com/doc</a>
            <a class="result__a" href="https://example.com/doc">FastAPI Documentation</a>
            <a class="result__snippet">Modern, fast web framework for building APIs with Python.</a>
        </div>
        </div>
        """
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = mock_html

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = web_search("fastapi documentation")
            assert "FastAPI Documentation" in res
            assert "https://example.com/doc" in res


    def test_export_session_report(self, tmp_path):
        mm = MemoryManager(tmp_path / "mem.json")
        mm.remember("preferred_lang", "Python")
        agent = AIAgent(provider="ollama", memory_manager=mm)
        agent.history = [
            {"role": "user", "content": "Hello agent"},
            {"role": "assistant", "content": "Hello! How can I help?"},
        ]

        out_file = tmp_path / "session_report.md"
        report_msg = agent.export_session_report(str(out_file))
        assert "saved to" in report_msg
        assert out_file.exists()

        content = out_file.read_text(encoding="utf-8")
        assert "Session Execution Report" in content
        assert "preferred_lang" in content
        assert "Hello agent" in content

    def test_plan_and_execute(self, tmp_path):
        mm = MemoryManager(tmp_path / "mem.json")
        agent = AIAgent(provider="ollama", memory_manager=mm)

        with patch.object(agent, "process_turn", side_effect=["Step 1: Check files", "All tasks done"]):
            res = agent.plan_and_execute("Refactor helper")
            assert "Implementation Plan" in res
            assert "Execution Result" in res
