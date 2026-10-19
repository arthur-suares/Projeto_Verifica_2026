"""
Skills Routes - HTTP endpoints for skill-related operations.

Endpoints for getting user skill profile and answer submission.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.services.answer import (
    AnswerConflictError,
    AnswerForbiddenError,
    AnswerNotFoundError,
    AnswerService,
)
from app.services.skill_feedback import SkillFeedbackService
from app.schemas import AnswerCreate, AnswerResponse, UserSkillProfileResponse

router = APIRouter(prefix="/api", tags=["skills"])


@router.get("/users/me/skills", response_model=UserSkillProfileResponse)
def get_user_skills(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get the current user's skill profile.

    Returns mastery probabilities for all four skills (SOURCE, EVIDENCE, CONTEXT, VISUAL).

    Response:
        {
            "skills": [
                {
                    "skill_id": "...",
                    "skill_code": "SOURCE",
                    "mastery_probability": 0.72,
                    "updated_at": "2024-01-01T12:00:00"
                },
                ...
            ]
        }
    """
    try:
        profile = AnswerService.get_user_skill_profile(db, user_id)
        feedback, feedback_status = SkillFeedbackService.generate(profile)

        return {
            "skills": profile["skills"],
            "feedback": feedback,
            "feedback_status": feedback_status,
            "bkt_version": profile["bkt_version"],
            "parameter_status": profile["parameter_status"],
        }
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching skills: {str(error)}",
        )


@router.post("/games/{game_id}/answers", response_model=AnswerResponse, status_code=status.HTTP_201_CREATED)
def submit_answer(
    game_id: str,
    answer: AnswerCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Submit an answer to a question.

    This endpoint:
    1. Validates the answer (game ownership, round, question and option)
    2. Stores it in the database
    3. Updates user's skill mastery using BKT
    4. Returns feedback including correctness and new mastery level

    Errors:
        403: The game belongs to another user
        404: Game, round or question not found
        409: Round already answered or game finished
        422: Invalid answer payload or option

    Request:
        {
            "question_id": "...",
            "game_round_id": "...",
            "selected_option": "A",
            "confidence": 4,
            "response_time": 5320
        }

    Response:
        {
            "id": "...",
            "correct": true,
            "skill_code": "SOURCE",
            "mastery_probability": 0.57,
            "previous_mastery_probability": 0.30,
            "correct_option": "A",
            "explanation": "..."
        }
    """
    try:
        result = AnswerService.process_answer(
            db,
            user_id,
            game_id,
            answer.game_round_id,
            answer.question_id,
            answer.selected_option,
            answer.confidence,
            answer.response_time,
        )

        return {
            "id": result["answer_id"],
            "correct": result["correct"],
            "skill_code": result["skill_code"],
            "mastery_probability": result["new_mastery"],
            "previous_mastery_probability": result["old_mastery"],
            "correct_option": result["correct_option"],
            "explanation": result["explanation"],
        }
    except AnswerForbiddenError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    except AnswerNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except AnswerConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting answer: {str(error)}",
        )
