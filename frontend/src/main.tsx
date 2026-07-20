import React, { useEffect, useMemo, useRef, useState, useTransition } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import { DpoCompare } from './components/DpoCompare'
import { ErrorReportPanel } from './components/ErrorReportPanel'
import { ExportButtons } from './components/ExportButtons'
import { RunControls } from './components/RunControls'
import { RunHistory } from './components/RunHistory'
import { SuiteTable } from './components/SuiteTable'
import { TraceTimeline } from './components/TraceTimeline'
import type { Artifact, ChatMsg, Task, TraceEvent } from './types'
import { pct } from './types'

const API = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
const ACCEPT =
  '.json,.jsonl,.yaml,.yml,.csv,.tsv,.txt,.md,.markdown,.png,.jpg,.jpeg,.webp,.gif,.pdf,.docx,.zip'

function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [selected, setSelected] = useState<Task | null>(null)
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [status, setStatus] = useState<'empty' | 'loading' | 'success' | 'error'>('empty')
  const [artifact, setArtifact] = useState<Artifact | null>(null)
  const [runs, setRuns] = useState<Array<Record<string, unknown>>>([])
  const [formats, setFormats] = useState<string[]>([])
  const [mcpOk, setMcpOk] = useState<boolean | null>(null)
  const [preview, setPreview] = useState<{ tasks: any[]; errors: any[] } | null>(null)
  const [pendingFiles, setPendingFiles] = useState<FileList | null>(null)
  const [isPending, startTransition] = useTransition()

  const [assistantOpen, setAssistantOpen] = useState(true)
  const [chat, setChat] = useState<ChatMsg[]>([
    {
      role: 'assistant',
      content:
        '你好，我是 TraceAlign Agent 助手。可以直接让我执行复杂多跳任务，例如：“查 Auth 刷新规则，再按 Billing 8% 税率算 250-20 发票，并判断 risk=0.82 是否需人工审核”。',
    },
  ])
  const [draft, setDraft] = useState('')
  const [assistantBusy, setAssistantBusy] = useState(false)
  const [assistantPulse, setAssistantPulse] = useState(false)
  const chatEndRef = useRef<HTMLDivElement | null>(null)

  const activeError = useMemo(() => {
    const compare = artifact?.compares?.find((c) => c.current.error_report)
    return compare?.current.error_report || null
  }, [artifact])

  const activeDpo = useMemo(() => {
    if (artifact?.dpo_pairs?.length) return artifact.dpo_pairs[0]
    const compare = artifact?.compares?.find((c) => c.current.dpo_pair)
    return compare?.current.dpo_pair || null
  }, [artifact])

  async function refreshRuns() {
    const res = await fetch(`${API}/api/runs`)
    const data = await res.json()
    setRuns(data.runs || [])
  }

  useEffect(() => {
    fetch(`${API}/api/tasks/sample`)
      .then((res) => res.json())
      .then((data) => {
        setTasks(data)
        setSelected(data[0] ?? null)
      })
      .catch(() => setStatus('error'))
    fetch(`${API}/api/formats`)
      .then((res) => res.json())
      .then((data) => setFormats(data.extensions || []))
      .catch(() => undefined)
    fetch(`${API}/api/health`)
      .then((res) => res.json())
      .then((data) => setMcpOk(Boolean(data.mcp?.ok)))
      .catch(() => setMcpOk(false))
    refreshRuns().catch(() => undefined)
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chat, assistantBusy])

  async function runTask(task = selected) {
    if (!task) return
    startTransition(() => {
      setStatus('loading')
      setEvents([{ type: 'planning', message: '正在建立实时 SSE 通道' }])
      setArtifact(null)
    })
    try {
      const res = await fetch(`${API}/api/evaluate/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(task),
      })
      if (!res.body) throw new Error('No stream body')
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() ?? ''
        for (const chunk of chunks) {
          const eventLine = chunk.split('\n').find((line) => line.startsWith('event: '))
          const dataLine = chunk.split('\n').find((line) => line.startsWith('data: '))
          if (!dataLine) continue
          const parsed = JSON.parse(dataLine.slice(6))
          const eventName = eventLine ? eventLine.slice(7) : parsed.type || 'message'
          if (eventName === 'done') {
            setArtifact(parsed.artifact || parsed)
            setStatus(parsed.success ? 'success' : 'error')
            await refreshRuns()
          } else {
            setEvents((prev) => [
              ...prev,
              { type: eventName, message: parsed.message || eventName, payload: parsed.payload || parsed },
            ])
          }
        }
      }
    } catch (error) {
      setStatus('error')
      setEvents((prev) => [...prev, { type: 'error', message: String(error) }])
    }
  }

  async function runSuite() {
    setStatus('loading')
    setEvents([{ type: 'planning', message: '正在运行内置任务 naive vs full A/B suite…' }])
    const res = await fetch(`${API}/api/evaluate/suite`, { method: 'POST' })
    const data = await res.json()
    setArtifact(data)
    setStatus(res.ok ? 'success' : 'error')
    setEvents((prev) => [
      ...prev,
      {
        type: 'success',
        message: `Suite 完成 run_id=${data.run_id}，成功率 ${pct(data.metrics?.current_success_rate)}（基线 ${pct(data.metrics?.baseline_success_rate)}）`,
      },
    ])
    await refreshRuns()
  }

  async function previewUpload(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return
    setPendingFiles(fileList)
    const form = new FormData()
    Array.from(fileList).forEach((file) => form.append('files', file))
    const res = await fetch(`${API}/api/ingest/preview`, { method: 'POST', body: form })
    const data = await res.json()
    setPreview({ tasks: data.tasks || [], errors: data.errors || [] })
    setStatus('empty')
  }

  async function confirmUpload() {
    if (!pendingFiles) return
    setStatus('loading')
    const form = new FormData()
    Array.from(pendingFiles).forEach((file) => form.append('files', file))
    const res = await fetch(`${API}/api/evaluate/upload`, { method: 'POST', body: form })
    const data = await res.json()
    setArtifact(data.artifact || data)
    setStatus(res.ok ? 'success' : 'error')
    setEvents([
      {
        type: 'multimodal',
        message: `上传评测完成：${data.count} 条，成功率 ${pct(data.success_rate)}，run_id=${data.run_id}`,
      },
    ])
    if (data.results?.[0]?.trace) {
      setEvents((prev) => [...prev, ...data.results[0].trace])
    }
    setPreview(null)
    setPendingFiles(null)
    await refreshRuns()
  }

  async function openRun(runId: string) {
    const res = await fetch(`${API}/api/runs/${runId}`)
    const data = await res.json()
    setArtifact(data)
    setStatus('success')
  }

  async function rerun(runId: string) {
    setStatus('loading')
    const res = await fetch(`${API}/api/runs/${runId}/rerun`, { method: 'POST' })
    const data = await res.json()
    setArtifact(data)
    setStatus(res.ok ? 'success' : 'error')
    await refreshRuns()
  }

  async function sendAssistant() {
    const text = draft.trim()
    if (!text || assistantBusy) return
    setDraft('')
    setAssistantBusy(true)
    setAssistantPulse(true)
    const history = chat.filter((m) => m.role !== 'system').map((m) => ({ role: m.role, content: m.content }))
    setChat((prev) => [...prev, { role: 'user', content: text }])

    const wantsComplex =
      /复杂|多步|执行|计算|检索|invoice|tax|auth|risk|workflow|评测|工具/i.test(text) || text.length > 40

    try {
      if (wantsComplex && /执行|计算|查|invoice|tax|risk|auth|复杂/.test(text)) {
        const streamRes = await fetch(`${API}/api/assistant/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, history }),
        })
        let liveTrace: TraceEvent[] = []
        if (streamRes.body) {
          const reader = streamRes.body.getReader()
          const decoder = new TextDecoder()
          let buffer = ''
          let finalReply = ''
          while (true) {
            const { done, value } = await reader.read()
            if (done) break
            buffer += decoder.decode(value, { stream: true })
            const chunks = buffer.split('\n\n')
            buffer = chunks.pop() ?? ''
            for (const chunk of chunks) {
              const eventLine = chunk.split('\n').find((l) => l.startsWith('event: '))
              const dataLine = chunk.split('\n').find((l) => l.startsWith('data: '))
              if (!dataLine) continue
              const parsed = JSON.parse(dataLine.slice(6))
              const eventName = eventLine ? eventLine.slice(7) : 'message'
              if (eventName === 'done') {
                finalReply = parsed.reply || finalReply
                liveTrace = parsed.trace || liveTrace
              } else {
                liveTrace = [...liveTrace, { type: eventName, message: parsed.message || eventName, payload: parsed.payload }]
              }
            }
          }
          setChat((prev) => [...prev, { role: 'assistant', content: finalReply || '复杂任务处理完成。', trace: liveTrace }])
          setEvents(liveTrace)
        }

        const complexRes = await fetch(`${API}/api/tasks/complex`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ instruction: text }),
        })
        const complexData = await complexRes.json()
        if (complexData.artifact) {
          setArtifact(complexData.artifact)
          setStatus(complexData.evaluation?.success ? 'success' : 'error')
          await refreshRuns()
        }
      } else {
        const res = await fetch(`${API}/api/assistant/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, history }),
        })
        const data = await res.json()
        setChat((prev) => [...prev, { role: 'assistant', content: data.reply || '（无回复）', trace: data.trace }])
        if (data.trace) setEvents(data.trace)
      }
    } catch (error) {
      setChat((prev) => [...prev, { role: 'assistant', content: `助手异常：${String(error)}` }])
    } finally {
      setAssistantBusy(false)
      setAssistantPulse(false)
    }
  }

  return (
    <main>
      <section className="hero">
        <div className="heroCopy">
          <p className="eyebrow">Credible Eval Console</p>
          <h1>TraceAlign Lab</h1>
          <p className="lead">
            可审计评测控制台：真实 MCP、实时 SSE、复杂多跳任务、可视化 Agent 助手对话，以及错误报告 / DPO 导出。
          </p>
          <RunControls
            loading={status === 'loading'}
            isPending={isPending}
            mcpOk={mcpOk}
            formats={formats}
            accept={ACCEPT}
            onRunSelected={() => runTask()}
            onRunSuite={runSuite}
            onPreviewUpload={previewUpload}
          />
        </div>
        <div className="tracePlane" aria-label="pipeline">
          <span>Complex Multi-hop</span>
          <span>GraphRAG Local+Global</span>
          <span>MCP HTTP Tools</span>
          <span>Visual Agent Chat</span>
          <span>ErrorReport + DPO</span>
        </div>
      </section>

      {preview && (
        <section className="previewPanel">
          <h2>上传预览（确认后才会评测）</h2>
          <p className="muted">
            解析到 {preview.tasks.length} 条任务；错误 {preview.errors.length} 个。
          </p>
          <ul>
            {preview.tasks.map((t) => (
              <li key={t.task_id}>
                <strong>{t.task_id}</strong> [{t.source_format}] {(t.modalities || []).join(',')} — {t.instruction}
              </li>
            ))}
          </ul>
          {preview.errors.map((e, idx) => (
            <p className="errorText" key={idx}>
              {e.filename}: {e.error}
            </p>
          ))}
          <div className="actions">
            <button className="cta" type="button" onClick={confirmUpload}>
              确认评测
            </button>
            <button
              className="cta"
              type="button"
              onClick={() => {
                setPreview(null)
                setPendingFiles(null)
              }}
            >
              取消
            </button>
          </div>
        </section>
      )}

      <section className="console">
        <div className="taskPicker">
          <h2>内置任务</h2>
          {tasks.map((task) => (
            <button
              className={selected?.task_id === task.task_id ? 'active' : ''}
              key={task.task_id}
              onClick={() => setSelected(task)}
            >
              <strong>
                {task.task_id}
                {task.difficulty === 'hard' ? ' · 复杂' : ''}
              </strong>
              <span>{task.instruction}</span>
            </button>
          ))}
          <RunHistory runs={runs} onOpen={openRun} />
        </div>

        <div>
          <TraceTimeline status={status} events={events} />
          <ErrorReportPanel report={activeError} />
          <DpoCompare pair={activeDpo} />
        </div>

        <div>
          <SuiteTable runId={artifact?.run_id} metrics={artifact?.metrics} compares={artifact?.compares} />
          <ExportButtons runId={artifact?.run_id} apiBase={API} onRerun={rerun} />
        </div>
      </section>

      <button
        className={`agentFab ${assistantPulse ? 'pulse' : ''}`}
        type="button"
        aria-label="打开 Agent 助手"
        onClick={() => setAssistantOpen((v) => !v)}
      >
        <span className="agentAvatar" />
        <span>Agent</span>
      </button>

      {assistantOpen && (
        <aside className="agentPanel" aria-label="可视化 Agent 助手">
          <header className="agentHeader">
            <div className={`agentFace ${assistantBusy ? 'thinking' : ''}`}>
              <i />
              <i />
              <b />
            </div>
            <div>
              <strong>TraceAlign Agent</strong>
              <p>{assistantBusy ? '思考 / 调工具中…' : '可对话 · 可执行复杂多跳任务'}</p>
            </div>
            <button className="agentClose" type="button" onClick={() => setAssistantOpen(false)}>
              ×
            </button>
          </header>
          <div className="agentMessages">
            {chat.map((m, idx) => (
              <div className={`bubble ${m.role}`} key={idx}>
                <p>{m.content}</p>
                {m.trace && m.trace.length > 0 && (
                  <div className="miniTrace">
                    {m.trace.slice(-4).map((t, i) => (
                      <span key={i}>{t.type}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>
          <div className="agentQuick">
            <button
              type="button"
              onClick={() =>
                setDraft(
                  '执行复杂任务：查 Auth 刷新规则，再按 Billing 8% 税率计算 250-20 的发票总额，并判断 risk=0.82 是否需要人工审核。',
                )
              }
            >
              复杂多跳示例
            </button>
            <button type="button" onClick={() => setDraft('解释一下你们的 naive vs full A/B 评测怎么证明更好？')}>
              问评测方法
            </button>
          </div>
          <form
            className="agentInput"
            onSubmit={(e) => {
              e.preventDefault()
              sendAssistant()
            }}
          >
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="输入问题或复杂任务…"
              disabled={assistantBusy}
            />
            <button className="cta" type="submit" disabled={assistantBusy || !draft.trim()}>
              发送
            </button>
          </form>
        </aside>
      )}
    </main>
  )
}

createRoot(document.getElementById('root')!).render(<App />)
