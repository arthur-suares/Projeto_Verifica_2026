"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { AlertCircle, Loader2, RotateCcw } from "lucide-react"

import { SkillProfile } from "@/components/profile/skill-profile"
import { Button, buttonVariants } from "@/components/ui/button"
import { describeApiError, getUserSkills, isAuthenticationError } from "@/lib/game-api"
import type { UserSkillProfileResponse } from "@/lib/types"
import { cn } from "@/lib/utils"

type ProfileState =
  | { phase: "loading" }
  | { phase: "loaded"; profile: UserSkillProfileResponse }
  | { phase: "error"; message: string; requiresLogin: boolean }

export default function ProfilePage() {
  const [state, setState] = useState<ProfileState>({ phase: "loading" })
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    let active = true
    setState({ phase: "loading" })
    getUserSkills().then(
      (profile) => {
        if (active) setState({ phase: "loaded", profile })
      },
      (error: unknown) => {
        if (active) {
          setState({
            phase: "error",
            message: describeApiError(error),
            requiresLogin: isAuthenticationError(error),
          })
        }
      },
    )
    return () => {
      active = false
    }
  }, [retryCount])

  if (state.phase === "loading") {
    return (
      <div className="flex flex-1 items-center justify-center gap-3 py-16 text-sm text-muted-foreground" role="status">
        <Loader2 className="size-5 animate-spin" />
        Carregando seu perfil...
      </div>
    )
  }

  if (state.phase === "error") {
    return (
      <main className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center gap-4 px-4 py-12 text-center">
        <AlertCircle className="size-8 text-destructive" />
        <p role="alert" className="text-sm text-foreground">{state.message}</p>
        {state.requiresLogin ? (
          <Link href="/login" className={cn(buttonVariants(), "gap-2")}>
            Entrar
          </Link>
        ) : (
          <Button type="button" onClick={() => setRetryCount((count) => count + 1)} className="gap-2">
            <RotateCcw className="size-4" />
            Tentar novamente
          </Button>
        )}
      </main>
    )
  }

  return <SkillProfile profile={state.profile} />
}
