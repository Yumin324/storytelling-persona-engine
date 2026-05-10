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
