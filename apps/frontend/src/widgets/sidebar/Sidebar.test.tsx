import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import Sidebar from './index'
import { TooltipProvider } from '@/shared/ui/tooltip'

const pushMock = vi.fn()

vi.mock('next/navigation', () => ({
  usePathname: () => '/jobs',
  useRouter: () => ({ push: pushMock }),
}))

vi.mock('next/dynamic', () => ({
  __esModule: true,
  default: () => () => null,
}))

vi.mock('@/shared/lib/auth-context', () => ({
  useAuth: () => ({
    user: { id: 'test-user', username: 'hassan', display_name: 'Hassan' },
    token: 'test-token',
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    setUser: vi.fn(),
  }),
}))

const renderSidebar = () =>
  render(
    <TooltipProvider>
      <Sidebar>page</Sidebar>
    </TooltipProvider>
  )

describe('Sidebar', () => {
  beforeEach(() => {
    pushMock.mockClear()
  })

  it('renders all main nav items', () => {
    renderSidebar()
    expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument()
    for (const label of ['Jobs', 'Opportunities', 'Companies', 'Candidate', 'Skills', 'Rules', 'AI']) {
      expect(screen.getByRole('button', { name: new RegExp(label, 'i') })).toBeInTheDocument()
    }
  })

  it('marks the active tab', () => {
    renderSidebar()
    expect(screen.getByRole('button', { name: /jobs/i })).toHaveClass('text-primary')
  })

  it('navigates on non-active item click', async () => {
    const user = userEvent.setup()
    renderSidebar()
    await user.click(screen.getByRole('button', { name: /companies/i }))
    expect(pushMock).toHaveBeenCalledWith('/companies')
  })

  it('does not hide the menu when the active item is clicked', async () => {
    const user = userEvent.setup()
    renderSidebar()
    const jobs = screen.getByRole('button', { name: /jobs/i })
    await user.click(jobs)
    expect(pushMock).toHaveBeenCalledWith('/jobs')
    expect(screen.getByRole('button', { name: /jobs/i })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument()
  })

  it('expands the AI submenu inline with LLM Configurations and navigates', async () => {
    const user = userEvent.setup()
    renderSidebar()
    await user.click(screen.getByRole('button', { name: /ai/i }))
    const submenu = screen.getByRole('button', { name: /llm configurations/i })
    await user.click(submenu)
    expect(pushMock).toHaveBeenCalledWith('/ai/llm-configurations')
  })

  it('renders the bottom cluster with history button', () => {
    renderSidebar()
    expect(screen.getAllByTitle('Generation History').length).toBeGreaterThan(0)
  })
})
