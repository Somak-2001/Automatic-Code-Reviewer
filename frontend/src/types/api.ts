// Types that mirror the FastAPI backend Pydantic models

export type StageStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped'

export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type Category =
  | 'security'
  | 'correctness'
  | 'performance'
  | 'maintainability'
  | 'testing'
  | 'architecture'
export type ProviderName = 'openai' | 'anthropic' | 'gemini'

export interface ReviewIssue {
  title: string
  severity: Severity
  category: Category
  file_path: string
  line_hint: string
  line_start: number | null
  line_end: number | null
  cell_number?: number | null
  summary: string
  recommendation: string
  source_model: ProviderName
  reviewer_role: string
  confidence: number
  evidence: string
  detected_by: ProviderName[]
}

export interface ConsensusSection {
  headline: string
  details: string[]
}

export interface ProviderResultSummary {
  provider: ProviderName
  role: string
  status: StageStatus
  summary: string
  strengths: string[]
  error: string
  issues_count: number
}

export interface StaticSignal {
  kind: string
  file_path: string
  message: string
  severity: Severity
  line_hint: string
}

export interface ReviewReport {
  generated_at: string
  repo_name: string
  repo_url: string
  branch: string
  executive_summary: string
  risk_score: number
  providers_attempted: ProviderName[]
  providers_succeeded: ProviderName[]
  providers_failed: ProviderName[]
  top_issues: ReviewIssue[]
  consensus: ConsensusSection[]
  provider_results: ProviderResultSummary[]
  static_signals: StaticSignal[]
  next_steps: string[]
}

export interface ReviewJobStatus {
  review_id: string
  status: StageStatus
  progress: number
  error: string
  stages: {
    repository: StageStatus
    static_analysis: StageStatus
    openai: StageStatus
    anthropic: StageStatus
    gemini: StageStatus
    aggregation: StageStatus
    report: StageStatus
  }
  repository_url: string
  started_at: string | null
  completed_at: string | null
}

export interface ReviewStartResponse {
  review_id: string
  status: StageStatus
}

export interface BackendConfig {
  providers_configured: ProviderName[]
  models: {
    openai: string | null
    anthropic: string | null
    gemini: string | null
  }
  limits: {
    max_files: number
    max_file_bytes: number
  }
}

