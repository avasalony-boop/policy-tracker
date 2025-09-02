\
import os, argparse, hashlib, requests, math
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from sqlalchemy import text
from db import get_engine, upsert_bill, upsert_action, set_labels
from normalize import normalize_openstates_bill
from classify import label_record
from alerts import send_slack

load_dotenv()

OPENSTATES_API_KEY = os.getenv("OPENSTATES_API_KEY")
DEFAULT_SINCE_DAYS = int(os.getenv("DEFAULT_SINCE_DAYS", "2"))
DEFAULT_QUERY = os.getenv("DEFAULT_QUERY", "artificial intelligence OR generative OR privacy")
DEFAULT_STATES = [s.strip() for s in os.getenv("DEFAULT_STATES","CA,NY").split(",")]
DRY_RUN = os.getenv("DRY_RUN","0") == "1"

BASE_URL = "https://v3.openstates.org/bills"

def openstates_get(params):
    headers = {"X-API-KEY": OPENSTATES_API_KEY}
    r = requests.get(BASE_URL, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def hash_action(bill_uid, a):
    s = f"{bill_uid}|{a.get('action_date')}|{a.get('organization')}|{','.join(a.get('classification',[]))}|{a.get('action_text')}"
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", help="ISO8601 date (YYYY-MM-DD) to use for updated_since")
    parser.add_argument("--state", action="append", help="State name or postal (e.g., CA). Repeatable.")
    parser.add_argument("--q", help="Search query string")
    args = parser.parse_args()

    if not OPENSTATES_API_KEY:
        raise SystemExit("OPENSTATES_API_KEY not set")

    since = args.since or (datetime.now(timezone.utc) - timedelta(days=DEFAULT_SINCE_DAYS)).date().isoformat()
    q = args.q or DEFAULT_QUERY
    states = args.state or DEFAULT_STATES

    engine = get_engine()
    total_new_status = 0

    for st in states:
        page = 1
        while True:
            params = {
                "q": q,
                "jurisdiction": st,
                "updated_since": since,
                "sort": "updated_at",
                "per_page": 50,
                "page": page,
                "include": "sponsorships,actions,subject,related_bills"
            }
            data = openstates_get(params)
            results = data.get("results", [])
            if not results:
                break

            with engine.begin() as conn:
                for b in results:
                    pack = normalize_openstates_bill(b)
                    bill = pack["bill"]
                    actions = pack["actions"]
                    # Detect old status to decide if we alert
                    old_status = conn.execute(text("SELECT status_general FROM bills WHERE bill_uid=:u"), {"u": bill["bill_uid"]}).scalar()
                    upsert_bill(conn, bill)

                    # Insert actions idempotently
                    for a in actions:
                        aid = hash_action(bill["bill_uid"], a)
                        upsert_action(conn, {
                            "id": aid,
                            "bill_uid": bill["bill_uid"],
                            "action_date": a.get("action_date"),
                            "organization": a.get("organization"),
                            "classification": ",".join(a.get("classification", [])),
                            "action_text": a.get("action_text"),
                        })

                    # Labels
                    labels = label_record(" ".join([bill.get("title") or "", bill.get("summary") or ""]))
                    topics = [k for k,v in labels.items() if v]
                    set_labels(conn, {
                        "bill_uid": bill["bill_uid"],
                        "topic_labels": ",".join(topics),
                        "client_vertical": "property_mgmt,healthcare" if ("housing" in topics or "healthcare" in topics) else "",
                        "impact_score": 50 if ("ai" in topics or "privacy" in topics) else 20
                    })

                    # Alert on meaningful status change
                    new_status = bill["status_general"]
                    if new_status and new_status != (old_status or ""):
                        total_new_status += 1
                        if not DRY_RUN:
                            msg = f"*{bill['bill_number']}* · {bill['title']}\nState: {bill['jurisdiction']}  •  Status: *{new_status}*\nUpdated: {bill['last_action_date']}"
                            blocks = [
                                {"type":"section","text":{"type":"mrkdwn","text":msg}},
                            ]
                            send_slack(msg, blocks=blocks)

            page += 1

    print(f"Done. Status changes alerted: {total_new_status}")

if __name__ == "__main__":
    main()
