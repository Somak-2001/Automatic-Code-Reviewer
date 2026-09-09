import { useState } from 'react'
import type { ReviewReport, Severity } from '../../types/api'
import { CategoryBadge, ProviderBadge, SeverityBadge } from '../ui/Badge'
import { Card, CardTitle } from '../ui/Card'
import { FindingsList } from './FindingsList'

interface ReviewReportViewProps {
  report: ReviewReport
  repositoryUrl: string
  onNewReview: () => void
}

function RiskGauge({ score }: { score: number }) {
  const color =
    score >= 75
      ? 'from-red-600 to-red-400'
      : score >= 50
      ? 'from-orange-600 to-orange-400'
      : score >= 25
      ? 'from-yellow-600 to-yellow-400'
      : 'from-green-600 to-green-400'

  const label =
    score >= 75 ? 'High Risk' : score >= 50 ? 'Elevated Risk' : score >= 25 ? 'Moderate' : 'Low Risk'

  return (
    <div className="text-center">
      <div className="relative inline-flex items-center justify-center">
        <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="40" fill="none" stroke="#1e2535" strokeWidth="10" />
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            strokeWidth="10"
            strokeDasharray={`${score * 2.51} 251`}
            strokeLinecap="round"
            className={`stroke-current ${score >= 75 ? 'text-red-500' : score >= 50 ? 'text-orange-500' : score >= 25 ? 'text-yellow-500' : 'text-green-500'}`}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-gray-100">{score}</span>
          <span className="text-xs text-gray-500">/100</span>
        </div>
      </div>
      <p className={`text-sm font-semibold mt-2 bg-gradient-to-r ${color} bg-clip-text text-transparent`}>
        {label}
      </p>
    </div>
  )
}

type Tab = 'overview' | 'findings' | 'providers' | 'consensus' | 'static'

export function ReviewReportView({ report, repositoryUrl, onNewReview }: ReviewReportViewProps) {
  const [activeTab, setActiveTab] = useState<Tab>('overview')

  const severityCounts: Record<Severity, number> = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  }
  for (const issue of report.top_issues) {
    severityCounts[issue.severity]++
  }

  const severityBarColors: Record<Severity, string> = {
    critical: 'bg-red-500',
    high: 'bg-orange-500',
    medium: 'bg-yellow-500',
    low: 'bg-blue-500',
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'findings', label: `Findings (${report.top_issues.length})` },
    { key: 'providers', label: 'Providers' },
    { key: 'consensus', label: 'Consensus' },
    { key: 'static', label: `Static Signals (${report.static_signals.length})` },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">{report.repo_name}</h1>
          <p className="text-sm text-gray-500 mt-1">
            Branch: <span className="text-gray-400 font-mono">{report.branch}</span>
            {' · '}
            Generated {new Date(report.generated_at).toLocaleString()}
          </p>
          {/* Provider status pills */}
          <div className="flex flex-wrap gap-2 mt-3">
            {(['openai', 'anthropic', 'gemini'] as const).map((p) => {
              const attempted = report.providers_attempted.includes(p)
              const succeeded = report.providers_succeeded.includes(p)
              const failed = report.providers_failed.includes(p)
              if (!attempted) return (
                <span key={p} className="text-xs px-2.5 py-1 rounded-md bg-gray-800/50 text-gray-600 border border-gray-700/30">
                  {p} — not configured
                </span>
              )
              return (
                <span
                  key={p}
                  className={`text-xs px-2.5 py-1 rounded-md border font-medium ${
                    succeeded
                      ? 'bg-green-900/30 text-green-300 border-green-700/30'
                      : 'bg-red-900/30 text-red-300 border-red-700/30'
                  }`}
                >
                  {succeeded ? '✓' : '✗'} {p}
                  {failed ? ' (failed)' : ''}
                </span>
              )
            })}
          </div>
        </div>
        <button
          onClick={onNewReview}
          className="text-sm px-4 py-2 bg-[#1e2535] hover:bg-[#252d3f] border border-gray-700/50 text-gray-300 rounded-lg transition-colors shrink-0"
        >
          New Review
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-700/40 pb-px overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors whitespace-nowrap ${
              activeTab === tab.key
                ? 'text-indigo-400 border-b-2 border-indigo-500 bg-indigo-900/10'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview tab */}
      {activeTab === 'overview' && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Risk score */}
            <Card className="flex flex-col items-center justify-center py-4">
              <CardTitle className="mb-4 text-center">Risk Score</CardTitle>
              <RiskGauge score={report.risk_score} />
            </Card>

            {/* Severity breakdown */}
            <Card>
              <CardTitle className="mb-4">Findings by Severity</CardTitle>
              <div className="space-y-2.5">
                {(['critical', 'high', 'medium', 'low'] as Severity[]).map((sev) => (
                  <div key={sev} className="flex items-center gap-2">
                    <span className="w-16 text-xs text-gray-500 capitalize">{sev}</span>
                    <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${severityBarColors[sev]} rounded-full`}
                        style={{
                          width: report.top_issues.length
                            ? `${(severityCounts[sev] / report.top_issues.length) * 100}%`
                            : '0%',
                        }}
                      />
                    </div>
                    <span className="w-6 text-right text-xs text-gray-400 font-mono">
                      {severityCounts[sev]}
                    </span>
                  </div>
                ))}
              </div>
            </Card>

            {/* Summary */}
            <Card>
              <CardTitle className="mb-3">Summary</CardTitle>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Total findings</span>
                  <span className="text-gray-200 font-semibold">{report.top_issues.length}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Static signals</span>
                  <span className="text-gray-200 font-semibold">{report.static_signals.length}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Providers used</span>
                  <span className="text-gray-200 font-semibold">{report.providers_succeeded.length}</span>
                </div>
              </div>
            </Card>
          </div>

          {/* Executive summary */}
          <Card>
            <CardTitle className="mb-3">Executive Summary</CardTitle>
            <p className="text-sm text-gray-300 leading-relaxed">{report.executive_summary}</p>
          </Card>

          {/* Next steps */}
          {report.next_steps.length > 0 && (
            <Card>
              <CardTitle className="mb-3">Recommended Next Steps</CardTitle>
              <ol className="space-y-2">
                {report.next_steps.map((step, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-gray-300">
                    <span className="shrink-0 w-6 h-6 rounded-full bg-indigo-900/50 text-indigo-400 text-xs flex items-center justify-center font-semibold">
                      {i + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </Card>
          )}
        </div>
      )}

      {/* Findings tab */}
      {activeTab === 'findings' && (
        <FindingsList
          issues={report.top_issues}
          providersAttempted={report.providers_attempted}
        />
      )}

      {/* Providers tab */}
      {activeTab === 'providers' && (
        <div className="space-y-4">
          {report.provider_results.map((result) => (
            <Card key={result.provider}>
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex items-center gap-3">
                  <ProviderBadge provider={result.provider} detected={result.status === 'completed'} />
                  <span className="text-xs text-gray-500 capitalize">Role: {result.role}</span>
                </div>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    result.status === 'completed'
                      ? 'bg-green-900/40 text-green-400'
                      : result.status === 'failed'
                      ? 'bg-red-900/40 text-red-400'
                      : 'bg-gray-800 text-gray-500'
                  }`}
                >
                  {result.status}
                </span>
              </div>

              {result.error ? (
                <p className="text-sm text-red-400 bg-red-900/20 p-3 rounded-lg">{result.error}</p>
              ) : (
                <>
                  {result.summary && (
                    <p className="text-sm text-gray-400 mb-3">{result.summary}</p>
                  )}
                  {result.strengths.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs text-gray-600 mb-1.5">Strengths noted:</p>
                      <ul className="space-y-1">
                        {result.strengths.slice(0, 5).map((s, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-gray-400">
                            <span className="text-green-500 shrink-0">+</span>
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <p className="text-xs text-gray-600">
                    Issues found: <span className="text-gray-400 font-semibold">{result.issues_count}</span>
                  </p>
                </>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Consensus tab */}
      {activeTab === 'consensus' && (
        <div className="space-y-4">
          {report.consensus.map((section, i) => (
            <Card key={i}>
              <h3 className="text-sm font-semibold text-gray-300 mb-3">{section.headline}</h3>
              <ul className="space-y-2">
                {section.details.map((d, j) => (
                  <li key={j} className="text-sm text-gray-400 flex items-start gap-2">
                    <span className="text-indigo-500 shrink-0">·</span>
                    {d}
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      )}

      {/* Static signals tab */}
      {activeTab === 'static' && (
        <div className="space-y-3">
          {report.static_signals.length === 0 ? (
            <div className="text-center py-10 text-gray-600">
              <p>No static signals detected.</p>
            </div>
          ) : (
            report.static_signals.map((signal, i) => (
              <div
                key={i}
                className="flex items-start gap-3 p-3.5 bg-[#161b27] border border-gray-700/40 rounded-xl"
              >
                <SeverityBadge severity={signal.severity} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-mono text-indigo-300 truncate">
                    {signal.file_path}
                    {signal.line_hint ? `:${signal.line_hint}` : ''}
                  </p>
                  <p className="text-sm text-gray-300 mt-1">{signal.message}</p>
                  <p className="text-xs text-gray-600 mt-0.5">{signal.kind}</p>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

