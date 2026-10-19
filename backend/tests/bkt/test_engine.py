"""
Unit tests for BKTEngine.

Tests the core mathematical implementation of Bayesian Knowledge Tracing.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parents[2]))

import pytest
from app.bkt.engine import BKTEngine


class TestBKTEngine:
    """Tests for BKTEngine core functionality."""

    def test_engine_initialization(self):
        """Test that engine initializes with valid parameters."""
        engine = BKTEngine(
            p_guess=0.20,
            p_slip=0.05,
            p_transition=0.10,
            p_init=0.30,
        )
        assert engine.p_guess == 0.20
        assert engine.p_slip == 0.05
        assert engine.p_transition == 0.10
        assert engine.p_init == 0.30

    def test_engine_default_parameters(self):
        """Test that engine uses sensible defaults."""
        engine = BKTEngine()
        assert engine.p_guess == BKTEngine.DEFAULT_P_GUESS
        assert engine.p_slip == BKTEngine.DEFAULT_P_SLIP
        assert engine.p_transition == BKTEngine.DEFAULT_P_TRANSITION
        assert engine.p_init == BKTEngine.DEFAULT_P_INIT

    def test_engine_parameter_validation_p_guess(self):
        """Test that p_guess must be between 0 and 1."""
        with pytest.raises(ValueError):
            BKTEngine(p_guess=1.5)
        
        with pytest.raises(ValueError):
            BKTEngine(p_guess=-0.1)

    def test_engine_parameter_validation_p_slip(self):
        """Test that p_slip must be between 0 and 1."""
        with pytest.raises(ValueError):
            BKTEngine(p_slip=1.5)
        
        with pytest.raises(ValueError):
            BKTEngine(p_slip=-0.1)

    def test_engine_parameter_validation_p_transition(self):
        """Test that p_transition must be between 0 and 1."""
        with pytest.raises(ValueError):
            BKTEngine(p_transition=1.5)
        
        with pytest.raises(ValueError):
            BKTEngine(p_transition=-0.1)

    def test_engine_parameter_validation_p_init(self):
        """Test that p_init must be between 0 and 1."""
        with pytest.raises(ValueError):
            BKTEngine(p_init=1.5)
        
        with pytest.raises(ValueError):
            BKTEngine(p_init=-0.1)

    def test_update_mastery_validation(self):
        """Test that update validates mastery input."""
        engine = BKTEngine()
        
        with pytest.raises(ValueError):
            engine.update(1.5, correct=True)
        
        with pytest.raises(ValueError):
            engine.update(-0.1, correct=True)

    def test_update_accepts_per_call_parameters(self):
        """Test that update uses parameters passed in the call."""
        engine = BKTEngine(p_guess=0.50, p_slip=0.40, p_transition=0.90)

        result = engine.update(
            0.30, correct=True, p_guess=0.20, p_slip=0.05, p_transition=0.10
        )

        assert result == pytest.approx(0.7035294118)

    def test_update_per_call_parameters_do_not_change_engine(self):
        """Test that per-call overrides are not stored in the engine."""
        engine = BKTEngine(p_guess=0.20, p_slip=0.05, p_transition=0.10)

        engine.update(0.30, correct=True, p_guess=0.50)

        assert engine.p_guess == 0.20
        assert engine.update(0.30, correct=True) == pytest.approx(0.7035294118)

    def test_update_partial_override_keeps_other_defaults(self):
        """Test that only overridden parameters change the result."""
        engine = BKTEngine(p_guess=0.20, p_slip=0.05, p_transition=0.10)

        no_learning = engine.update(0.30, correct=True, p_transition=0.0)

        assert no_learning == pytest.approx(0.285 / 0.425)

    @pytest.mark.parametrize("param", ["p_guess", "p_slip", "p_transition"])
    @pytest.mark.parametrize("value", [-0.1, 1.5])
    def test_update_validates_per_call_parameters(self, param, value):
        """Test that per-call parameters must be between 0 and 1."""
        engine = BKTEngine()

        with pytest.raises(ValueError):
            engine.update(0.5, correct=True, **{param: value})

    def test_update_correct_answer_increases_mastery(self):
        """Test that correct answer increases mastery probability."""
        engine = BKTEngine(p_guess=0.20, p_slip=0.05, p_transition=0.10)
        
        initial_mastery = 0.30
        new_mastery = engine.update(initial_mastery, correct=True)
        
        assert new_mastery > initial_mastery
        assert 0 <= new_mastery <= 1

    def test_update_matches_bayesian_observation_then_learning_transition(self):
        engine = BKTEngine(p_guess=0.20, p_slip=0.05, p_transition=0.10)

        assert engine.update(0.30, correct=True) == pytest.approx(0.7035294118)
        assert engine.update(0.30, correct=False) == pytest.approx(0.1234782609)

    def test_update_incorrect_answer_decreases_mastery(self):
        """Test that incorrect answer decreases mastery probability."""
        engine = BKTEngine(p_guess=0.20, p_slip=0.05, p_transition=0.10)
        
        initial_mastery = 0.70
        new_mastery = engine.update(initial_mastery, correct=False)
        
        assert new_mastery < initial_mastery
        assert 0 <= new_mastery <= 1

    def test_update_result_bounded(self):
        """Test that update result is always between 0 and 1."""
        engine = BKTEngine()
        
        # Test with extreme values
        for mastery in [0, 0.1, 0.5, 0.9, 1.0]:
            result_correct = engine.update(mastery, correct=True)
            result_incorrect = engine.update(mastery, correct=False)
            
            assert 0 <= result_correct <= 1
            assert 0 <= result_incorrect <= 1

    def test_update_sequence(self):
        """Test a sequence of correct and incorrect answers."""
        engine = BKTEngine(p_guess=0.20, p_slip=0.05, p_transition=0.10)
        
        mastery = 0.30
        
        # Correct answer
        mastery = engine.update(mastery, correct=True)
        mastery_after_first_correct = mastery
        assert mastery_after_first_correct > 0.30
        
        # Another correct answer
        mastery = engine.update(mastery, correct=True)
        assert mastery > mastery_after_first_correct
        
        # Incorrect answer
        mastery_after_incorrect = engine.update(mastery, correct=False)
        assert mastery_after_incorrect < mastery

    def test_perfect_mastery_stays_high_with_correct(self):
        """Test that high mastery stays high with correct answers."""
        engine = BKTEngine(p_slip=0.05)
        
        mastery = 0.95
        new_mastery = engine.update(mastery, correct=True)
        
        assert 0.90 <= new_mastery <= 1.0
        assert new_mastery >= 0.90  # Should remain high

    def test_low_mastery_stays_low_with_incorrect(self):
        """Test that low mastery stays low with incorrect answers."""
        engine = BKTEngine(p_guess=0.20)
        
        mastery = 0.05
        new_mastery = engine.update(mastery, correct=False)
        
        assert 0 <= new_mastery <= 0.2
        assert new_mastery <= 0.2  # Should remain low

    def test_get_parameters(self):
        """Test that get_parameters returns the correct parameters."""
        params = {
            "p_guess": 0.25,
            "p_slip": 0.08,
            "p_transition": 0.15,
            "p_init": 0.35,
        }
        engine = BKTEngine(**params)
        
        retrieved = engine.get_parameters()
        
        for key in params:
            assert retrieved[key] == params[key]

    def test_convergence_many_correct_answers(self):
        """Test that mastery converges toward high value with many correct answers."""
        engine = BKTEngine(p_slip=0.05, p_transition=0.10)
        
        mastery = 0.30
        
        # Many correct answers
        for _ in range(50):
            mastery = engine.update(mastery, correct=True)
        
        # Should be close to 1.0
        assert mastery > 0.95

    def test_convergence_many_incorrect_answers(self):
        """Test convergence to the nonzero equilibrium when learning remains possible."""
        engine = BKTEngine(p_guess=0.20, p_transition=0.10)
        
        mastery = 0.70
        
        # Many incorrect answers
        for _ in range(50):
            mastery = engine.update(mastery, correct=False)
        
        assert mastery == pytest.approx(0.1066666667)

    def test_moderate_parameter_variations_can_shift_estimate_without_fitting(self):
        """Sensitivity check documents that defaults are hypotheses, not learned values."""
        sequence = [True, False, True, True, False, False, True, False, True, True]
        defaults = {
            "p_init": 0.30,
            "p_guess": 0.20,
            "p_slip": 0.05,
            "p_transition": 0.10,
        }
        scenarios = [
            defaults,
            {**defaults, "p_init": 0.25},
            {**defaults, "p_init": 0.35},
            {**defaults, "p_guess": 0.15},
            {**defaults, "p_guess": 0.25},
            {**defaults, "p_slip": 0.02},
            {**defaults, "p_slip": 0.08},
            {**defaults, "p_transition": 0.05},
            {**defaults, "p_transition": 0.15},
        ]
        estimates = []
        for parameters in scenarios:
            engine = BKTEngine(**parameters)
            mastery = parameters["p_init"]
            for correct in sequence:
                mastery = engine.update(mastery, correct)
            estimates.append(mastery)

        assert max(estimates) - min(estimates) == pytest.approx(0.2142, abs=0.0001)

    def test_zero_mastery_edge_case(self):
        """Test update at exactly zero mastery."""
        engine = BKTEngine()
        
        result_correct = engine.update(0.0, correct=True)
        result_incorrect = engine.update(0.0, correct=False)
        
        assert 0 <= result_correct <= 1
        assert 0 <= result_incorrect <= 1

    def test_one_mastery_edge_case(self):
        """Test update at exactly one mastery."""
        engine = BKTEngine()
        
        result_correct = engine.update(1.0, correct=True)
        result_incorrect = engine.update(1.0, correct=False)
        
        assert 0 <= result_correct <= 1
        assert 0 <= result_incorrect <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
