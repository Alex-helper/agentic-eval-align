import type { TraceEvent } from '../types'

type Props = {
  status: 'empty' | 'loading' | 'success' | 'error'
  events: TraceEvent[]
}

function transportHint(event: TraceEvent): string | null {
  const t = event.payload?.transport
  if (typeof t === 'string') return t
  return null
}

export function TraceTimeline({ status, events }: Props) {
  return (
    <div className="stream">
      <h2>实时轨迹</h2>
      {status === 'empty' && <p className="empty">运行案例、Suite、上传，或与右侧 Agent 助手对话执行复杂任务。</p>}
      {status === 'loading' && <p className="loading">Agent 正在规划 / 检索 / 调 MCP / 评分…</p>}
      {events.map((event, idx) => {
        const transport = transportHint(event)
        return (
          <div className={`event ${event.type}`} key={idx}>
            <b>{event.type}</b>
            <span>
              {event.message}
              {transport ? ` · transport=${transport}` : ''}
            </span>
          </div>
        )
      })}
    </div>
  )
}
