export default function TopNav({ tabs, activeTab, onTabChange }) {
  return (
    <header className="border-b border-border bg-background/95">
      <div className="mx-auto flex max-w-[1180px] flex-col gap-5 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
        <button
          className="w-fit text-left text-xl font-semibold tracking-normal text-neutral-950"
          onClick={() => onTabChange("personas")}
          type="button"
        >
          UGCLABs
        </button>
        <nav aria-label="Primary navigation" className="flex flex-wrap gap-2">
          {Object.entries(tabs).map(([key, tab]) => {
            const isActive = key === activeTab

            return (
              <button
                className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                  isActive
                    ? "bg-neutral-950 text-white"
                    : "text-neutral-500 hover:bg-surface-muted hover:text-neutral-950"
                }`}
                key={key}
                onClick={() => onTabChange(key)}
                type="button"
              >
                {tab.label}
              </button>
            )
          })}
        </nav>
      </div>
    </header>
  )
}
