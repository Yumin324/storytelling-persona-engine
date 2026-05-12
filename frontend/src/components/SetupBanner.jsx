import React, { useEffect, useState } from "react"

import { healthCheck } from "../api/client.js"

export default function SetupBanner() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState("")

  useEffect(() => {
    let isMounted = true
    healthCheck()
      .then((data) => {
        if (isMounted) setHealth(data)
      })
      .catch((requestError) => {
        if (isMounted) setError(requestError.message)
      })
    return () => {
      isMounted = false
    }
  }, [])

  if (error) {
    return (
      <Banner tone="error" title="Backend is not reachable">
        {error}
      </Banner>
    )
  }

  return null
}

function Banner({ tone, title, children }) {
  const classes =
    tone === "error"
      ? "border-red-100 bg-red-50 text-red-900"
      : "border-amber-100 bg-amber-50 text-amber-950"

  return (
    <div className={`border-b ${classes}`}>
      <div className="mx-auto max-w-[1180px] px-6 py-3">
        <p className="text-sm leading-6">
          <span className="font-semibold">{title}:</span> {children}
        </p>
      </div>
    </div>
  )
}
