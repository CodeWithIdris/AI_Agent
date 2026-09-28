import html
import re
import urllib.parse
import urllib.request
from typing import List, Dict, Any


def fetch_webpage(url: str, max_length: int = 4000) -> str:
    """
    Safely download and extract readable text content from any documentation or webpage URL.
    Strips scripts, styles, and HTML tags, returning clean text.
    """
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return "Error: Invalid URL. URL must start with http:// or https://"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36 AI-Agent/1.0"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type and "text/plain" not in content_type and "application/json" not in content_type:
                return f"Unsupported content type: {content_type}"

            charset = resp.headers.get_content_charset() or "utf-8"
            raw_html = resp.read().decode(charset, errors="replace")

        # Strip scripts and styling
        cleaned = re.sub(r"<script.*?</script>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<style.*?</style>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<!--.*?-->", "", cleaned, flags=re.DOTALL)

        # Convert headers and paragraph breaks to double newlines
        cleaned = re.sub(r"<(?:h[1-6]|p|div|section|article)[^>]*>", "\n\n", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<(?:li|br)[^>]*>", "\n* ", cleaned, flags=re.IGNORECASE)

        # Remove remaining HTML tags
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)

        # Unescape HTML entities
        text = html.unescape(cleaned)

        # Collapse excess whitespace
        lines = [line.strip() for line in text.splitlines()]
        filtered_lines = [l for l in lines if l]
        result_text = "\n".join(filtered_lines)

        if len(result_text) > max_length:
            result_text = result_text[:max_length] + f"\n\n... [Content truncated to {max_length} characters]"

        return f"📄 Content from {url}:\n\n{result_text}"

    except Exception as err:
        return f"Failed to fetch webpage ({url}): {err}"


def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for up-to-date documentation, solutions, and answers using zero-key search.
    Returns titles, links, and concise snippets.
    """
    if not query.strip():
        return "Error: Empty search query."

    try:
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        req = urllib.request.Request(
            search_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")

        # Parse DuckDuckGo HTML results
        # Look for result titles and snippet bodies
        results = []
        result_blocks = re.findall(r'<div class="result__body">.*?</div>\s*</div>', content, flags=re.DOTALL)

        for block in result_blocks[:max_results]:
            # Extract title and link
            link_match = re.search(r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.DOTALL)
            title_match = re.search(r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.DOTALL)
            snippet_match = re.search(r'<a class="result__snippet"[^>]*>(.*?)</a>', block, flags=re.DOTALL)

            title = html.unescape(re.sub(r"<[^>]+>", "", title_match.group(2))).strip() if title_match else "No Title"
            link = title_match.group(1) if title_match else (link_match.group(1) if link_match else "")
            
            # Clean DuckDuckGo redirect link /uddg=
            if "uddg=" in link:
                try:
                    parsed_link = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                    if "uddg" in parsed_link:
                        link = parsed_link["uddg"][0]
                except Exception:
                    pass

            snippet = html.unescape(re.sub(r"<[^>]+>", "", snippet_match.group(1))).strip() if snippet_match else ""

            if link and not link.startswith("/"):
                results.append(f"• **{title}**\n  URL: {link}\n  Snippet: {snippet}")

        if not results:
            # Fallback regex if layout differs
            generic_links = re.findall(r'<a class="result__snippet"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', content, flags=re.DOTALL)
            for link, snippet in generic_links[:max_results]:
                clean_snippet = html.unescape(re.sub(r"<[^>]+>", "", snippet)).strip()
                results.append(f"• {link}\n  {clean_snippet}")

        if not results:
            return f"🔍 Web Search for '{query}': No direct results parsed. Try refining the query."

        return f"🔍 Web Search Results for '{query}':\n\n" + "\n\n".join(results)

    except Exception as err:
        return f"Web search error for '{query}': {err}"
