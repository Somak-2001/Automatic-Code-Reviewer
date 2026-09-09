import { useEffect } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { useReviewJob } from '../hooks/useReviewJob'
import { ReviewProgress } from '../components/review/ReviewProgress'
import { ReviewReportView } from '../components/review/ReviewReport'
import { Spinner } from '../components/ui/Spinner'

export function ReviewPage() {
  const { reviewId } = useParams<{ reviewId: string }>()
  const location = useLocation()
  const navigate = useNavigate()

  const repositoryUrl: string =
    (location.state as { repositoryUrl?: string })?.repositoryUrl ?? ''

  const { status, report, error, isPolling } = useReviewJob(reviewId ?? null)

  // If review_id is missing, go home
  useEffect(() => {
    if (!reviewId) navigate('/')
  }, [reviewId, navigate])

  const handleNewReview = () => navigate('/')

  return (
    <div className="min-h-screen bg-[#0f1117]">
      {/* Top bar */}
      <header className="border-b border-gray-800/60 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-600 to-indigo-400 flex items-center justify-center text-white text-sm font-bold"
            >
              CR
            </button>
            <span className="text-gray-400 font-medium text-sm">CodeReview AI</span>
          </div>
          {status && (
            <span className="text-xs text-gray-600 font-mono">
              {reviewId}
            </span>
          )}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Initial loading */}
        {!status && !error && (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <Spinner size="lg" />
            <p className="text-sm text-gray-500">Connecting to review…</p>
          </div>
        )}

        {/* Fatal network error before we got any status */}
        {!status && error && (
          <div className="flex flex-col items-center gap-6 py-16">
            <div className="p-5 rounded-xl bg-red-900/20 border border-red-700/30 max-w-lg w-full">
              <p className="text-sm font-medium text-red-300">⚠ Failed to connect</p>
              <p className="text-sm text-red-400/70 mt-2">{error}</p>
            </div>
            <button
              onClick={handleNewReview}
              className="text-sm px-4 py-2 bg-[#1e2535] border border-gray-700 text-gray-300 rounded-lg hover:bg-[#252d3f] transition-colors"
            >
              ← Back to Home
            </button>
          </div>
        )}

        {/* Review in progress */}
        {status && status.status !== 'completed' && status.status !== 'failed' && (
          <div className="max-w-xl mx-auto">
            <div className="mb-6">
              <h2 className="text-xl font-bold text-gray-100">Review In Progress</h2>
              <p className="text-sm text-gray-500 mt-1">
                This usually takes 1–3 minutes. The page will update automatically.
              </p>
            </div>
            <div className="bg-[#161b27] border border-gray-700/40 rounded-2xl p-6">
              <ReviewProgress
                status={status}
                repositoryUrl={repositoryUrl || status.repository_url}
              />
            </div>
          </div>
        )}

        {/* Review failed */}
        {status && status.status === 'failed' && (
          <div className="max-w-xl mx-auto space-y-6">
            <div className="bg-[#161b27] border border-gray-700/40 rounded-2xl p-6">
              <ReviewProgress
                status={status}
                repositoryUrl={repositoryUrl || status.repository_url}
              />
            </div>
            <button
              onClick={handleNewReview}
              className="text-sm px-4 py-2 bg-[#1e2535] border border-gray-700 text-gray-300 rounded-lg hover:bg-[#252d3f] transition-colors"
            >
              ← Try a different repository
            </button>
          </div>
        )}

        {/* Report ready */}
        {status && status.status === 'completed' && report && (
          <ReviewReportView
            report={report}
            repositoryUrl={repositoryUrl || status.repository_url}
            onNewReview={handleNewReview}
          />
        )}

        {/* Completed but report fetch error */}
        {status && status.status === 'completed' && !report && error && (
          <div className="flex flex-col items-center gap-4 py-16">
            <div className="p-4 rounded-xl bg-red-900/20 border border-red-700/30">
              <p className="text-sm font-medium text-red-300">Review completed but report failed to load</p>
              <p className="text-sm text-red-400/70 mt-1">{error}</p>
            </div>
            <button
              onClick={handleNewReview}
              className="text-sm px-4 py-2 bg-[#1e2535] border border-gray-700 text-gray-300 rounded-lg hover:bg-[#252d3f] transition-colors"
            >
              ← Back to Home
            </button>
          </div>
        )}
      </main>
    </div>
  )
}

