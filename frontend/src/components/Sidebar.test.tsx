// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LocaleProvider } from '../lib/i18n'
import { Sidebar } from './Sidebar'

afterEach(cleanup)

describe('Sidebar', () => {
  it('shows only the two implemented extraction strategies', () => {
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
    expect(screen.getAllByText(/^Strategy [12]$/)).toHaveLength(2)
  })

  it('routes New extraction to Strategy 2 and closes the mobile drawer', () => {
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
    expect(onNavigate).toHaveBeenCalledWith('strategy2')
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
