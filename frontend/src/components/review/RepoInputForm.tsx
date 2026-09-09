import { useState } from 'react'
import { Spinner } from '../ui/Spinner'

interface RepoInputFormProps {
  onSubmit: (url: string) => Promise<void>
  isLoading: boolean
  error: string | null
}

export function RepoInputForm({ onSubmit, isLoading, error }: RepoInputFormProps) {
  const [url, setUrl] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)

  const validate = (value: string): string | null => {
    if (!value.trim()) return 'Please enter a GitHub repository URL.'
    if (!value.startsWith('https://github.com/') && !value.startsWith('http://github.com/')) {
      return 'Only public GitHub URLs (https://github.com/...) are supported.'
    }
    const parts = value.replace(/\/$/, '').split('/')
    if (parts.length < 5) {
      return 'URL must include owner and repository name (e.g. https://github.com/owner/repo).'
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const err = validate(url)
    if (err) {
      setValidationError(err)
      return
    }
    setValidationError(null)
    await onSubmit(url.trim())
  }

  const displayError = validationError || error

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="repo-url" className="block text-sm font-medium text-gray-400 mb-2">
          GitHub Repository URL
        </label>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
              <svg className="w-4 h-4 text-gray-500" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
              </svg>
            </div>
            <input
              id="repo-url"
              type="text"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value)
                if (validationError) setValidationError(null)
              }}
              placeholder="https://github.com/owner/repository"
              disabled={isLoading}
              className="w-full bg-[#1e2535] border border-gray-700/60 rounded-lg pl-10 pr-4 py-3 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !url.trim()}
            className="px-5 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition-colors flex items-center gap-2 shrink-0 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Spinner size="sm" />
                Starting…
              </>
            ) : (
              <>
                <span>Analyze Repository</span>
                <span>→</span>
              </>
            )}
          </button>
        </div>
      </div>

      {displayError && (
        <div className="flex items-start gap-3 p-3.5 rounded-lg bg-red-900/20 border border-red-700/40">
          <span className="text-red-400 shrink-0 mt-0.5">⚠</span>
          <p className="text-sm text-red-300">{displayError}</p>
        </div>
      )}

      <p className="text-xs text-gray-600">
        Only public GitHub repositories are supported. Reviews may take 1–3 minutes depending on repository size.
      </p>
    </form>
  )
}

