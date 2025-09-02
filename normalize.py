\
from datetime import datetime
from typing import Dict, Any, List

CLASSIFY_MAP = {
    "introduced": "INTRODUCED",
    "referral": "IN_COMMITTEE",
    "committee-referral": "IN_COMMITTEE",
    "committee-passage": "REPORTED",
    "committee-passage-favorable": "REPORTED",
    "reading-1": "ON_FLOOR",
    "reading-2": "ON_FLOOR",
    "reading-3": "ON_FLOOR",
    "floor-passage": "ON_FLOOR",
    "passage": "PASSED_CHAMBER",
    "executive-signature": "ENACTED",
    "enacted": "ENACTED",
    "chaptered": "ENACTED",
    "veto": "VETOED",
}

def derive_status_general(actions: List[Dict[str, Any]]) -> str:
    # Coarse heuristic: last-most-significant classification wins
    order = [
        "VETOED", "ENACTED", "PASSED_LEGISLATURE",
        "ON_FLOOR", "REPORTED", "IN_COMMITTEE", "INTRODUCED"
    ]
    seen = set()
    for a in sorted(actions, key=lambda x: x.get("action_date","")):
        for c in a.get("classification", []):
            mapped = CLASSIFY_MAP.get(c)
            if mapped:
                if mapped == "PASSED_CHAMBER":
                    seen.add(mapped)
                    if "PASSED_CHAMBER" in seen and len([1 for s in actions if "passage" in s.get("classification",[])]) >= 2:
                        return "PASSED_LEGISLATURE"
                else:
                    last = mapped
    return last if (last := locals().get("last")) else "INTRODUCED"

def normalize_openstates_bill(b: Dict[str, Any]) -> Dict[str, Any]:
    bill_uid = f"openstates:{b['id']}"
    jurisdiction = b.get("jurisdiction", {}).get("name")
    session = b.get("from_session")
    bill_number = b.get("identifier")
    title = b.get("title")
    summary = b.get("summary")
    subjects = ",".join(b.get("subject", []) or [])
    sponsors = b.get("sponsorships", [])
    sponsor_primary = ""
    for s in sponsors:
        if s.get("primary"):
            sponsor_primary = s.get("name") or s.get("person", {}).get("name") or ""
            break
    committees = []
    for a in b.get("actions", []):
        org = a.get("organization", {}).get("name") or ""
        if org and org not in committees:
            committees.append(org)
    actions_norm = []
    for a in b.get("actions", []):
        actions_norm.append({
            "action_date": a.get("date"),
            "organization": a.get("organization", {}).get("name"),
            "classification": a.get("classification", []),
            "action_text": a.get("description")
        })
    status_general = derive_status_general(actions_norm) if actions_norm else "INTRODUCED"
    introduced_date = None
    if b.get("first_action_date"):
        introduced_date = b.get("first_action_date")
    last_action_date = b.get("latest_action_date") or (actions_norm[-1]["action_date"] if actions_norm else None)
    return {
        "bill": {
            "bill_uid": bill_uid,
            "source": "openstates",
            "jurisdiction": jurisdiction,
            "session": session,
            "bill_number": bill_number,
            "title": title,
            "summary": summary,
            "subjects": subjects,
            "sponsors_primary": sponsor_primary,
            "committees": ",".join(committees[:10]),
            "status_general": status_general,
            "status_specific": "",
            "introduced_date": introduced_date,
            "effective_date": None,
            "last_action_date": last_action_date,
            "updated_at": datetime.utcnow().isoformat()
        },
        "actions": actions_norm
    }
