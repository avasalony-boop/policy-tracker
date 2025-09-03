# Multi-source patch: RSS + "Policies now in effect" alerts

This patch adds:
- A **pluggable source system** (put new sources under `plugins/`).
- An **RSS plugin** powered by `feedparser` and `feeds.yml` config.
- `implemented_alerts.py` to send a digest of bills whose **effective_date** is within a recent window.
- `collector_plugins.py` to run *both* OpenStates and RSS in one command.

## Files added
- `plugins/base.py`
- `plugins/rss_source.py`
- `plugins/openstates_plugin.py`
- `feeds.yml` (edit this to choose your feeds)
- `implemented_alerts.py`
- `collector_plugins.py`

## Install extra dependency
```sh
pip install feedparser pyyaml
```

## Configure RSS feeds
Edit `feeds.yml` and add/remove feeds. Start with the examples, then expand with:
- Governor press releases, Attorney General press, State Dept. of Health news
- NCSL, IAPP, HUD, HHS OCR, etc.

## Run everything
- **OpenStates + RSS together (broad):**
```sh
python collector_plugins.py --since 2025-08-01 --q "artificial OR privacy OR telehealth OR tenant"
```
- **RSS only:**
```sh
python collector_plugins.py --no-openstates
```
- **OpenStates only:**
```sh
python collector_plugins.py --no-rss --since 2025-08-01 --q "artificial OR privacy OR telehealth OR tenant"
```

## Policies now in effect (digest)
Send a Slack summary of bills whose `effective_date` is within the last 7 days:
```sh
python implemented_alerts.py
```
Change the window by editing the script (e.g., 30 days).

## Schedule (cron examples)
- Hourly OpenStates + RSS:
```
0 * * * * cd /Users/YOU/Desktop/policy-tracker && source .venv/bin/activate && python collector_plugins.py --since $(date -v-2d +\%Y-\%m-\%d) --q "artificial OR privacy OR telehealth OR tenant"
```
- Daily "now effective" digest at 9am:
```
0 9 * * * cd /Users/YOU/Desktop/policy-tracker && source .venv/bin/activate && python implemented_alerts.py
```
