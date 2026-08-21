// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { LocaleProvider } from '../lib/i18n'
import { Sidebar } from './Sidebar'

describe('Sidebar', () => {
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
