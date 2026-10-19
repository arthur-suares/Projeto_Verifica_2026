import type { UserSkillProfileResponse, SkillFeedbackStatus } from "@/lib/types"
import { SkillProgress } from "@/components/profile/skill-progress"

type SkillProfileProps = {
  profile: UserSkillProfileResponse
}

const FEEDBACK_STATUS_LABEL: Record<SkillFeedbackStatus, string> = {
  generated: "Orientação personalizada baseada nas estimativas e no histórico agregado.",
  insufficient_data: "Ainda há poucas respostas para personalizar conclusões; as sugestões abaixo são exercícios gerais.",
  provider_unconfigured: "Feedback gerado localmente; o serviço de linguagem não está configurado.",
  provider_error: "O serviço de feedback está indisponível; suas estimativas BKT continuam disponíveis.",
  invalid_response: "A resposta do serviço não passou pela validação; exibindo orientação local segura.",
}

export function SkillProfile({ profile }: SkillProfileProps) {
  const { skills, feedback } = profile

  return (
    <div className="mx-auto max-w-3xl space-y-4 px-4 py-8">
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900">Perfil de habilidades</h1>
        <p className="mt-2 text-sm text-slate-600">
          Estimativas de domínio produzidas pelo BKT a partir das respostas registradas. Não são uma medida definitiva de competência.
        </p>
      </div>

      <section className="space-y-3 rounded-xl border border-border bg-card p-5" aria-labelledby="feedback-heading">
        <div className="flex flex-col gap-1">
          <h2 id="feedback-heading" className="text-lg font-semibold text-foreground">Orientação para praticar</h2>
          <p className="text-sm text-muted-foreground">{FEEDBACK_STATUS_LABEL[profile.feedback_status]}</p>
          <p className="text-sm leading-relaxed text-foreground">{feedback.summary}</p>
        </div>

        {feedback.strengths.length > 0 && (
          <div className="border-t border-border pt-3">
            <h3 className="text-sm font-semibold text-foreground">Sinais de progresso</h3>
            <ul className="mt-2 space-y-2">
              {feedback.strengths.map((strength) => (
                <li key={strength.skill} className="text-sm text-muted-foreground">
                  <span className="font-medium text-foreground">{strength.title}:</span> {strength.explanation}
                </li>
              ))}
            </ul>
          </div>
        )}

        {feedback.improvement_areas.length > 0 && (
          <div className="border-t border-border pt-3">
            <h3 className="text-sm font-semibold text-foreground">Prioridades de prática</h3>
            <div className="mt-2 space-y-3">
              {feedback.improvement_areas.map((area) => (
                <article key={area.skill} className="border-l-2 border-primary/50 pl-3">
                  <h4 className="text-sm font-semibold text-foreground">{area.title}</h4>
                  <p className="mt-1 text-xs text-muted-foreground">{area.observed_pattern}</p>
                  <p className="mt-1 text-sm text-foreground">{area.recommendation}</p>
                  <p className="mt-1 text-sm text-muted-foreground"><span className="font-medium">Exercício:</span> {area.exercise}</p>
                  <p className="mt-1 text-sm text-muted-foreground"><span className="font-medium">Pergunta:</span> {area.reflection_question}</p>
                </article>
              ))}
            </div>
          </div>
        )}

        <div className="border-t border-border pt-3">
          <h3 className="text-sm font-semibold text-foreground">Próximo passo</h3>
          <p className="mt-1 text-sm text-foreground">{feedback.next_step}</p>
          <p className="mt-2 text-xs text-muted-foreground">{feedback.confidence_note}</p>
        </div>
      </section>

      <div className="space-y-3">
        {skills.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-slate-500">
            Nenhum estado de habilidade registrado ainda.
          </div>
        ) : (
          skills.map((skill) => <SkillProgress key={skill.skill_code} skill={skill} />)
        )}
      </div>
    </div>
  )
}
