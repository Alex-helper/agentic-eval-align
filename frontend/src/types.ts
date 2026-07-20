export type Task = {
  task_id: string
  instruction: string
  tools: string[]
  expected: Record<string, unknown>
  difficulty: string
  modalities?: string[]
  source_format?: string
}

export type TraceEvent = {
  type: string
  message: string
  payload?: Record<string, unknown>
}

export type Metrics = {
  task_count: number
  baseline_success_rate: number
  current_success_rate: number
  success_rate_delta_pct: number
  tool_success_rate: number
  knowledge_hit_rate: number
  avg_total_ms: number
  avg_first_event_ms: number
}

export type CompareRow = {
  task_id: string
  improved: boolean
  delta_score: number
  baseline: { success: boolean; score: number }
  current: {
    success: boolean
    score: number
    error_report?: Record<string, unknown>
    dpo_pair?: Record<string, unknown>
    tool_transport?: string
  }
}

export type Artifact = {
  run_id: string
  kind: string
  metrics?: Metrics
  compares?: CompareRow[]
  results?: Array<Record<string, unknown>>
  dpo_pairs?: Array<Record<string, unknown>>
}

export type ChatMsg = {
  role: 'user' | 'assistant' | 'system'
  content: string
  trace?: TraceEvent[]
}

export function pct(v?: number) {
  if (v == null || Number.isNaN(v)) return '—'
  return `${(v * 100).toFixed(0)}%`
}
