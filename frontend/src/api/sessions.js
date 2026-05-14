import { apiRequest } from "./client.js"

export function createSession(payload) {
  return apiRequest("/api/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function listSessions() {
  return apiRequest("/api/sessions")
}

export function getSession(sessionId) {
  return apiRequest(`/api/sessions/${sessionId}`)
}

export function updateSession(sessionId, payload) {
  return apiRequest(`/api/sessions/${sessionId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  })
}

export function deleteSession(sessionId) {
  return apiRequest(`/api/sessions/${sessionId}`, { method: "DELETE" })
}

export async function uploadProductImages(sessionId, files) {
  const formData = new FormData()
  Array.from(files).forEach((file) => formData.append("files", file))

  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}/api/sessions/${sessionId}/upload-product-images`, {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.message || "Product upload failed.")
  }

  return response.json()
}

export function removeProductImage(sessionId, imagePath) {
  return apiRequest(`/api/sessions/${sessionId}/product-images?image_path=${encodeURIComponent(imagePath)}`, {
    method: "DELETE",
  })
}

export function generateReferences(sessionId) {
  return apiRequest(`/api/sessions/${sessionId}/generate-references`, { method: "POST" })
}

export function getReferenceJob(sessionId, jobId) {
  return apiRequest(`/api/sessions/${sessionId}/reference-job/${jobId}`)
}

export function generateScript(sessionId) {
  return apiRequest(`/api/sessions/${sessionId}/generate-script`, { method: "POST" })
}

export function saveScript(sessionId, scriptJson) {
  return apiRequest(`/api/sessions/${sessionId}/script`, {
    method: "PUT",
    body: JSON.stringify({ script_json: scriptJson }),
  })
}
