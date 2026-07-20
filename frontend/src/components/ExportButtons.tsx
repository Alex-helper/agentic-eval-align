type Props = {
  runId?: string
  apiBase: string
  onRerun?: (runId: string) => void
}

export function ExportButtons({ runId, apiBase, onRerun }: Props) {
  if (!runId) return null
  function download(path: string) {
    window.open(`${apiBase}${path}`, '_blank')
  }
  return (
    <div className="actions">
      <button className="cta" type="button" onClick={() => download(`/api/runs/${runId}/export.json`)}>
        导出 JSON
      </button>
      <button className="cta" type="button" onClick={() => download(`/api/runs/${runId}/export.md`)}>
        导出 MD
      </button>
      <button className="cta" type="button" onClick={() => download(`/api/runs/${runId}/export.dpo.jsonl`)}>
        导出 DPO
      </button>
      {onRerun && (
        <button className="cta" type="button" onClick={() => onRerun(runId)}>
          基于原输入重跑
        </button>
      )}
    </div>
  )
}
