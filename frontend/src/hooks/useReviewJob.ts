import { useCallback, useEffect, useRef, useState } from 'react'
import { getReviewReport, getReviewStatus } from '../services/api'
import type { ReviewJobStatus, ReviewReport } from '../types/api'

const POLL_INTERVAL_MS = 2000 // poll every 2 seconds

interface UseReviewJobResult {
  status: ReviewJobStatus | null
  report: ReviewReport | null
  error: string | null
  isPolling: boolean
  stopPolling: () => void
}

export function useReviewJob(reviewId: string | null): UseReviewJobResult {
  const [status, setStatus] = useState<ReviewJobStatus | null>(null)
  const [report, setReport] = useState<ReviewReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const activeRef = useRef(true)

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    setIsPolling(false)
  }, [])

  useEffect(() => {
    if (!reviewId) return

    activeRef.current = true
    setIsPolling(true)
    setError(null)
    setReport(null)

    const poll = async () => {
      if (!activeRef.current) return
      try {
        const jobStatus = await getReviewStatus(reviewId)
        if (!activeRef.current) return
        setStatus(jobStatus)

        if (jobStatus.status === 'completed') {
          // Fetch the full report
          try {
            const { report: fullReport } = await getReviewReport(reviewId)
            if (!activeRef.current) return
            setReport(fullReport)
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load report')
          }
          stopPolling()
          return
        }

        if (jobStatus.status === 'failed') {
          setError(jobStatus.error || 'Review failed for an unknown reason.')
          stopPolling()
          return
        }
      } catch (err) {
        if (!activeRef.current) return
        // Network errors during polling — show but keep polling (transient)
        setError(err instanceof Error ? err.message : 'Network error while polling status')
      }
    }

    // Poll immediately, then on interval
    poll()
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS)

    return () => {
      activeRef.current = false
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [reviewId, stopPolling])

  return { status, report, error, isPolling, stopPolling }
}

