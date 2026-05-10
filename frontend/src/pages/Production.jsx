export default function Production() {
  return (
    <section className="grid gap-8">
      <div className="max-w-3xl">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-neutral-500">Production</p>
        <h1 className="mt-4 text-4xl font-semibold leading-tight text-neutral-950 sm:text-5xl">
          Generate scene-level assets for editing in CapCut.
        </h1>
        <p className="mt-4 text-base leading-7 text-neutral-600">
          Production will create first-frame images, silent B-roll clips, voiceover audio, and downloadable scene kits.
        </p>
      </div>
      <div className="rounded-3xl border border-border bg-surface p-8 shadow-sm">
        <p className="text-lg font-semibold text-neutral-950">No production session.</p>
        <p className="mt-2 text-sm leading-6 text-neutral-600">
          Complete a Studio session first, then continue to Production.
        </p>
      </div>
    </section>
  )
}
