// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { LocaleProvider } from '../lib/i18n'
import type { CorpusDocument } from '../types'
import { CorpusPicker } from './CorpusPicker'

const documents: CorpusDocument[] = [
  { company: '3M', company_slug: '3M', fiscal_year: 2022, source_url: 'https://example.com/3m.pdf', local_path: 'corpus_dataset/3M/2022/stamp/3M_annual_report_2022.pdf', filename: '3M_annual_report_2022.pdf', downloaded_at: '2026-08-20T00:00:00Z', sha256: 'three-m', pages: 142, readable_pages: 142, balance_sheet_page: 50, currency: 'USD', screened: 'ok', fiscal_year_confirmed: true },
  { company: 'LayerX', company_slug: 'LayerX', fiscal_year: 2024, source_url: 'https://example.com/layerx.pdf', local_path: 'corpus_dataset/LayerX/2024/stamp/LayerX_annual_report_2024.pdf', filename: 'LayerX_annual_report_2024.pdf', downloaded_at: '2026-08-20T00:00:00Z', sha256: 'layer-x', pages: 90, readable_pages: 90, balance_sheet_page: 20, currency: 'JPY', screened: 'review', fiscal_year_confirmed: true },
]

describe('CorpusPicker', () => {
  it('searches stored companies and selects a single report', () => {
    const onSelectionChange = vi.fn()
    render(<LocaleProvider><CorpusPicker documents={documents} selected={[]} mode="single" onModeChange={() => undefined} onSelectionChange={onSelectionChange} /></LocaleProvider>)

    fireEvent.change(screen.getByPlaceholderText('Search company or year'), { target: { value: 'LayerX' } })
    expect(screen.queryByText('3M')).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('LayerX'))
    expect(onSelectionChange).toHaveBeenCalledWith(['layer-x'])
  })
})
