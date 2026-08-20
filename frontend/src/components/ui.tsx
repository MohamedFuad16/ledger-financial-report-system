import { AnimatePresence, motion, type HTMLMotionProps } from 'framer-motion'
import { AlertCircle, Check, ChevronDown, LoaderCircle, X } from 'lucide-react'
import type { PropsWithChildren, ReactNode } from 'react'
import { clsx } from 'clsx'
import { useLocale } from '../lib/i18n'

export function Button({
  className,
  children,
  variant = 'primary',
  ...props
}: HTMLMotionProps<'button'> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger' }) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      whileHover={{ y: -1 }}
      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
      className={clsx('button', `button-${variant}`, className)}
      {...props}
    >
      {children}
    </motion.button>
  )
}

export function Card({ children, className }: PropsWithChildren<{ className?: string }>) {
  return <section className={clsx('card', className)}>{children}</section>
}

export function Badge({
  children,
  tone = 'neutral',
}: PropsWithChildren<{ tone?: 'neutral' | 'green' | 'blue' | 'amber' | 'red' | 'purple' }>) {
  return <span className={clsx('badge', `badge-${tone}`)}>{children}</span>
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {action && <div className="section-action">{action}</div>}
    </div>
  )
}

export function MetricCard({
  label,
  value,
  detail,
  accent,
}: {
  label: string
  value: ReactNode
  detail: string
  accent?: string
}) {
  return (
    <Card className="metric-card">
      <div className="metric-topline">
        <span>{label}</span>
        <i style={{ background: accent }} />
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-detail">{detail}</div>
    </Card>
  )
}

export function Disclosure({
  title,
  subtitle,
  children,
  defaultOpen = false,
}: PropsWithChildren<{ title: string; subtitle?: string; defaultOpen?: boolean }>) {
  return (
    <details className="disclosure" open={defaultOpen}>
      <summary>
        <span>
          <strong>{title}</strong>
          {subtitle && <small>{subtitle}</small>}
        </span>
        <ChevronDown size={16} />
      </summary>
      <div className="disclosure-body">{children}</div>
    </details>
  )
}

export function EmptyState({
  icon,
  title,
  description,
}: {
  icon?: ReactNode
  title: string
  description: string
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  )
}

export function LoadingState({ label, detail }: { label?: string; detail?: string }) {
  const { tr } = useLocale()
  return (
    <div className="loading-state" role="status">
      <span className="pixel-loader" aria-hidden="true">
        {Array.from({ length: 9 }, (_, index) => <i key={index} />)}
      </span>
      <strong>{label || tr('Processing', '処理中')}</strong>
      {detail && <span>{detail}</span>}
    </div>
  )
}

export function InlineStatus({
  status,
  children,
}: PropsWithChildren<{ status: 'success' | 'error' | 'loading' | 'neutral' }>) {
  const Icon = status === 'success' ? Check : status === 'error' ? AlertCircle : status === 'loading' ? LoaderCircle : null
  return (
    <span className={clsx('inline-status', `inline-status-${status}`)}>
      {Icon && <Icon size={14} className={status === 'loading' ? 'spin' : ''} />}
      {children}
    </span>
  )
}

export function Toast({ message, tone, onClose }: { message: string; tone: 'success' | 'error'; onClose: () => void }) {
  const { tr } = useLocale()
  return (
    <AnimatePresence>
      {message && (
        <motion.div
          className={clsx('toast', `toast-${tone}`)}
          initial={{ opacity: 0, y: 16, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10 }}
          role="status"
        >
          {tone === 'success' ? <Check size={16} /> : <AlertCircle size={16} />}
          <span>{message}</span>
          <button aria-label={tr('Dismiss notification', '通知を閉じる')} onClick={onClose}><X size={15} /></button>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
