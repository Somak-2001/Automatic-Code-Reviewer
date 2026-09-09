import type {
  BackendConfig,
  ReviewJobStatus,
  ReviewReport,
  ReviewStartResponse,
} from '../types/api'

const BASE = '' // Uses Vite proxy; empty string means relative URLs

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail: string = `HTTP ${res.status}`
    try {
      const body = await res.json()
      detail = body?.detail?.message ?? body?.detail ?? detail
    } catch {
      // ignore JSON parse errors for error body
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export async function fetchConfig(): Promise<BackendConfig> {
  const res = await fetch(`${BASE}/api/config`)
  return handleResponse<BackendConfig>(res)
}

export async function startReview(repositoryUrl: string): Promise<ReviewStartResponse> {
  const res = await fetch(`${BASE}/api/reviews`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repository_url: repositoryUrl }),
  })
  return handleResponse<ReviewStartResponse>(res)
}

export async function getReviewStatus(reviewId: string): Promise<ReviewJobStatus> {
  const res = await fetch(`${BASE}/api/reviews/${reviewId}`)
  return handleResponse<ReviewJobStatus>(res)
}

export async function getReviewReport(reviewId: string): Promise<{ review_id: string; report: ReviewReport }> {
  const res = await fetch(`${BASE}/api/reviews/${reviewId}/report`)
  return handleResponse<{ review_id: string; report: ReviewReport }>(res)
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/health`)
    return res.ok
  } catch {
    return false
  }
}

