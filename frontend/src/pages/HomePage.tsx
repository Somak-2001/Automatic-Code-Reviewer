import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchConfig, startReview } from '../services/api'
import { RepoInputForm } from '../components/review/RepoInputForm'
import type { BackendConfig } from '../types/api'

export function HomePage() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [config, setConfig] = useState<BackendConfig | null>(null)
  const [backendDown, setBackendDown] = useState(false)

  useEffect(() => {
    fetchConfig()
      .then(setConfig)
      .catch(() => setBackendDown(true))
  }, [])

  const handleSubmit = async (url: string) => {
    setIsLoading(true)
    setError(null)
    try {
      const { review_id } = await startReview(url)
      navigate(`/review/${review_id}`, { state: { repositoryUrl: url } })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start review.')
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0f1117] flex flex-col">
      {/* Top bar */}
      <header className="border-b border-gray-800/60 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-600 to-indigo-400 flex items-center justify-center text-white text-sm font-bold">
            CR
          </div>
          <span className="text-gray-200 font-semibold text-sm">CodeReview AI</span>
          <span className="text-gray-700 text-xs ml-2">Multi-LLM Code Reviewer</span>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-2xl space-y-10">
          {/* Hero */}
          <div className="text-center space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-900/30 border border-indigo-700/30 text-xs text-indigo-400 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
              Powered by OpenAI · Anthropic · Google Gemini
            </div>
            <h1 className="text-4xl sm:text-5xl font-extrabold text-gray-50 leading-tight tracking-tight">
              Automatic Code{' '}
              <span className="bg-gradient-to-r from-indigo-400 to-indigo-300 bg-clip-text text-transparent">
                Reviewer
              </span>
            </h1>
            <p className="text-gray-500 text-base max-w-lg mx-auto">
              Paste a GitHub repository URL. Real source code is analyzed by multiple LLM families,
              findings are deduplicated and consensus-ranked, and a structured report is generated.
            </p>
          </div>

          {/* Config warnings */}
          {backendDown && (
            <div className="p-4 rounded-xl bg-red-900/20 border border-red-700/30">
              <p className="text-sm text-red-300 font-medium">⚠ Cannot connect to backend</p>
              <p className="text-xs text-red-400/70 mt-1">
                Make sure FastAPI is running: <code className="font-mono">uvicorn app.main:app --reload</code>
              </p>
            </div>
          )}

          {config && config.providers_configured.length === 0 && (
            <div className="p-4 rounded-xl bg-yellow-900/20 border border-yellow-700/30">
              <p className="text-sm text-yellow-300 font-medium">⚠ No LLM providers configured</p>
              <p className="text-xs text-yellow-400/70 mt-1">
                Set at least one of <code className="font-mono">OPENAI_API_KEY</code>,{' '}
                <code className="font-mono">ANTHROPIC_API_KEY</code>, or{' '}
                <code className="font-mono">GEMINI_API_KEY</code> in your <code className="font-mono">.env</code> file.
              </p>
            </div>
          )}

          {/* Form card */}
          <div className="bg-[#161b27] border border-gray-700/40 rounded-2xl p-6">
            <RepoInputForm
              onSubmit={handleSubmit}
              isLoading={isLoading}
              error={error}
            />
          </div>

          {/* Provider status */}
          {config && (
            <div className="grid grid-cols-3 gap-3">
              {(['openai', 'anthropic', 'gemini'] as const).map((p) => {
                const configured = config.providers_configured.includes(p)
                return (
                  <div
                    key={p}
                    className={`text-center p-3 rounded-xl border ${
                      configured
                        ? 'bg-green-900/10 border-green-700/30'
                        : 'bg-gray-800/30 border-gray-700/30 opacity-50'
                    }`}
                  >
                    <p className={`text-xs font-semibold ${configured ? 'text-green-400' : 'text-gray-600'}`}>
                      {configured ? '✓' : '✗'} {p.charAt(0).toUpperCase() + p.slice(1)}
                    </p>
                    {config.models[p] && (
                      <p className="text-xs text-gray-600 font-mono mt-0.5">{config.models[p]}</p>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* Feature list */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
            {[
              {
                icon: '🔒',
                title: 'Security Review',
                desc: 'Injection, auth, secrets',
              },
              {
                icon: '⚡',
                title: 'Performance',
                desc: 'Hot paths, N+1, I/O',
              },
              {
                icon: '🏗',
                title: 'Code Quality',
                desc: 'Structure, naming, bugs',
              },
            ].map((f) => (
              <div key={f.title} className="p-4 rounded-xl bg-[#161b27] border border-gray-800/60">
                <div className="text-2xl mb-2">{f.icon}</div>
                <p className="text-xs font-semibold text-gray-300">{f.title}</p>
                <p className="text-xs text-gray-600 mt-1">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}

