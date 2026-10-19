import type {
  Answer,
  AnswerResponse,
  AnswerSubmission,
  Game,
  GameRoundPayload,
  Skill,
  UserSkillState,
  UserSkillProfileResponse,
} from "@/lib/types"

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "")
const ACCESS_TOKEN_KEY = "fact-check-access-token"

export function getAccessToken(): string | null {
  return typeof window === "undefined" ? null : window.localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function clearAccessToken(): void {
  if (typeof window !== "undefined") window.localStorage.removeItem(ACCESS_TOKEN_KEY)
}

function saveAccessToken(token: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, token)
}

// status 0 = falha de rede (backend fora do ar, CORS, sem internet)
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(status ? `${status} ${detail}` : detail)
    this.name = "ApiError"
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    const headers = new Headers(init?.headers)
    const token = getAccessToken()
    if (token) headers.set("Authorization", `Bearer ${token}`)
    response = await fetch(`${API_URL}${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, "Não foi possível conectar ao servidor.")
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === "string" ? body.detail : response.statusText
    throw new ApiError(response.status, detail)
  }
  return (await response.json()) as T
}

// Mensagem amigável para exibir ao usuário
export function describeApiError(error: unknown): string {
  if (!(error instanceof ApiError)) return "Algo deu errado. Tente novamente."
  if (error.status === 0) return "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente."
  if (error.status === 401) return "Sua sessão não está ativa. Entre para continuar."
  if (error.status === 404) return "Partida não encontrada. Inicie uma nova partida."
  if (error.status === 409) return `A partida não pode avançar neste momento: ${error.detail}`
  if (error.status === 403) return "Você não tem acesso a esta partida."
  if (error.status === 422) return `Não foi possível registrar a resposta: ${error.detail}`
  return "O servidor encontrou um erro. Tente novamente em instantes."
}

export function isAuthenticationError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

interface AccessTokenResponse {
  access_token: string
  token_type: "bearer"
}

export async function login(email: string, password: string): Promise<void> {
  const response = await request<AccessTokenResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  saveAccessToken(response.access_token)
}

export async function registerAndLogin(
  name: string,
  email: string,
  phone: string,
  password: string,
): Promise<void> {
  await request<{ user_id: string }>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, phone, password }),
  })
  await login(email, password)
}

export async function createGame(): Promise<GameRoundPayload> {
  return request<GameRoundPayload>("/api/games", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
}

// null quando a partida terminou (10 rodadas ou sem perguntas novas)
export async function getNextRound(gameId: string): Promise<GameRoundPayload | null> {
  return request<GameRoundPayload | null>(`/api/games/${encodeURIComponent(gameId)}/next`)
}

export async function submitAnswer(gameId: string, payload: AnswerSubmission): Promise<AnswerResponse> {
  return request<AnswerResponse>(`/api/games/${encodeURIComponent(gameId)}/answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
}

export async function getUserSkills(): Promise<UserSkillProfileResponse> {
  return request<UserSkillProfileResponse>("/api/users/me/skills")
}

export type { Answer, AnswerResponse, AnswerSubmission, Game, GameRoundPayload, Skill, UserSkillState }
export type { Question } from "@/lib/types"
