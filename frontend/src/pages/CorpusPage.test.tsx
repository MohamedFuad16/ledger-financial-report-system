// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LocaleProvider } from '../lib/i18n'
import { api } from '../lib/api'
import type { CorpusDocument, CorpusManifest, CorpusVerification, CorpusVerificationRow } from '../types'
import { CorpusPage } from './CorpusPage'

const document: CorpusDocument = {
  company: 'Example',
  company_slug: 'Example',
  fiscal_year: 2024,
  source_url: 'https://example.com/report.pdf',
  local_path: 'corpus_dataset/Example/2024/Example_annual_report_2024.pdf',
  filename: 'Example_annual_report_2024.pdf',
  downloaded_at: '2026-08-22T00:00:00Z',
  sha256: 'a'.repeat(64),
  pages: 100,
  readable_pages: 100,
  balance_sheet_page: 42,
  currency: 'USD',
  screened: 'ok',
  fiscal_year_confirmed: true,
  official_source_verified: true,
  verification_status: 'human_review_required',
  candidate_extracted: false,
  candidate_count: 0,
}

const manifest: CorpusManifest = {
  version: 1,
  updated_at: '2026-08-22T00:00:00Z',
  documents: [document],
  summary: { documents: 1, companies: 1, ok: 1, review: 0, unreadable: 0, verified: 0, human_review_required: 1 },
}

const rows: CorpusVerificationRow[] = Array.from({ length: 27 }, (_, index) => ({
  classification: 'Current Assets',
  subclassification: index === 0 ? 'Cash' : 'Other',
  item: index === 0 ? 'Cash & Cash Equivalents' : `Asset row ${index + 1}`,
  answer_m_usd: index === 0 ? 125 : index,
  source_page: 42,
  evidence: `PDF evidence ${index + 1}`,
  agreement_count: 3,
  successful_passes: 3,
  stability: 'exact',
}))

const extracted: CorpusVerification = {
  document_id: document.sha256,
  company: document.company,
  fiscal_year: document.fiscal_year,
  filename: document.filename,
  sha256: document.sha256,
  status: 'human_review_required',
  candidate_extracted: true,
  extracted_row_count: 27,
  consensus_summary: {
    requested_passes: 3,
    successful_passes: 3,
    exact_agreement_rows: 27,
    stable_rows: 0,
    disagreement_rows: 0,
    missing_rows: 0,
  },
  rows,
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('CorpusPage answer review', () => {
  it('extracts and prefills PDF answers before allowing corrections and approval', async () => {
    vi.spyOn(api, 'corpus').mockResolvedValue(manifest)
    vi.spyOn(api, 'corpusJobs').mockResolvedValue({ jobs: [] })
    vi.spyOn(api, 'corpusVerification').mockResolvedValue({ ...extracted, candidate_extracted: false, extracted_row_count: 0, rows: [] })
    const extract = vi.spyOn(api, 'extractCorpusVerification').mockResolvedValue(extracted)
    const approve = vi.spyOn(api, 'approveCorpusVerification').mockImplementation(async (_id, approvedRows) => ({
      ...extracted,
      status: 'human_verified',
      rows: approvedRows,
    }))

    render(<LocaleProvider><CorpusPage settings={null} onNotify={vi.fn()} /></LocaleProvider>)

    fireEvent.click(await screen.findByRole('button', { name: 'Review answers' }))
    expect(await screen.findByText('Extracted prefill — verify, then correct')).toBeInTheDocument()
    expect(extract).toHaveBeenCalledWith(document.sha256)

    const cash = screen.getByLabelText('Cash & Cash Equivalents answer')
    expect(cash).toHaveValue(125)
    fireEvent.change(cash, { target: { value: '130' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save & approve reviewed answers' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save & confirm approval' }))

    await waitFor(() => expect(approve).toHaveBeenCalled())
    expect(approve.mock.calls[0][0]).toBe(document.sha256)
    expect(approve.mock.calls[0][1][0].answer_m_usd).toBe(130)
  })

  it('shows a retry state instead of a blank manual-entry table when extraction fails', async () => {
    vi.spyOn(api, 'corpus').mockResolvedValue(manifest)
    vi.spyOn(api, 'corpusJobs').mockResolvedValue({ jobs: [] })
    vi.spyOn(api, 'corpusVerification').mockResolvedValue({ ...extracted, candidate_extracted: false, extracted_row_count: 0, rows: [] })
    vi.spyOn(api, 'extractCorpusVerification').mockRejectedValue(new Error('Extractor unavailable'))

    render(<LocaleProvider><CorpusPage settings={null} onNotify={vi.fn()} /></LocaleProvider>)

    fireEvent.click(await screen.findByRole('button', { name: 'Review answers' }))
    expect(await screen.findByText('PDF extraction did not complete')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry PDF extraction' })).toBeInTheDocument()
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument()
  })
})
