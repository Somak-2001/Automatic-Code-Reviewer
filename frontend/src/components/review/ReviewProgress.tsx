import { Spinner } from '../ui/Spinner'
import type { ReviewJobStatus, StageStatus } from '../../types/api'

interface ReviewProgressProps {
  status: ReviewJobStatus
  repositoryUrl: string
}

interface StageInfo {
  key: keyof ReviewJobStatus['stages']
  label: string
  description: string
}

const STAGES: StageInfo[] = [
  { key: 'repository', label: 'Repository Clone', description: 'Cloning and sampling source files' },
  { key: 'static_analysis', label: 'Static Analysis', description: 'Pattern-based secret and code signal detection' },
  { key: 'openai', label: 'OpenAI Review', description: 'Security-focused analysis' },
  { key: 'anthropic', label: 'Anthropic Review', description: 'Maintainability & code quality analysis' },
  { key: 'gemini', label: 'Gemini Review', description: 'Performance analysis' },
  { key: 'aggregation', label: 'Consensus Analysis', description: 'Deduplicating and scoring multi-provider findings' },
  { key: 'report', label: 'Final Report', description: 'Generating structured report' },
]

function StageIcon({ status }: { status: StageStatus }) {
  switch (status) {
    case 'completed':
      return <span className="text-green-400 text-lg">✓</span>
    case 'running':
      return <Spinner size="sm" />
    case 'failed':
      return <span className="text-red-400 text-lg">✗</span>
    case 'skipped':
      return <span className="text-gray-600 text-lg">–</span>
    default:
      return <span className="text-gray-700 text-lg">○</span>
  }
}

function StageRow({ stage, status }: { stage: StageInfo; status: StageStatus }) {
  const textColor =
    status === 'completed'
      ? 'text-gray-200'
      : status === 'running'
      ? 'text-indigo-300'
      : status === 'failed'
      ? 'text-red-300'
      : status === 'skipped'
      ? 'text-gray-600'
      : 'text-gray-600'

  const borderColor =
    status === 'running'
      ? 'border-indigo-500/30 bg-indigo-900/10'
      : status === 'completed'
      ? 'border-green-700/20 bg-green-900/5'
      : status === 'failed'
      ? 'border-red-700/30 bg-red-900/10'
      : status === 'skipped'
      ? 'border-gray-800/50'
      : 'border-gray-800/30'

  return (
    <div className={`flex items-start gap-4 p-3.5 rounded-lg border ${borderColor} transition-all duration-300`}>
      <div className="mt-0.5 w-5 flex justify-center shrink-0">
        <StageIcon status={status} />
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium ${textColor}`}>{stage.label}</p>
        <p className="text-xs text-gray-600 mt-0.5">{stage.description}</p>
      </div>
      <div className="shrink-0">
        <span
          className={`text-xs font-medium px-2 py-0.5 rounded-full ${
            status === 'running'
              ? 'bg-indigo-900/50 text-indigo-300'
              : status === 'completed'
              ? 'bg-green-900/40 text-green-400'
              : status === 'failed'
              ? 'bg-red-900/40 text-red-400'
              : status === 'skipped'
              ? 'bg-gray-800 text-gray-600'
              : 'bg-gray-900 text-gray-700'
          }`}
        >
          {status}
        </span>
      </div>
    </div>
  )
}

export function ReviewProgress({ status, repositoryUrl }: ReviewProgressProps) {
  const repoName = repositoryUrl.replace(/\/$/, '').split('/').slice(-2).join('/')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-1">
          <span>Reviewing</span>
          <code className="text-indigo-400 bg-indigo-900/20 px-1.5 py-0.5 rounded text-xs font-mono">
            {repoName}
          </code>
        </div>

        {/* Progress bar */}
        <div className="mt-3">
          <div className="flex justify-between text-xs text-gray-600 mb-1.5">
            <span>Progress</span>
            <span>{status.progress}%</span>
          </div>
          <div className="h-1.5 w-full bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-600 to-indigo-400 rounded-full transition-all duration-500"
              style={{ width: `${status.progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Stage list */}
      <div className="space-y-2">
        {STAGES.map((stage) => (
          <StageRow
            key={stage.key}
            stage={stage}
            status={status.stages[stage.key]}
          />
        ))}
      </div>

      {/* Error state */}
      {status.status === 'failed' && status.error && (
        <div className="flex items-start gap-3 p-4 rounded-lg bg-red-900/20 border border-red-700/40">
          <span className="text-red-400 shrink-0">⚠</span>
          <div>
            <p className="text-sm font-medium text-red-300">Review Failed</p>
            <p className="text-sm text-red-400/80 mt-1">{status.error}</p>
          </div>
        </div>
      )}
    </div>
  )
}

