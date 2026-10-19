import type { UserSkillState } from "@/lib/types"

type SkillProgressProps = {
  skill: UserSkillState
}

export function SkillProgress({ skill }: SkillProgressProps) {
  const value = Math.min(100, Math.max(0, skill.mastery_probability * 100))

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex flex-col">
          <span className="font-medium text-slate-800">{skill.skill_name}</span>
          <span className="text-xs text-slate-500">{skill.skill_code} · domínio estimado BKT</span>
        </div>
        <span className="text-sm font-semibold text-slate-700">{value.toFixed(0)}%</span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-gradient-to-r from-sky-500 to-indigo-500"
          style={{ width: `${value}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-slate-600">
        {skill.attempts} tentativa(s): {skill.correct_count} acertos e {skill.incorrect_count} erros.
      </p>
      {skill.attempts === 0 ? (
        <p className="mt-1 text-xs text-amber-700">Estimativa inicial; ainda não há respostas registradas.</p>
      ) : skill.insufficient_evidence ? (
        <p className="mt-1 text-xs text-amber-700">Histórico curto para uma interpretação individualizada.</p>
      ) : null}
    </div>
  )
}
