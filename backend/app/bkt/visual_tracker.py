"""
VISUAL skill tracker.

Tracks user's ability to evaluate if an image really supports the presented claim.
"""

from app.bkt.base import SkillTracker
from app.bkt.engine import BKTEngine
from app.bkt.parameters import get_bkt_parameters


class VisualTracker(SkillTracker):
    """Tracker for VISUAL skill: evaluating image-claim relationships."""

    PARAMETERS = get_bkt_parameters("VISUAL")

    def __init__(self):
        """Initialize the VISUAL tracker with appropriate parameters."""
        self.engine = BKTEngine(**self.PARAMETERS)

    def update(self, mastery: float, correct: bool) -> float:
        """
        Update mastery probability for VISUAL skill.

        Args:
            mastery: Current mastery probability (0 to 1)
            correct: Whether the user correctly evaluated the image relationship

        Returns:
            Updated mastery probability (0 to 1)
        """
        return self.engine.update(mastery, correct)

    def get_parameters(self) -> dict:
        """Return VISUAL-specific BKT parameters."""
        return self.engine.get_parameters()
