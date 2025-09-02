# Policy Radar Starter (Open States + Slack)

This is a minimal, no-license-cost pipeline that:
- Fetches updates from Open States API v3 on a schedule
- Normalizes bill records into a single schema (Postgres or SQLite)
- Detects lifecycle changes (introduced → committee → floor → passed/enacted → veto/failed)
- Tags bills for EliseAI-relevant topics (AI, Privacy, Housing, Healthcare)
- Sends alerts to Slack when meaningful changes occur

bash

git clone https://github.com/avasalony/policy-radar.git
cd policy-radar

bash

.env

#Open States (https://v3.openstates.org/) 
be79973d-628b-4f4a-b771-ce40dc6791c0

#Slack incoming webhook for alerts Slack_WEBHOOK_URL=https://hooks.slack.com/services/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

#DB: DATABASE_URL=sqlite:///policy_radar.db

# Defaults for the committee
DEFAULT_SINCE_DAYS=2
DEFAULT_QUERY="artificial intelligence" OR "comprehensive privacy" OR "health data" OR "sensitive data" OR "biometric" OR "data broker" OR "telehealth" OR "tenant screening" OR "tenant screening" OR "rental application" OR "eviction record" OR "fair housing" OR "telemarketing"
DEFAULT_STATES= 
DEFAULT_COMMITTEES=Housing, Healthcare,Health, Judiciary, Commerce, Urban Affairs
DRY_RUN=0

python db.py migrate
