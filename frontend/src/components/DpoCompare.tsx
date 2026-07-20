type Props = {
  pair: Record<string, unknown> | null
}

export function DpoCompare({ pair }: Props) {
  if (!pair) return null
  const chosen = String(pair.chosen || '')
  const rejected = String(pair.rejected || '')
  return (
    <div className="card">
      <h3>DPO chosen / rejected</h3>
      {pair.run_id != null && pair.run_id !== '' ? (
        <p className="muted">bound run_id: {String(pair.run_id)}</p>
      ) : null}
      <div className="dpoGrid">
        <div>
          <strong>chosen</strong>
          <pre>{chosen}</pre>
        </div>
        <div>
          <strong>rejected</strong>
          <pre>{rejected}</pre>
        </div>
      </div>
    </div>
  )
}
