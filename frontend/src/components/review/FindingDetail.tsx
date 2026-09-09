import type { ReviewIssue } from '../../types/api'
import { CategoryBadge, ProviderBadge, SeverityBadge } from '../ui/Badge'
import { Card } from '../ui/Card'

interface FindingDetailProps {
  issue: ReviewIssue
  providersAttempted: string[]
  onBack: () => void
}

export function FindingDetail({ issue, providersAttempted, onBack }: FindingDetailProps) {
  const allProviders = ['openai', 'anthropic', 'gemini']
  const confidence = Math.round(issue.confidence * 100)

  const confidenceColor =
    confidence >= 70
      ? 'text-green-400'
      : confidence >= 40
      ? 'text-yellow-400'
      : 'text-red-400'

  return (
    <div className="space-y-5">
      {/* Back button */}
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-300 transition-colors group"
      >
        <span className="group-hover:-translate-x-0.5 transition-transform">←</span>
        Back to findings
      </button>

      {/* Header */}
      <div>
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <SeverityBadge severity={issue.severity} />
          <CategoryBadge category={issue.category} />
        </div>
        <h2 className="text-xl font-semibold text-gray-100">{issue.title}</h2>
      </div>

      {/* Key metadata grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card padding="sm">
          <p className="text-xs text-gray-600 mb-1">Severity</p>
          <SeverityBadge severity={issue.severity} />
        </Card>
        <Card padding="sm">
          <p className="text-xs text-gray-600 mb-1">Confidence</p>
          <p className={`text-lg font-bold ${confidenceColor}`}>{confidence}%</p>
        </Card>
        <Card padding="sm">
          <p className="text-xs text-gray-600 mb-1">Consensus</p>
          <p className="text-sm font-semibold text-gray-200">
            {issue.detected_by.length}/{providersAttempted.length} providers
          </p>
        </Card>
        <Card padding="sm">
          <p className="text-xs text-gray-600 mb-1">Category</p>
          <CategoryBadge category={issue.category} />
        </Card>
      </div>

      {/* File location */}
      <Card>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-gray-600 uppercase tracking-widest">Location</p>
          {issue.file_path.endsWith('.ipynb') && (
            <span className="text-xs px-2 py-0.5 rounded bg-purple-900/40 text-purple-300 border border-purple-700/30 font-medium">
              Jupyter Notebook
            </span>
          )}
        </div>
        <p className="text-sm font-mono text-indigo-300">{issue.file_path}</p>
        <div className="flex flex-wrap items-center gap-2 mt-2">
          {issue.cell_number != null && (
            <span className="text-xs px-2.5 py-0.5 rounded bg-indigo-900/50 text-indigo-300 border border-indigo-700/50 font-mono font-semibold">
              Cell {issue.cell_number}
            </span>
          )}
          {(issue.line_hint || issue.line_start) && (
            <span className="text-xs text-gray-400 font-mono">
              {issue.line_hint || (issue.line_start ? `Line ${issue.line_start}${issue.line_end ? `–${issue.line_end}` : ''}` : '')}
            </span>
          )}
        </div>
      </Card>

      {/* Provider consensus */}
      <Card>
        <p className="text-xs text-gray-600 uppercase tracking-widest mb-3">Detected By</p>
        <div className="flex flex-wrap gap-2">
          {allProviders.map((provider) => {
            const wasAttempted = providersAttempted.includes(provider)
            const detected = issue.detected_by.includes(provider as 'openai' | 'anthropic' | 'gemini')
            if (!wasAttempted && !detected) return null
            return (
              <ProviderBadge key={provider} provider={provider} detected={detected} />
            )
          })}
        </div>
        <p className="text-xs text-gray-600 mt-3">
          {issue.detected_by.length > 1
            ? `${issue.detected_by.length} providers agree on this finding — higher confidence.`
            : 'Detected by a single provider — lower confidence; verify before acting.'}
        </p>
      </Card>

      {/* Summary */}
      <Card>
        <p className="text-xs text-gray-600 uppercase tracking-widest mb-2">Explanation</p>
        <p className="text-sm text-gray-300 leading-relaxed">{issue.summary}</p>
      </Card>

      {/* Evidence */}
      {issue.evidence && (
        <Card>
          <p className="text-xs text-gray-600 uppercase tracking-widest mb-2">Evidence</p>
          <p className="text-sm text-gray-400 leading-relaxed font-mono bg-[#0d1117] p-3 rounded-lg border border-gray-800">
            {issue.evidence}
          </p>
        </Card>
      )}

      {/* Recommendation */}
      <Card>
        <p className="text-xs text-gray-600 uppercase tracking-widest mb-2">Recommended Fix</p>
        <p className="text-sm text-gray-300 leading-relaxed">{issue.recommendation}</p>
      </Card>

      {/* Reviewer role */}
      {issue.reviewer_role && (
        <p className="text-xs text-gray-600">
          Primary reviewer role:{' '}
          <span className="text-gray-400 capitalize">{issue.reviewer_role}</span>
        </p>
      )}
    </div>
  )
}

