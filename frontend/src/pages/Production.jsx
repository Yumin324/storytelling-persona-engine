import { useEffect, useMemo, useState } from "react"

import { fileUrl } from "../api/client.js"
import { listPersonas } from "../api/personas.js"
import { getProductionJob, getProductionScenes, startProduction } from "../api/production.js"
import { getSession } from "../api/sessions.js"
import StatusBadge from "../components/StatusBadge.jsx"

export default function Production() {
  const [session, setSession] = useState(null)
  const [persona, setPersona] = useState(null)
  const [job, setJob] = useState(null)
  const [scenes, setScenes] = useState([])
  const [pageError, setPageError] = useState("")
  const [isStarting, setIsStarting] = useState(false)

  useEffect(() => {
    loadActiveSession()
  }, [])

  useEffect(() => {
    if (!job || ["completed", "failed", "cancelled"].includes(job.status)) return undefined

    const timer = window.setInterval(async () => {
      try {
        const freshJob = await getProductionJob(job.id)
        setJob(freshJob)
        setScenes(await getProductionScenes(job.id))
      } catch (error) {
        setPageError(error.message)
      }
    }, 2500)

    return () => window.clearInterval(timer)
  }, [job])

  const scriptScenes = session?.script_json?.scenes || []
  const estimatedSeconds = scriptScenes.length * 8
  const canStart = Boolean(session?.script_json && session?.session_character_ref_path && session?.environment_ref_path && session?.product_ref_path)

  async function loadActiveSession() {
    const sessionId = window.localStorage.getItem("ugclabs_active_session_id")
    if (!sessionId) return

    try {
      const loadedSession = await getSession(sessionId)
      setSession(loadedSession)
      const personas = await listPersonas()
      setPersona(personas.find((item) => item.id === loadedSession.persona_id) || null)
      setPageError("")
    } catch (error) {
      setPageError(error.message)
    }
  }

  async function handleStartProduction() {
    if (!session) return
    setIsStarting(true)
    setPageError("")
    try {
      const createdJob = await startProduction(session.id)
      setJob(createdJob)
      setScenes(await getProductionScenes(createdJob.id))
    } catch (error) {
      setPageError(error.message)
    } finally {
      setIsStarting(false)
    }
  }

  return (
    <section className="grid gap-8">
      <div className="max-w-3xl">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-neutral-500">Production</p>
        <h1 className="mt-4 text-4xl font-semibold leading-tight text-neutral-950 sm:text-5xl">
          Generate scene-level prompts for the production asset pipeline.
        </h1>
        <p className="mt-4 text-base leading-7 text-neutral-600">
          This stage creates the production prompt kit first. Image, video, and audio generation will follow in the next stage.
        </p>
      </div>

      {pageError ? <ErrorPanel message={pageError} /> : null}

      {!session ? (
        <div className="rounded-3xl border border-border bg-surface p-8 shadow-sm">
          <p className="text-lg font-semibold text-neutral-950">No production session.</p>
          <p className="mt-2 text-sm leading-6 text-neutral-600">
            Complete a Studio session first, then continue to Production.
          </p>
        </div>
      ) : (
        <>
          <ProductionSummary
            canStart={canStart}
            estimatedSeconds={estimatedSeconds}
            isStarting={isStarting}
            job={job}
            onStart={handleStartProduction}
            persona={persona}
            session={session}
          />
          {job ? <ProgressPanel job={job} scenes={scenes} /> : null}
          <ScenePromptGrid scenes={scenes} scriptScenes={scriptScenes} />
        </>
      )}
    </section>
  )
}

function ProductionSummary({ session, persona, estimatedSeconds, job, canStart, isStarting, onStart }) {
  const product = session.product_json || {}
  const environment = session.environment_json || {}

  return (
    <section className="rounded-3xl border border-border bg-surface p-6 shadow-sm">
      <div className="grid gap-6 lg:grid-cols-[160px_1fr_auto]">
        <div className="overflow-hidden rounded-3xl bg-surface-muted">
          {persona?.base_image_path ? (
            <img alt={persona.name} className="aspect-square h-full w-full object-cover" src={fileUrl(persona.base_image_path)} />
          ) : (
            <div className="flex aspect-square items-center justify-center text-sm text-neutral-500">Persona</div>
          )}
        </div>
        <div className="grid gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-neutral-950">{product.name || "Untitled product"}</h2>
            <p className="mt-2 text-sm leading-6 text-neutral-600">
              {persona?.name || "Selected persona"} in {environment.primary_environment || "environment"} · {estimatedSeconds} seconds
            </p>
          </div>
          <div className="grid gap-3 text-sm text-neutral-700 sm:grid-cols-2">
            <SummaryLine label="Outfit" value={session.outfit || "Not set"} />
            <SummaryLine label="Accessories" value={(session.accessories_json || []).join(", ") || "None"} />
            <SummaryLine label="Environment" value={`${environment.time_of_day || ""} · ${environment.lighting_style || ""}`} />
            <SummaryLine label="Product Category" value={product.category || "Not set"} />
          </div>
          <details className="rounded-2xl border border-border bg-surface-muted p-4">
            <summary className="cursor-pointer text-sm font-semibold text-neutral-900">Script Preview</summary>
            <div className="mt-3 grid gap-2 text-sm leading-6 text-neutral-700">
              {(session.script_json?.scenes || []).map((scene) => (
                <p key={scene.scene_id}>
                  <span className="font-semibold">{scene.scene_id}:</span> {scene.voiceover}
                </p>
              ))}
            </div>
          </details>
        </div>
        <div className="flex min-w-44 flex-col items-start gap-3 lg:items-end">
          <StatusBadge status={job?.status || "draft"} />
          <button
            className="rounded-full bg-neutral-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
            disabled={!canStart || isStarting || job?.status === "running" || job?.status === "queued"}
            onClick={onStart}
            type="button"
          >
            {isStarting ? "Starting..." : "Generate Ad"}
          </button>
          {!canStart ? <p className="text-right text-xs leading-5 text-red-700">Script and all references are required.</p> : null}
        </div>
      </div>
    </section>
  )
}

function ProgressPanel({ job, scenes }) {
  return (
    <section className="rounded-3xl border border-border bg-surface p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-neutral-950">Prompt Generation</h2>
          <p className="mt-1 text-sm text-neutral-600">{job.current_step || "Queued"}</p>
        </div>
        <StatusBadge status={job.status} />
      </div>
      <div className="mt-5 flex items-center gap-4">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-muted">
          <div className="h-full rounded-full bg-neutral-950 transition-all" style={{ width: `${job.progress_percent || 0}%` }} />
        </div>
        <span className="text-sm font-medium text-neutral-700">{job.progress_percent || 0}%</span>
      </div>
      {job.error_message ? <p className="mt-4 rounded-2xl bg-red-50 p-3 text-sm text-red-800">{job.error_message}</p> : null}
      <p className="mt-3 text-sm text-neutral-600">{scenes.length} scene rows created.</p>
    </section>
  )
}

function ScenePromptGrid({ scenes, scriptScenes }) {
  const displayScenes = scenes.length
    ? scenes
    : scriptScenes.map((scene, index) => ({
        id: scene.scene_id,
        scene_number: index + 1,
        script_visual: scene.visual,
        script_voiceover: scene.voiceover,
        status: "draft",
      }))

  return (
    <div className="grid gap-5">
      {displayScenes.map((scene) => (
        <article className="rounded-3xl border border-border bg-surface p-6 shadow-sm" key={scene.id}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-neutral-950">Scene {String(scene.scene_number).padStart(2, "0")}</h2>
            <StatusBadge status={scene.status} />
          </div>
          <div className="mt-5 grid gap-4 text-sm leading-6 text-neutral-700">
            <PromptBlock title="Visual Direction" value={scene.script_visual} />
            <PromptBlock title="Voiceover" value={scene.script_voiceover} />
            <PromptBlock title="First Frame Prompt" value={scene.image_prompt} />
            <PromptBlock title="Animation Prompt" value={scene.video_prompt} />
            <PromptBlock title="Voice Prompt" value={scene.voice_prompt} />
            {scene.safety_notes_json?.length ? (
              <PromptBlock title="Safety Notes" value={scene.safety_notes_json.join("; ")} />
            ) : null}
            {scene.error_message ? <p className="rounded-2xl bg-red-50 p-3 text-red-800">{scene.error_message}</p> : null}
          </div>
        </article>
      ))}
    </div>
  )
}

function PromptBlock({ title, value }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">{title}</p>
      <p className="mt-1 rounded-2xl bg-surface-muted p-3 text-neutral-800">{value || "Pending"}</p>
    </div>
  )
}

function SummaryLine({ label, value }) {
  return (
    <p>
      <span className="font-semibold text-neutral-950">{label}:</span> {value}
    </p>
  )
}

function ErrorPanel({ message }) {
  return <div className="rounded-3xl border border-red-100 bg-red-50 p-5 text-sm leading-6 text-red-800">{message}</div>
}
