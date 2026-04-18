import re

_PATTERNS = [
    # "Team: Risk Management" or "Department: Customer Support"
    r"(?:Team|Department|Group|Division)\s*:\s*(.+?)(?:\n|$)",
    # "join the Detection Engineering team"
    r"join the\s+(.+?)\s+team",
    # "part of our Ads & Shopping team"
    r"part of (?:our|the)\s+(.+?)\s+team",
    # "within the Platform Engineering organization"
    r"within the\s+(.+?)\s+(?:organization|org|group|division)",
]

def detect_team(jd_text: str | None) -> str | None:
    if not jd_text:
        return None
    for pattern in _PATTERNS:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None
