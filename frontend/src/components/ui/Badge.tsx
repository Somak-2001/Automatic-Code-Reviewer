import type { Severity } from '../../types/api'

interface BadgeProps {
  label: string
  variant?: 'severity' | 'category' | 'provider' | 'status' | 'default'
  severity?: Severity
  className?: string
}

const severityClasses: Record<Severity, string> = {
  critical: 'bg-red-900/60 text-red-300 border border-red-700/50',
  high: 'bg-orange-900/60 text-orange-300 border border-orange-700/50',
  medium: 'bg-yellow-900/60 text-yellow-300 border border-yellow-700/50',
  low: 'bg-blue-900/60 text-blue-300 border border-blue-700/50',
}

const severityDotClasses: Record<Severity, string> = {
  critical: 'bg-red-400',
  high: 'bg-orange-400',
  medium: 'bg-yellow-400',
  low: 'bg-blue-400',
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide ${severityClasses[severity]}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${severityDotClasses[severity]}`} />
      {severity}
    </span>
  )
}

export function Badge({ label, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-surface-2 text-gray-300 border border-gray-700/50 ${className}`}
    >
      {label}
    </span>
  )
}

export function CategoryBadge({ category }: { category: string }) {
  const colors: Record<string, string> = {
    security: 'bg-red-900/40 text-red-300 border-red-700/30',
    correctness: 'bg-orange-900/40 text-orange-300 border-orange-700/30',
    performance: 'bg-purple-900/40 text-purple-300 border-purple-700/30',
    maintainability: 'bg-blue-900/40 text-blue-300 border-blue-700/30',
    testing: 'bg-green-900/40 text-green-300 border-green-700/30',
    architecture: 'bg-indigo-900/40 text-indigo-300 border-indigo-700/30',
  }
  const cls = colors[category] ?? 'bg-gray-800 text-gray-400 border-gray-700/30'
  return (
    <span className={`inline-flex px-2.5 py-0.5 rounded-md text-xs font-medium border ${cls}`}>
      {category}
    </span>
  )
}

export function ProviderBadge({
  provider,
  detected,
}: {
  provider: string
  detected: boolean
}) {
  const name = provider.charAt(0).toUpperCase() + provider.slice(1)
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${
        detected
          ? 'bg-green-900/30 text-green-300 border-green-700/40'
          : 'bg-gray-800/50 text-gray-500 border-gray-700/30 line-through opacity-60'
      }`}
    >
      <span>{detected ? '✓' : '✗'}</span>
      {name}
    </span>
  )
}

