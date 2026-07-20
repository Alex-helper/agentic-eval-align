type Props = {
  report: Record<string, unknown> | null
}

export function ErrorReportPanel({ report }: Props) {
  if (!report) return null
  return (
    <div className="card">
      <h3>ErrorReport</h3>
      <pre>{JSON.stringify(report, null, 2)}</pre>
    </div>
  )
}
