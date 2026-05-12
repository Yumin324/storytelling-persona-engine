import React from "react"

export default function ErrorPanel({ message }) {
  if (!message) return null

  return (
    <div className="rounded-3xl border border-red-100 bg-red-50 p-5 text-sm leading-6 text-red-800 shadow-sm">
      {message}
    </div>
  )
}
