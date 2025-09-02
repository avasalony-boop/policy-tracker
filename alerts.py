\
import os, json, requests
from dotenv import load_dotenv

load_dotenv()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_slack(message: str, blocks=None):
    if not SLACK_WEBHOOK_URL:
        print("⚠️ No SLACK_WEBHOOK_URL set; skipping Slack")
        return
    payload = {"text": message}
    if blocks:
        payload["blocks"] = blocks
    resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
    try:
        resp.raise_for_status()
    except Exception as e:
        print("Slack send failed:", e)
