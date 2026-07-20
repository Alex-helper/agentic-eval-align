import { pct } from '../types'

type Props = {
  runs: Array<Record<string, unknown>>
  onOpen: (runId: string) => void
}

export function RunHistory({ runs, onOpen }: Props) {
  return (
    <>
      <h2>运行历史</h2>
      {runs.length === 0 && <p className="muted">暂无运行记录。</p>}
      {runs.map((run) => (
        <button key={String(run.run_id)} onClick={() => onOpen(String(run.run_id))}>
          <strong>{String(run.run_id)}</strong>
          <span>
            {String(run.kind)} · {pct(Number(run.success_rate))}
          </span>
        </button>
      ))}
    </>
  )
}
