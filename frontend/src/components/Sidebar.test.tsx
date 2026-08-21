// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LocaleProvider } from '../lib/i18n'
import { Sidebar } from './Sidebar'

afterEach(cleanup)

describe('Sidebar', () => {
  it('shows all three active strategy surfaces', () => {
    render(
      <LocaleProvider>
        <Sidebar
          active="dashboard"
          onNavigate={() => undefined}
          theme="light"
          onThemeToggle={() => undefined}
          open={false}
          onOpenChange={() => undefined}
          collapsed={false}
          onCollapsedChange={() => undefined}
        />
      </LocaleProvider>,
    )

    expect(screen.getByText('Strategy 1')).toBeInTheDocument()
    expect(screen.getByText('Strategy 2')).toBeInTheDocument()
    expect(screen.getByText('Strategy 3')).toBeInTheDocument()
    expect(screen.getAllByText(/^Strategy [123]$/)).toHaveLength(3)
  })

  it('routes New extraction to Strategy 1 and closes the mobile drawer', () => {
    const onNavigate = vi.fn()
    const onOpenChange = vi.fn()
    render(
      <LocaleProvider>
        <Sidebar
          active="dashboard"
          onNavigate={onNavigate}
          theme="light"
          onThemeToggle={() => undefined}
          open
          onOpenChange={onOpenChange}
          collapsed={false}
          onCollapsedChange={() => undefined}
        />
      </LocaleProvider>,
    )

    fireEvent.click(screen.getByTitle('New extraction'))
    expect(onNavigate).toHaveBeenCalledWith('strategy1')
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
