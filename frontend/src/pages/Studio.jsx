export default function Studio() {
  return (
    <section className="grid gap-8 lg:grid-cols-[1fr_340px]">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-neutral-500">Studio</p>
        <h1 className="mt-4 text-4xl font-semibold leading-tight text-neutral-950 sm:text-5xl">
          Design the ad concept and compliant UGC script.
        </h1>
        <div className="mt-8 grid gap-4">
          {["Choose Influencer", "Session Customizations", "Environment", "Product Information", "Script"].map(
            (title) => (
              <div className="rounded-3xl border border-border bg-surface p-6 shadow-sm" key={title}>
                <h2 className="text-lg font-semibold text-neutral-950">{title}</h2>
                <p className="mt-2 text-sm leading-6 text-neutral-600">
                  This section will be implemented in the next product stage.
                </p>
              </div>
            ),
          )}
        </div>
      </div>
      <aside className="h-fit rounded-3xl border border-border bg-surface p-6 shadow-sm lg:sticky lg:top-6">
        <h2 className="text-lg font-semibold text-neutral-950">Session Summary</h2>
        <p className="mt-2 text-sm leading-6 text-neutral-600">
          Select a persona from your bank to begin configuring this ad.
        </p>
      </aside>
    </section>
  )
}
