import re

from app.models.lead import LeadInput

HIGH_URGENCY_PATTERNS = (
    r"\basap\b",
    r"\burgent(?:ly)?\b",
    r"\bimmediately\b",
    r"\btoday\b",
    r"\btomorrow\b",
    r"\bwithin (?:24|48) hours?\b",
)

MEDIUM_URGENCY_PATTERNS = (
    r"\bthis week\b",
    r"\bwithin (?:a|one) week\b",
    r"\bnext few days\b",
    r"\bsoon\b",
    r"\bready to (?:buy|purchase)\b",
)


def classify_urgency(lead: LeadInput) -> str:
    """Apply an auditable CRM urgency policy to customer-provided timing signals."""
    text = " ".join(
        value
        for value in (lead.vehicle_interest, lead.notes)
        if isinstance(value, str) and value.strip()
    ).casefold()
    if any(re.search(pattern, text) for pattern in HIGH_URGENCY_PATTERNS):
        return "high"
    if any(re.search(pattern, text) for pattern in MEDIUM_URGENCY_PATTERNS):
        return "medium"
    return "low"
