import { apiRequest } from "./client.js"

export function listPersonas() {
  return apiRequest("/api/personas")
}

export function createPersona(payload) {
  return apiRequest("/api/personas", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function deletePersona(personaId) {
  return apiRequest(`/api/personas/${personaId}`, { method: "DELETE" })
}

export function generatePersonaAssets(personaId) {
  return apiRequest(`/api/personas/${personaId}/generate-assets`, { method: "POST" })
}

export function getPersonaJob(jobId) {
  return apiRequest(`/api/personas/jobs/${jobId}`)
}
