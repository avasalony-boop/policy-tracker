import os
from datetime import date, timedelta
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from alerts import send_slack

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///policy_radar.db")

def main(window_days: int = 7):
    eng = create_engine(DATABASE_URL, future=True)
    today = date.today()
    start = (today - timedelta(days=window_days)).isoformat()
    end = (today + timedelta(days=0)).isoformat()

    sql = text("""
        SELECT bill_uid, jurisdiction, bill_number, title, status_general, effective_date, last_action_date
        FROM bills
        WHERE effective_date IS NOT NULL
          AND effective_date BETWEEN :start AND :end
        ORDER BY effective_date DESC
        LIMIT 100
    """)

    rows = []
    with eng.begin() as conn:
        rows = list(conn.execute(sql, {"start": start, "end": end}))

    if not rows:
        send_slack(f"ℹ️ No policies became effective in the last {window_days} days.")
        print("No effective policies in the window.")
        return

    # Send one summary block
    lines = [f"*Policies now in effect (last {window_days} days)*"]
    for r in rows:
        j, num, title, eff = r.jurisdiction, r.bill_number, r.title, r.effective_date
        lines.append(f"• *{j} {num}* — {title}  _(effective {eff})_")
    msg = "\n".join(lines)
    send_slack(msg, blocks=[{"type":"section","text":{"type":"mrkdwn","text":msg}}])
    print(f"Sent {len(rows)} items.")

if __name__ == "__main__":
    main()
