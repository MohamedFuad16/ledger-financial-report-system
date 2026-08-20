// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LocaleProvider } from '../lib/i18n'
import type { ExecutionFile } from '../types'
import { ExecutionPipeline } from './ExecutionPipeline'

const runningFiles: ExecutionFile[] = [{
  name: '3M_annual_report_2024.pdf',
  pages: 192,
  approxTokens: 84_000,
  state: 'running',
  passes: [{
    strategy: 's2-docling',
    strategyLabel: 'Docling',
    state: 'running',
    step: 'api',
    message: 'Extracting balance-sheet rows',
  }],
}]

describe('ExecutionPipeline', () => {
  it('renders separate live task capsules and the current streamed message', () => {
    render(<LocaleProvider><ExecutionPipeline files={runningFiles} running /></LocaleProvider>)

    expect(screen.getByText('Extracting balance-sheet rows')).toBeInTheDocument()
    expect(screen.getByText('Run model')).toBeInTheDocument()
    expect(screen.getByText('Save report')).toBeInTheDocument()
    expect(screen.getByText('Save result')).toBeInTheDocument()
    expect(screen.getByText('Live execution events are streaming')).toBeInTheDocument()
  })

  it('renders the centered idle state when no work is staged', () => {
    render(<LocaleProvider><ExecutionPipeline files={[]} running={false} /></LocaleProvider>)

    expect(screen.getByText('No execution in progress')).toBeInTheDocument()
  })
})
