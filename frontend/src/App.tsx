import { useCallback, useEffect, useLayoutEffect, useState } from 'react'
import { api } from './lib/api'
import type { PanelKey, ProviderInfo, RunSummary, SchemaRow, SettingsData } from './types'
import { Sidebar } from './components/Sidebar'
import { Toast } from './components/ui'
import { DashboardPage } from './pages/DashboardPage'
import { HistoryPage } from './pages/HistoryPage'
import { CorpusPage } from './pages/CorpusPage'
import { PlannedPage } from './pages/PlannedPage'
import { SchemaPage } from './pages/SchemaPage'
import { SettingsPage } from './pages/SettingsPage'
import { StrategyPage } from './pages/StrategyPage'
import { useLocale } from './lib/i18n'

const panels: PanelKey[] = ['dashboard', 'strategy1', 'strategy2', 'strategy3', 'strategy4', 'history', 'corpus', 'schema', 'settings']

function panelFromHash(): PanelKey {
  const key = window.location.hash.replace(/^#\/?/, '') as PanelKey
  return panels.includes(key) ? key : 'dashboard'
}

export default function App() {
  const { tr } = useLocale()
  const [panel, setPanel] = useState<PanelKey>(panelFromHash)
  const [theme, setTheme] = useState<'light' | 'dark'>(() => localStorage.getItem('ledger-theme') === 'dark' ? 'dark' : 'light')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem('ledger-sidebar-collapsed') === 'true')
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [schema, setSchema] = useState<SchemaRow[]>([])
  const [settings, setSettings] = useState<SettingsData | null>(null)
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState<{ message: string; tone: 'success' | 'error' }>({ message: '', tone: 'success' })

  const notify = useCallback((message: string, tone: 'success' | 'error') => {
    setToast({ message, tone })
    window.setTimeout(() => setToast((current) => current.message === message ? { ...current, message: '' } : current), 5000)
  }, [])

  const refreshRuns = useCallback(async () => {
    try { setRuns(await api.runs()) }
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
      api.schema().then(setSchema),
      api.settings().then(setSettings),
      api.providers().then((data) => setProviders(data.providers)),
    ]).catch((error) => notify(error instanceof Error ? error.message : tr('The workspace could not be loaded.', 'ワークスペースを読み込めませんでした。'), 'error')).finally(() => setLoading(false))
    return () => window.removeEventListener('hashchange', onHash)
  }, [notify])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('ledger-theme', theme)
  }, [theme])

  useEffect(() => {
    const reportedKey = 'ledger-visit-reported'
    if (window.sessionStorage.getItem(reportedKey)) return
    const sessionKey = 'ledger-visit-session'
    const sessionId = window.sessionStorage.getItem(sessionKey) || window.crypto.randomUUID()
    window.sessionStorage.setItem(sessionKey, sessionId)
    window.sessionStorage.setItem(reportedKey, 'pending')
    void api.trackVisit({
      session_id: sessionId,
      path: `${window.location.pathname}${window.location.hash}`,
      referrer: document.referrer,
      locale: navigator.language,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      viewport: `${window.innerWidth}x${window.innerHeight}`,
      user_agent: navigator.userAgent,
    }).then(() => window.sessionStorage.setItem(reportedKey, 'sent')).catch(() => {
      window.sessionStorage.removeItem(reportedKey)
    })
  }, [])

  useEffect(() => {
    localStorage.setItem('ledger-sidebar-collapsed', String(sidebarCollapsed))
  }, [sidebarCollapsed])

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
    document.documentElement.scrollTop = 0
    document.body.scrollTop = 0
    document.querySelector<HTMLElement>('.main-content')?.scrollTo({ top: 0, left: 0, behavior: 'auto' })
  }, [panel])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        navigate('strategy2')
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
    try {
      await Promise.all(targets.map((run) => api.deleteRun(run.run_id)))
      await refreshRuns()
      notify(tr(`${targets.length} runs deleted.`, `${targets.length}件の実行を削除しました。`), 'success')
    } catch (error) { notify(error instanceof Error ? error.message : tr('Could not delete the selected runs.', '選択した実行を削除できませんでした。'), 'error') }
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
        {panel === 'dashboard' && <DashboardPage runs={runs} loading={loading} onNavigate={navigate} />}
        {panel === 'strategy1' && <StrategyPage kind="s1" runs={runs} onRefreshRuns={refreshRuns} onNotify={notify} />}
        {panel === 'strategy2' && <StrategyPage kind="s2" runs={runs} onRefreshRuns={refreshRuns} onNotify={notify} />}
        {panel === 'strategy3' && <PlannedPage strategy={3} onNavigate={navigate} />}
        {panel === 'strategy4' && <PlannedPage strategy={4} onNavigate={navigate} />}
        {panel === 'history' && <HistoryPage runs={runs} onDeleteRun={deleteRun} onDeleteRuns={deleteRuns} onDeleteAllRuns={deleteAllRuns} />}
        {panel === 'corpus' && <CorpusPage settings={settings} onNotify={notify} />}
        {panel === 'schema' && <SchemaPage rows={schema} />}
        {panel === 'settings' && <SettingsPage settings={settings} providers={providers} onSaved={refreshSettings} onNotify={notify} />}
      </main>
      <Toast message={toast.message} tone={toast.tone} onClose={() => setToast((current) => ({ ...current, message: '' }))} />
    </div>
  )
}
