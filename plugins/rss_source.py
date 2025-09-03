import time
from typing import Iterable, Dict, Any, List
import requests
import feedparser

from .base import SourcePlugin

def _match_filters(title: str, summary: str, include: List[str], exclude: List[str]) -> bool:
    t = (title or "").lower()
    s = (summary or "").lower()
    if include:
        if not any(k.lower() in t or k.lower() in s for k in include):
            return False
    if exclude:
        if any(k.lower() in t or k.lower() in s for k in exclude):
            return False
    return True

class RSSPlugin(SourcePlugin):
    name = "rss"

    def __init__(self, feeds: List[dict]):
        self.feeds = feeds

    def fetch(self, **kwargs) -> Iterable[Dict[str, Any]]:
        now = time.strftime("%Y-%m-%d")
        for f in self.feeds:
            url = f.get("url")
            if not url:
                continue
            try:
                d = feedparser.parse(url)
            except Exception:
                continue
            include = f.get("include") or []
            exclude = f.get("exclude") or []
            topic = f.get("topic") or ""
            state = f.get("state")
            for e in d.entries:
                title = getattr(e, "title", "")
                summary = getattr(e, "summary", "") or getattr(e, "subtitle", "")
                link = getattr(e, "link", "")
                if not _match_filters(title, summary, include, exclude):
                    continue
                item = {
                    "source": "rss",
                    "jurisdiction": state,
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "status": "ANNOUNCEMENT",
                    "effective_date": None,
                    "updated_at": now,
                    "topic_labels": topic,
                }
                yield item
