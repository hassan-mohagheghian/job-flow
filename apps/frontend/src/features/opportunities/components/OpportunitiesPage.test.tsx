import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { OpportunitiesPage } from './OpportunitiesPage'
import type { OpportunityListItem } from '@/entities/opportunity/types'

const items: OpportunityListItem[] = [
  {
    id: 'opp-1',
    title: 'Senior Backend Engineer',
    company_name: 'Acme GmbH',
    job_title: null,
    source: 'manual',
    status: 'ready_to_apply',
    evaluation_status: 'complete',
    overall_score: 79,
    fit_score: 85,
    success_score: 70,
    recommendation: 'consider',
    next_action: 'Reply to the recruiter',
    job_id: null,
    company_id: null,
    created_at: '2026-09-01T10:00:00+00:00',
    updated_at: '2026-09-01T10:00:00+00:00',
  },
  {
    id: 'opp-2',
    title: 'Unknown role',
    company_name: null,
    job_title: null,
    source: 'manual',
    status: 'needs_info',
    evaluation_status: 'pending',
    overall_score: null,
    fit_score: null,
    success_score: null,
    recommendation: null,
    next_action: 'Research the opportunity first',
    job_id: null,
    company_id: null,
    created_at: '2026-09-02T10:00:00+00:00',
    updated_at: '2026-09-02T10:00:00+00:00',
  },
]

function renderPage(overrides: Record<string, unknown> = {}) {
  const props = {
    items,
    total: 2,
    isLoading: false,
    isError: false,
    onRefetch: vi.fn(),
    query: '',
    onQueryChange: vi.fn(),
    filterStatus: '',
    onFilterStatusChange: vi.fn(),
    onOpenCreate: vi.fn(),
    onOpenDetail: vi.fn(),
    onDelete: vi.fn(),
    deletingId: null,
    ...overrides,
  }
  return render(<OpportunitiesPage {...(props as any)} />)
}

describe('OpportunitiesPage', () => {
  it('renders scored and pending opportunities with delete actions', () => {
    const onOpenDetail = vi.fn()
    const onDelete = vi.fn()
    renderPage({ onOpenDetail, onDelete })

    expect(screen.getByText('Senior Backend Engineer')).toBeInTheDocument()
    expect(screen.getByText('79')).toBeInTheDocument()
    expect(screen.getByText('Evaluation pending')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Senior Backend Engineer'))
    expect(onOpenDetail).toHaveBeenCalledWith('opp-1')

    fireEvent.click(screen.getByRole('button', { name: /delete opportunity senior backend engineer/i }))
    fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
    expect(onDelete).toHaveBeenCalledWith('opp-1')
  })

  it('opens the create flow and filters by status', () => {
    const onOpenCreate = vi.fn()
    const onFilterStatusChange = vi.fn()
    renderPage({ onOpenCreate, onFilterStatusChange })

    fireEvent.click(screen.getByRole('button', { name: /new opportunity/i }))
    expect(onOpenCreate).toHaveBeenCalledTimes(1)

    fireEvent.change(screen.getByLabelText(/filter by status/i), { target: { value: 'needs_info' } })
    expect(onFilterStatusChange).toHaveBeenCalledWith('needs_info')
  })
})
