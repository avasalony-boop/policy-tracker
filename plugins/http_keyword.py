import time
from typing import Iterable, Dict, Any, List
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# A lightweight HTML keyword-scanner for list pages.
# It does not do deep crawling; it scans the page, extracts links by CSS selector,
# and filters by include/exclude keywords in link text (and optionally snippet).

DEFAULT_HEADERS = {
    "User-Agent": "PolicyTrackerBot/0.1 (contact: your-email@example.com)"
}

def _match(text: str, include: List[str], exclude: List[str]) -> bool:
    t = (text or "").lower()
    if include:
        if not any(k.lower() in t for k in include):
            return False
    if exclude:
        if any(k.lower() in t for k in exclude):
            return False
    return True

class HTTPKeywordPlugin:
    name = "http-keyword"

    def __init__(self, sources: List[dict]):
        self.sources = sources

    def fetch(self, **kwargs) -> Iterable[Dict[str, Any]]:
        now = time.strftime("%Y-%m-%d")
        for s in self.sources:
            url = s.get("url")
            if not url:
                continue
            try:
                r = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
                r.raise_for_status()
            except Exception:
                continue
            soup = BeautifulSoup(r.text, "lxml")

            link_sel = s.get("link_selector") or "a"
            snippet_sel = s.get("snippet_selector")  # optional

            include = s.get("include") or []
            exclude = s.get("exclude") or []
            topic = s.get("topic") or ""
            state = s.get("state")

            for a in soup.select(link_sel):
                title = (a.get_text() or "").strip()
                href = a.get("href")
                if not href or not title:
                    continue
                if not _match(title, include, exclude):
                    # if we have a snippet selector, try to grab neighbor text to match on
                    if snippet_sel:
                        sn = soup.select_one(snippet_sel)
                        sn_text = (sn.get_text() or "").strip() if sn else ""
                        if not _match(sn_text, include, exclude):
                            continue
                    else:
                        continue
                abs_url = urljoin(url, href)
                yield {
                    "source": "http",
                    "jurisdiction": state,
                    "title": title,
                    "summary": "",
                    "url": abs_url,
                    "status": "ANNOUNCEMENT",
                    "effective_date": None,
                    "updated_at": now,
                    "topic_labels": topic,
                }
