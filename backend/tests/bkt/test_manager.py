import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from app.bkt.manager import BKTManager, InvalidSkillError
from app.bkt.source_tracker import SourceTracker
from app.bkt.visual_tracker import VisualTracker
from app.bkt.context_tracker import ContextTracker
from app.bkt.evidence_tracker import EvidenceTracker


EXPECTED_TRACKERS = {
    "SOURCE": SourceTracker,
    "VISUAL": VisualTracker,
    "CONTEXT": ContextTracker,
    "EVIDENCE": EvidenceTracker,
}


def test_bkt_manager_registers_the_four_trackers():
    trackers = BKTManager.get_all_trackers()

    assert set(trackers) == set(EXPECTED_TRACKERS)
    assert len(BKTManager.VALID_SKILLS) == 4


@pytest.mark.parametrize("skill, tracker_class", EXPECTED_TRACKERS.items())
def test_bkt_manager_selects_correct_tracker(skill, tracker_class):
    assert isinstance(BKTManager.get_tracker(skill), tracker_class)


@pytest.mark.parametrize("skill, tracker_class", EXPECTED_TRACKERS.items())
@pytest.mark.parametrize("correct", [True, False])
def test_bkt_manager_update_delegates_to_tracker(skill, tracker_class, correct):
    expected = tracker_class().update(0.4, correct)

    assert BKTManager.update(skill, 0.4, correct) == pytest.approx(expected)


def test_bkt_manager_updates_mastery_for_each_skill():
    mastery = 0.30

    for skill_code in BKTManager.VALID_SKILLS:
        mastery = BKTManager.update(skill_code, mastery, correct=True)
        assert 0.0 <= mastery <= 1.0

    assert mastery > 0.30


def test_bkt_manager_update_skill_alias_matches_update():
    assert BKTManager.update_skill("SOURCE", 0.5, True) == BKTManager.update(
        "SOURCE", 0.5, True
    )


@pytest.mark.parametrize("skill", ["INVALID_SKILL", "source", "", None])
def test_bkt_manager_rejects_invalid_skill(skill):
    with pytest.raises(InvalidSkillError) as exc_info:
        BKTManager.update(skill, 0.5, correct=True)

    assert exc_info.value.skill_code == skill
    assert "Valid skills are" in str(exc_info.value)


def test_invalid_skill_error_is_a_value_error():
    # Routes already translate ValueError into a controlled HTTP error.
    with pytest.raises(ValueError):
        BKTManager.update("INVALID_SKILL", 0.5, correct=True)


def test_bkt_manager_rejects_invalid_mastery():
    with pytest.raises(ValueError):
        BKTManager.update("SOURCE", 1.5, correct=True)


def test_bkt_parameters_are_centralized_and_marked_provisional():
    for skill_code in BKTManager.VALID_SKILLS:
        parameters = BKTManager.get_tracker(skill_code).get_parameters()
        assert parameters == {
            "p_init": 0.30,
            "p_guess": 0.20,
            "p_slip": 0.05,
            "p_transition": 0.10,
        }
        assert BKTManager.get_initial_mastery(skill_code) == parameters["p_init"]
