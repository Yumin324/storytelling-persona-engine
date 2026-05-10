const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"

export function fileUrl(relativePath) {
  if (!relativePath) return null
  return `${API_BASE_URL}/api/files/${relativePath}`
}

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(extractMessage(body) || `Request failed with status ${response.status}`)
  }

  if (response.status === 204) return null
  return response.json()
}

function extractMessage(body) {
  if (!body) return null
  if (typeof body.detail === "string") return body.detail
  if (body.detail?.message) return body.detail.message
  if (Array.isArray(body.detail)) return body.detail.map((item) => item.msg).join(" ")
  return body.message || null
}
