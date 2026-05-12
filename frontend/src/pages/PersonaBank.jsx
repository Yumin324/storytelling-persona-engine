import React, { useEffect, useMemo, useState } from "react"

import StatusBadge from "../components/StatusBadge.jsx"
import { fileUrl } from "../api/client.js"
import { createPersona, deletePersona, generatePersonaAssets, getPersonaJob, listPersonas } from "../api/personas.js"
import { listVoices } from "../api/voices.js"

const physicalOptions = {
  ethnicity: ["White", "Black", "East Asian", "South Asian", "Southeast Asian", "Middle Eastern", "Hispanic"],
  skin_tone: ["Very Fair", "Fair", "Medium", "Olive", "Brown", "Dark"],
  face_shape: ["Oval", "Round", "Square", "Heart", "Diamond", "Oblong"],
  jawline: ["Soft", "Defined", "Sharp"],
  cheekbones: ["High", "Medium", "Low"],
  eye_shape: ["Almond", "Round", "Hooded", "Monolid", "Upturned", "Downturned"],
  eye_color: ["Brown", "Dark Brown", "Hazel", "Green", "Blue", "Grey", "Amber"],
  eyebrow_shape: ["Straight", "Arched", "Flat", "Curved", "Angled"],
  eyebrow_color: ["Black", "Blonde", "Brown", "Dark Brown", "Red"],
  nose_shape: ["Straight", "Button", "Wide", "Narrow", "Upturned", "Hooked"],
  mouth_shape: ["Wide", "Medium", "Small"],
  lip_fullness: ["Thin", "Medium", "Full"],
  hair_length: ["Bald", "Buzz cut", "Short", "Medium", "Long", "Very long"],
  hair_texture: ["Straight", "Wavy", "Curly", "Coily", "Kinky"],
  default_hair_color: ["Black", "Dark Brown", "Brown", "Dirty Blonde", "Blonde", "Auburn", "Red", "Grey", "White"],
  facial_hair: ["None", "Light stubble", "Full stubble", "Short beard", "Medium beard", "Full beard", "Goatee", "Mustache"],
  body_type: ["Slim", "Athletic", "Average", "Curvy", "Muscular", "Plus-size"],
}

const distinguishingFeatures = [
  "None",
  "Freckles",
  "Moles",
  "Dimples",
  "Birthmark",
  "Vitiligo",
  "Visible tattoos",
  "Pierced ears",
  "Scar",
]

const personalityOptions = {
  core_personality: [
    "Relatable",
    "Ambitious",
    "Laid-back",
    "Intellectual",
    "Adventurous",
    "Nurturing",
    "Confident",
    "Quirky",
    "Minimalist",
    "Trendy",
    "Authentic",
    "Sarcastic",
    "Empathetic",
    "Bold",
  ],
  content_niche: [
    "Lifestyle",
    "Fitness",
    "Beauty",
    "Skincare",
    "Tech",
    "Food",
    "Travel",
    "Wellness",
    "Fashion",
    "Parenting",
    "Finance",
    "Gaming",
    "Home",
    "Pets",
  ],
  communication_style: ["Storytelling", "Problem-solution", "Review-based", "Tutorial", "Comparison", "Emotional appeal"],
  humor_level: ["None", "Dry", "Subtle", "Moderate", "Highly comedic"],
  values: [
    "Sustainability",
    "Self-improvement",
    "Family",
    "Freedom",
    "Community",
    "Luxury",
    "Minimalism",
    "Health",
    "Authenticity",
    "Innovation",
  ],
}

const initialPhysical = Object.fromEntries(Object.entries(physicalOptions).map(([key, values]) => [key, values[0]]))
const initialPersonality = {
  core_personality: "Relatable",
  content_niche: "Lifestyle",
  communication_style: "Storytelling",
  humor_level: "Subtle",
  values: ["Authenticity"],
}

export default function PersonaBank() {
  const [personas, setPersonas] = useState([])
  const [voices, setVoices] = useState([])
  const [voiceError, setVoiceError] = useState("")
  const [pageError, setPageError] = useState("")
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [activeJobs, setActiveJobs] = useState({})
  const [form, setForm] = useState(() => createInitialForm())

  useEffect(() => {
    refreshPersonas()
    loadVoices()
  }, [])

  useEffect(() => {
    const jobIds = Object.values(activeJobs).filter(Boolean)
    if (jobIds.length === 0) return undefined

    const timer = window.setInterval(async () => {
      const nextJobs = { ...activeJobs }
      let changed = false

      await Promise.all(
        Object.entries(activeJobs).map(async ([personaId, jobId]) => {
          try {
            const job = await getPersonaJob(jobId)
            if (["completed", "failed", "cancelled"].includes(job.status)) {
              delete nextJobs[personaId]
              changed = true
            }
          } catch (error) {
            delete nextJobs[personaId]
            changed = true
          }
        }),
      )

      await refreshPersonas()
      if (changed) setActiveJobs(nextJobs)
    }, 2500)

    return () => window.clearInterval(timer)
  }, [activeJobs])

  const filteredVoices = useMemo(() => {
    const gender = form.gender.toLowerCase()
    return voices.filter((voice) => !voice.gender || voice.gender.toLowerCase() === gender)
  }, [form.gender, voices])

  async function refreshPersonas() {
    try {
      setPersonas(await listPersonas())
      setPageError("")
    } catch (error) {
      setPageError(error.message)
    }
  }

  async function loadVoices() {
    try {
      setVoices(await listVoices())
      setVoiceError("")
    } catch (error) {
      if (isMissingElevenLabsKeyError(error)) {
        setVoices([])
        setVoiceError("")
        return
      }
      setVoiceError(error.message)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setIsSubmitting(true)
    setPageError("")

    try {
      validateForm(form)
      const selectedVoice = voices.find((voice) => voice.voice_id === form.voice_id)
      const persona = await createPersona({
        name: form.name,
        age: Number(form.age),
        gender: form.gender,
        physical_json: {
          ...form.physical,
          facial_hair: form.gender === "Male" ? form.physical.facial_hair : "None",
          distinguishing_features: form.distinguishing_features,
        },
        voice_json: {
          voice_id: form.voice_id,
          voice_name: selectedVoice?.name || form.voice_name,
          provider: "elevenlabs",
          gender_category: form.gender,
          voice_settings: {
            stability: 0.5,
            similarity_boost: 0.75,
            style: 0.2,
            use_speaker_boost: true,
          },
        },
        personality_json: form.personality,
      })
      const job = await generatePersonaAssets(persona.id)
      setActiveJobs((jobs) => ({ ...jobs, [persona.id]: job.id }))
      setForm(createInitialForm())
      setIsFormOpen(false)
      await refreshPersonas()
    } catch (error) {
      setPageError(error.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleRetry(personaId) {
    try {
      const job = await generatePersonaAssets(personaId)
      setActiveJobs((jobs) => ({ ...jobs, [personaId]: job.id }))
      await refreshPersonas()
    } catch (error) {
      setPageError(error.message)
    }
  }

  async function handleDelete(personaId) {
    try {
      await deletePersona(personaId)
      setPersonas((items) => items.filter((persona) => persona.id !== personaId))
      setActiveJobs((jobs) => {
        const next = { ...jobs }
        delete next[personaId]
        return next
      })
    } catch (error) {
      setPageError(error.message)
    }
  }

  return (
    <section className="grid gap-8">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="max-w-2xl">
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-neutral-500">Persona Bank</p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight text-neutral-950 sm:text-5xl">
            Create and manage reusable AI influencers for your UGC ad sessions.
          </h1>
        </div>
        <button
          className="rounded-full bg-neutral-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-neutral-800"
          onClick={() => setIsFormOpen((value) => !value)}
          type="button"
        >
          {isFormOpen ? "Close Form" : "Create Persona"}
        </button>
      </div>

      {pageError ? <ErrorPanel message={pageError} /> : null}

      {isFormOpen ? (
        <PersonaForm
          filteredVoices={filteredVoices}
          form={form}
          isSubmitting={isSubmitting}
          onChange={setForm}
          onSubmit={handleSubmit}
          onVoiceRetry={loadVoices}
          voiceError={voiceError}
          voices={voices}
        />
      ) : null}

      {personas.length === 0 ? (
        <div className="rounded-3xl border border-border bg-surface p-8 shadow-sm">
          <p className="text-lg font-semibold text-neutral-950">No personas yet.</p>
          <p className="mt-2 text-sm leading-6 text-neutral-600">
            Create your first AI influencer to start building UGC ad sessions.
          </p>
        </div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {personas.map((persona) => (
            <PersonaCard
              key={persona.id}
              onDelete={handleDelete}
              onRetry={handleRetry}
              persona={persona}
            />
          ))}
        </div>
      )}
    </section>
  )
}

function PersonaForm({
  filteredVoices,
  form,
  isSubmitting,
  onChange,
  onSubmit,
  onVoiceRetry,
  voiceError,
  voices,
}) {
  const selectedVoice = filteredVoices.find((voice) => voice.voice_id === form.voice_id)

  return (
    <form className="grid gap-5" onSubmit={onSubmit}>
      <Stepper />
      <FormSection eyebrow="1 Identity" title="Identity">
        <div className="grid gap-4 md:grid-cols-3">
          <TextInput label="Name" value={form.name} onChange={(name) => onChange({ ...form, name })} />
          <TextInput
            label="Age"
            type="number"
            value={form.age}
            onChange={(age) => onChange({ ...form, age })}
            min="18"
            max="70"
          />
          <SelectInput
            label="Gender"
            value={form.gender}
            options={["Female", "Male"]}
            onChange={(gender) => onChange({ ...form, gender, voice_id: "" })}
          />
        </div>
      </FormSection>

      <FormSection eyebrow="2 Physical Attributes" title="Physical Attributes">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Object.entries(physicalOptions).map(([key, options]) => {
            if (key === "facial_hair" && form.gender !== "Male") return null
            return (
              <SelectInput
                key={key}
                label={labelize(key)}
                value={form.physical[key]}
                options={options}
                onChange={(value) => onChange({ ...form, physical: { ...form.physical, [key]: value } })}
              />
            )
          })}
        </div>
        <CheckboxGroup
          label="Distinguishing Features"
          options={distinguishingFeatures}
          values={form.distinguishing_features}
          onChange={(values) => onChange({ ...form, distinguishing_features: values })}
        />
      </FormSection>

      <FormSection eyebrow="3 Voice" title="Voice">
        {voiceError ? (
          <div className="rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-800">
            <p>{voiceError}</p>
            <button className="mt-3 rounded-full border border-red-200 px-4 py-2 font-medium" onClick={onVoiceRetry} type="button">
              Retry Voices
            </button>
          </div>
        ) : null}
        <div className="grid gap-4">
          <SelectInput
            label="ElevenLabs Voice"
            value={form.voice_id}
            options={filteredVoices.map((voice) => ({
              label: `${voice.name || "Unnamed voice"}${voice.gender ? ` (${voice.gender})` : ""}`,
              value: voice.voice_id,
            }))}
            placeholder={voices.length ? "Select a voice" : "No voices loaded"}
            onChange={(voice_id) => onChange({ ...form, voice_id })}
          />
          <VoicePreview voice={selectedVoice} />
        </div>
      </FormSection>

      <FormSection eyebrow="4 Personality" title="Personality Attributes">
        <div className="grid gap-4 md:grid-cols-2">
          {Object.entries(personalityOptions)
            .filter(([key]) => key !== "values")
            .map(([key, options]) => (
              <SelectInput
                key={key}
                label={labelize(key)}
                value={form.personality[key]}
                options={options}
                onChange={(value) => onChange({ ...form, personality: { ...form.personality, [key]: value } })}
              />
            ))}
        </div>
        <CheckboxGroup
          label="Values"
          max={2}
          options={personalityOptions.values}
          values={form.personality.values}
          onChange={(values) => onChange({ ...form, personality: { ...form.personality, values } })}
        />
      </FormSection>

      <div className="flex justify-end">
        <button
          className="rounded-full bg-neutral-950 px-6 py-3 text-sm font-semibold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Creating..." : "Generate Influencer"}
        </button>
      </div>
    </form>
  )
}

function VoicePreview({ voice }) {
  if (!voice) return null

  if (!voice.preview_url) {
    return (
      <p className="rounded-2xl border border-border bg-surface-muted p-4 text-sm text-neutral-600">
        No preview is available for this voice.
      </p>
    )
  }

  return (
    <div className="rounded-2xl border border-border bg-surface-muted p-4">
      <p className="mb-3 text-sm font-medium text-neutral-800">
        Preview {voice.name || "selected voice"}
      </p>
      <audio className="w-full" controls preload="none" src={voice.preview_url}>
        Your browser does not support audio previews.
      </audio>
    </div>
  )
}

function PersonaCard({ persona, onDelete, onRetry }) {
  const niche = persona.personality_json?.content_niche || "Unassigned"
  const voiceName = persona.voice_json?.voice_name || "Voice pending"
  const thumbnail = fileUrl(persona.base_image_path)

  return (
    <article className="overflow-hidden rounded-3xl border border-border bg-surface shadow-sm">
      <div className="aspect-[4/3] bg-surface-muted">
        {thumbnail ? (
          <img alt={`${persona.name} avatar`} className="h-full w-full object-cover" src={thumbnail} />
        ) : (
          <div className="flex h-full items-center justify-center px-6 text-center text-sm text-neutral-500">
            {persona.status === "failed" ? "Generation failed" : "Avatar will appear after generation"}
          </div>
        )}
      </div>
      <div className="grid gap-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-neutral-950">{persona.name}</h2>
            <p className="mt-1 text-sm text-neutral-600">
              {persona.age} · {persona.gender}
            </p>
          </div>
          <StatusBadge status={persona.status} />
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full bg-surface-muted px-3 py-1 text-xs font-medium text-neutral-700">{niche}</span>
          <span className="rounded-full bg-surface-muted px-3 py-1 text-xs font-medium text-neutral-700">{voiceName}</span>
        </div>
        {persona.error_message ? (
          <p className="rounded-2xl border border-red-100 bg-red-50 p-3 text-sm leading-6 text-red-800">
            {persona.error_message}
          </p>
        ) : null}
        <div className="flex gap-2">
          {persona.status === "failed" ? (
            <button className="rounded-full border border-border px-4 py-2 text-sm font-medium" onClick={() => onRetry(persona.id)} type="button">
              Retry
            </button>
          ) : null}
          <button
            className="ml-auto rounded-full border border-red-100 px-4 py-2 text-sm font-medium text-red-700"
            onClick={() => onDelete(persona.id)}
            type="button"
          >
            Delete
          </button>
        </div>
      </div>
    </article>
  )
}

function Stepper() {
  return (
    <div className="flex flex-wrap gap-2 rounded-3xl border border-border bg-surface p-3 shadow-sm">
      {["Identity", "Physical Attributes", "Voice", "Personality", "Generate"].map((step, index) => (
        <span className="rounded-full bg-surface-muted px-3 py-1.5 text-xs font-medium text-neutral-700" key={step}>
          {index + 1} {step}
        </span>
      ))}
    </div>
  )
}

function FormSection({ eyebrow, title, children }) {
  return (
    <section className="rounded-3xl border border-border bg-surface p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-neutral-500">{eyebrow}</p>
      <h2 className="mt-2 text-xl font-semibold text-neutral-950">{title}</h2>
      <div className="mt-5 grid gap-5">{children}</div>
    </section>
  )
}

function TextInput({ label, value, onChange, type = "text", ...props }) {
  return (
    <label className="grid gap-2 text-sm font-medium text-neutral-800">
      {label}
      <input
        className="rounded-xl border border-border bg-white px-4 py-3 text-sm outline-none transition focus:border-border-strong"
        onChange={(event) => onChange(event.target.value)}
        type={type}
        value={value}
        {...props}
      />
    </label>
  )
}

function SelectInput({ label, value, onChange, options, placeholder }) {
  const normalizedOptions = options.map((option) =>
    typeof option === "string" ? { label: option, value: option } : option,
  )

  return (
    <label className="grid gap-2 text-sm font-medium text-neutral-800">
      {label}
      <select
        className="rounded-xl border border-border bg-white px-4 py-3 text-sm outline-none transition focus:border-border-strong"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {placeholder ? <option value="">{placeholder}</option> : null}
        {normalizedOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

function CheckboxGroup({ label, options, values, onChange, max }) {
  function toggle(option) {
    if (option === "None") {
      onChange(["None"])
      return
    }
    const withoutNone = values.filter((value) => value !== "None")
    const next = withoutNone.includes(option)
      ? withoutNone.filter((value) => value !== option)
      : [...withoutNone, option]
    if (max && next.length > max) return
    onChange(next.length ? next : ["None"])
  }

  return (
    <fieldset className="grid gap-3">
      <legend className="text-sm font-medium text-neutral-800">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <label
            className={`cursor-pointer rounded-full border px-3 py-2 text-sm transition ${
              values.includes(option)
                ? "border-neutral-950 bg-neutral-950 text-white"
                : "border-border bg-white text-neutral-700 hover:border-border-strong"
            }`}
            key={option}
          >
            <input
              checked={values.includes(option)}
              className="sr-only"
              onChange={() => toggle(option)}
              type="checkbox"
            />
            {option}
          </label>
        ))}
      </div>
    </fieldset>
  )
}

function ErrorPanel({ message }) {
  return <div className="rounded-3xl border border-red-100 bg-red-50 p-5 text-sm leading-6 text-red-800">{message}</div>
}

function createInitialForm() {
  return {
    name: "",
    age: 25,
    gender: "Female",
    physical: initialPhysical,
    distinguishing_features: ["None"],
    voice_id: "",
    voice_name: "",
    personality: initialPersonality,
  }
}

function validateForm(form) {
  if (!form.name.trim()) throw new Error("Name is required.")
  if (Number(form.age) < 18 || Number(form.age) > 70) throw new Error("Age must be between 18 and 70.")
  if (!form.voice_id) throw new Error("Select an ElevenLabs voice before generating a persona.")
  if (!form.personality.values.length || form.personality.values.length > 2) {
    throw new Error("Choose one or two persona values.")
  }
}

function isMissingElevenLabsKeyError(error) {
  return error.message.includes("ELEVENLABS_API_KEY is missing")
}

function labelize(value) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase())
}
