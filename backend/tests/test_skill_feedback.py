import json
from copy import deepcopy

import httpx

from app.config import settings
from app.services.skill_feedback import SkillFeedbackService


SKILL_CODES = ("SOURCE", "EVIDENCE", "CONTEXT", "VISUAL")


def make_profile(attempts_per_skill=1):
    skills = []
    for index, skill_code in enumerate(SKILL_CODES):
        attempts = attempts_per_skill
        correct = max(0, attempts - index)
        skills.append(
            {
                "skill_id": f"private-skill-id-{index}",
                "skill_code": skill_code,
                "skill_name": skill_code,
                "description": "Description not sent to the provider.",
                "mastery_probability": 0.25 + index * 0.1,
                "attempts": attempts,
                "correct_count": correct,
                "incorrect_count": attempts - correct,
                "accuracy": correct / attempts if attempts else None,
                "insufficient_evidence": attempts < 3,
                "bkt_parameters": {
                    "p_init": 0.3,
                    "p_guess": 0.2,
                    "p_slip": 0.05,
                    "p_transition": 0.1,
                },
                "trajectory": [],
                "updated_at": "2026-01-01T00:00:00",
            }
        )
    return {
        "user_id": "must-not-leave-backend",
        "skills": skills,
        "bkt_version": "classic-bkt-observation-transition-v1",
        "parameter_status": "provisional_defaults_not_fitted_to_real_users",
    }


def valid_feedback_payload():
    return {
        "summary": "As respostas oferecem sinais iniciais, não uma medida definitiva.",
        "strengths": [
            {
                "skill": "VISUAL",
                "title": "Análise visual",
                "explanation": "A estimativa está relativamente alta para o histórico observado.",
            }
        ],
        "improvement_areas": [
            {
                "skill": "SOURCE",
                "title": "Avaliação de fontes",
                "observed_pattern": "Dados observados: respostas registradas nesta habilidade.",
                "recommendation": "Confira o veículo e procure a fonte original.",
                "exercise": "Compare uma notícia com a publicação original.",
                "reflection_question": "Consigo verificar quem publicou a afirmação?",
            }
        ],
        "next_step": "Na próxima leitura, confira a fonte original.",
        "confidence_note": "A quantidade de tentativas ainda limita a interpretação.",
    }


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}


def test_short_history_skips_provider_and_returns_insufficient_data(monkeypatch):
    monkeypatch.setattr(settings, "feedback_llm_api_key", "")
    monkeypatch.setattr(
        "app.services.skill_feedback.httpx.post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("provider must not be called")),
    )
    profile = make_profile(attempts_per_skill=0)
    before = deepcopy(profile)

    feedback, status = SkillFeedbackService.generate(profile)

    assert status == "insufficient_data"
    assert "não há respostas" in feedback.summary
    assert feedback.improvement_areas
    assert profile == before


def test_distributed_single_attempts_do_not_call_provider(monkeypatch):
    monkeypatch.setattr(settings, "feedback_llm_api_key", "test-only-key")
    monkeypatch.setattr(
        "app.services.skill_feedback.httpx.post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("history is too thin")),
    )

    feedback, status = SkillFeedbackService.generate(make_profile(attempts_per_skill=1))

    assert status == "insufficient_data"
    assert "curto" in feedback.summary


def test_missing_provider_key_returns_skill_specific_fallback(monkeypatch):
    monkeypatch.setattr(settings, "feedback_llm_api_key", "")
    profile = make_profile(attempts_per_skill=3)

    feedback, status = SkillFeedbackService.generate(profile)

    assert status == "provider_unconfigured"
    assert len(feedback.improvement_areas) <= 3
    assert feedback.improvement_areas[0].skill == "SOURCE"
    assert "publicação original" in feedback.improvement_areas[0].recommendation.lower()


def test_local_fallback_is_structured_bounded_and_uses_lowest_mastery_first():
    profile = make_profile(attempts_per_skill=3)
    profile["skills"][0]["mastery_probability"] = 0.12
    profile["skills"][1]["mastery_probability"] = 0.24
    before = deepcopy(profile)

    feedback = SkillFeedbackService._fallback(
        SkillFeedbackService._build_context(profile)
    )

    assert len(feedback.improvement_areas) == 3
    assert feedback.improvement_areas[0].skill == "SOURCE"
    assert all(area.exercise and area.reflection_question for area in feedback.improvement_areas)
    assert feedback.next_step
    assert "12%" in feedback.improvement_areas[0].observed_pattern
    assert profile == before


def test_valid_provider_json_is_validated_and_context_has_no_identifiers(monkeypatch):
    monkeypatch.setattr(settings, "feedback_llm_api_key", "test-only-key")
    captured = {}

    def fake_post(url, *, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "payload": json, "timeout": timeout})
        return FakeResponse(json_module.dumps(valid_feedback_payload()))

    json_module = json
    monkeypatch.setattr("app.services.skill_feedback.httpx.post", fake_post)
    profile = make_profile(attempts_per_skill=3)
    before = deepcopy(profile)

    feedback, status = SkillFeedbackService.generate(profile)

    assert status == "generated"
    assert feedback.improvement_areas[0].skill == "SOURCE"
    assert captured["url"].endswith("/chat/completions")
    assert "user_id" not in captured["payload"]["messages"][1]["content"]
    assert "private-skill-id" not in captured["payload"]["messages"][1]["content"]
    assert "selected_option" not in captured["payload"]["messages"][1]["content"]
    assert profile == before


def test_invalid_or_incomplete_provider_json_uses_safe_fallback(monkeypatch):
    monkeypatch.setattr(settings, "feedback_llm_api_key", "test-only-key")
    monkeypatch.setattr(
        "app.services.skill_feedback.httpx.post",
        lambda *_args, **_kwargs: FakeResponse('{"summary":"incomplete"}'),
    )

    feedback, status = SkillFeedbackService.generate(make_profile(attempts_per_skill=3))

    assert status == "invalid_response"
    assert feedback.improvement_areas
    assert feedback.confidence_note


def test_provider_feedback_for_unknown_skill_is_classified_as_invalid(monkeypatch):
    monkeypatch.setattr(settings, "feedback_llm_api_key", "test-only-key")
    payload = valid_feedback_payload()
    payload["improvement_areas"][0]["skill"] = "UNTRACKED"
    monkeypatch.setattr(
        "app.services.skill_feedback.httpx.post",
        lambda *_args, **_kwargs: FakeResponse(json.dumps(payload)),
    )

    feedback, status = SkillFeedbackService.generate(make_profile(attempts_per_skill=3))

    assert status == "invalid_response"
    assert feedback.improvement_areas[0].skill in SKILL_CODES


def test_timeout_keeps_bkt_profile_available(monkeypatch):
    monkeypatch.setattr(settings, "feedback_llm_api_key", "test-only-key")
    monkeypatch.setattr(
        "app.services.skill_feedback.httpx.post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(httpx.TimeoutException("timeout")),
    )
    profile = make_profile(attempts_per_skill=3)
    before = deepcopy(profile)

    feedback, status = SkillFeedbackService.generate(profile)

    assert status == "provider_error"
    assert feedback.summary
    assert profile == before
