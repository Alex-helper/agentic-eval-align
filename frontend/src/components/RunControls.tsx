type Props = {
  loading: boolean
  isPending: boolean
  mcpOk: boolean | null
  formats: string[]
  accept: string
  onRunSelected: () => void
  onRunSuite: () => void
  onPreviewUpload: (files: FileList | null) => void
}

export function RunControls({
  loading,
  isPending,
  mcpOk,
  formats,
  accept,
  onRunSelected,
  onRunSuite,
  onPreviewUpload,
}: Props) {
  return (
    <>
      <div className="actions">
        <button className="cta" type="button" onClick={onRunSelected} disabled={loading || isPending}>
          运行选中案例
        </button>
        <button className="cta" type="button" onClick={onRunSuite} disabled={loading}>
          一键 A/B Suite
        </button>
        <label className="cta upload">
          上传并预览
          <input type="file" multiple accept={accept} onChange={(e) => onPreviewUpload(e.target.files)} />
        </label>
      </div>
      <p className="formatHint">
        MCP: {mcpOk == null ? '检测中' : mcpOk ? 'HTTP 可用' : '将 fallback 本地工具'} · 支持 {formats.join(' ')}
      </p>
    </>
  )
}
