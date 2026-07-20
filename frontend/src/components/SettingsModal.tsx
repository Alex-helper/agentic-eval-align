import { useEffect, useState } from 'react'

const API = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

type Props = {
  open: boolean
  onClose: () => void
}

type Catalog = {
  providers?: Array<{
    id: string
    name: string
    base_url?: string
    models?: string[]
    console_url?: string
    third_party?: Array<{ name: string; base_url: string; notes?: string; site_url?: string; docs_url?: string }>
  }>
  regions?: Array<{ id: string; name: string }>
}

export function SettingsModal({ open, onClose }: Props) {
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('https://api.deepseek.com/v1')
  const [model, setModel] = useState('deepseek-chat')
  const [providerId, setProviderId] = useState('deepseek')
  const [region, setRegion] = useState('cn')
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    if (!open) return
    setMsg('')
    Promise.all([
      fetch(`${API}/api/config`).then((r) => r.json()),
      fetch(`${API}/api/providers-catalog`).then((r) => r.json()).catch(() => null),
    ])
      .then(([cfg, cat]) => {
        setApiKey(cfg.api_key || '')
        setBaseUrl(cfg.base_url || 'https://api.deepseek.com/v1')
        setModel(cfg.model || 'deepseek-chat')
        setProviderId(cfg.provider_id || 'deepseek')
        setRegion(cfg.region || 'cn')
        setCatalog(cat)
      })
      .catch(() => setMsg('读取配置失败'))
  }, [open])

  if (!open) return null

  const providers = catalog?.providers || []
  const current = providers.find((p) => p.id === providerId)

  async function save() {
    if (!apiKey.trim()) {
      setMsg('请填写 API Key')
      return
    }
    setSaving(true)
    setMsg('')
    try {
      const r = await fetch(`${API}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: apiKey.trim(),
          base_url: baseUrl.trim(),
          model: model.trim(),
          provider_id: providerId,
          region,
        }),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      setMsg('已保存到 .env，新评测将使用此配置')
    } catch (e) {
      setMsg(`保存失败：${String(e)}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <header className="modal-head">
          <strong>API 配置</strong>
          <button type="button" className="agentClose" onClick={onClose}>
            ×
          </button>
        </header>
        <label className="label">服务商</label>
        <select
          value={providerId}
          onChange={(e) => {
            const id = e.target.value
            setProviderId(id)
            const p = providers.find((x) => x.id === id)
            if (p?.base_url) setBaseUrl(p.base_url)
            if (p?.models?.[0]) setModel(p.models[0])
          }}
        >
          {(providers.length ? providers : [{ id: 'deepseek', name: 'DeepSeek' }]).map((p) => (
            <option key={p.id} value={p.id}>
              {p.name || p.id}
            </option>
          ))}
        </select>
        {(catalog?.regions || []).length > 0 && (
          <>
            <label className="label">区域</label>
            <select value={region} onChange={(e) => setRegion(e.target.value)}>
              {catalog!.regions!.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name || r.id}
                </option>
              ))}
            </select>
          </>
        )}
        {current?.console_url && (
          <p className="muted">
            控制台：{' '}
            <a href={current.console_url} target="_blank" rel="noreferrer">
              {current.console_url}
            </a>
          </p>
        )}
        <label className="label">API Key</label>
        <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="sk-..." />
        <label className="label">Base URL</label>
        <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
        <label className="label">模型名称</label>
        <input value={model} onChange={(e) => setModel(e.target.value)} />
        <div className="actions" style={{ marginTop: '1rem' }}>
          <button type="button" className="cta" onClick={onClose}>
            取消
          </button>
          <button type="button" className="cta" disabled={saving} onClick={save}>
            {saving ? '保存中…' : '保存配置'}
          </button>
        </div>
        {msg && <p className="muted">{msg}</p>}
      </div>
    </div>
  )
}
