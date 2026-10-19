export type Veredito = "verdadeiro" | "falso" | "enganoso" | "nao_verificado"

// Formatos retornados pelo backend (backend/app/schemas.py)
export type StatusVerificacao = "processing" | "completed" | "failed"

export interface Evidencia {
  source: string
  rating: string | null
  url: string | null
}

export interface VerificacaoApi {
  id: string
  status: StatusVerificacao
  verdict: string | null
  evidence: Evidencia[]
  created_at: string
}

export interface ResultadoVerificacao {
  id: string
  veredito: Veredito
  classificacao: string | null
  evidencias: Evidencia[]
  temImagem: boolean
}

// Respostas antes da verificação, com as chaves que o backend espera
// em `answers` (backend/app/ml/perfil.py). A q9 (opinião mudou?) é
// respondida depois, na tela de resultado.
export interface RespostasPre {
  q1: number // crença inicial
  q2: number // credibilidade
  q3: number // costuma verificar
  q4: number // confia nas redes sociais
  q5: number // abertura para mudar de opinião
  q6: number // probabilidade de compartilhar
  q7: number // emoção
  q8: number // desconfia de notícias do WhatsApp/Instagram (invertida da q4)
}

// Ordem de EXIBIÇÃO (igual a ORDEM_EXIBICAO no backend): hábitos gerais
// primeiro, depois a notícia, e a q8 por último, para ficarem 5
// perguntas entre a q4 e a sua invertida (q8). Textos iguais a
// PERGUNTAS em backend/app/ml/perfil.py.
export const PERGUNTAS_PRE = [
  {
    id: "q3",
    texto: "Você costuma verificar informações antes de compartilhá-las?",
    min: "Nunca",
    max: "Sempre",
  },
  {
    id: "q4",
    texto: "Eu confio nas notícias que recebo pelas redes sociais.",
    min: "Discordo totalmente",
    max: "Concordo totalmente",
  },
  {
    id: "q1",
    texto: "Antes da verificação, você achava que a notícia era verdadeira?",
    min: "Definitivamente falsa",
    max: "Definitivamente verdadeira",
  },
  {
    id: "q2",
    texto: "O quanto você acreditava na notícia?",
    min: "Nada",
    max: "Totalmente",
  },
  {
    id: "q5",
    texto: "Se a verificação indicar o oposto do que você acha, o quão aberto você está para mudar de opinião?",
    min: "Nada aberto",
    max: "Totalmente aberto",
  },
  {
    id: "q6",
    texto:
      "Qual a probabilidade de você compartilhar essa notícia com outras pessoas (grupos de app, redes sociais, amigos)?",
    min: "Muito improvável",
    max: "Muito provável",
  },
  {
    id: "q7",
    texto: "O quanto o assunto desta notícia mexeu com suas emoções?",
    min: "Nada",
    max: "Muito",
  },
  {
    id: "q8",
    texto: "Quando uma notícia chega pelo WhatsApp ou Instagram, eu desconfio dela.",
    min: "Discordo totalmente",
    max: "Concordo totalmente",
  },
] as const

export type SkillCode = "SOURCE" | "EVIDENCE" | "CONTEXT" | "VISUAL"

export interface Skill {
  id: string
  code: SkillCode
  name: string
  description?: string | null
}

// Procedência de uma alegação checada do dataset (GameNewsDetails no backend).
// Não traz o veredito nem a manchete da checagem, que entregariam a resposta.
export interface NewsDetails {
  kind: "fact_check_claim"
  claim: string
  origin?: string | null
  checked_on?: string | null
  fact_checker?: string | null
  fact_checker_site?: string | null
  source_url?: string | null
}

export interface News {
  id: string
  title: string
  content: string
  image_url?: string | null
  verdict?: string | null
  created_at?: string
  details?: NewsDetails | null
}

export interface Question {
  id: string
  text: string
  difficulty: number
  options: Record<string, string>
  skill_id: string
  skill_code?: SkillCode | null
  explanation?: string | null
  correct_option?: string | null
  hints?: string[]
}

// Rodada jogável devolvida por POST /api/games e GET /api/games/{id}/next
// (GameRoundResponse no backend). O gabarito só vem após a resposta.
export interface GameRoundPayload {
  game_id: string
  round: {
    id: string
    number: number
    news_id: string
    question_id: string
  }
  news: News
  question: Question
}

export interface GameRound {
  id: string
  game_id: string
  round_number: number
  news: News
  questions: Question[]
  started_at: string
  finished_at?: string | null
}

export interface Game {
  id: string
  user_id: string
  status: "IN_PROGRESS" | "FINISHED"
  started_at: string
  finished_at?: string | null
  rounds?: GameRound[]
}

export interface Answer {
  id: string
  user_id: string
  game_round_id: string
  question_id: string
  selected_option: string
  correct: boolean
  confidence?: number | null
  response_time?: number | null
  created_at: string
}

export interface UserSkillState {
  skill_id: string
  skill_code: SkillCode
  skill_name: string
  description?: string | null
  mastery_probability: number
  updated_at: string
  attempts: number
  correct_count: number
  incorrect_count: number
  accuracy: number | null
  insufficient_evidence: boolean
  bkt_parameters: Record<string, number>
  trajectory: SkillTrajectoryPoint[]
}

export interface SkillTrajectoryPoint {
  attempt: number
  created_at: string
  mastery_probability: number
}

export interface SkillFeedbackStrength {
  skill: SkillCode
  title: string
  explanation: string
}

export interface SkillFeedbackArea {
  skill: SkillCode
  title: string
  observed_pattern: string
  recommendation: string
  exercise: string
  reflection_question: string
}

export interface PersonalizedSkillFeedback {
  summary: string
  strengths: SkillFeedbackStrength[]
  improvement_areas: SkillFeedbackArea[]
  next_step: string
  confidence_note: string
}

export type SkillFeedbackStatus =
  | "generated"
  | "insufficient_data"
  | "provider_unconfigured"
  | "provider_error"
  | "invalid_response"

export interface UserSkillProfileResponse {
  skills: UserSkillState[]
  feedback: PersonalizedSkillFeedback
  feedback_status: SkillFeedbackStatus
  bkt_version: string
  parameter_status: string
}

// Payload de POST /api/games/{game_id}/answers (AnswerCreate no backend)
export interface AnswerSubmission {
  question_id: string
  game_round_id: string
  selected_option: string
  confidence: number // 1..5
  response_time: number // milissegundos
}

// Resposta de POST /api/games/{game_id}/answers (AnswerResponse no backend)
export interface AnswerResponse {
  id: string
  correct: boolean
  skill_code: SkillCode
  mastery_probability: number
  previous_mastery_probability?: number | null
  correct_option?: string | null
  explanation?: string | null
}

// Dados exibidos na tela de feedback após uma resposta. Os campos de
// domínio são opcionais: quando o backend passar a devolver
// old_mastery/new_mastery (AnswerService.process_answer), a tela mostra
// a evolução da skill rastreada pelo BKT.
export interface AnswerFeedback {
  correct: boolean
  skill_code: SkillCode
  selected_option: string
  selected_option_text?: string | null
  correct_option?: string | null
  correct_option_text?: string | null
  explanation?: string | null
  next_action?: string | null
  mastery_before?: number | null
  mastery_after?: number | null
  source_url?: string | null
  fact_checker?: string | null
}
