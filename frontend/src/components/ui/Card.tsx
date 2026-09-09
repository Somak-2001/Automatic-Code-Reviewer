import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  padding?: 'sm' | 'md' | 'lg'
}

export function Card({ children, className = '', padding = 'md' }: CardProps) {
  const padClass = { sm: 'p-4', md: 'p-5', lg: 'p-6' }[padding]
  return (
    <div
      className={`bg-[#161b27] border border-gray-700/40 rounded-xl ${padClass} ${className}`}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`mb-4 ${className}`}>{children}</div>
}

export function CardTitle({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <h3 className={`text-sm font-semibold text-gray-400 uppercase tracking-widest ${className}`}>
      {children}
    </h3>
  )
}

