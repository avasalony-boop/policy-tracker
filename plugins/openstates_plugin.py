from typing import Iterable, Dict, Any
from normalize import normalize_openstates_bill

class OpenStatesAdapter:
    name = "openstates-adapter"

    def wrap(self, bill_json) -> Dict[str, Any]:
        pack = normalize_openstates_bill(bill_json)
        b = pack['bill']
        return {
            "source": "openstates",
            "jurisdiction": b.get("jurisdiction"),
            "title": b.get("title"),
            "summary": b.get("summary"),
            "url": None,  # could construct from jurisdiction/bill number if desired
            "status": b.get("status_general"),
            "effective_date": b.get("effective_date"),
            "updated_at": b.get("updated_at")[:10] if b.get("updated_at") else None,
            "topic_labels": "",
            "bill": b,
            "actions": pack.get("actions", []),
        }
