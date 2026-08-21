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
})
