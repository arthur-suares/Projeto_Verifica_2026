"""
Answer Service - Business logic for handling user answers.

Processes answers, updates skill mastery using BKT, and returns feedback.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.repositories.answer_repository import AnswerRepository
from app.repositories.question_repository import QuestionRepository
from app.repositories.game_repository import GameRepository
from app.repositories.skill_repository import SkillRepository
from app.bkt.manager import BKTManager
from app.bkt.engine import BKTEngine
from app.models import GameStatusEnum
from datetime import datetime


class AnswerError(ValueError):
    """Base error for answers that cannot be processed."""


class AnswerNotFoundError(AnswerError):
    """Game, round or question does not exist."""


class AnswerForbiddenError(AnswerError):
    """User is trying to answer a round from another user's game."""


class AnswerConflictError(AnswerError):
    """Round was already answered or the game is finished."""


class AnswerService:
    """Service for answer-related business logic."""

    @staticmethod
    def process_answer(
        db: Session,
        user_id: str,
        game_id: str,
        game_round_id: str,
        question_id: str,
        selected_option: str,
        confidence: int | None = None,
        response_time: int | None = None,
    ) -> dict:
        """
        Process a user's answer to a question.

        Flow: validate -> determine correct -> save Answer -> identify skill ->
        retrieve UserSkillState -> BKTManager -> save new mastery -> return result.

        Args:
            db: Database session
            user_id: ID of the user answering
            game_id: ID of the game the round belongs to
            game_round_id: ID of the game round
            question_id: ID of the question
            selected_option: The option selected (e.g., "A", "B", "C")
            confidence: User's confidence (1-5)
            response_time: Time taken in milliseconds

        Returns:
            Dictionary with feedback including correctness, skill, and new mastery

        Raises:
            AnswerNotFoundError: If game, round or question does not exist
            AnswerForbiddenError: If the game belongs to another user
            AnswerConflictError: If the round was already answered or the game is finished
            ValueError: If the answer itself is invalid
        """
        # 1. Validate
        if confidence is not None and not (1 <= confidence <= 5):
            raise ValueError("confidence must be between 1 and 5")

        if response_time is not None and response_time < 0:
            raise ValueError("response_time must be non-negative")

        game = GameRepository.get_game_by_id(db, game_id)
        if not game:
            raise AnswerNotFoundError(f"Game {game_id} not found")

        if game.user_id != user_id:
            raise AnswerForbiddenError("User does not own this game")

        if game.status == GameStatusEnum.FINISHED:
            raise AnswerConflictError(f"Game {game_id} is already finished")

        game_round = GameRepository.get_game_round_by_id(db, game_round_id)
        if not game_round or game_round.game_id != game.id:
            raise AnswerNotFoundError(
                f"Round {game_round_id} not found in game {game_id}"
            )

        rounds = GameRepository.get_game_rounds(db, game.id)
        if not rounds or rounds[-1].id != game_round.id:
            raise AnswerConflictError("Only the current game round can be answered")

        question = QuestionRepository.get_question_by_id(db, question_id)
        if (
            not question
            or question.news_id != game_round.news_id
            or question.id != game_round.question_id
        ):
            raise AnswerNotFoundError(
                f"Question {question_id} not found in round {game_round_id}"
            )

        if selected_option not in question.options:
            raise ValueError(
                f"Invalid option {selected_option}. "
                f"Valid options are: {', '.join(sorted(question.options))}"
            )
        if AnswerRepository.get_answers_for_round(db, game_round.id):
            raise AnswerConflictError(f"Round {game_round_id} was already answered")
        is_correct = selected_option == question.correct_option

        # 3. Identify skill and current state
        skill = question.skill
        if not skill:
            raise ValueError(f"Question {question_id} has no skill associated")

        try:
            user_skill_state = SkillRepository.get_or_create_user_skill_state(
                db,
                user_id,
                skill.id,
                initial_mastery=BKTManager.get_initial_mastery(skill.code),
                commit=False,
            )
            current_mastery = user_skill_state.mastery_probability
            new_mastery = BKTManager.update(skill.code, current_mastery, is_correct)

            answer = AnswerRepository.create_answer(
                db,
                user_id,
                game_round.id,
                question.id,
                selected_option,
                is_correct,
                confidence,
                response_time,
                commit=False,
            )
            SkillRepository.update_user_skill_mastery(
                db,
                user_id,
                skill.id,
                new_mastery,
                commit=False,
            )
            game_round.finished_at = datetime.utcnow()
            if game_round.round_number >= 10:
                GameRepository.finish_game(db, game.id, commit=False)
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise AnswerConflictError(
                f"Round {game_round_id} was already answered"
            ) from error
        except Exception:
            db.rollback()
            raise
        db.refresh(answer)

        # 6. Return result
        return {
            "answer_id": answer.id,
            "correct": is_correct,
            "skill_code": skill.code,
            "skill_name": skill.name,
            "old_mastery": current_mastery,
            "new_mastery": new_mastery,
            "explanation": question.explanation,
            "correct_option": question.correct_option,
        }

    @staticmethod
    def get_user_skill_profile(db: Session, user_id: str) -> dict:
        """
        Get a user's complete skill profile.

        Returns mastery probabilities for all four skills.

        Args:
            db: Database session
            user_id: ID of the user

        Returns:
            Dictionary with skills and their mastery probabilities
        """
        try:
            skills = SkillRepository.get_all_skills(db)
            for skill in skills:
                SkillRepository.get_or_create_user_skill_state(
                    db,
                    user_id,
                    skill.id,
                    initial_mastery=BKTManager.get_initial_mastery(skill.code),
                    commit=False,
                )
            db.commit()
        except Exception:
            db.rollback()
            raise

        user_skill_states = SkillRepository.get_user_skill_states(db, user_id)

        history_by_skill: dict[str, list[tuple]] = {
            skill_code: [] for skill_code in BKTManager.VALID_SKILLS
        }
        for answer_id, correct, created_at, skill_code in AnswerRepository.get_user_skill_history(
            db, user_id
        ):
            if skill_code in history_by_skill:
                history_by_skill[skill_code].append((answer_id, correct, created_at))

        skills = []
        for state in user_skill_states:
            skill_code = state.skill.code
            skill_history = history_by_skill.get(skill_code, [])
            parameters = BKTManager.get_tracker(skill_code).get_parameters()
            engine = BKTEngine(**parameters)
            replayed_mastery = parameters["p_init"]
            trajectory = []
            for attempt_number, (_, correct, created_at) in enumerate(skill_history, start=1):
                replayed_mastery = engine.update(replayed_mastery, bool(correct))
                if attempt_number <= 5 or attempt_number == len(skill_history):
                    trajectory.append({
                        "attempt": attempt_number,
                        "created_at": created_at.isoformat(),
                        "mastery_probability": replayed_mastery,
                    })

            skills.append({
                "skill_id": state.skill_id,
                "skill_code": skill_code,
                "skill_name": state.skill.name,
                "description": state.skill.description,
                "mastery_probability": state.mastery_probability,
                "attempts": len(skill_history),
                "correct_count": sum(bool(row[1]) for row in skill_history),
                "incorrect_count": sum(not bool(row[1]) for row in skill_history),
                "accuracy": (
                    sum(bool(row[1]) for row in skill_history) / len(skill_history)
                    if skill_history else None
                ),
                "insufficient_evidence": len(skill_history) < 3,
                "bkt_parameters": parameters,
                "trajectory": trajectory,
                "updated_at": state.updated_at.isoformat(),
            })

        return {
            "user_id": user_id,
            "skills": sorted(skills, key=lambda x: x["skill_code"]),
            "updated_at": max(
                (s["updated_at"] for s in skills),
                default=None,
            ),
            "bkt_version": "classic-bkt-observation-transition-v1",
            "parameter_status": "provisional_defaults_not_fitted_to_real_users",
        }
