import os, argparse, hashlib, requests, yaml
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from sqlalchemy import text
from db import get_engine, upsert_bill, upsert_action, set_labels
from alerts import send_slack
from plugins.rss_source import RSSPlugin
from plugins.openstates_plugin import OpenStatesAdapter

load_dotenv()

OPENSTATES_API_KEY = os.getenv("OPENSTATES_API_KEY")
DEFAULT_SINCE_DAYS = int(os.getenv("DEFAULT_SINCE_DAYS", "2"))
DEFAULT_QUERY = os.getenv("DEFAULT_QUERY", "artificial intelligence OR generative OR privacy")
DEFAULT_STATES = [s.strip() for s in os.getenv("DEFAULT_STATES","").split(",")]
DRY_RUN = os.getenv("DRY_RUN","0") == "1"

BASE_URL = "https://v3.openstates.org/bills"

def openstates_get(params):
    headers = {"X-API-KEY": OPENSTATES_API_KEY}
    r = requests.get(BASE_URL, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def hash_action(bill_uid, a):
    s = f"{bill_uid}|{a.get('action_date')}|{a.get('organization')}|{','.join(a.get('classification',[]))}|{a.get('action_text')}"
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def load_feeds_config(path="feeds.yml"):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", help="ISO date YYYY-MM-DD for OpenStates updated_since")
    parser.add_argument("--q", help="OpenStates keyword query")
    parser.add_argument("--no-openstates", action="store_true", help="Skip OpenStates source")
    parser.add_argument("--no-rss", action="store_true", help="Skip RSS source")
    parser.add_argument("--feeds", default="feeds.yml", help="Path to feeds.yml")
    args = parser.parse_args()

    since = args.since or (datetime.now(timezone.utc) - timedelta(days=DEFAULT_SINCE_DAYS)).date().isoformat()
    q = args.q or DEFAULT_QUERY

    engine = get_engine()

    # --- RSS plugin ---
    if not args.no_rss:
        feeds = load_feeds_config(args.feeds)
        rss = RSSPlugin(feeds)
        count = 0
        for item in rss.fetch():
            count += 1
            # For now, just Slack it (could upsert into a 'news' table later)
            title = item.get("title","")
            url = item.get("url","")
            topic = item.get("topic_labels","")
            msg = f"📰 *{title}*\n{url}"
            if topic:
                msg = f"[{topic}] " + msg
            if not DRY_RUN and (item.get("slack") or True):
                send_slack(msg, blocks=[{"type":"section","text":{"type":"mrkdwn","text":msg}}])
        print(f"RSS items processed: {count}")

    # --- OpenStates pass-through (still uses your existing DB + normalize) ---
    if not args.no_openstates:
        raw_states = DEFAULT_STATES
        states = [s for s in (raw_states or []) if s.strip()]
        if not states:
            states = ["__ALL__"]
        total_new_status = 0
        adapter = OpenStatesAdapter()

        for st in states:
            page = 1
            while True:
                params = {
                    "q": q,
                    "updated_since": since,
                    "sort": "updated_at",
                    "per_page": 50,
                    "page": page,
                    "include": "sponsorships,actions,subject,related_bills"
                }
                if st != "__ALL__":
                    params["jurisdiction"] = st
                data = openstates_get(params)
                results = data.get("results", [])
                if not results:
                    break

                with engine.begin() as conn:
                    for b in results:
                        item = adapter.wrap(b)
                        bill = item["bill"]
                        actions = item["actions"]
                        old_status = conn.execute(text("SELECT status_general FROM bills WHERE bill_uid=:u"), {"u": bill["bill_uid"]}).scalar()
                        upsert_bill(conn, bill)
                        for a in actions:
                            aid = hash_action(bill["bill_uid"], a)
                            conn.execute(text("""
                                INSERT INTO actions (id, bill_uid, action_date, organization, classification, action_text)
                                VALUES (:id, :bill_uid, :action_date, :organization, :classification, :action_text)
                                ON CONFLICT(id) DO NOTHING
                            """), {
                                "id": aid,
                                "bill_uid": bill["bill_uid"],
                                "action_date": a.get("action_date"),
                                "organization": a.get("organization"),
                                "classification": ",".join(a.get("classification", [])),
                                "action_text": a.get("action_text"),
                            })
                        new_status = bill["status_general"]
                        if new_status and new_status != (old_status or "") and not DRY_RUN:
                            msg = f"*{bill['bill_number']}* · {bill['title']}\nState: {bill['jurisdiction']}  •  Status: *{new_status}*\nUpdated: {bill['last_action_date']}"
                            if bill.get("effective_date"):
                                msg += f"\nEffective: {bill['effective_date']}"
                            send_slack(msg, blocks=[{"type":"section","text":{"type":"mrkdwn","text":msg}}])

                page += 1
        print("OpenStates processing complete.")

    print("✅ Plugin run finished.")

if __name__ == "__main__":
    main()
