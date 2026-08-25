// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LocaleProvider } from '../lib/i18n'
import type { RunSummary } from '../types'
import { HistoryPage } from './HistoryPage'

afterEach(cleanup)

function run(runId: string, strategy: string): RunSummary {
  return {
    run_id: runId,
    strategy,
    parser: strategy,
    experiment: strategy.startsWith('s2') ? 'ocr' : 'no_ocr',
    pdf_file: `${runId}.pdf`,
    fiscal_year: '2022',
    model: 'test-model',
    accuracy: null,
    coverage: 10,
  } as unknown as RunSummary
}

const runs = [run('A', 's1'), run('B', 's1'), run('C', 's2')]

function renderPage(onDeleteRuns: (targets: RunSummary[]) => void) {
  return render(
    <LocaleProvider>
      <HistoryPage
        runs={runs}
        onDeleteRun={() => undefined}
        onDeleteRuns={onDeleteRuns}
        onDeleteAllRuns={() => undefined}
      />
    </LocaleProvider>,
  )
}

describe('HistoryPage bulk selection', () => {
  it('drops a selection that the current filter hides, so hidden runs cannot be deleted', () => {
    const onDeleteRuns = vi.fn()
    renderPage(onDeleteRuns)

    // Select every visible run (the header checkbox selects all rows shown).
    fireEvent.click(screen.getByLabelText('Select all visible runs'))
    expect(screen.getByRole('button', { name: /Delete selected \(3\)/ })).toBeEnabled()

    // Narrow the filter so only the s2 run remains on screen. The two s1 runs
    // were selected but are now hidden: they must not stay selected, because
    // the confirm dialog names a count and never the individual runs.
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 's2' } })

    expect(screen.getByRole('button', { name: /Delete selected \(1\)/ })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Delete selected \(1\)/ }))
    expect(onDeleteRuns).toHaveBeenCalledTimes(1)
    expect(onDeleteRuns.mock.calls[0][0].map((item: RunSummary) => item.run_id)).toEqual(['C'])
  })

  it('only ever hands back runs that are currently visible', () => {
    const onDeleteRuns = vi.fn()
    renderPage(onDeleteRuns)

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 's1' } })
    fireEvent.click(screen.getByLabelText('Select all visible runs'))
    fireEvent.click(screen.getByRole('button', { name: /Delete selected \(2\)/ }))

    expect(onDeleteRuns.mock.calls[0][0].map((item: RunSummary) => item.run_id)).toEqual(['A', 'B'])
  })
})
