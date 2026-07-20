import { useEffect, useState } from 'react'

const API = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

type View = 'console' | 'health' | 'metrics' | 'mcp' | 'complex' | 'formats'

type Props = {
  view: View
  formats: string[]
  mcpOk: boolean | null
  onOpenSettings: () => void
}

export function ExtraPanels({ view, formats, mcpOk, onOpenSettings }: Props) {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null)
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null)
  const [mcp, setMcp] = useState<{ tools?: any[]; transport?: string; error?: string; mcp?: any } | null>(null)
  const [complexInstr, setComplexInstr] = useState(
    '查 Auth 刷新规则，再按 Billing 8% 税率计算 250-20 的发票总额，并判断 risk=0.82 是否需要人工审核。',
  )
  const [complexBusy, setComplexBusy] = useState(false)
  const [complexResult, setComplexResult] = useState<any>(null)

  useEffect(() => {
    if (view === 'health') {
      fetch(`${API}/api/health`)
        .then((r) => r.json())
        .then(setHealth)
        .catch(() => setHealth({ status: 'error' }))
    }
    if (view === 'metrics') {
      fetch(`${API}/api/metrics/latest`)
        .then((r) => r.json())
        .then(setMetrics)
        .catch(() => setMetrics({ error: 'load failed' }))
    }
    if (view === 'mcp') {
      fetch(`${API}/api/mcp/tools`)
        .then((r) => r.json())
        .then(setMcp)
        .catch((e) => setMcp({ error: String(e), tools: [] }))
    }
  }, [view])

  if (view === 'console') return null

  async function runComplex() {
    setComplexBusy(true)
    setComplexResult(null)
    try {
      const res = await fetch(`${API}/api/tasks/complex`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction: complexInstr }),
      })
      const data = await res.json()
      setComplexResult(data)
    } catch (e) {
      setComplexResult({ error: String(e) })
    } finally {
      setComplexBusy(false)
    }
  }

  return (
    <section className="extra-panel">
      {view === 'health' && (
        <>
          <h2>系统健康</h2>
          <div className="chip-row" style={{ marginBottom: '1rem' }}>
            <span className="chip">
              <span className={`status-dot ${mcpOk ? 'ok' : 'bad'}`} /> MCP
            </span>
            <span className="chip">
              <span className={`status-dot ${health?.llm_configured ? 'ok' : 'bad'}`} /> LLM
            </span>
            <button type="button" className="cta" onClick={onOpenSettings}>
              API 配置
            </button>
          </div>
          <pre className="code-block">{JSON.stringify(health, null, 2)}</pre>
        </>
      )}

      {view === 'metrics' && (
        <>
          <h2>指标看板</h2>
          <p className="muted">来源：{String(metrics?.source || '—')} · run_id：{String(metrics?.run_id || '—')}</p>
          {metrics?.markdown ? (
            <pre className="code-block">{String(metrics.markdown)}</pre>
          ) : (
            <pre className="code-block">{JSON.stringify(metrics?.metrics || metrics, null, 2)}</pre>
          )}
          {Array.isArray(metrics?.compares) && metrics!.compares.length > 0 && (
            <pre className="code-block">{JSON.stringify(metrics!.compares, null, 2)}</pre>
          )}
        </>
      )}

      {view === 'mcp' && (
        <>
          <h2>MCP 工具目录</h2>
          <p className="muted">
            transport：{mcp?.transport || mcp?.mcp?.transport || '—'}
            {mcp?.error ? ` · ${mcp.error}` : ''}
          </p>
          <div className="tool-grid">
            {(mcp?.tools || []).map((t: any) => (
              <article className="tool-card" key={t.name || JSON.stringify(t)}>
                <strong>{t.name}</strong>
                <p>{t.description || '—'}</p>
              </article>
            ))}
            {(mcp?.tools || []).length === 0 && <p className="muted">暂无工具列表（可检查 MCP :8100）</p>}
          </div>
        </>
      )}

      {view === 'complex' && (
        <>
          <h2>复杂多跳任务</h2>
          <p className="muted">调用 /api/tasks/complex：助手规划 + Supervisor 正式评测产物。</p>
          <textarea
            className="complex-input"
            rows={4}
            value={complexInstr}
            onChange={(e) => setComplexInstr(e.target.value)}
          />
          <div className="actions">
            <button type="button" className="cta" disabled={complexBusy || !complexInstr.trim()} onClick={runComplex}>
              {complexBusy ? '执行中…' : '执行复杂任务'}
            </button>
          </div>
          {complexResult && <pre className="code-block">{JSON.stringify(complexResult, null, 2)}</pre>}
        </>
      )}

      {view === 'formats' && (
        <>
          <h2>上传格式说明</h2>
          <p className="muted">支持扩展名（来自 /api/formats）：</p>
          <div className="chip-row">
            {formats.map((f) => (
              <span className="chip" key={f}>
                {f}
              </span>
            ))}
          </div>
          <ul className="format-list">
            <li>json / jsonl / yaml：结构化任务清单</li>
            <li>csv / tsv：表格任务行</li>
            <li>md / txt：自然语言任务说明</li>
            <li>png / jpg / webp / pdf / docx：多模态附件（解析预览 → 确认评测）</li>
          </ul>
        </>
      )}
    </section>
  )
}
