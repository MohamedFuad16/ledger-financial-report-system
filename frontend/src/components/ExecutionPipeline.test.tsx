// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { LocaleProvider } from '../lib/i18n'
import type { ExecutionFile } from '../types'
import { ExecutionPipeline } from './ExecutionPipeline'

const comparisonFile: ExecutionFile = {
  name: '3M_annual_report_2024.pdf',
  pages: 192,
  approxTokens: 84_000,
  state: 'running',
  passes: [
    { strategy: 's1', strategyLabel: 'PyPDF', state: 'complete', step: 'output', message: '94.7% accuracy' },
    { strategy: 's2', strategyLabel: 'PyMuPDF', state: 'running', step: 'api', message: 'Rate limited — retry 1 in 5s' },
    { strategy: 's2-inspector', strategyLabel: 'Inspector', state: 'queued' },
  ],
}

afterEach(cleanup)

describe('ExecutionPipeline', () => {
  it('renders one live card per file and follows the currently active parser', () => {
    render(<LocaleProvider><ExecutionPipeline files={[comparisonFile]} running /></LocaleProvider>)

    expect(screen.getAllByTestId('execution-file-card')).toHaveLength(1)
    expect(screen.getByText('Rate limited — retry 1 in 5s')).toBeInTheDocument()
    expect(screen.getByText('Run model')).toBeInTheDocument()
    expect(screen.getByText('1 of 3 parsers complete')).toBeInTheDocument()
    expect(screen.getByText('Live execution events are streaming')).toHaveClass('sr-only')
  })

  it('transitions the single card to the next running parser', async () => {
    const { rerender } = render(<LocaleProvider><ExecutionPipeline files={[comparisonFile]} running /></LocaleProvider>)
    const advanced: ExecutionFile = {
      ...comparisonFile,
      passes: comparisonFile.passes.map((pass) => pass.strategy === 's2'
        ? { ...pass, state: 'complete' as const, step: 'output', message: 'Pass complete' }
        : pass.strategy === 's2-inspector'
          ? { ...pass, state: 'running' as const, step: 'extract', message: 'Parsing with Inspector' }
          : pass),
    }

    rerender(<LocaleProvider><ExecutionPipeline files={[advanced]} running /></LocaleProvider>)

    expect(screen.getAllByTestId('execution-file-card')).toHaveLength(1)
    expect(await screen.findByText('Parsing with Inspector')).toBeInTheDocument()
    expect(screen.getByText('Parse document')).toBeInTheDocument()
  })

  it('renders the centered idle state when no work is staged', () => {
    render(<LocaleProvider><ExecutionPipeline files={[]} running={false} /></LocaleProvider>)

    expect(screen.getByText('No execution in progress')).toBeInTheDocument()
  })

  it('shows total elapsed time after completion instead of the millisecond output-write step', () => {
    const completed: ExecutionFile = {
      ...comparisonFile,
      state: 'complete',
      passes: [{
        strategy: 's3',
        strategyLabel: 'Inspector Gate',
        state: 'complete',
        step: 'output',
        totalSeconds: 72,
        steps: { output: { state: 'complete', durationSeconds: 0.01 } },
      }],
    }

    render(<LocaleProvider><ExecutionPipeline files={[completed]} running={false} /></LocaleProvider>)

    expect(screen.getByText('1 min 12 s')).toHaveAttribute('title', 'Total elapsed time')
    expect(screen.queryByText('10ms')).not.toBeInTheDocument()
  })

  it('keeps every selected report visible while a batch advances', () => {
    const reports: ExecutionFile[] = Array.from({ length: 2 }, (_, index) => ({
      ...comparisonFile,
      name: index === 0 ? '3M_annual_report_2022.pdf' : 'Dainichi_annual_report_2022.pdf',
      state: index === 0 ? 'running' : 'queued',
      passes: [{
        strategy: 's3',
        strategyLabel: 'Inspector Gate',
        state: index === 0 ? 'running' : 'queued',
        step: index === 0 ? 'api' : undefined,
      }],
    }))

    render(<LocaleProvider><ExecutionPipeline files={reports} running /></LocaleProvider>)

    expect(screen.getAllByTestId('execution-file-card')).toHaveLength(2)
    expect(screen.getByText('3M_annual_report_2022.pdf')).toBeInTheDocument()
    expect(screen.getByText('Dainichi_annual_report_2022.pdf')).toBeInTheDocument()
    expect(screen.getByText('0 complete · 1 running · 1 queued')).toBeInTheDocument()
  })
})
