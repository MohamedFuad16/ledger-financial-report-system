import { useEffect, useMemo, useState } from 'react'
import { Activity, Cable, CheckCircle2, Eye, EyeOff, ExternalLink, Flame, Gauge, KeyRound, Lock, Save, Server, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import type { ProviderInfo, SettingsData } from '../types'
import { Badge, Button, Card, SectionHeading } from '../components/ui'
import { useLocale } from '../lib/i18n'

function ProviderLogo({ providerKey }: { providerKey: string }) {
  const logos: Record<string, { src: string; alt: string }> = {
    openrouter: { src: '/providers/openrouter.png', alt: 'OpenRouter' },
    openai: { src: '/providers/openai.svg', alt: 'OpenAI' },
    zai: { src: '/providers/zai.svg', alt: 'Z.AI' },
    'zai-coding': { src: '/providers/zai.svg', alt: 'Z.AI' },
  }
  const logo = logos[providerKey]
  return <span className={`provider-mark provider-mark-${providerKey}`}>{logo ? <img src={logo.src} alt={`${logo.alt} logo`} /> : <Cable size={18} strokeWidth={1.9} />}</span>
}

function CredentialField({ label, value, onChange, saved, masked, placeholder, icon }: { label: string; value: string; onChange: (value: string) => void; saved: boolean; masked: string; placeholder: string; icon: 'key' | 'fire' }) {
  const { tr } = useLocale()
  const [visible, setVisible] = useState(false)
  const Icon = icon === 'fire' ? Flame : KeyRound
  return <label className="credential-field"><span><b>{label}</b>{saved ? <small className="credential-saved"><CheckCircle2 size={13} /> {tr('Saved', '保存済み')} · {masked}</small> : <small>{tr('Not configured', '未設定')}</small>}</span><div className="input-with-icon credential-input"><Icon size={17} /><input type={visible ? 'text' : 'password'} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} autoComplete="new-password" /><button type="button" aria-label={visible ? tr('Hide replacement key', '置換キーを隠す') : tr('Show replacement key', '置換キーを表示')} onClick={() => setVisible((current) => !current)}>{visible ? <EyeOff size={16} /> : <Eye size={16} />}</button></div><em>{saved ? tr('Enter a new key only when you want to replace the saved credential.', '保存済み認証情報を置き換える場合のみ、新しいキーを入力してください。') : tr('The key is tested before it is stored locally.', 'キーはローカル保存前に接続テストされます。')}</em></label>
}

export function SettingsPage({
  settings,
  providers,
  onSaved,
  onNotify,
}: {
  settings: SettingsData | null
  providers: ProviderInfo[]
  onSaved: () => Promise<void>
  onNotify: (message: string, tone: 'success' | 'error') => void
}) {
  const { tr } = useLocale()
  const [providerKey, setProviderKey] = useState(settings?.provider || 'openrouter')
  const [model, setModel] = useState(settings?.model || '')
  const [baseUrl, setBaseUrl] = useState(settings?.base_url || '')
  const [apiKey, setApiKey] = useState('')
  const [reasoningEnabled, setReasoningEnabled] = useState((settings?.reasoning_effort || 'high') !== 'none')
  const [temperature, setTemperature] = useState(settings?.temperature ?? 0.0)
  const [saving, setSaving] = useState(false)
  const [runtimeSaving, setRuntimeSaving] = useState(false)
  const [maxConcurrency, setMaxConcurrency] = useState(settings?.max_concurrency ?? 6)
  const [autoConcurrency, setAutoConcurrency] = useState(settings?.auto_concurrency ?? true)
  const [firecrawlKey, setFirecrawlKey] = useState('')
  const provider = useMemo(() => providers.find((item) => item.key === providerKey), [providers, providerKey])
  const providerCredentialSaved = Boolean(settings?.has_key && settings.provider === providerKey && settings.base_url.replace(/\/$/, '') === baseUrl.replace(/\/$/, ''))
  const finiteRate = (value: unknown, fallback: number) => Number.isFinite(Number(value)) ? Number(value) : fallback

  useEffect(() => {
    if (!settings) return
    setProviderKey(settings.provider); setModel(settings.model); setBaseUrl(settings.base_url); setReasoningEnabled(settings.reasoning_effort !== 'none'); setTemperature(settings.temperature); setMaxConcurrency(settings.max_concurrency); setAutoConcurrency(settings.auto_concurrency)
  }, [settings])

  const chooseProvider = (key: string) => {
    const next = providers.find((item) => item.key === key)
    setProviderKey(key)
    if (next) { setModel(next.default_model); setBaseUrl(next.base_url) }
  }

  const saveRuntime = async () => {
    setRuntimeSaving(true)
    try {
      const result = await api.saveRuntimeSettings({ max_concurrency: maxConcurrency, auto_concurrency: autoConcurrency, firecrawl_api_key: firecrawlKey })
      setFirecrawlKey('')
      await onSaved()
      const remaining = result.firecrawl_credits?.remainingCredits
      onNotify(tr(`Firecrawl verified${remaining != null ? ` · ${remaining.toLocaleString()} credits remaining` : ''}. Runtime settings saved locally.`, `Firecrawlの接続を確認${remaining != null ? ` · 残り${remaining.toLocaleString()}クレジット` : ''}。ランタイム設定を保存しました。`), 'success')
    } catch (error) { onNotify(error instanceof Error ? error.message : tr('Runtime settings could not be saved.', 'ランタイム設定を保存できませんでした。'), 'error') }
    finally { setRuntimeSaving(false) }
  }

  const save = async () => {
    setSaving(true)
    try {
      const result = await api.saveSettings({ provider: providerKey, model, base_url: baseUrl, api_key: apiKey, reasoning_effort: reasoningEnabled ? 'high' : 'none', enable_reasoning: reasoningEnabled, temperature })
      setApiKey('')
      await onSaved()
      onNotify(tr(`Connection verified in ${result.elapsed.toFixed(1)}s.`, `${result.elapsed.toFixed(1)}秒で接続を確認しました。`), 'success')
    } catch (error) {
      onNotify(error instanceof Error ? error.message : tr('The provider settings could not be saved.', 'プロバイダー設定を保存できませんでした。'), 'error')
    } finally { setSaving(false) }
  }

  return (
    <div className="page settings-page">
      <header className="page-header"><div><div className="page-kicker">{tr('Workspace configuration', 'ワークスペース設定')}</div><h1>{tr('Connections & runtime', '接続とランタイム')}</h1><p>{tr('Manage model credentials, corpus discovery, and one global adaptive request ceiling.', 'モデル認証情報、コーパス探索、グローバルな同時実行上限を管理します。')}</p></div></header>
      <div className="settings-layout">
        <div className="settings-stack">
        <Card className="settings-main">
          <SectionHeading eyebrow={tr('Provider', 'プロバイダー')} title={tr('Model gateway', 'モデルゲートウェイ')} description={tr('Changing the destination requires re-entering the API key.', '接続先を変更する場合はAPIキーの再入力が必要です。')} />
          <div className="provider-grid">{providers.map((item) => <button className={providerKey === item.key ? 'is-selected' : ''} onClick={() => chooseProvider(item.key)} key={item.key}><ProviderLogo providerKey={item.key} /><span><strong>{item.label}</strong><small>{item.automatic_prompt_caching ? tr('Automatic prompt cache', '自動プロンプトキャッシュ') : item.reasoning_style === 'thinking' ? tr('GLM thinking mode', 'GLM思考モード') : tr('Compatible endpoint', '互換エンドポイント')}</small></span>{providerKey === item.key && <CheckCircle2 size={16} />}</button>)}</div>
          <div className="settings-fields">
            <CredentialField label={tr('Provider API key', 'プロバイダーAPIキー')} value={apiKey} onChange={setApiKey} saved={providerCredentialSaved} masked={settings?.api_key_masked || ''} placeholder={providerCredentialSaved ? tr('Enter replacement key', '置換するキーを入力') : tr('Enter provider API key', 'プロバイダーAPIキーを入力')} icon="key" />
            <label><span>{tr('Model ID', 'モデルID')}</span><input value={model} onChange={(event) => setModel(event.target.value)} list="suggested-models" /><datalist id="suggested-models">{provider?.suggested_models.map((item) => <option value={item} key={item} />)}</datalist></label>
            <label className="field-wide"><span>{tr('Base URL', 'ベースURL')}</span><div className="input-with-icon"><Server size={16} /><input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} /></div></label>
            <div className="reasoning-toggle"><span><strong>{tr('Model reasoning', 'モデル推論')}</strong><small>{tr('Native thinking mode: on or off.', 'ネイティブ思考モード：オン／オフ。')}</small></span><div><button className={!reasoningEnabled ? 'is-active' : ''} onClick={() => setReasoningEnabled(false)}>{tr('Off', 'オフ')}</button><button className={reasoningEnabled ? 'is-active' : ''} onClick={() => setReasoningEnabled(true)}>{tr('On', 'オン')}</button></div></div>
            <label><span>{tr('Temperature', '温度')} <b>{temperature.toFixed(2)}</b></span><input type="range" min="0" max="1" step="0.05" value={temperature} onChange={(event) => setTemperature(Number(event.target.value))} /></label>
          </div>
          <Button className="save-settings" onClick={save} disabled={saving || !model || !baseUrl}><Save size={15} /> {saving ? tr('Testing connection…', '接続をテスト中…') : tr('Test connection & save', '接続をテストして保存')}</Button>
        </Card>
        <Card className="settings-main runtime-settings">
          <SectionHeading eyebrow={tr('Corpus & scheduling', 'コーパスとスケジュール')} title={tr('Firecrawl and adaptive concurrency', 'Firecrawlと適応型同時実行')} description={tr('This single ceiling applies to every strategy. The live limiter reduces it on HTTP 429, waits for Retry-After, and recovers gradually after successful calls.', 'この上限は全戦略に適用されます。HTTP 429では縮小し、Retry-Afterを待って、成功後に徐々に回復します。')} />
          <div className="runtime-grid">
            <div className="field-wide"><CredentialField label={tr('Firecrawl API key', 'Firecrawl APIキー')} value={firecrawlKey} onChange={setFirecrawlKey} saved={Boolean(settings?.has_firecrawl_key)} masked={settings?.firecrawl_key_masked || ''} placeholder={settings?.has_firecrawl_key ? tr('Enter replacement Firecrawl key', '置換するFirecrawlキーを入力') : 'fc-…'} icon="fire" /></div>
            <label><span>{tr('Parallel request ceiling', '並列リクエスト上限')} <b>{maxConcurrency}</b></span><input type="range" min="1" max="20" step="1" value={maxConcurrency} onChange={(event) => setMaxConcurrency(Number(event.target.value))} /></label>
            <label className="toggle-setting"><span><strong>{tr('Automatic batch sizing', '自動バッチサイズ')}</strong><small>{tr('Use PDF count and estimated token load to choose the initial width.', 'PDF数と推定トークン量から初期並列数を選びます。')}</small></span><input type="checkbox" checked={autoConcurrency} onChange={(event) => setAutoConcurrency(event.target.checked)} /></label>
            <div className="ocr-policy-contract field-wide">
              <strong>{tr('OCR policy is fixed by parser', 'OCRポリシーはパーサーごとに固定')}</strong>
              <span>{tr('Strategy 1 never uses OCR. Strategy 2 uses page-adaptive OCR for pdf-inspector and PyMuPDF, while PyPDF and Docling force OCR because they do not expose the same reliable per-page decision boundary.', '戦略1はOCRを使用しません。戦略2ではpdf-inspectorとPyMuPDFがページ単位の適応OCRを使用し、同等の判定境界を持たないPyPDFとDoclingはOCRを強制します。')}</span>
            </div>
          </div>
          <div className="rate-state">
            <span><Activity size={16} /><strong>{finiteRate(settings?.rate_limit?.permitted_concurrency, maxConcurrency)}</strong> {tr('permitted now', '現在許可')}</span>
            <span><Gauge size={16} /><strong>{finiteRate(settings?.rate_limit?.in_flight, 0)}</strong> {tr('requests in flight', '実行中リクエスト')}</span>
            <span><Flame size={16} /><strong>{finiteRate(settings?.rate_limit?.throttle_events, 0)}</strong> {tr('throttle events', 'スロットル回数')}</span>
          </div>
          <Button className="save-settings" onClick={saveRuntime} disabled={runtimeSaving}><Save size={15} /> {runtimeSaving ? tr('Testing Firecrawl…', 'Firecrawlをテスト中…') : tr('Test Firecrawl & save runtime', 'Firecrawlをテストして保存')}</Button>
        </Card>
        </div>
        <aside className="settings-aside">
          <Card><div className="settings-icon"><Lock size={18} /></div><h3>{tr('Local credential storage', 'ローカル認証情報保存')}</h3><p>{tr('The API key is written to the project’s ignored .env file and never included in run artifacts.', 'APIキーはGit管理外の.envに保存され、実行成果物には含まれません。')}</p></Card>
          <Card><div className="settings-icon"><Sparkles size={18} /></div><h3>{tr('Prompt cache aware', 'プロンプトキャッシュ対応')}</h3><p>{tr('The fixed system prompt and schema stay at the start of every request so compatible providers can reuse the prefix.', '固定プロンプトとスキーマを先頭に置き、対応プロバイダーが接頭辞を再利用できるようにします。')}</p></Card>
          {provider?.docs && <a className="provider-doc-link" href={provider.docs} target="_blank" rel="noreferrer">{tr(`Open ${provider.label} documentation`, `${provider.label}のドキュメントを開く`)} <ExternalLink size={14} /></a>}
        </aside>
      </div>
    </div>
  )
}
