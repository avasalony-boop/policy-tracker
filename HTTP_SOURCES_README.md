# HTTP keyword plugin (Plural + state sites)

This patch adds:
- `plugins/http_keyword.py` — a lightweight HTML scanner that pulls links from list pages and filters them by keywords.
- `sources.yml` — configure pages for Plural Policy searches and state sites you care about.

## Install
```
pip install beautifulsoup4 lxml
```
(You likely already installed `feedparser pyyaml` earlier.)

## Configure
Edit `sources.yml`. Each entry has `url`, `link_selector`, and `include` keywords. Start with the examples, then add more state sites (newsrooms, bill search result pages).

## Run (HTTP-only)
```
python collector_plugins.py --no-openstates --no-rss --sources sources.yml
```

## Run (all sources)
```
python collector_plugins.py --since 2025-08-01 --q "artificial OR privacy OR telehealth OR tenant" --sources sources.yml
```

> Note: This is a simple list-page scanner. If a site has an official RSS feed, prefer adding it to `feeds.yml` for stability. Always respect robots.txt and be gentle (no rapid polling).
