// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { LocaleProvider } from '../lib/i18n'
import type { RunDetail } from '../types'
import { RunDrawer } from './RunDrawer'

afterEach(cleanup)

const detail = {
  ok: true,
  run_id: 'S3_TEST_001',
  strategy: 's3',
  experiment: 'intelligent_scan',
  pdf_file: 'Example_annual_report_2022.pdf',
  fiscal_year: '2022',
  company: 'Example',
  currency: 'USD',
  metrics: { accuracy: 96.3, coverage: 100, precision: 96.3 },
  rows: [
    {
      classification: 'Current Assets', subclassification: 'Quick Assets',
      item: 'Cash & Cash Equivalents', description: '', answer_m_usd: 3655,
      confidence: 0.95, accepted: true, source_page: 50, source_label: null, evidence: null,
    },
    {
      classification: 'Fixed Assets', subclassification: 'Financial Assets',
      item: 'Other Financial Assets', description: '', answer_m_usd: 1563,
      confidence: 0.7, accepted: false, source_page: 68, source_label: null, evidence: null,
    },
  ],
} as unknown as RunDetail

describe('RunDrawer confidence display (ADR-0031)', () => {
  it('shows a sub-0.80-confidence value instead of hiding it, while still dimming the row', () => {
    render(<LocaleProvider><RunDrawer detail={detail} loading={false} onClose={() => {}} /></LocaleProvider>)

    // The low-confidence value is displayed, never replaced with an em dash.
    const lowConfidenceCell = screen.getByText('1,563')
    expect(lowConfidenceCell).toBeInTheDocument()
    expect(lowConfidenceCell.closest('tr')).toHaveClass('is-rejected')
    // The accepted count badge still reports review priority.
    expect(screen.getByText(/1\/27/)).toBeInTheDocument()
  })
})

describe('RunDrawer detail strip layout', () => {
  it('renders the copy action as a direct child of the stats strip', () => {
    const { container } = render(<LocaleProvider><RunDrawer detail={detail} loading={false} onClose={() => {}} /></LocaleProvider>)

    const strip = container.querySelector('.detail-strip')!
    // The strip is a CSS grid with an explicit track list, which jsdom cannot
    // lay out. Pin the shape the grid is sized for: when this count changes,
    // update `.detail-strip { grid-template-columns }` in editor-theme.css to
    // match, or the action wraps onto a second row under the first stat.
    expect(strip.querySelectorAll(':scope > div')).toHaveLength(5)
    expect(strip.querySelector(':scope > .button')).toBeInTheDocument()
  })
})
