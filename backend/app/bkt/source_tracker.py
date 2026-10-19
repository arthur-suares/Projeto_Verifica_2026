"""
SOURCE skill tracker.

Tracks user's ability to analyze information source/origin.
"""

from app.bkt.base import SkillTracker
from app.bkt.engine import BKTEngine
from app.bkt.parameters import get_bkt_parameters


class SourceTracker(SkillTracker):
    """Tracker for SOURCE skill: analyzing information source/origin."""

    PARAMETERS = get_bkt_parameters("SOURCE")

    def __init__(self):
        """Initialize the SOURCE tracker with appropriate parameters."""
        self.engine = BKTEngine(**self.PARAMETERS)

    def update(self, mastery: float, correct: bool) -> float:
        """
        Update mastery probability for SOURCE skill.

        Args:
            mastery: Current mastery probability (0 to 1)
            correct: Whether the user answered correctly about the source

        Returns:
            Updated mastery probability (0 to 1)
        """
        return self.engine.update(mastery, correct)

    def get_parameters(self) -> dict:
        """Return SOURCE-specific BKT parameters."""
        return self.engine.get_parameters()
