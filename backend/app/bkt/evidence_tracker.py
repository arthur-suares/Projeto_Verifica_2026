"""
EVIDENCE skill tracker.

Tracks user's ability to evaluate supporting evidence.
"""

from app.bkt.base import SkillTracker
from app.bkt.engine import BKTEngine
from app.bkt.parameters import get_bkt_parameters


class EvidenceTracker(SkillTracker):
    """Tracker for EVIDENCE skill: evaluating supporting evidence."""

    PARAMETERS = get_bkt_parameters("EVIDENCE")

    def __init__(self):
        """Initialize the EVIDENCE tracker with appropriate parameters."""
        self.engine = BKTEngine(**self.PARAMETERS)

    def update(self, mastery: float, correct: bool) -> float:
        """
        Update mastery probability for EVIDENCE skill.

        Args:
            mastery: Current mastery probability (0 to 1)
            correct: Whether the user correctly evaluated the evidence

        Returns:
            Updated mastery probability (0 to 1)
        """
        return self.engine.update(mastery, correct)

    def get_parameters(self) -> dict:
        """Return EVIDENCE-specific BKT parameters."""
        return self.engine.get_parameters()
