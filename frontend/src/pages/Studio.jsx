import { useEffect, useMemo, useState } from "react"

import { fileUrl } from "../api/client.js"
import { listPersonas } from "../api/personas.js"
import {
  createSession,
  generateReferences,
  getReferenceJob,
  getSession,
  updateSession,
  uploadProductImages,
} from "../api/sessions.js"
import StatusBadge from "../components/StatusBadge.jsx"

const accessoryOptions = ["Glasses", "Earrings", "Necklace", "Bracelet", "Ring", "Hat", "Bandana", "Watch"]
const environmentOptions = {
  primary_environment: ["Kitchen", "Living room", "Bedroom", "Bathroom", "Home gym", "Car interior"],
  time_of_day: ["Morning", "Midday", "Golden hour", "Evening", "Night"],
  lighting_style: ["Natural light", "Soft studio", "Moody dim", "Overcast"],
  aesthetic: ["Minimal clean", "Cozy warm", "Urban gritty", "Luxury", "Rustic", "Modern trendy"],
}
const productCategories = [
  "Skincare",
  "Haircare",
  "Supplement",
  "Fitness equipment",
  "Tech gadget",
  "Apparel",
  "Home product",
  "Pet product",
  "Service",
  "App",
  "Other",
]
const ctaOptions = ["Link in bio", "Use code [X]", "Shop now", "Try for free", "Limited time offer", "Custom"]

const initialEnvironment = {
  primary_environment: "Kitchen",
  time_of_day: "Morning",
  lighting_style: "Natural light",
  aesthetic: "Minimal clean",
}

const initialProduct = {
  name: "",
  category: "Skincare",
  key_benefits: "",
  target_audience: "",
  number_of_scenes: 5,
  cta: "Shop now",
  custom_cta: "",
}

export default function Studio() {
  const [personas, setPersonas] = useState([])
  const [selectedPersona, setSelectedPersona] = useState(null)
  const [session, setSession] = useState(null)
  const [outfit, setOutfit] = useState("")
  const [accessories, setAccessories] = useState([])
  const [environment, setEnvironment] = useState(initialEnvironment)
  const [product, setProduct] = useState(initialProduct)
  const [uploadFiles, setUploadFiles] = useState([])
  const [referenceJob, setReferenceJob] = useState(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [pageError, setPageError] = useState("")

  useEffect(() => {
    loadPersonas()
  }, [])

  useEffect(() => {
    if (!referenceJob || !session) return undefined
    if (["completed", "failed", "cancelled"].includes(referenceJob.status)) return undefined

    const timer = window.setInterval(async () => {
      try {
        const job = await getReferenceJob(session.id, referenceJob.id)
        setReferenceJob(job)
        const freshSession = await getSession(session.id)
        setSession(freshSession)
      } catch (error) {
        setPageError(error.message)
      }
    }, 3000)

    return () => window.clearInterval(timer)
  }, [referenceJob, session])

  const completedPersonas = useMemo(() => personas.filter((persona) => persona.status === "completed"), [personas])

  async function loadPersonas() {
    try {
      setPersonas(await listPersonas())
    } catch (error) {
      setPageError(error.message)
    }
  }

  async function handlePersonaSelect(persona) {
    setSelectedPersona(persona)
    setPageError("")
    if (!session) return
    const updated = await updateSession(session.id, { persona_id: persona.id })
    setSession(updated)
  }

  async function saveSession() {
    if (!selectedPersona) throw new Error("Select a completed persona first.")
    const payload = {
      persona_id: selectedPersona.id,
      outfit,
      accessories_json: accessories,
      environment_json: environment,
      product_json: normalizedProduct(product),
    }
    if (session) {
      const updated = await updateSession(session.id, payload)
      setSession(updated)
      return updated
    }
    const created = await createSession(payload)
    setSession(created)
    return created
  }

  async function handleSaveSession() {
    setIsSaving(true)
    setPageError("")
    try {
      await saveSession()
    } catch (error) {
      setPageError(error.message)
    } finally {
      setIsSaving(false)
    }
  }

  async function handleUpload() {
    setIsUploading(true)
    setPageError("")
    try {
      const currentSession = session || (await saveSession())
      const updated = await uploadProductImages(currentSession.id, uploadFiles)
      setSession(updated)
      setUploadFiles([])
    } catch (error) {
      setPageError(error.message)
    } finally {
      setIsUploading(false)
    }
  }

  async function handleGenerateReferences() {
    setIsSaving(true)
    setPageError("")
    try {
      const currentSession = await saveSession()
      const job = await generateReferences(currentSession.id)
      setReferenceJob(job)
      setSession(await getSession(currentSession.id))
    } catch (error) {
      setPageError(error.message)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <section className="grid gap-8 lg:grid-cols-[1fr_340px]">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-neutral-500">Studio</p>
        <h1 className="mt-4 text-4xl font-semibold leading-tight text-neutral-950 sm:text-5xl">
          Design the ad concept, product context, and session references.
        </h1>

        {pageError ? <ErrorPanel message={pageError} /> : null}

        <div className="mt-8 grid gap-5">
          <Section title="Choose Influencer">
            {completedPersonas.length === 0 ? (
              <p className="text-sm leading-6 text-neutral-600">
                Complete a persona in Persona Bank before configuring a Studio session.
              </p>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {completedPersonas.map((persona) => (
                  <PersonaPickCard
                    isSelected={selectedPersona?.id === persona.id}
                    key={persona.id}
                    onSelect={() => handlePersonaSelect(persona)}
                    persona={persona}
                  />
                ))}
              </div>
            )}
          </Section>

          <Section title="Session Customizations">
            <TextInput label="Outfit" value={outfit} onChange={setOutfit} placeholder="linen shirt, relaxed fit" />
            <CheckboxGroup options={accessoryOptions} values={accessories} onChange={setAccessories} />
          </Section>

          <Section title="Environment">
            <div className="grid gap-4 md:grid-cols-2">
              {Object.entries(environmentOptions).map(([key, options]) => (
                <SelectInput
                  key={key}
                  label={labelize(key)}
                  value={environment[key]}
                  options={options}
                  onChange={(value) => setEnvironment({ ...environment, [key]: value })}
                />
              ))}
            </div>
          </Section>

          <Section title="Product Information">
            <div className="grid gap-4 md:grid-cols-2">
              <TextInput label="Product Name" value={product.name} onChange={(name) => setProduct({ ...product, name })} />
              <SelectInput
                label="Product Category"
                value={product.category}
                options={productCategories}
                onChange={(category) => setProduct({ ...product, category })}
              />
              <TextInput
                label="Key Benefits"
                value={product.key_benefits}
                onChange={(key_benefits) => setProduct({ ...product, key_benefits })}
              />
              <TextInput
                label="Target Audience"
                value={product.target_audience}
                onChange={(target_audience) => setProduct({ ...product, target_audience })}
              />
              <TextInput
                label="Number of Scenes"
                min="3"
                max="10"
                type="number"
                value={product.number_of_scenes}
                onChange={(number_of_scenes) => setProduct({ ...product, number_of_scenes })}
              />
              <SelectInput label="Call to Action" value={product.cta} options={ctaOptions} onChange={(cta) => setProduct({ ...product, cta })} />
              {product.cta === "Custom" ? (
                <TextInput label="Custom CTA" value={product.custom_cta} onChange={(custom_cta) => setProduct({ ...product, custom_cta })} />
              ) : null}
            </div>

            <div className="rounded-3xl border border-border bg-surface-muted p-4">
              <label className="grid gap-2 text-sm font-medium text-neutral-800">
                Product Reference Images
                <input
                  accept="image/png,image/jpeg,image/webp"
                  className="rounded-xl border border-border bg-white px-4 py-3 text-sm"
                  multiple
                  onChange={(event) => setUploadFiles(Array.from(event.target.files || []))}
                  type="file"
                />
              </label>
              <div className="mt-3 flex flex-wrap gap-2">
                {session?.product_upload_paths_json?.map((path) => (
                  <img alt="Uploaded product" className="h-16 w-16 rounded-2xl object-cover" key={path} src={fileUrl(path)} />
                ))}
              </div>
              <button
                className="mt-4 rounded-full border border-border bg-white px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:text-neutral-400"
                disabled={!uploadFiles.length || isUploading}
                onClick={handleUpload}
                type="button"
              >
                {isUploading ? "Uploading..." : "Upload Images"}
              </button>
            </div>
          </Section>

          <Section title="Generated References">
            <ReferenceGrid session={session} />
          </Section>
        </div>
      </div>

      <aside className="h-fit rounded-3xl border border-border bg-surface p-6 shadow-sm lg:sticky lg:top-6">
        <h2 className="text-lg font-semibold text-neutral-950">Session Summary</h2>
        <div className="mt-5 grid gap-4 text-sm text-neutral-600">
          <SummaryRow label="Influencer" value={selectedPersona?.name || "Not selected"} />
          <SummaryRow label="Outfit" value={outfit || "Not set"} />
          <SummaryRow label="Environment" value={`${environment.primary_environment}, ${environment.time_of_day}`} />
          <SummaryRow label="Product" value={product.name || "Not set"} />
          <SummaryRow label="Scenes" value={`${product.number_of_scenes || 0} scenes`} />
          <SummaryRow label="Uploads" value={`${session?.product_upload_paths_json?.length || 0} images`} />
        </div>
        <div className="mt-5 flex items-center justify-between">
          <span className="text-sm font-medium text-neutral-700">Status</span>
          <StatusBadge status={session?.status || "draft"} />
        </div>
        {referenceJob ? (
          <p className="mt-3 text-sm leading-6 text-neutral-600">{referenceJob.current_step || referenceJob.status}</p>
        ) : null}
        {session?.error_message ? <p className="mt-3 rounded-2xl bg-red-50 p-3 text-sm text-red-800">{session.error_message}</p> : null}
        <button
          className="mt-6 w-full rounded-full bg-neutral-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
          disabled={isSaving || referenceJob?.status === "running" || referenceJob?.status === "queued"}
          onClick={handleGenerateReferences}
          type="button"
        >
          {referenceJob?.status === "running" || referenceJob?.status === "queued" ? "Generating..." : "Generate References"}
        </button>
        <button
          className="mt-3 w-full rounded-full border border-border bg-white px-5 py-3 text-sm font-semibold text-neutral-900"
          disabled={isSaving}
          onClick={handleSaveSession}
          type="button"
        >
          {isSaving ? "Saving..." : "Save Session"}
        </button>
      </aside>
    </section>
  )
}

function PersonaPickCard({ persona, isSelected, onSelect }) {
  return (
    <article className={`rounded-3xl border bg-surface p-4 shadow-sm ${isSelected ? "border-neutral-950" : "border-border"}`}>
      <div className="flex gap-4">
        <img alt={`${persona.name} avatar`} className="h-20 w-20 rounded-2xl object-cover" src={fileUrl(persona.base_image_path)} />
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold text-neutral-950">{persona.name}</h2>
          <p className="mt-1 text-sm text-neutral-600">
            {persona.gender}, {persona.age}
          </p>
          <p className="mt-2 w-fit rounded-full bg-surface-muted px-3 py-1 text-xs font-medium text-neutral-700">
            {persona.personality_json?.content_niche || "Niche"}
          </p>
        </div>
      </div>
      <button className="mt-4 rounded-full bg-neutral-950 px-4 py-2 text-sm font-medium text-white" onClick={onSelect} type="button">
        {isSelected ? "Selected" : "Select"}
      </button>
    </article>
  )
}

function ReferenceGrid({ session }) {
  const references = [
    ["Session Character", session?.session_character_ref_path],
    ["Environment Base", session?.environment_base_path],
    ["Environment Reference", session?.environment_ref_path],
    ["Product Reference", session?.product_ref_path],
  ]

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {references.map(([label, path]) => (
        <div className="rounded-3xl border border-border bg-surface-muted p-3" key={label}>
          <p className="mb-3 text-sm font-medium text-neutral-800">{label}</p>
          {path ? (
            <img alt={label} className="aspect-video w-full rounded-2xl object-cover" src={fileUrl(path)} />
          ) : (
            <div className="flex aspect-video items-center justify-center rounded-2xl bg-white text-center text-sm text-neutral-500">
              Pending generation
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <section className="rounded-3xl border border-border bg-surface p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-neutral-950">{title}</h2>
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

function SelectInput({ label, value, options, onChange }) {
  return (
    <label className="grid gap-2 text-sm font-medium text-neutral-800">
      {label}
      <select
        className="rounded-xl border border-border bg-white px-4 py-3 text-sm outline-none transition focus:border-border-strong"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  )
}

function CheckboxGroup({ options, values, onChange }) {
  function toggle(option) {
    onChange(values.includes(option) ? values.filter((value) => value !== option) : [...values, option])
  }

  return (
    <fieldset className="grid gap-3">
      <legend className="text-sm font-medium text-neutral-800">Accessories</legend>
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
            <input checked={values.includes(option)} className="sr-only" onChange={() => toggle(option)} type="checkbox" />
            {option}
          </label>
        ))}
      </div>
    </fieldset>
  )
}

function SummaryRow({ label, value }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border pb-3">
      <span>{label}</span>
      <span className="text-right font-medium text-neutral-950">{value}</span>
    </div>
  )
}

function ErrorPanel({ message }) {
  return <div className="mt-6 rounded-3xl border border-red-100 bg-red-50 p-5 text-sm leading-6 text-red-800">{message}</div>
}

function normalizedProduct(product) {
  return {
    ...product,
    number_of_scenes: Number(product.number_of_scenes),
    cta: product.cta === "Custom" ? product.custom_cta : product.cta,
  }
}

function labelize(value) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase())
}
