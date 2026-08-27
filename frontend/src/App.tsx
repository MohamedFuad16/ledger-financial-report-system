import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { api } from './lib/api'
import type { BenchmarkSummary, PanelKey, ProviderInfo, RunSummary, SchemaRow, SettingsData } from './types'
import { Sidebar } from './components/Sidebar'
import { Toast } from './components/ui'
import { DashboardPage } from './pages/DashboardPage'
import { HistoryPage } from './pages/HistoryPage'
import { CorpusPage } from './pages/CorpusPage'
import { SchemaPage } from './pages/SchemaPage'
import { SettingsPage } from './pages/SettingsPage'
import { StrategyPage } from './pages/StrategyPage'
import { useLocale } from './lib/i18n'

const panels: PanelKey[] = ['dashboard', 'strategy1', 'strategy2', 'strategy3', 'history', 'corpus', 'schema', 'settings']

function panelFromHash(): PanelKey {
  const key = window.location.hash.replace(/^#\/?/, '') as PanelKey
  return panels.includes(key) ? key : 'dashboard'
}

// Storage access throws outright when site data is blocked, in some embedded
// webviews, and in third-party frame contexts. These run during render and in
// effects, so an unguarded throw blanks the whole app. lib/i18n, lib/currency
// and lib/benchmarkSource already guard their reads; App did not.
function readStored(key: string): string | null {
  try { return window.localStorage.getItem(key) } catch { return null }
}

function writeStored(key: string, value: string): void {
  try { window.localStorage.setItem(key, value) } catch { /* storage unavailable */ }
}

export default function App() {
  const { tr } = useLocale()
  const [panel, setPanel] = useState<PanelKey>(panelFromHash)
  const [theme, setTheme] = useState<'light' | 'dark'>(() => readStored('ledger-theme') === 'dark' ? 'dark' : 'light')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => readStored('ledger-sidebar-collapsed') === 'true')
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [benchmarkRuns, setBenchmarkRuns] = useState<RunSummary[]>([])
  const [benchmarkSummary, setBenchmarkSummary] = useState<BenchmarkSummary | null>(null)
  const [schema, setSchema] = useState<SchemaRow[]>([])
  const [settings, setSettings] = useState<SettingsData | null>(null)
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState<{ id: number; message: string; tone: 'success' | 'error' }>({ id: 0, message: '', tone: 'success' })
  const toastSequence = useRef(0)

  const notify = useCallback((message: string, tone: 'success' | 'error') => {
    // Each toast dismisses itself by identity, not by matching its own text.
    // Matching on text meant a repeated message ("Run deleted.") let the first
    // timer clear the second toast early, cutting it short by however long
    // separated the two.
    const id = (toastSequence.current += 1)
    setToast({ id, message, tone })
    window.setTimeout(() => setToast((current) => current.id === id ? { ...current, message: '' } : current), 5000)
  }, [])

  const refreshRuns = useCallback(async () => {
    try {
      setRuns(await api.runs())
      setBenchmarkRuns(await api.benchmarkRuns())
      setBenchmarkSummary(await api.benchmarkSummary())
    }
    catch (error) { notify(error instanceof Error ? error.message : tr('Could not load run history.', '実行履歴を読み込めませんでした。'), 'error') }
  }, [notify])

  const refreshSettings = useCallback(async () => {
    try { setSettings(await api.settings()) }
    catch (error) { notify(error instanceof Error ? error.message : tr('Could not load settings.', '設定を読み込めませんでした。'), 'error') }
  }, [notify])

  useEffect(() => {
    const onHash = () => setPanel(panelFromHash())
    window.addEventListener('hashchange', onHash)
    Promise.all([
      api.runs().then(setRuns),
      api.benchmarkRuns().then(setBenchmarkRuns),
      api.benchmarkSummary().then(setBenchmarkSummary),
      api.schema().then(setSchema),
      api.settings().then(setSettings),
      api.providers().then((data) => setProviders(data.providers)),
    ]).catch((error) => notify(error instanceof Error ? error.message : tr('The workspace could not be loaded.', 'ワークスペースを読み込めませんでした。'), 'error')).finally(() => setLoading(false))
    return () => window.removeEventListener('hashchange', onHash)
  }, [notify])

  // The benchmark feed is server-global (other workers append runs), so an
  // open tab must refetch it when the Overview becomes active, not only on mount.
  useEffect(() => {
    if (panel !== 'dashboard') return
    api.benchmarkRuns().then(setBenchmarkRuns).catch(() => { /* keep the last loaded feed */ })
    api.benchmarkSummary().then(setBenchmarkSummary).catch(() => { /* keep the last loaded summary */ })
  }, [panel])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    writeStored('ledger-theme', theme)
  }, [theme])

  useEffect(() => {
    // Telemetry is best-effort and must never be able to take the app down.
    // crypto.randomUUID is secure-context only, so it is undefined when the
    // dev server is reached over plain http on a LAN address — the obvious way
    // to demo this. lib/api.ts guards the same call; this one did not.
    const reportedKey = 'ledger-visit-reported'
    const sessionKey = 'ledger-visit-session'
    let stored: Storage
    try {
      stored = window.sessionStorage
      if (stored.getItem(reportedKey)) return
    } catch { return }
    const randomId = () => (
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
    )
    let sessionId: string
    try {
      sessionId = stored.getItem(sessionKey) || randomId()
      stored.setItem(sessionKey, sessionId)
      stored.setItem(reportedKey, 'pending')
    } catch { return }
    const mark = (value: string | null) => {
      try { value === null ? stored.removeItem(reportedKey) : stored.setItem(reportedKey, value) }
      catch { /* storage went away mid-flight */ }
    }
    void api.trackVisit({
      session_id: sessionId,
      path: `${window.location.pathname}${window.location.hash}`,
      referrer: document.referrer,
      locale: navigator.language,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      viewport: `${window.innerWidth}x${window.innerHeight}`,
      user_agent: navigator.userAgent,
    }).then(() => mark('sent')).catch(() => mark(null))
  }, [])

  useEffect(() => {
    writeStored('ledger-sidebar-collapsed', String(sidebarCollapsed))
  }, [sidebarCollapsed])

  useEffect(() => {
    if (!sidebarOpen || !window.matchMedia('(max-width: 900px)').matches) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = previousOverflow }
  }, [sidebarOpen])

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
    document.documentElement.scrollTop = 0
    document.body.scrollTop = 0
    document.querySelector<HTMLElement>('.main-content')?.scrollTo({ top: 0, left: 0, behavior: 'auto' })
  }, [panel])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      // Never steal the shortcut from a field the user is typing in: Cmd+K
      // inside the system-prompt textarea used to navigate away and discard
      // the unsaved prompt.
      const target = event.target as HTMLElement | null
      const isEditing = !!target && (target.isContentEditable
        || target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT')
      if (!isEditing && (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        navigate('strategy1')
      }
      if (event.key === 'Escape') setSidebarOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const navigate = (next: PanelKey) => {
    if (window.location.hash !== `#${next}`) window.location.hash = next
    else setPanel(next)
  }

  const deleteRun = async (run: RunSummary) => {
    if (!window.confirm(tr(`Delete ${run.run_id}? This removes its stored artifacts.`, `${run.run_id} を削除しますか？保存された成果物も削除されます。`))) return
    try {
      await api.deleteRun(run.run_id)
      await refreshRuns()
      notify(tr('Run deleted.', '実行を削除しました。'), 'success')
    } catch (error) { notify(error instanceof Error ? error.message : tr('Could not delete the run.', '実行を削除できませんでした。'), 'error') }
  }

  const deleteRuns = async (targets: RunSummary[]) => {
    if (!targets.length || !window.confirm(tr(`Delete ${targets.length} selected runs and their stored artifacts?`, `選択した${targets.length}件の実行と保存成果物を削除しますか？`))) return
    // allSettled, not all: Promise.all rejects on the first failure and skipped
    // the refresh, so the runs that WERE deleted stayed on screen and the next
    // click 404'd on ghosts. Always resync, then report honestly.
    const results = await Promise.allSettled(targets.map((run) => api.deleteRun(run.run_id)))
    await refreshRuns()
    const failed = results.filter((result) => result.status === 'rejected').length
    const deleted = targets.length - failed
    if (!failed) {
      notify(tr(`${deleted} runs deleted.`, `${deleted}件の実行を削除しました。`), 'success')
    } else {
      notify(tr(
        `${deleted} of ${targets.length} runs deleted; ${failed} could not be removed.`,
        `${targets.length}件中${deleted}件を削除しました。${failed}件は削除できませんでした。`,
      ), 'error')
    }
  }

  const deleteAllRuns = async () => {
    if (!runs.length || !window.confirm(tr(`Delete all ${runs.length} runs and their stored artifacts? This cannot be undone.`, `${runs.length}件すべての実行と保存成果物を削除しますか？この操作は元に戻せません。`))) return
    try {
      const result = await api.deleteAllRuns()
      await refreshRuns()
      notify(tr(`${result.deleted} runs deleted.`, `${result.deleted}件の実行を削除しました。`), 'success')
    } catch (error) { notify(error instanceof Error ? error.message : tr('Could not delete all runs.', 'すべての実行を削除できませんでした。'), 'error') }
  }

  return (
    <div className={`app-shell${sidebarCollapsed ? ' sidebar-is-collapsed' : ''}`}>
      <Sidebar active={panel} onNavigate={navigate} theme={theme} onThemeToggle={() => setTheme((current) => current === 'light' ? 'dark' : 'light')} open={sidebarOpen} onOpenChange={setSidebarOpen} collapsed={sidebarCollapsed} onCollapsedChange={setSidebarCollapsed} />
      <main className="main-content">
        {panel === 'dashboard' && <DashboardPage runs={benchmarkRuns} benchmarkSummary={benchmarkSummary} loading={loading} onNavigate={navigate} />}
        {panel === 'strategy1' && <StrategyPage kind="s1" runs={runs} onRefreshRuns={refreshRuns} onNotify={notify} />}
        {panel === 'strategy2' && <StrategyPage kind="s2" runs={runs} onRefreshRuns={refreshRuns} onNotify={notify} />}
        {panel === 'strategy3' && <StrategyPage kind="s3" runs={runs} onRefreshRuns={refreshRuns} onNotify={notify} />}
        {panel === 'history' && <HistoryPage runs={runs} onDeleteRun={deleteRun} onDeleteRuns={deleteRuns} onDeleteAllRuns={deleteAllRuns} />}
        {panel === 'corpus' && <CorpusPage settings={settings} onNotify={notify} />}
        {panel === 'schema' && <SchemaPage rows={schema} />}
        {panel === 'settings' && <SettingsPage settings={settings} providers={providers} onSaved={refreshSettings} onNotify={notify} />}
      </main>
      <Toast message={toast.message} tone={toast.tone} onClose={() => setToast((current) => ({ ...current, message: '' }))} />
    </div>
  )
}
