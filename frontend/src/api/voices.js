import { apiRequest } from "./client.js"

export function listVoices() {
  return apiRequest("/api/voices")
}
