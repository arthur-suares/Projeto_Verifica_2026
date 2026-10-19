"""
BKT Manager - Maps skills to their trackers.

This module serves as a registry and factory for skill trackers.
It provides a unified interface for updating skill mastery across all four skills.
"""

from app.bkt.base import SkillTracker
from app.bkt.source_tracker import SourceTracker
from app.bkt.evidence_tracker import EvidenceTracker
from app.bkt.context_tracker import ContextTracker
from app.bkt.visual_tracker import VisualTracker


class InvalidSkillError(ValueError):
    """Raised when a skill code has no registered tracker."""

    def __init__(self, skill_code: str, valid_skills: list[str]):
        self.skill_code = skill_code
        self.valid_skills = valid_skills
        super().__init__(
            f"Invalid skill code: {skill_code}. "
            f"Valid skills are: {', '.join(valid_skills)}"
        )


class BKTManager:
    """
    Manager for BKT trackers.

    Maps each skill code (SOURCE, EVIDENCE, CONTEXT, VISUAL) to its corresponding tracker.
    Provides a unified interface for updating mastery probabilities.
    """

    # Skill codes (must match Skill.code values in database)
    SKILL_SOURCE = "SOURCE"
    SKILL_EVIDENCE = "EVIDENCE"
    SKILL_CONTEXT = "CONTEXT"
    SKILL_VISUAL = "VISUAL"

    # Registry mapping skill code to tracker
    _TRACKERS = {
        SKILL_SOURCE: SourceTracker(),
        SKILL_EVIDENCE: EvidenceTracker(),
        SKILL_CONTEXT: ContextTracker(),
        SKILL_VISUAL: VisualTracker(),
    }

    # List of valid skill codes
    VALID_SKILLS = list(_TRACKERS.keys())

    @classmethod
    def update(cls, skill: str, mastery: float, correct: bool) -> float:
        """
        Update mastery probability for a specific skill.

        Single entry point for the backend: callers only pass the skill code,
        the manager selects the matching tracker.

        Args:
            skill: Code of the skill (SOURCE, EVIDENCE, CONTEXT, or VISUAL)
            mastery: Current mastery probability (0 to 1)
            correct: Whether the user answered correctly

        Returns:
            Updated mastery probability (0 to 1)

        Raises:
            InvalidSkillError: If skill is not registered
            ValueError: If mastery is out of range
        """
        return cls.get_tracker(skill).update(mastery, correct)

    @classmethod
    def update_skill(cls, skill_code: str, mastery: float, correct: bool) -> float:
        """Alias of update(), kept for backwards compatibility."""
        return cls.update(skill_code, mastery, correct)

    @classmethod
    def get_tracker(cls, skill_code: str) -> SkillTracker:
        """
        Get the tracker for a specific skill.

        Args:
            skill_code: Code of the skill

        Returns:
            SkillTracker instance

        Raises:
            InvalidSkillError: If skill_code is invalid
        """
        if skill_code not in cls._TRACKERS:
            raise InvalidSkillError(skill_code, cls.VALID_SKILLS)
        return cls._TRACKERS[skill_code]

    @classmethod
    def get_all_trackers(cls) -> dict[str, SkillTracker]:
        """
        Get all registered trackers.

        Returns:
            Dictionary mapping skill codes to SkillTracker instances
        """
        return cls._TRACKERS.copy()

    @classmethod
    def validate_skill_code(cls, skill_code: str) -> bool:
        """
        Check if a skill code is valid.

        Args:
            skill_code: Code to validate

        Returns:
            True if valid, False otherwise
        """
        return skill_code in cls._TRACKERS

    @classmethod
    def get_initial_mastery(cls, skill_code: str) -> float:
        """Return the configured P(L0) for a tracked skill."""
        return cls.get_tracker(skill_code).get_parameters()["p_init"]
