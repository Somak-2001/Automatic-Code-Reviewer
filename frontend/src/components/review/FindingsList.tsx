import { useState } from 'react'
import type { Category, ReviewIssue, Severity } from '../../types/api'
import { CategoryBadge, ProviderBadge, SeverityBadge } from '../ui/Badge'
import { FindingDetail } from './FindingDetail'

interface FindingsListProps {
  issues: ReviewIssue[]
  providersAttempted: string[]
}

type FilterState = {
  severity: Severity | 'all'
  category: Category | 'all'
  search: string
}

const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}

export function FindingsList({ issues, providersAttempted }: FindingsListProps) {
  const [selected, setSelected] = useState<ReviewIssue | null>(null)
  const [filters, setFilters] = useState<FilterState>({
    severity: 'all',
    category: 'all',
    search: '',
  })

  const filtered = issues.filter((issue) => {
    if (filters.severity !== 'all' && issue.severity !== filters.severity) return false
    if (filters.category !== 'all' && issue.category !== filters.category) return false
    if (filters.search) {
      const q = filters.search.toLowerCase()
      if (
        !issue.title.toLowerCase().includes(q) &&
        !issue.file_path.toLowerCase().includes(q) &&
        !issue.summary.toLowerCase().includes(q)
      ) {
        return false
      }
    }
    return true
  })

  // Count by severity
  const counts: Record<string, number> = {}
  for (const issue of issues) {
    counts[issue.severity] = (counts[issue.severity] ?? 0) + 1
  }

  const allSeverities: Severity[] = ['critical', 'high', 'medium', 'low']
  const allCategories: Category[] = [
    'security', 'correctness', 'performance', 'maintainability', 'testing', 'architecture',
  ]

  if (selected) {
    return (
      <FindingDetail
        issue={selected}
        providersAttempted={providersAttempted}
        onBack={() => setSelected(null)}
      />
    )
  }

  return (
    <div className="space-y-4">
      {/* Severity summary pills */}
      <div className="flex flex-wrap gap-2">
        {allSeverities.map((sev) => (
          <button
            key={sev}
            onClick={() => setFilters((f) => ({ ...f, severity: f.severity === sev ? 'all' : sev }))}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${
              filters.severity === sev
                ? 'bg-indigo-600/30 border-indigo-500/50 text-indigo-300'
                : 'bg-[#1e2535] border-gray-700/40 text-gray-400 hover:border-gray-600'
            }`}
          >
            <SeverityBadge severity={sev} />
            <span className="text-gray-500">{counts[sev] ?? 0}</span>
          </button>
        ))}
        <div className="h-8 w-px bg-gray-700/40 mx-1 self-center" />
        {allCategories.map((cat) => {
          const catCount = issues.filter((i) => i.category === cat).length
          if (catCount === 0) return null
          return (
            <button
              key={cat}
              onClick={() => setFilters((f) => ({ ...f, category: f.category === cat ? 'all' : cat }))}
              className={`text-xs px-2.5 py-1.5 rounded-lg border transition-all ${
                filters.category === cat
                  ? 'bg-indigo-600/30 border-indigo-500/50 text-indigo-300'
                  : 'bg-[#1e2535] border-gray-700/40 text-gray-400 hover:border-gray-600'
              }`}
            >
              {cat} ({catCount})
            </button>
          )
        })}
      </div>

      {/* Search */}
      <div className="relative">
        <span className="absolute inset-y-0 left-3 flex items-center text-gray-600 text-sm">🔍</span>
        <input
          type="text"
          value={filters.search}
          onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
          placeholder="Search findings…"
          className="w-full bg-[#1e2535] border border-gray-700/50 rounded-lg pl-9 pr-4 py-2.5 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
        />
      </div>

      {/* Results count */}
      <p className="text-xs text-gray-600">
        Showing {filtered.length} of {issues.length} finding{issues.length !== 1 ? 's' : ''}
        {filters.severity !== 'all' || filters.category !== 'all' || filters.search
          ? ' (filtered)'
          : ''}
      </p>

      {/* Findings list */}
      {filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-600">
          <p className="text-3xl mb-3">🔍</p>
          <p className="text-sm">No findings match the current filters.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((issue, idx) => (
            <button
              key={idx}
              onClick={() => setSelected(issue)}
              className="w-full text-left p-4 bg-[#161b27] hover:bg-[#1e2535] border border-gray-700/40 hover:border-gray-600/60 rounded-xl transition-all group"
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5 shrink-0">
                  <SeverityBadge severity={issue.severity} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-gray-200 group-hover:text-white transition-colors">
                      {issue.title}
                    </p>
                    <span className="text-xs text-gray-600 group-hover:text-indigo-400 transition-colors shrink-0">
                      →
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 font-mono truncate">
                    {issue.file_path}
                    {issue.cell_number != null ? ` · Cell ${issue.cell_number}` : (issue.line_hint ? ` · ${issue.line_hint}` : '')}
                  </p>
                  <p className="text-xs text-gray-600 mt-1.5 line-clamp-2">{issue.summary}</p>
                  <div className="flex items-center gap-2 mt-2.5 flex-wrap">
                    <CategoryBadge category={issue.category} />
                    <span className="text-xs text-gray-600">
                      {Math.round(issue.confidence * 100)}% confidence
                    </span>
                    <div className="flex gap-1 ml-1">
                      {issue.detected_by.map((p) => (
                        <ProviderBadge key={p} provider={p} detected={true} />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

