import type { CompareRow, Metrics } from '../types'
import { pct } from '../types'

type Props = {
  runId?: string
  metrics?: Metrics
  compares?: CompareRow[]
}

export function SuiteTable({ runId, metrics, compares }: Props) {
  return (
    <div className="metrics">
      <h2>实测指标</h2>
      {runId && <p className="muted">run_id: {runId}</p>}
      <div className="metricBar">
        <span>成功率（full） {pct(metrics?.current_success_rate)}</span>
        <i style={{ width: `${(metrics?.current_success_rate || 0) * 100}%` }} />
      </div>
      <div className="metricBar">
        <span>基线成功率 {pct(metrics?.baseline_success_rate)}</span>
        <i style={{ width: `${(metrics?.baseline_success_rate || 0) * 100}%` }} />
      </div>
      <div className="metricBar">
        <span>工具成功率 {pct(metrics?.tool_success_rate)}</span>
        <i style={{ width: `${(metrics?.tool_success_rate || 0) * 100}%` }} />
      </div>
      <div className="metricBar">
        <span>知识命中率 {pct(metrics?.knowledge_hit_rate)}</span>
        <i style={{ width: `${(metrics?.knowledge_hit_rate || 0) * 100}%` }} />
      </div>
      <p className="muted">
        Δ成功率 {metrics?.success_rate_delta_pct ?? '—'}% · 首事件 {metrics?.avg_first_event_ms?.toFixed?.(0) ?? '—'}ms
      </p>
      <p className="formatHint">目标项（非本次实测）：错误分析时间↓93.3%、DPO 成本↓99.75%</p>
      {compares && compares.length > 0 && (
        <table className="suiteTable">
          <thead>
            <tr>
              <th>task</th>
              <th>baseline</th>
              <th>full</th>
              <th>transport</th>
              <th>Δscore</th>
            </tr>
          </thead>
          <tbody>
            {compares.map((row) => (
              <tr key={row.task_id}>
                <td>{row.task_id}</td>
                <td>
                  {row.baseline.success ? '✓' : '✗'} {row.baseline.score.toFixed(2)}
                </td>
                <td>
                  {row.current.success ? '✓' : '✗'} {row.current.score.toFixed(2)}
                </td>
                <td>{row.current.tool_transport || '—'}</td>
                <td>{row.delta_score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
