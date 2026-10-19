from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# LEGACY SCHEMAS (Verification, Feedback)
# ============================================================================

class VerificationCreate(BaseModel):
    text: str = Field(min_length=1)


class VerificationAccepted(BaseModel):
    id: str
    status: str


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    rating: str | None
    url: str | None


class VerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    verdict: str | None
    evidence: list[EvidenceResponse]
    created_at: datetime


class FeedbackCreate(BaseModel):
    answers: dict[str, Any]


class FeedbackResponse(BaseModel):
    id: str
    verification_id: str


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str
    phone: str
    password: str = Field(min_length=6, max_length=100)


class UserLogin(BaseModel):
    email: str
    password: str


# ============================================================================
# NEW SCHEMAS (Game, Skills, Knowledge Tracing)
# ============================================================================

class SkillResponse(BaseModel):
    """Response schema for a skill."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    description: str | None = None


class UserSkillStateResponse(BaseModel):
    """Response schema for user's skill state."""
    model_config = ConfigDict(from_attributes=True)

    skill_id: str
    skill_code: str
    skill_name: str
    description: str | None = None
    mastery_probability: float
    updated_at: datetime
    attempts: int = Field(ge=0)
    correct_count: int = Field(ge=0)
    incorrect_count: int = Field(ge=0)
    accuracy: float | None = Field(default=None, ge=0, le=1)
    insufficient_evidence: bool
    bkt_parameters: dict[str, float]
    trajectory: list["SkillTrajectoryPoint"] = Field(max_length=6)


class SkillTrajectoryPoint(BaseModel):
    attempt: int = Field(ge=1)
    created_at: datetime
    mastery_probability: float = Field(ge=0, le=1)


class SkillFeedbackStrength(BaseModel):
    skill: Literal["SOURCE", "EVIDENCE", "CONTEXT", "VISUAL"]
    title: str = Field(min_length=1, max_length=100)
    explanation: str = Field(min_length=1, max_length=350)


class SkillFeedbackArea(BaseModel):
    skill: Literal["SOURCE", "EVIDENCE", "CONTEXT", "VISUAL"]
    title: str = Field(min_length=1, max_length=100)
    observed_pattern: str = Field(min_length=1, max_length=300)
    recommendation: str = Field(min_length=1, max_length=350)
    exercise: str = Field(min_length=1, max_length=350)
    reflection_question: str = Field(min_length=1, max_length=200)


class PersonalizedSkillFeedback(BaseModel):
    summary: str = Field(min_length=1, max_length=500)
    strengths: list[SkillFeedbackStrength] = Field(max_length=3)
    improvement_areas: list[SkillFeedbackArea] = Field(max_length=3)
    next_step: str = Field(min_length=1, max_length=250)
    confidence_note: str = Field(min_length=1, max_length=300)


class UserSkillProfileResponse(BaseModel):
    """User's complete skill profile."""
    skills: list[UserSkillStateResponse]
    feedback: PersonalizedSkillFeedback
    feedback_status: Literal[
        "generated",
        "insufficient_data",
        "provider_unconfigured",
        "provider_error",
        "invalid_response",
    ]
    bkt_version: str
    parameter_status: str


class NewsResponse(BaseModel):
    """Response schema for news."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    content: str
    image_url: str | None = None
    verdict: str | None = None
    created_at: datetime


class QuestionOptionResponse(BaseModel):
    """Response schema for question with options."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    text: str
    difficulty: float
    options: dict[str, str]
    skill_id: str
    explanation: str | None = None


class AnswerCreate(BaseModel):
    """Request schema for submitting an answer."""
    question_id: str
    game_round_id: str
    selected_option: str = Field(min_length=1, max_length=10)
    confidence: int | None = Field(None, ge=1, le=5)
    response_time: int | None = Field(None, ge=0)


class AnswerResponse(BaseModel):
    """Response schema after answer submission."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    correct: bool
    skill_code: str
    mastery_probability: float
    previous_mastery_probability: float | None = None
    correct_option: str | None = None
    explanation: str | None = None


class GameRoundInfo(BaseModel):
    """Identifiers of the round being played."""
    id: str
    number: int
    news_id: str
    question_id: str


class GameNewsDetails(BaseModel):
    """Provenance of a fact-checked claim from the dataset (no verdict, no fact-check headline)."""
    kind: str
    claim: str
    origin: str | None = None
    checked_on: str | None = None
    fact_checker: str | None = None
    fact_checker_site: str | None = None
    source_url: str | None = None


class GameNewsResponse(BaseModel):
    """News shown during a round. The verdict is omitted so it doesn't spoil the answer."""
    id: str
    title: str
    content: str
    image_url: str | None = None
    details: GameNewsDetails | None = None


class GameQuestionResponse(BaseModel):
    """Question shown during a round. correct_option and explanation are only revealed after answering."""
    id: str
    text: str
    difficulty: float
    options: dict[str, str]
    skill_id: str
    skill_code: str
    hints: list[str] = []


class GameRoundResponse(BaseModel):
    """A playable round, as returned by GameService (create and next)."""
    game_id: str
    round: GameRoundInfo
    news: GameNewsResponse
    question: GameQuestionResponse


class GameCreateResponse(GameRoundResponse):
    """Response when creating a new game: the game with its first round."""


class GameStatusResponse(BaseModel):
    """Response with game status."""
    model_config = ConfigDict(from_attributes=True)

    game_id: str
    status: str
    round_number: int | None = None
    finished_at: datetime | None = None
