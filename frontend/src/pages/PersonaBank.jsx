export default function PersonaBank() {
  return (
    <section className="grid gap-8">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="max-w-2xl">
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-neutral-500">Persona Bank</p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight text-neutral-950 sm:text-5xl">
            Create reusable AI influencers for B-roll ad sessions.
          </h1>
          <p className="mt-4 text-base leading-7 text-neutral-600">
            Build structured personas with physical, voice, and personality attributes before moving into Studio.
          </p>
        </div>
        <button className="rounded-full bg-neutral-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-neutral-800">
          Create Persona
        </button>
      </div>

      <div className="rounded-3xl border border-border bg-surface p-8 shadow-sm">
        <p className="text-lg font-semibold text-neutral-950">No personas yet.</p>
        <p className="mt-2 text-sm leading-6 text-neutral-600">
          Create your first AI influencer to start building UGC ad sessions.
        </p>
      </div>
    </section>
  )
}
