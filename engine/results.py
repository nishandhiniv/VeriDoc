from dataclasses import asdict, dataclass

# Results that need a human. Anything else ("match", "pass") is clean.
ISSUE_RESULTS = {"mismatch", "missing", "not_entered", "unreadable", "fail", "error", "review"}


@dataclass
class Check:
    """One row of the validation report: Validation · Result · Details (FR-R02/R03)."""

    section: str          # "marks" | "marksheet" | "photo" | "system"
    name: str             # e.g. "Mathematics", "Resolution"
    result: str           # match | mismatch | missing | not_entered | unreadable | pass | fail | error | review
    detail: str = ""      # human-readable measured value, e.g. "180 × 220 px"
    rule: str = ""        # the rule applied, e.g. "minimum 300 × 400 px"
    entered: str = None
    uploaded: str = None
    confidence: float = None

    @property
    def is_issue(self):
        return self.result in ISSUE_RESULTS

    def to_dict(self):
        data = asdict(self)
        data["is_issue"] = self.is_issue
        return data
