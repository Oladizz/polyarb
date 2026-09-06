"""
Multi-Engine Search Discovery Provider for PolyArb.
Supports Google Custom Search, DuckDuckGo HTML scraping, Wikipedia, and arXiv.
"""
import urllib.parse

import requests
from bs4 import BeautifulSoup

from app.core.config import GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_ENGINE_ID


def normalize_url(url: str) -> str:
    """Strips tracking query params, www, and trailing slashes."""
    if not url or not url.startswith("http"):
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        netloc = netloc.removeprefix("www.")
        tracking = ("utm_", "fbclid", "gclid", "ref", "source")
        if parsed.query:
            qsl = urllib.parse.parse_qsl(parsed.query)
            filtered = [(k, v) for k, v in qsl if not any(k.startswith(p) for p in tracking)]
            query_str = urllib.parse.urlencode(filtered)
        else:
            query_str = ""
        return urllib.parse.urlunparse((parsed.scheme, netloc, parsed.path.rstrip("/"), "", query_str, ""))
    except Exception:
        return url.strip()


class ResearchSearchEngine:
    """Discovers relevant developer and quant links across search engines."""

    def __init__(self):
        self.google_key = GOOGLE_SEARCH_API_KEY
        self.google_cx = GOOGLE_SEARCH_ENGINE_ID
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    def search_duckduckgo(self, query: str, max_results: int = 5) -> list[str]:
        urls = []
        try:
            url = "https://html.duckduckgo.com/html/"
            resp = requests.post(url, data={"q": query}, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.select(".result__url"):
                    href = a.get("href", "")
                    if href.startswith("//"):
                        href = "https:" + href
                    clean = normalize_url(href)
                    if clean and clean not in urls:
                        urls.append(clean)
                        if len(urls) >= max_results:
                            break
        except Exception as e:
            print(f"DuckDuckGo warning: {e}")
        return urls

    def search_wikipedia(self, query: str, max_results: int = 3) -> list[str]:
        urls = []
        try:
            endpoint = "https://en.wikipedia.org/w/api.php"
            params = {"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": max_results}
            resp = requests.get(endpoint, params=params, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                for item in resp.json().get("query", {}).get("search", []):
                    title = item.get("title", "")
                    if title:
                        slug = urllib.parse.quote(title.replace(" ", "_"))
                        urls.append(f"https://en.wikipedia.org/wiki/{slug}")
        except Exception:
            pass
        return urls

    def discover(self, query: str, target_count: int = 5) -> list[str]:
        results = self.search_duckduckgo(query, max_results=target_count)
        if len(results) < target_count:
            wiki = self.search_wikipedia(query, max_results=2)
            for w in wiki:
                if w not in results:
                    results.append(w)
        return results[:target_count]
