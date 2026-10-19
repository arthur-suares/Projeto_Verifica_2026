import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, Float, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base


# ============================================================================
# LEGACY MODELS (Verification, Evidence, Feedback)
# ============================================================================
class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="processing", nullable=False)
    verdict: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fact_check_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    evidence: Mapped[list["Evidence"]] = relationship(back_populates="verification", cascade="all, delete-orphan")
    feedback: Mapped[list["Feedback"]] = relationship(back_populates="verification", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    verification_id: Mapped[str] = mapped_column(ForeignKey("verifications.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    verification: Mapped[Verification] = relationship(back_populates="evidence")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    verification_id: Mapped[str] = mapped_column(ForeignKey("verifications.id"), nullable=False)
    answers: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    verification: Mapped[Verification] = relationship(back_populates="feedback")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )


# ============================================================================
# NEW MODELS (Game, Knowledge Tracing, Skills) - MVP Architecture
# ============================================================================

class GameStatusEnum(PyEnum):
    """Status of a game session."""
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"


class Skill(Base):
    """Represents a learnable skill.
    
    Skills tracked by BKT:
    - SOURCE: Ability to analyze information source/origin
    - EVIDENCE: Ability to evaluate supporting evidence
    - CONTEXT: Ability to perceive omitted/distorted context
    - VISUAL: Ability to evaluate image-claim relationship
    """
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user_skill_states: Mapped[list["UserSkillState"]] = relationship(
        back_populates="skill", 
        cascade="all, delete-orphan"
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="skill",
        cascade="all, delete-orphan"
    )


class UserSkillState(Base):
    """Tracks user's mastery probability for each skill.
    
    Updated by BKT after each answer.
    Constraints:
    - One state per user + skill combination.
    - mastery_probability between 0 and 1.
    """
    __tablename__ = "user_skill_states"
    __table_args__ = (
        UniqueConstraint('user_id', 'skill_id', name='uq_user_skill'),
        CheckConstraint(
            'mastery_probability >= 0 AND mastery_probability <= 1',
            name='ck_user_skill_mastery_range',
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"), nullable=False, index=True)
    mastery_probability: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship()
    skill: Mapped[Skill] = relationship(back_populates="user_skill_states")

    @validates("mastery_probability")
    def validate_mastery_probability(self, key: str, value: float) -> float:
        if value is None or not (0 <= value <= 1):
            raise ValueError(f"mastery_probability must be between 0 and 1, got {value}")
        return value


class News(Base):
    """Represents a news article or claim to be evaluated."""
    __tablename__ = "news"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(100), nullable=True)  # "true", "false", etc.
    fact_check_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    game_rounds: Mapped[list["GameRound"]] = relationship(back_populates="news")
    questions: Mapped[list["Question"]] = relationship(back_populates="news", cascade="all, delete-orphan")


class Question(Base):
    """Represents a question associated with a skill and news.
    
    One question evaluates one skill.
    Difficulty: 0 (easy) to 1 (hard).
    """
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    news_id: Mapped[str] = mapped_column(ForeignKey("news.id"), nullable=False, index=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[float] = mapped_column(Float, nullable=False)  # 0 to 1
    options: Mapped[dict] = mapped_column(JSON, nullable=False)  # {"A": "...", "B": "...", ...}
    correct_option: Mapped[str] = mapped_column(String(10), nullable=False)  # "A", "B", "C", etc.
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    news: Mapped[News] = relationship(back_populates="questions")
    skill: Mapped[Skill] = relationship(back_populates="questions")
    answers: Mapped[list["Answer"]] = relationship(back_populates="question", cascade="all, delete-orphan")


class Game(Base):
    """Represents a game session for a user.
    
    A game consists of multiple rounds where the user answers questions.
    """
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        Enum(GameStatusEnum), 
        default=GameStatusEnum.IN_PROGRESS,
        nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    rounds: Mapped[list["GameRound"]] = relationship(back_populates="game", cascade="all, delete-orphan")


class GameRound(Base):
    """Represents a single round within a game.
    
    One round = one question about one news item.
    """
    __tablename__ = "game_rounds"
    __table_args__ = (UniqueConstraint("game_id", "round_number", name="uq_game_round_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), nullable=False, index=True)
    news_id: Mapped[str] = mapped_column(ForeignKey("news.id"), nullable=False, index=True)
    question_id: Mapped[str | None] = mapped_column(ForeignKey("questions.id"), nullable=True, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    game: Mapped[Game] = relationship(back_populates="rounds")
    news: Mapped[News] = relationship(back_populates="game_rounds")
    question: Mapped["Question | None"] = relationship()
    answers: Mapped[list["Answer"]] = relationship(back_populates="game_round", cascade="all, delete-orphan")


class Answer(Base):
    """Represents a user's answer to a question.
    
    Fields:
    - selected_option: Option chosen by the user (key of Question.options)
    - correct: Observation used by BKT (whether answer was correct)
    - confidence: User's confidence 1-5 (optional)
    - response_time: Time taken in milliseconds (optional, >= 0)
    """
    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint("game_round_id", name="uq_answers_game_round_id"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 1 AND confidence <= 5)",
            name="ck_answer_confidence_range",
        ),
        CheckConstraint(
            "response_time IS NULL OR response_time >= 0",
            name="ck_answer_response_time_non_negative",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    game_round_id: Mapped[str] = mapped_column(ForeignKey("game_rounds.id"), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), nullable=False, index=True)
    selected_option: Mapped[str] = mapped_column(String(10), nullable=False)
    correct: Mapped[bool] = mapped_column(default=False, nullable=False)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    response_time: Mapped[int | None] = mapped_column(Integer, nullable=True)  # milliseconds
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship()
    game_round: Mapped[GameRound] = relationship(back_populates="answers")
    question: Mapped[Question] = relationship(back_populates="answers")

    @validates("confidence")
    def validate_confidence(self, key: str, value: int | None) -> int | None:
        if value is not None and not (1 <= value <= 5):
            raise ValueError(f"confidence must be between 1 and 5, got {value}")
        return value

    @validates("response_time")
    def validate_response_time(self, key: str, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError(f"response_time must be non-negative, got {value}")
        return value
