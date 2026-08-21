import { motion } from 'framer-motion'
import {
  BarChart3,
  Beaker,
  BookOpen,
  FileClock,
  FolderSearch2,
  FlaskConical,
  ExternalLink,
  FilePlus2,
  Menu,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Sun,
  X,
} from 'lucide-react'
import type { PanelKey } from '../types'
import { clsx } from 'clsx'
import { useLocale } from '../lib/i18n'

export function Sidebar({
  active,
  onNavigate,
  theme,
  onThemeToggle,
  open,
  onOpenChange,
  collapsed,
  onCollapsedChange,
}: {
  active: PanelKey
  onNavigate: (key: PanelKey) => void
  theme: 'light' | 'dark'
  onThemeToggle: () => void
  open: boolean
  onOpenChange: (open: boolean) => void
  collapsed: boolean
  onCollapsedChange: (collapsed: boolean) => void
}) {
  const { locale, setLocale, tr } = useLocale()
  const groups: Array<{ label: string; items: Array<{ key: PanelKey; label: string; icon: typeof BarChart3; count?: string }> }> = [
    {
      label: tr('Workspace', 'ワークスペース'),
      items: [
        { key: 'dashboard', label: tr('Overview', '概要'), icon: BarChart3 },
        { key: 'strategy1', label: tr('Strategy 1', '戦略 1'), icon: Beaker, count: '01' },
        { key: 'strategy2', label: tr('Strategy 2', '戦略 2'), icon: FlaskConical, count: '02' },
      ],
    },
    {
      label: tr('Library', 'ライブラリ'),
      items: [
        { key: 'history', label: tr('Run history', '実行履歴'), icon: FileClock },
        { key: 'corpus', label: tr('Report corpus', 'レポートコーパス'), icon: FolderSearch2 },
        { key: 'schema', label: tr('Target schema', '対象スキーマ'), icon: BookOpen, count: '27' },
      ],
    },
  ]
  const navigate = (key: PanelKey) => {
    onNavigate(key)
    onOpenChange(false)
  }

  return (
    <>
      <header className="mobile-header">
        <button aria-label={tr('Open navigation', 'ナビゲーションを開く')} aria-controls="primary-sidebar" aria-expanded={open} onClick={() => onOpenChange(true)}><Menu size={19} /></button>
        <Wordmark />
        <button aria-label={tr('Toggle theme', 'テーマを切り替える')} onClick={onThemeToggle}>{theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}</button>
      </header>
      <button className={clsx('sidebar-scrim', open && 'is-open')} aria-label={tr('Close navigation', 'ナビゲーションを閉じる')} onClick={() => onOpenChange(false)} />
      <aside id="primary-sidebar" className={clsx('sidebar', open && 'is-open', collapsed && 'is-collapsed')}>
        <div className="sidebar-brand">
          <Wordmark />
          <button className="sidebar-collapse" aria-label={collapsed ? tr('Expand navigation', 'ナビゲーションを開く') : tr('Collapse navigation', 'ナビゲーションを閉じる')} onClick={() => onCollapsedChange(!collapsed)}>
            {collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
          </button>
          <button className="mobile-close" aria-label={tr('Close navigation', 'ナビゲーションを閉じる')} onClick={() => onOpenChange(false)}><X size={18} /></button>
        </div>

        <button className="new-run-button" onClick={() => navigate('strategy2')} title={tr('New extraction', '新規抽出')}>
          <FilePlus2 size={17} strokeWidth={1.9} />
          <span>{tr('New extraction', '新規抽出')}</span>
          <kbd>⌘ K</kbd>
        </button>

        <nav aria-label={tr('Primary navigation', 'メインナビゲーション')}>
          {groups.map((group) => (
            <div className="nav-group" key={group.label}>
              <div className="nav-group-label">{group.label}</div>
              {group.items.map((item) => {
                const Icon = item.icon
                const selected = active === item.key
                return (
                  <button className={clsx('nav-item', selected && 'is-active')} onClick={() => navigate(item.key)} key={item.key}>
                    {selected && <motion.span className="active-nav-pill" layoutId="active-nav" transition={{ type: 'spring', stiffness: 430, damping: 38 }} />}
                    <Icon size={16} />
                    <span>{item.label}</span>
                    {item.count && <small>{item.count}</small>}
                  </button>
                )
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button className={clsx('nav-item', active === 'settings' && 'is-active')} onClick={() => navigate('settings')}>
            {active === 'settings' && <motion.span className="active-nav-pill" layoutId="active-nav" />}
            <Settings size={16} /><span>{tr('Settings', '設定')}</span>
          </button>
          <button className="theme-button" onClick={onThemeToggle}>
            {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
            <span>{theme === 'light' ? tr('Dark appearance', 'ダーク表示') : tr('Light appearance', 'ライト表示')}</span>
          </button>
          <div className="locale-switcher" aria-label={tr('Language', '言語')}>
            <button className={locale === 'en' ? 'is-active' : ''} onClick={() => setLocale('en')}>EN</button>
            <button className={locale === 'ja' ? 'is-active' : ''} onClick={() => setLocale('ja')}>日本語</button>
          </div>
          <a className="creator-link" href="https://www.mohamedfuad.com/" target="_blank" rel="noreferrer">
            <span className="creator-copy">
              <span>{tr('Built by', '制作')}</span>
              <strong>{locale === 'ja' ? 'モハメド　フアド' : 'mohamed fuad'}</strong>
            </span>
            <ExternalLink size={15} aria-label={tr('Open portfolio', 'ポートフォリオを開く')} />
          </a>
        </div>
      </aside>
    </>
  )
}

function Wordmark() {
  const { tr } = useLocale()
  return <div className="wordmark"><img src="/ledger-icon.png" alt="" /><span><b>LEDGER</b><small>{tr('financial report system', '財務レポートシステム')}</small></span></div>
}
