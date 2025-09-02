\
import re
from typing import Dict

AI_TERMS = [
    r"artificial intelligence", r"\balgorithmic\b", r"automated decision",
    r"\bdeepfake\b", r"synthetic media", r"\bgenerative\b", r"machine learning"
]

PRIVACY_TERMS = [
    r"consumer data privacy", r"\bbiometric\b", r"data broker",
    r"children'?s privacy", r"health data", r"data minimization", r"sensitive data"
]

HOUSING_TERMS = [
    r"tenant screening", r"rental application", r"\beviction\b", r"fair housing",
    r"rent cap", r"security deposit", r"habitability", r"source of income"
]

HEALTH_TERMS = [
    r"\btelehealth\b", r"\btelemedicine\b", r"prior authorization",
    r"utilization management", r"clinical decision support", r"health data", r"HIPAA"
]

def label_record(text: str) -> Dict[str, bool]:
    tx = (text or "").lower()
    def any_match(patterns):
        return any(re.search(p, tx) for p in patterns)
    return {
        "ai": any_match(AI_TERMS),
        "privacy": any_match(PRIVACY_TERMS),
        "housing": any_match(HOUSING_TERMS),
        "healthcare": any_match(HEALTH_TERMS),
    }
