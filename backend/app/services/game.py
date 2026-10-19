"""
Game Service - Business logic for game operations.

Handles game creation, round initialization, and game flow.
Does not directly handle HTTP concerns or database access (delegates to repositories).
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.bkt.manager import BKTManager

from app.repositories.answer_repository import AnswerRepository
from app.repositories.game_repository import GameRepository
from app.repositories.skill_repository import SkillRepository
from app.repositories.question_repository import NewsRepository
from app.adaptation.question_selector import QuestionSelector
from app.models import Game, GameRound, Question, News
from app.services import news_questions


class GameNotFoundError(ValueError):
    """Raised when a game does not exist."""


class GameForbiddenError(ValueError):
    """Raised when a user accesses another user's game."""


class GameConflictError(ValueError):
    """Raised when the current game state does not allow another round."""


class GameService:
    """Service for game-related business logic."""

    MAX_ROUNDS = 10

    @staticmethod
    def create_game_with_first_round(db: Session, user_id: str) -> dict:
        """
        Create a new game and initialize the first round.

        This ensures that when a game starts, it already has its first question.

        Args:
            db: Database session
            user_id: ID of the user starting the game

        Returns:
            Dictionary with game_id, round details, and first question

        Raises:
            ValueError: If no questions/news available or user not found
        """
        try:
            GameService._ensure_user_skills_initialized(db, user_id)
            game = GameRepository.create_game(db, user_id, commit=False)
            question_news = QuestionSelector.select_next_question(db, user_id, game.id)
            if not question_news:
                raise ValueError("No valid questions available to start game")

            question, news = question_news
            game_round = GameRepository.create_game_round(
                db,
                game.id,
                news.id,
                round_number=1,
                question_id=question.id,
                commit=False,
            )
            db.commit()
            return GameService._round_payload(game.id, game_round, question, news)
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_next_question(db: Session, user_id: str, game_id: str) -> dict | None:
        """
        Get the next question for a game.

        Args:
            db: Database session
            user_id: ID of the user
            game_id: ID of the game

        Returns:
            Dictionary with round and question details, or None if game is finished

        Raises:
            ValueError: If game not found or user doesn't own the game
        """
        game = GameRepository.get_game_by_id(db, game_id)
        if not game:
            raise GameNotFoundError(f"Game {game_id} not found")

        if game.user_id != user_id:
            raise GameForbiddenError("User does not own this game")

        from app.models import GameStatusEnum
        if game.status == GameStatusEnum.FINISHED:
            return None

        game_rounds = GameRepository.get_game_rounds(db, game_id)
        current_round = game_rounds[-1] if game_rounds else None
        if current_round and not AnswerRepository.get_answers_for_round(db, current_round.id):
            raise GameConflictError("The current round must be answered before continuing")
        last_round = current_round.round_number if current_round else 0

        if last_round >= GameService.MAX_ROUNDS:
            GameRepository.finish_game(db, game_id)
            return None

        # Select next question
        question_news = QuestionSelector.select_next_question(db, user_id, game_id)

        if not question_news:
            GameRepository.finish_game(db, game_id)
            return None

        question, news = question_news

        # Create next round
        try:
            game_round = GameRepository.create_game_round(
                db,
                game_id,
                news.id,
                round_number=last_round + 1,
                question_id=question.id,
            )
        except IntegrityError as error:
            db.rollback()
            raise GameConflictError("A round was already created for this position") from error

        return GameService._round_payload(game_id, game_round, question, news)

    @staticmethod
    def _round_payload(game_id: str, game_round: GameRound, question: Question, news: News) -> dict:
        """Build the round payload shared by game creation and next question."""
        return {
            "game_id": game_id,
            "round": {
                "id": game_round.id,
                "number": game_round.round_number,
                "news_id": news.id,
                "question_id": question.id,
            },
            "news": {
                "id": news.id,
                "title": news_questions.round_title(news),
                "content": news.content,
                "image_url": news.image_url,
                "verdict": news.verdict,
                "details": news_questions.news_details(news),
            },
            "question": {
                "id": question.id,
                "text": question.text,
                "difficulty": question.difficulty,
                "options": question.options,
                "skill_id": question.skill_id,
                "skill_code": question.skill.code,
                "hints": news_questions.question_hints(news, question.skill.code),
            },
        }

    @staticmethod
    def _ensure_user_skills_initialized(db: Session, user_id: str) -> None:
        """
        Ensure that user has skill states for all four skills.

        If not, create them with initial mastery probability.

        Args:
            db: Database session
            user_id: ID of the user
        """
        all_skills = SkillRepository.get_all_skills(db)

        for skill in all_skills:
            SkillRepository.get_or_create_user_skill_state(
                db,
                user_id,
                skill.id,
                initial_mastery=BKTManager.get_initial_mastery(skill.code),
                commit=False,
            )
            db.flush()
