import React from "react"

const styles = {
  draft: "bg-neutral-100 text-neutral-700 border-neutral-200",
  queued: "bg-neutral-100 text-neutral-700 border-neutral-200",
  running: "bg-blue-50 text-blue-700 border-blue-100",
  completed: "bg-emerald-50 text-emerald-700 border-emerald-100",
  failed: "bg-red-50 text-red-700 border-red-100",
  retrying: "bg-amber-50 text-amber-700 border-amber-100",
  cancelled: "bg-neutral-100 text-neutral-700 border-neutral-200",
}

export default function StatusBadge({ status }) {
  const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : "Draft"

  return (
    <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${styles[status] || styles.draft}`}>
      {label}
    </span>
  )
}
