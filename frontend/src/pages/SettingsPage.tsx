import { useEffect, useMemo, useState } from 'react'
import { Activity, Cable, CheckCircle2, Eye, EyeOff, ExternalLink, Flame, Gauge, KeyRound, Lock, Save, Server, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import type { ProviderInfo, SettingsData } from '../types'
import { Badge, Button, Card, SectionHeading } from '../components/ui'
import { useLocale } from '../lib/i18n'
import { currencyPreference, saveCurrencyPreference, type DisplayCurrency } from '../lib/currency'
import { benchmarkSource, benchmarkSourceMeta, saveBenchmarkSource, type BenchmarkSource } from '../lib/benchmarkSource'

function ProviderLogo({ providerKey }: { providerKey: string }) {
  const logos: Record<string, { src: string; alt: string }> = {
    openrouter: { src: '/providers/openrouter.png', alt: 'OpenRouter' },
    openai: { src: '/providers/openai.svg', alt: 'OpenAI' },
    zai: { src: '/providers/zai.svg', alt: 'Z.AI' },
    'zai-coding': { src: '/providers/zai.svg', alt: 'Z.AI' },
    glm: { src: '/providers/zai.svg', alt: 'Z.AI' },
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
  const [resultsSource, setResultsSource] = useState<BenchmarkSource>(() => benchmarkSource())
  const [outputCurrency, setOutputCurrency] = useState<DisplayCurrency>(() => currencyPreference().currency)
  const [jpyPerUsd, setJpyPerUsd] = useState(() => currencyPreference().jpyPerUsd)
  const provider = useMemo(() => providers.find((item) => item.key === providerKey), [providers, providerKey])
  const GLM_KEYS = ['zai-coding', 'zai']
  const isGlmSelected = GLM_KEYS.includes(providerKey)
  // One tile represents both GLM destinations; the endpoint toggle below picks
  // between the Coding Plan endpoint and the Open Platform base URL.
  const displayProviders = useMemo(() => {
    const merged: (ProviderInfo & { glmGroup?: boolean })[] = []
    for (const item of providers) {
      if (GLM_KEYS.includes(item.key)) {
        if (!merged.some((entry) => entry.glmGroup)) merged.push({ ...item, key: 'glm', glmGroup: true })
        continue
      }
      merged.push(item)
    }
    return merged
  }, [providers])
  const wiredOpenRouterModels = [
    { id: 'google/gemini-3.7-flash', label: 'Gemini 3.7 Flash' },
    { id: 'openai/gpt-5-mini', label: 'GPT-5 Mini' },
  ]
  const providerCredentialSaved = Boolean(settings?.has_key && settings.provider === providerKey && settings.base_url.replace(/\/$/, '') === baseUrl.replace(/\/$/, ''))
  const finiteRate = (value: unknown, fallback: number) => Number.isFinite(Number(value)) ? Number(value) : fallback

  useEffect(() => {
    if (!settings) return
    setProviderKey(settings.provider); setModel(settings.model); setBaseUrl(settings.base_url); setReasoningEnabled(settings.reasoning_effort !== 'none'); setTemperature(settings.temperature); setMaxConcurrency(settings.max_concurrency); setAutoConcurrency(settings.auto_concurrency)
  }, [settings])

  useEffect(() => {
    saveCurrencyPreference({ currency: outputCurrency, jpyPerUsd })
  }, [outputCurrency, jpyPerUsd])

  const chooseProvider = (key: string) => {
    // The merged GLM tile keeps the currently selected GLM endpoint and
    // defaults new selections to the Coding Plan endpoint.
    const resolved = key === 'glm' ? (isGlmSelected ? providerKey : 'zai-coding') : key
    const next = providers.find((item) => item.key === resolved)
    setProviderKey(resolved)
    if (next) { setModel(next.default_model); setBaseUrl(next.base_url) }
  }

  const saveRuntime = async () => {
    setRuntimeSaving(true)
    try {
      await api.saveRuntimeSettings({ max_concurrency: maxConcurrency, auto_concurrency: autoConcurrency, firecrawl_api_key: '' })
      saveCurrencyPreference({ currency: outputCurrency, jpyPerUsd })
      await onSaved()
      onNotify(tr('Runtime settings saved locally.', 'ランタイム設定を保存しました。'), 'success')
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
      <header className="page-header"><div><div className="page-kicker">{tr('Workspace configuration', 'ワークスペース設定')}</div><h1>{tr('Connections & runtime', '接続とランタイム')}</h1><p>{tr('Manage model credentials, the benchmark results source, display currency, and one global adaptive request ceiling.', 'モデル認証情報、ベンチマーク結果ソース、表示通貨、グローバルな同時実行上限を管理します。')}</p></div></header>
      <div className="settings-layout">
        <div className="settings-stack">
        <Card className="settings-main">
          <SectionHeading eyebrow={tr('Provider', 'プロバイダー')} title={tr('Model gateway', 'モデルゲートウェイ')} description={tr('Changing the destination requires re-entering the API key.', '接続先を変更する場合はAPIキーの再入力が必要です。')} />
          <div className="provider-grid">{displayProviders.map((item) => {
            const selected = item.key === 'glm' ? isGlmSelected : providerKey === item.key
            const subtitle = item.key === 'glm'
              ? tr('Coding Plan or Open Platform endpoint', 'コーディングプラン／オープンプラットフォーム')
              : item.automatic_prompt_caching ? tr('Automatic prompt cache', '自動プロンプトキャッシュ') : item.reasoning_style === 'thinking' ? tr('GLM thinking mode', 'GLM思考モード') : tr('Compatible endpoint', '互換エンドポイント')
            const label = item.key === 'glm' ? 'GLM (Z.AI)' : item.label
            return <button className={selected ? 'is-selected' : ''} onClick={() => chooseProvider(item.key)} key={item.key}><ProviderLogo providerKey={item.key} /><span><strong>{label}</strong><small>{subtitle}</small></span>{selected && <CheckCircle2 size={16} />}</button>
          })}</div>
          {isGlmSelected && <div className="provider-subselect"><span><strong>{tr('GLM endpoint', 'GLMエンドポイント')}</strong><small>{tr('Coding Plan keys work only on the Coding Plan endpoint; Open Platform keys use the standard base URL.', 'コーディングプランのキーは専用エンドポイントのみで有効です。オープンプラットフォームのキーは標準ベースURLを使用します。')}</small></span><div className="segmented-control"><button type="button" className={providerKey === 'zai-coding' ? 'is-active' : ''} onClick={() => chooseProvider('zai-coding')}>{tr('Coding Plan', 'コーディングプラン')}</button><button type="button" className={providerKey === 'zai' ? 'is-active' : ''} onClick={() => chooseProvider('zai')}>{tr('Open Platform base URL', 'オープンプラットフォームURL')}</button></div></div>}
          {providerKey === 'openrouter' && <div className="provider-subselect"><span><strong>{tr('OpenRouter model', 'OpenRouterモデル')}</strong><small>{tr('Both wired models are cheap and fast; Gemini 3.7 Flash is the default. Any other OpenRouter model ID can still be typed below.', 'どちらも低コストで高速です。既定はGemini 3.7 Flashです。他のモデルIDも下の欄に直接入力できます。')}</small></span><div className="segmented-control">{wiredOpenRouterModels.map((item) => <button type="button" key={item.id} className={model === item.id ? 'is-active' : ''} onClick={() => setModel(item.id)}>{item.label}</button>)}</div></div>}
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
          <SectionHeading eyebrow={tr('Runtime', 'ランタイム')} title={tr('Adaptive concurrency & display', '適応型同時実行と表示設定')} description={tr('This single ceiling applies to every strategy. The live limiter reduces it on HTTP 429, waits for Retry-After, and recovers gradually after successful calls.', 'この上限は全戦略に適用されます。HTTP 429では縮小し、Retry-Afterを待って、成功後に徐々に回復します。')} />
          <div className="runtime-grid">
            <label><span>{tr('Parallel request ceiling', '並列リクエスト上限')} <b>{maxConcurrency}</b></span><input type="range" min="1" max="20" step="1" value={maxConcurrency} onChange={(event) => setMaxConcurrency(Number(event.target.value))} /></label>
            <label className="toggle-setting"><span><strong>{tr('Automatic batch sizing', '自動バッチサイズ')}</strong><small>{tr('Use PDF count and estimated token load to choose the initial width.', 'PDF数と推定トークン量から初期並列数を選びます。')}</small></span><input type="checkbox" checked={autoConcurrency} onChange={(event) => setAutoConcurrency(event.target.checked)} /></label>
            <div className="display-currency-setting field-wide"><span><strong>{tr('Benchmark results source', 'ベンチマーク結果ソース')}</strong><small>{tr('Which model\'s completed runs the Overview dashboard aggregates. It updates automatically as new runs of that model finish.', 'Overviewダッシュボードが集計するモデルを選択します。選択モデルの新しい実行が完了すると自動的に反映されます。')}</small></span><div className="segmented-control benchmark-source-control">{(Object.keys(benchmarkSourceMeta) as BenchmarkSource[]).map((source) => <button key={source} type="button" className={resultsSource === source ? 'is-active' : ''} onClick={() => { setResultsSource(source); saveBenchmarkSource(source) }}>{tr(benchmarkSourceMeta[source].label, benchmarkSourceMeta[source].labelJa)}</button>)}</div></div>
            <div className="display-currency-setting field-wide"><span><strong>{tr('Output display currency', '出力表示通貨')}</strong><small>{tr('Default shows every value in the filing\u2019s own currency exactly as reported (M JPY for Japanese reports, M USD for 3M). Scoring always stays in the filing currency; USD/JPY apply a display-only conversion.', '既定では提出書類の通貨のまま（日本の報告書はM JPY、3MはM USD）表示します。評価は常に原通貨で行われ、USD/JPYは表示のみ換算します。')}</small></span><div className="segmented-control"><button className={outputCurrency === 'NATIVE' ? 'is-active' : ''} type="button" onClick={() => setOutputCurrency('NATIVE')}>{tr('As reported', '原通貨')}</button><button className={outputCurrency === 'USD' ? 'is-active' : ''} type="button" onClick={() => setOutputCurrency('USD')}>USD</button><button className={outputCurrency === 'JPY' ? 'is-active' : ''} type="button" onClick={() => setOutputCurrency('JPY')}>JPY</button></div></div>
            <label className="field-wide"><span>{tr('Display FX rate (JPY per USD)', '表示用為替レート（1 USDあたりJPY）')}</span><input type="number" min="1" step="0.01" value={jpyPerUsd} onChange={(event) => setJpyPerUsd(Math.max(1, Number(event.target.value) || 1))} /><small>{tr('Applied to displayed values only. Set the assignment-approved historical rate here.', '表示値だけに適用します。課題で承認された過去レートを設定してください。')}</small></label>
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
          <Button className="save-settings" onClick={saveRuntime} disabled={runtimeSaving}><Save size={15} /> {runtimeSaving ? tr('Saving…', '保存中…') : tr('Save runtime settings', 'ランタイム設定を保存')}</Button>
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
