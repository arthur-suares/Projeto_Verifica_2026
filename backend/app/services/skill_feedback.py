"""Optional pedagogical feedback layered on top of immutable BKT estimates."""

import json
import logging

import httpx
from pydantic import ValidationError

from app.config import settings
from app.schemas import (
    PersonalizedSkillFeedback,
    SkillFeedbackArea,
    SkillFeedbackStrength,
)

logger = logging.getLogger(__name__)

SKILL_GUIDANCE = {
    "SOURCE": {
        "name": "Avaliação de fontes",
        "recommendation": "Confira quem publicou a notícia e procure a publicação original antes de confiar ou compartilhar.",
        "exercise": "Escolha uma notícia e localize o autor, o veículo e a fonte primária citada; registre o que conseguiu confirmar.",
        "question": "Consigo identificar quem publicou e verificar a origem da afirmação?",
    },
    "EVIDENCE": {
        "name": "Análise de evidências",
        "recommendation": "Separe a afirmação das evidências e confira se os dados realmente sustentam a conclusão.",
        "exercise": "Para uma alegação, anote uma evidência verificável e explique se ela apoia, contradiz ou não resolve a afirmação.",
        "question": "Qual evidência observável sustenta esta conclusão?",
    },
    "CONTEXT": {
        "name": "Verificação de contexto",
        "recommendation": "Procure a publicação original, confira datas e leia o trecho completo antes de interpretar uma citação.",
        "exercise": "Compare uma manchete com a fonte original e identifique data, trecho omitido e contexto necessário.",
        "question": "O que aconteceu antes ou depois do trecho apresentado?",
    },
    "VISUAL": {
        "name": "Análise visual",
        "recommendation": "Busque a origem da imagem e verifique data, local e se ela demonstra o que o texto afirma.",
        "exercise": "Pesquise uma imagem por origem e compare sinais de local/data com a legenda que a acompanha.",
        "question": "A imagem mostra este evento, neste local e neste período?",
    },
}


class SkillFeedbackService:
    """Generate bounded, validated advice without changing BKT state."""

    @classmethod
    def generate(cls, profile: dict) -> tuple[PersonalizedSkillFeedback, str]:
        context = cls._build_context(profile)
        total_attempts = sum(skill["attempts"] for skill in context["skills"])
        max_skill_attempts = max((skill["attempts"] for skill in context["skills"]), default=0)

        if (
            total_attempts < settings.feedback_llm_min_attempts
            or max_skill_attempts < 3
        ):
            return cls._fallback(context, insufficient=True), "insufficient_data"
        if not settings.feedback_llm_api_key:
            return cls._fallback(context), "provider_unconfigured"

        try:
            feedback = cls._request_feedback(context)
            known_skills = {item["skill"] for item in context["skills"]}
            if any(
                item.skill not in known_skills
                for item in [*feedback.strengths, *feedback.improvement_areas]
            ):
                raise ValueError("Feedback references a skill outside the supplied profile")
            if len({item.skill for item in feedback.improvement_areas}) != len(
                feedback.improvement_areas
            ):
                raise ValueError("Feedback contains duplicate improvement areas")
            return feedback, "generated"
        except (ValidationError, ValueError, KeyError, TypeError, IndexError):
            logger.warning("Skill feedback provider returned an invalid response")
            return cls._fallback(context), "invalid_response"
        except Exception:
            logger.warning("Skill feedback provider unavailable; using local fallback")
            return cls._fallback(context), "provider_error"

    @staticmethod
    def _build_context(profile: dict) -> dict:
        """Whitelist aggregate fields; never send identifiers or raw answers."""
        return {
            "bkt_version": profile["bkt_version"],
            "parameter_status": profile["parameter_status"],
            "skills": [
                {
                    "skill": item["skill_code"],
                    "mastery_probability": round(item["mastery_probability"], 4),
                    "attempts": item["attempts"],
                    "correct": item["correct_count"],
                    "incorrect": item["incorrect_count"],
                    "accuracy": round(item["accuracy"], 4) if item["accuracy"] is not None else None,
                    "insufficient_evidence": item["insufficient_evidence"],
                    "parameters": item["bkt_parameters"],
                    "trajectory": item["trajectory"],
                }
                for item in profile["skills"]
            ],
        }

    @classmethod
    def _request_feedback(cls, context: dict) -> PersonalizedSkillFeedback:
        base_url = settings.feedback_llm_base_url.rstrip("/")
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.feedback_llm_api_key}"},
            json={
                "model": settings.feedback_llm_model,
                "temperature": 0.2,
                "max_tokens": 1200,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Você é um tutor de alfabetização midiática. Responda somente JSON compatível "
                            "com o schema: summary, strengths, improvement_areas, next_step, confidence_note. "
                            "Use apenas os aggregates fornecidos como observações; não invente respostas, "
                            "notícias, causas psicológicas ou estatísticas. Mastery é uma estimativa BKT, "
                            "não porcentagem de acertos nem diagnóstico. Com poucas tentativas, diga que há "
                            "pouca evidência. Inclua até 3 strengths e até 3 improvement_areas, apenas para "
                            "skills informadas. Em observed_pattern, distinga fatos observados de interpretação. "
                            "Recomendações devem ser práticas, breves e adequadas à habilidade."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(context, ensure_ascii=False, separators=(",", ":")),
                    },
                ],
            },
            timeout=settings.feedback_llm_timeout_seconds,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str) or len(content) > 8000:
            raise ValueError("Feedback response missing or too large")
        return PersonalizedSkillFeedback.model_validate_json(content)

    @staticmethod
    def _fallback(context: dict, insufficient: bool = False) -> PersonalizedSkillFeedback:
        skills = sorted(context["skills"], key=lambda item: (item["mastery_probability"], item["skill"]))
        attempts = sum(item["attempts"] for item in skills)
        if attempts == 0:
            summary = (
                "Ainda não há respostas registradas. As estimativas começam nos valores iniciais do BKT; "
                "elas não permitem identificar pontos fortes ou dificuldades individuais."
            )
            note = "Sem tentativas, não há evidência individual para avaliar evolução ou domínio."
        elif insufficient:
            summary = (
                f"Há {attempts} tentativa(s) no total. O histórico ainda é curto para conclusões "
                "individualizadas; use as próximas rodadas para reunir mais evidências."
            )
            note = "Poucas tentativas por habilidade; estas orientações são exercícios gerais, não conclusões sobre competência."
        else:
            weakest = SKILL_GUIDANCE[skills[0]["skill"]]["name"]
            summary = (
                f"Com base em {attempts} respostas registradas, a menor estimativa atual está em "
                f"{weakest}. As probabilidades são estimativas do BKT e podem mudar com novas respostas."
            )
            note = "A estimativa BKT não é uma medida definitiva; a personalização usa contagens e histórico disponíveis."

        strengths = [
            SkillFeedbackStrength(
                skill=item["skill"],
                title=SKILL_GUIDANCE[item["skill"]]["name"],
                explanation=(
                    f"Estimativa BKT relativamente alta ({item['mastery_probability']:.0%}) com "
                    f"{item['attempts']} tentativas; isso é um sinal preliminar, não certeza de domínio."
                ),
            )
            for item in skills
            if item["attempts"] >= 3 and item["mastery_probability"] >= 0.65
        ][:3]

        areas = []
        for item in skills[:3]:
            guidance = SKILL_GUIDANCE[item["skill"]]
            if item["attempts"] >= 3:
                observed = (
                    f"Dados observados: {item['correct']} acertos e {item['incorrect']} erros "
                    f"em {item['attempts']} tentativas; mastery estimada em "
                    f"{item['mastery_probability']:.0%}."
                )
            else:
                observed = (
                    f"Há {item['attempts']} tentativa(s) nesta habilidade; ainda são poucas para "
                    "inferir um padrão individual."
                )
            areas.append(
                SkillFeedbackArea(
                    skill=item["skill"],
                    title=guidance["name"],
                    observed_pattern=observed,
                    recommendation=guidance["recommendation"],
                    exercise=guidance["exercise"],
                    reflection_question=guidance["question"],
                )
            )

        next_step = (
            "Na próxima notícia, escolha uma das perguntas de reflexão acima e anote a evidência que encontrou."
            if attempts
            else "Inicie uma partida e registre algumas respostas antes de interpretar sua evolução."
        )
        return PersonalizedSkillFeedback(
            summary=summary,
            strengths=strengths,
            improvement_areas=areas,
            next_step=next_step,
            confidence_note=note,
        )
