import React from "react"

export default function ProgressBar({ value = 0 }) {
  const clamped = Math.max(0, Math.min(100, Number(value) || 0))

  return (
    <div className="flex items-center gap-4">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-muted">
        <div className="h-full rounded-full bg-neutral-950 transition-all" style={{ width: `${clamped}%` }} />
      </div>
      <span className="w-10 text-right text-sm font-medium text-neutral-700">{clamped}%</span>
    </div>
  )
}
