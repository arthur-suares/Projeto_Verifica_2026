"""
Answer Repository - Database access layer for answer-related entities.

Handles Answer storage and retrieval.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import Answer, GameRound, Question, Skill


class AnswerRepository:
    """Repository for answer-related database operations."""

    @staticmethod
    def create_answer(
        db: Session,
        user_id: str,
        game_round_id: str,
        question_id: str,
        selected_option: str,
        correct: bool,
        confidence: int | None = None,
        response_time: int | None = None,
        commit: bool = True,
    ) -> Answer:
        """
        Create a new answer record.

        Args:
            db: Database session
            user_id: ID of the user
            game_round_id: ID of the game round
            question_id: ID of the question
            selected_option: The option selected by the user
            correct: Whether the answer was correct
            confidence: User's confidence level (1-5)
            response_time: Time taken to answer in milliseconds
            commit: If False, only flush so the caller controls the transaction

        Returns:
            Created Answer instance
        """
        answer = Answer(
            user_id=user_id,
            game_round_id=game_round_id,
            question_id=question_id,
            selected_option=selected_option,
            correct=correct,
            confidence=confidence,
            response_time=response_time,
        )
        db.add(answer)
        if commit:
            db.commit()
            db.refresh(answer)
        else:
            db.flush()
        return answer

    @staticmethod
    def get_answer_by_id(db: Session, answer_id: str) -> Answer | None:
        """
        Retrieve an answer by ID.

        Args:
            db: Database session
            answer_id: ID of the answer

        Returns:
            Answer instance or None if not found
        """
        return db.query(Answer).filter(Answer.id == answer_id).first()

    @staticmethod
    def get_answers_for_round(db: Session, game_round_id: str) -> list[Answer]:
        """
        Get all answers for a specific game round.

        Args:
            db: Database session
            game_round_id: ID of the game round

        Returns:
            List of Answer instances
        """
        return db.query(Answer).filter(Answer.game_round_id == game_round_id).all()

    @staticmethod
    def get_answers_for_user(
        db: Session,
        user_id: str,
        limit: int = 100,
    ) -> list[Answer]:
        """
        Get recent answers from a user.

        Args:
            db: Database session
            user_id: ID of the user
            limit: Maximum number of answers to retrieve

        Returns:
            List of Answer instances ordered by creation time (newest first)
        """
        return (
            db.query(Answer)
            .filter(Answer.user_id == user_id)
            .order_by(Answer.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_answered_question_ids_for_user(db: Session, user_id: str) -> set[str]:
        """Return question IDs answered by a user across all games."""
        question_ids = (
            db.query(Answer.question_id)
            .filter(Answer.user_id == user_id)
            .distinct()
            .all()
        )
        return {question_id for (question_id,) in question_ids}

    @staticmethod
    def get_answer_counts_by_question_for_user(db: Session, user_id: str) -> dict[str, int]:
        """Return how many times a user answered each question, across all games."""
        rows = (
            db.query(Answer.question_id, func.count(Answer.id))
            .filter(Answer.user_id == user_id)
            .group_by(Answer.question_id)
            .all()
        )
        return {question_id: count for question_id, count in rows}

    @staticmethod
    def get_answered_question_ids_for_game(db: Session, game_id: str) -> set[str]:
        """Return question IDs answered in one game, including rounds without question_id."""
        question_ids = (
            db.query(Answer.question_id)
            .join(GameRound, Answer.game_round_id == GameRound.id)
            .filter(GameRound.game_id == game_id)
            .distinct()
            .all()
        )
        return {question_id for (question_id,) in question_ids}

    @staticmethod
    def get_answers_for_question(
        db: Session,
        question_id: str,
    ) -> list[Answer]:
        """
        Get all answers for a specific question.

        Args:
            db: Database session
            question_id: ID of the question

        Returns:
            List of Answer instances
        """
        return db.query(Answer).filter(Answer.question_id == question_id).all()

    @staticmethod
    def get_user_answers_for_skill(
        db: Session,
        user_id: str,
        skill_id: str,
    ) -> list[Answer]:
        """
        Get all answers from a user for questions of a specific skill.

        Args:
            db: Database session
            user_id: ID of the user
            skill_id: ID of the skill

        Returns:
            List of Answer instances
        """
        return (
            db.query(Answer)
            .join(Answer.question)
            .filter(
                Answer.user_id == user_id,
            )
            .all()
        )

    @staticmethod
    def get_user_skill_history(db: Session, user_id: str) -> list[tuple]:
        """Return ordered, minimal observations joined to their skill codes."""
        return (
            db.query(Answer.id, Answer.correct, Answer.created_at, Skill.code)
            .join(Question, Answer.question_id == Question.id)
            .join(Skill, Question.skill_id == Skill.id)
            .filter(Answer.user_id == user_id)
            .order_by(Answer.created_at.asc(), Answer.id.asc())
            .all()
        )
