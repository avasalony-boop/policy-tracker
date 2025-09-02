\
import os, hashlib
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///policy_radar.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS bills (
  bill_uid TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  jurisdiction TEXT,
  session TEXT,
  bill_number TEXT,
  title TEXT,
  summary TEXT,
  subjects TEXT,
  sponsors_primary TEXT,
  committees TEXT,
  status_general TEXT,
  status_specific TEXT,
  introduced_date TEXT,
  effective_date TEXT,
  last_action_date TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS actions (
  id TEXT PRIMARY KEY,
  bill_uid TEXT NOT NULL,
  action_date TEXT,
  organization TEXT,
  classification TEXT,
  action_text TEXT,
  FOREIGN KEY (bill_uid) REFERENCES bills(bill_uid)
);

CREATE TABLE IF NOT EXISTS labels (
  bill_uid TEXT PRIMARY KEY,
  topic_labels TEXT,
  client_vertical TEXT,
  impact_score INTEGER DEFAULT 0,
  FOREIGN KEY (bill_uid) REFERENCES bills(bill_uid)
);

CREATE INDEX IF NOT EXISTS idx_actions_bill_uid ON actions (bill_uid);
CREATE INDEX IF NOT EXISTS idx_bills_status ON bills (status_general, jurisdiction);
"""

def get_engine() -> Engine:
    return create_engine(DATABASE_URL, future=True)

def migrate():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(SCHEMA_SQL))
    print("✅ DB migrated")

def upsert_bill(conn, bill):
    # bill is a dict with our normalized schema fields
    fields = [
        "bill_uid","source","jurisdiction","session","bill_number","title","summary",
        "subjects","sponsors_primary","committees","status_general","status_specific",
        "introduced_date","effective_date","last_action_date","updated_at"
    ]
    placeholders = ", ".join([f":{f}" for f in fields])
    updates = ", ".join([f"{f}=:{f}" for f in fields[1:]])
    sql = text(f"""
        INSERT INTO bills ({", ".join(fields)})
        VALUES ({placeholders})
        ON CONFLICT(bill_uid) DO UPDATE SET {updates}
    """)
    conn.execute(sql, bill)

def upsert_action(conn, action):
    # id is a content hash for idempotency
    fields = ["id","bill_uid","action_date","organization","classification","action_text"]
    sql = text(f"""
        INSERT INTO actions ({", ".join(fields)})
        VALUES (:{fields[0]}, :{fields[1]}, :{fields[2]}, :{fields[3]}, :{fields[4]}, :{fields[5]})
        ON CONFLICT(id) DO NOTHING
    """)
    conn.execute(sql, action)

def set_labels(conn, labels):
    fields = ["bill_uid","topic_labels","client_vertical","impact_score"]
    updates = ", ".join([f"{f}=:{f}" for f in fields[1:]])
    sql = text(f"""
        INSERT INTO labels ({", ".join(fields)})
        VALUES (:{fields[0]}, :{fields[1]}, :{fields[2]}, :{fields[3]})
        ON CONFLICT(bill_uid) DO UPDATE SET {updates}
    """)
    conn.execute(sql, labels)

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "migrate":
        migrate()
    else:
        print("Usage: python db.py migrate")
