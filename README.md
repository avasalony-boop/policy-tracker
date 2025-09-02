# Policy Radar Starter (Open States + Slack)

This is a minimal, no-license-cost pipeline that:
- Fetches updates from Open States API v3 on a schedule
- Normalizes bill records into a single schema (Postgres or SQLite)
- Detects lifecycle changes (introduced → committee → floor → passed/enacted → veto/failed)
- Tags bills for EliseAI-relevant topics (AI, Privacy, Housing, Healthcare)
- Sends alerts to Slack when meaningful changes occur

## Quick start

1. **Create a virtualenv** and install deps:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Copy env** and fill in your keys:
   ```bash
   cp .env.example .env
   # then edit .env with your Open States key and Slack webhook
   ```

3. **Run DB migrations** (creates tables):
   ```bash
   python db.py migrate
   ```

4. **Run a one-off sync**:
   ```bash
   python collector.py --since 2025-09-01 --state=CA --q "artificial intelligence OR generative"
   ```

5. **Schedule it** (e.g., cron every 30–60 mins during sessions):
   ```cron
   */45 * * * * cd /path/to/policy_radar_starter && . .venv/bin/activate && python collector.py
   ```

6. **Optional dashboard**: See `serve.py` for a tiny read-only FastAPI endpoint. Hook up to any table UI.

---

## Design

- **DB**: Uses SQLAlchemy; `DATABASE_URL` supports Postgres (`postgresql+psycopg2://...`) or SQLite (`sqlite:///policy_radar.db`).
- **Normalization**: Open States bill → `Bill` + `Action` rows. Key: `bill_uid = f"openstates:{bill.id}"`.
- **Change detection**: maps Open States `action.classification` to lifecycle and emits Slack only on *meaningful* transitions.
- **Classifier**: simple keyword labels on title/summary/action text. You can later replace with a small ML model.
- **Idempotency**: Upserts by `bill_uid` and `action` hash; only sends Slack when lifecycle actually changes.

---

## Environment variables

See `.env.example` for the full list; main ones:

- `OPENSTATES_API_KEY` – free key from https://openstates.org
- `SLACK_WEBHOOK_URL` – Incoming Webhook for your Slack channel
- `DATABASE_URL` – e.g., `postgresql+psycopg2://user:pass@host:5432/dbname` or `sqlite:///policy_radar.db`
- `DEFAULT_SINCE_DAYS` – fallback window (e.g., 2), if you don’t pass `--since`
- `DEFAULT_QUERY` – default search query (keyword string)
- `DEFAULT_STATES` – comma-separated like `CA,NY,TX`
- `DRY_RUN` – set `1` to avoid writing DB / sending Slack

---

## Lifecycle mapping

We use `action.classification` from Open States to derive a high-level status:
- `introduced` → `INTRODUCED`
- `referral`, `committee-referral` → `IN_COMMITTEE`
- `committee-passage`, `committee-passage-favorable` → `REPORTED`
- `reading-1`, `reading-2`, `reading-3`, `floor-passage` → `ON_FLOOR`
- `passage` in both chambers → `PASSED_LEGISLATURE`
- `executive-signature`, `chaptered`, `enacted` → `ENACTED`
- `veto` → `VETOED`
- session ended with no floor action (heuristic) → `FAILED_DEAD`

For "died in committee", a periodic job checks sessions that have adjourned sine die and marks bills that never reached floor passage as `FAILED_DEAD`.

---

## Extending

- Add `/events` ingestion to alert on hearings/floor calendars.
- Add a thin classifier model (TF-IDF + Logistic Regression) in `classifier_ml.py`.
- Add a simple front-end table to `serve.py` or push data to Notion/Sheets.

---

© 2025 EliseAI – Starter template for internal use.
