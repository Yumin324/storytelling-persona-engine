import { apiRequest } from "./client.js"

export function startProduction(sessionId) {
  return apiRequest(`/api/production/${sessionId}/start`, { method: "POST" })
}

export function getProductionJob(jobId) {
  return apiRequest(`/api/production/jobs/${jobId}`)
}

export function getProductionScenes(jobId) {
  return apiRequest(`/api/production/jobs/${jobId}/scenes`)
}

export function retryScene(sceneId) {
  return apiRequest(`/api/production/scenes/${sceneId}/retry`, { method: "POST" })
}

export function sceneDownloadUrl(sceneId) {
  return `${import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}/api/production/scenes/${sceneId}/download`
}
