import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

import pytest
from fastapi.testclient import TestClient

from app.bkt.manager import BKTManager
from app.dependencies import get_current_user_id
from app.main import app
from app.models import Answer, Game, GameRound, Question, UserSkillState
from app.repositories.game_repository import GameRepository
from app.security import create_access_token
from seed import seed_sample_news_and_questions


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def game_round(db_session):
    seed_sample_news_and_questions(db_session)
    question = db_session.query(Question).first()
    game = GameRepository.create_game(db_session, "test-user")
    round_ = GameRepository.create_game_round(
        db_session, game.id, question.news_id, round_number=1, question_id=question.id
    )
    return game, round_, question


def _payload(round_, question, option):
    return {
        "question_id": question.id,
        "game_round_id": round_.id,
        "selected_option": option,
        "confidence": 3,
        "response_time": 4000,
    }


def _wrong_option(question):
    return next(option for option in question.options if option != question.correct_option)


def _mastery(db_session, question):
    state = (
        db_session.query(UserSkillState)
        .filter_by(user_id="test-user", skill_id=question.skill_id)
        .one()
    )
    db_session.refresh(state)
    return state.mastery_probability


def test_game_endpoints_reject_requests_without_bearer_token(client):
    app.dependency_overrides.pop(get_current_user_id, None)
    try:
        response = client.post("/api/games")
    finally:
        app.dependency_overrides[get_current_user_id] = lambda: "test-user"

    assert response.status_code == 401


def test_game_endpoints_accept_login_jwt(client, game_round):
    game, _, _ = game_round
    app.dependency_overrides.pop(get_current_user_id, None)
    token = create_access_token({"sub": "test-user"})
    try:
        response = client.get(
            f"/api/games/{game.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides[get_current_user_id] = lambda: "test-user"

    assert response.status_code == 200
    assert response.json()["game_id"] == game.id


def test_registration_initializes_skills_and_login_jwt_authenticates(client, db_session):
    app.dependency_overrides.pop(get_current_user_id, None)
    try:
        registered = client.post(
            "/auth/register",
            json={
                "name": "New Learner",
                "email": "new-learner@example.test",
                "phone": "0000000002",
                "password": "test-password",
            },
        )
        assert registered.status_code == 200
        user_id = registered.json()["user_id"]
        states = db_session.query(UserSkillState).filter_by(user_id=user_id).all()
        assert len(states) == 4
        assert all(state.mastery_probability == pytest.approx(0.3) for state in states)

        logged_in = client.post(
            "/auth/login",
            json={"email": "new-learner@example.test", "password": "test-password"},
        )
        assert logged_in.status_code == 200
        token = logged_in.json()["access_token"]
        profile = client.get(
            "/api/users/me/skills",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert profile.status_code == 200
        assert len(profile.json()["skills"]) == 4
    finally:
        app.dependency_overrides[get_current_user_id] = lambda: "test-user"


@pytest.mark.parametrize(
    "credentials",
    [
        {"email": "missing@example.test", "password": "test-password"},
        {"email": "test@example.test", "password": "wrong-password"},
    ],
)
def test_login_rejects_unknown_user_or_wrong_password(client, db_session, credentials):
    """Authentication failures must not be reported as successful HTTP 200 responses."""
    from app.security import hash_password
    from app.models import User

    user = db_session.query(User).filter_by(email="test@example.test").one()
    user.password = hash_password("correct-password")
    db_session.commit()

    response = client.post("/auth/login", json=credentials)

    assert response.status_code == 401
    assert response.json()["detail"] == "E-mail ou senha inválidos"


def test_skill_profile_returns_four_persisted_states(db_session, client):
    seed_sample_news_and_questions(db_session)

    response = client.get("/api/users/me/skills")

    assert response.status_code == 200
    skills = response.json()["skills"]
    assert {skill["skill_code"] for skill in skills} == set(BKTManager.VALID_SKILLS)
    assert all(skill["mastery_probability"] == pytest.approx(0.3) for skill in skills)
    assert all(skill["attempts"] == 0 and skill["accuracy"] is None for skill in skills)
    assert response.json()["feedback_status"] == "insufficient_data"
    assert db_session.query(UserSkillState).filter_by(user_id="test-user").count() == 4


def test_profile_endpoint_keeps_bkt_available_when_feedback_provider_times_out(
    db_session, client, monkeypatch
):
    from app.config import settings

    seed_sample_news_and_questions(db_session)
    game = Game(user_id="test-user")
    db_session.add(game)
    db_session.flush()
    source_questions = (
        db_session.query(Question)
        .join(Question.skill)
        .filter_by(code="SOURCE")
        .order_by(Question.id)
        .limit(3)
        .all()
    )
    for round_number, question in enumerate(source_questions, start=1):
        game_round = GameRound(
            game_id=game.id,
            news_id=question.news_id,
            question_id=question.id,
            round_number=round_number,
        )
        db_session.add(game_round)
        db_session.flush()
        db_session.add(
            Answer(
                user_id="test-user",
                game_round_id=game_round.id,
                question_id=question.id,
                selected_option=question.correct_option,
                correct=True,
            )
        )
    db_session.commit()
    monkeypatch.setattr(settings, "feedback_llm_api_key", "test-only-key")
    monkeypatch.setattr(settings, "feedback_llm_min_attempts", 3)
    monkeypatch.setattr(
        "app.services.skill_feedback.httpx.post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            __import__("httpx").TimeoutException("test timeout")
        ),
    )

    response = client.get("/api/users/me/skills")

    assert response.status_code == 200
    body = response.json()
    assert body["feedback_status"] == "provider_error"
    assert len(body["skills"]) == 4
    source = next(skill for skill in body["skills"] if skill["skill_code"] == "SOURCE")
    persisted_state = (
        db_session.query(UserSkillState)
        .filter_by(user_id="test-user", skill_id=source["skill_id"])
        .one()
    )
    assert source["attempts"] == 3
    assert source["mastery_probability"] == persisted_state.mastery_probability


@pytest.mark.parametrize("correct", [True, False])
def test_answer_is_corrected_persisted_and_updates_bkt(db_session, client, game_round, correct):
    game, round_, question = game_round
    option = question.correct_option if correct else _wrong_option(question)

    response = client.post(f"/api/games/{game.id}/answers", json=_payload(round_, question, option))

    assert response.status_code == 201
    body = response.json()
    assert body["correct"] is correct

    # Answer persistida com a correção
    answer = db_session.get(Answer, body["id"])
    assert answer.correct is correct
    assert answer.selected_option == option
    assert answer.user_id == "test-user"

    # BKT executado a partir do domínio anterior e UserSkillState atualizado
    expected = BKTManager.update(question.skill.code, 0.3, correct)
    assert body["previous_mastery_probability"] == pytest.approx(0.3)
    assert body["mastery_probability"] == pytest.approx(expected)
    assert _mastery(db_session, question) == pytest.approx(expected)
    assert db_session.query(UserSkillState).filter_by(user_id="test-user").count() == 1

    profile = client.get("/api/users/me/skills").json()
    skill_profile = next(
        skill for skill in profile["skills"] if skill["skill_code"] == question.skill.code
    )
    assert skill_profile["attempts"] == 1
    assert skill_profile["correct_count"] == int(correct)
    assert skill_profile["incorrect_count"] == int(not correct)
    assert skill_profile["accuracy"] == pytest.approx(float(correct))
    assert skill_profile["mastery_probability"] == pytest.approx(expected)


def test_option_not_in_question_is_rejected(db_session, client, game_round):
    game, round_, question = game_round

    response = client.post(f"/api/games/{game.id}/answers", json=_payload(round_, question, "Z"))

    assert response.status_code == 422
    assert db_session.query(Answer).count() == 0


def test_round_cannot_be_answered_twice(db_session, client, game_round):
    game, round_, question = game_round
    payload = _payload(round_, question, question.correct_option)

    assert client.post(f"/api/games/{game.id}/answers", json=payload).status_code == 201
    mastery_after_first = _mastery(db_session, question)

    response = client.post(f"/api/games/{game.id}/answers", json=payload)

    assert response.status_code == 409
    assert db_session.query(Answer).count() == 1
    assert _mastery(db_session, question) == pytest.approx(mastery_after_first)


def test_bkt_failure_rolls_back_answer_and_new_skill_state(
    db_session, client, game_round, monkeypatch
):
    game, round_, question = game_round

    def fail_update(*_args, **_kwargs):
        raise ValueError("BKT failed")

    monkeypatch.setattr(BKTManager, "update", fail_update)
    response = client.post(
        f"/api/games/{game.id}/answers",
        json=_payload(round_, question, question.correct_option),
    )

    assert response.status_code == 422
    assert db_session.query(Answer).count() == 0
    assert db_session.query(UserSkillState).filter_by(user_id="test-user").count() == 0


def test_user_cannot_answer_round_from_another_users_game(db_session, client, game_round):
    game, round_, question = game_round
    app.dependency_overrides[get_current_user_id] = lambda: "other-user"
    try:
        response = client.post(
            f"/api/games/{game.id}/answers",
            json=_payload(round_, question, question.correct_option),
        )
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)

    assert response.status_code == 403
    assert db_session.query(Answer).count() == 0
    assert db_session.query(UserSkillState).filter_by(user_id="other-user").count() == 0


def test_round_from_another_game_is_rejected(db_session, client, game_round):
    _, round_, question = game_round
    other_game = GameRepository.create_game(db_session, "test-user")

    response = client.post(
        f"/api/games/{other_game.id}/answers",
        json=_payload(round_, question, question.correct_option),
    )

    assert response.status_code == 404


def test_question_for_same_news_but_not_assigned_to_round_is_rejected(
    db_session, client, game_round
):
    game, round_, question = game_round
    other_question = Question(
        news_id=question.news_id,
        skill_id=question.skill_id,
        text="Outra pergunta revisada para a mesma notícia?",
        difficulty=question.difficulty,
        options=question.options,
        correct_option=question.correct_option,
        explanation="Explicação de teste.",
    )
    db_session.add(other_question)
    db_session.commit()

    response = client.post(
        f"/api/games/{game.id}/answers",
        json=_payload(round_, other_question, other_question.correct_option),
    )

    assert response.status_code == 404
    assert db_session.query(Answer).count() == 0
    assert db_session.query(Answer).count() == 0


def test_question_from_another_round_is_rejected(db_session, client, game_round):
    game, round_, question = game_round
    other_question = db_session.query(Question).filter(Question.news_id != round_.news_id).first()

    response = client.post(
        f"/api/games/{game.id}/answers",
        json=_payload(round_, other_question, other_question.correct_option),
    )

    assert response.status_code == 404
    assert db_session.query(Answer).count() == 0


def test_unknown_game_returns_404(db_session, client, game_round):
    _, round_, question = game_round

    response = client.post(
        "/api/games/does-not-exist/answers",
        json=_payload(round_, question, question.correct_option),
    )

    assert response.status_code == 404


def test_finished_game_rejects_answers(db_session, client, game_round):
    game, round_, question = game_round
    GameRepository.finish_game(db_session, game.id)

    response = client.post(
        f"/api/games/{game.id}/answers",
        json=_payload(round_, question, question.correct_option),
    )

    assert response.status_code == 409
    assert db_session.query(Answer).count() == 0
