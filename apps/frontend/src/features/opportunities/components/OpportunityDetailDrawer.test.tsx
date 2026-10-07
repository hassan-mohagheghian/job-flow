import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { OpportunityDetailDrawer } from './OpportunityDetailDrawer'

const processMock = vi.fn()
const statusMock = vi.fn()
const deleteMock = vi.fn()

vi.mock('@/entities/opportunity/hooks', () => ({
  useOpportunityDetailQuery: () => ({
    data: {
      id: 'opp-1',
      title: 'Senior Backend Engineer',
      company_name: 'Acme GmbH',
      source: 'manual',
      status: 'evaluated',
      evaluation_status: 'complete',
      overall_score: 79,
      recommendation: 'consider',
      sender: 'Jane',
      raw_content: 'Hi Hassan, we are hiring a Senior Backend Engineer.',
      extracted: { role_title: 'Senior Backend Engineer' },
      evaluation: { concerns: ['Sponsorship is unclear'], missing_requirements: ['Job location'] },
      application_path: { kind: 'reply_sender', label: 'Reply to the sender' },
      next_action: 'Ask the recruiter for the location and JD',
      evaluations: [{ id: 'eval-1', status: 'evaluated', overall_score: 79 }],
    },
    isLoading: false,
    isError: false,
  }),
  useProcessOpportunity: () => ({ mutate: processMock, isPending: false }),
  useUpdateOpportunityStatus: () => ({ mutate: statusMock, isPending: false }),
  useDeleteOpportunity: () => ({ mutate: deleteMock, isPending: false }),
}))

describe('OpportunityDetailDrawer', () => {
  beforeEach(() => {
    processMock.mockClear()
    statusMock.mockClear()
    deleteMock.mockClear()
  })

  it('shows the original message, evaluation, score reasons, path and history', () => {
    render(<OpportunityDetailDrawer opportunityId="opp-1" onClose={vi.fn()} />)

    expect(screen.getByText(/we are hiring a Senior Backend Engineer/)).toBeInTheDocument()
    expect(screen.getByText('79')).toBeInTheDocument()
    expect(screen.getByText('Sponsorship is unclear')).toBeInTheDocument()
    expect(screen.getByText('Job location')).toBeInTheDocument()
    expect(screen.getByText(/Reply to the sender/)).toBeInTheDocument()
    expect(screen.getByText('Ask the recruiter for the location and JD')).toBeInTheDocument()
    expect(screen.getByText(/eval-1/)).toBeInTheDocument()
  })

  it('processes, changes status and deletes', () => {
    const onClose = vi.fn()
    render(<OpportunityDetailDrawer opportunityId="opp-1" onClose={onClose} />)

    fireEvent.click(screen.getByRole('button', { name: /process/i }))
    expect(processMock).toHaveBeenCalledWith({ id: 'opp-1' })

    fireEvent.change(screen.getByLabelText(/status/i), { target: { value: 'applied' } })
    expect(statusMock).toHaveBeenCalledWith({ id: 'opp-1', status: 'applied' })

    fireEvent.click(screen.getByRole('button', { name: /delete opportunity/i }))
    expect(deleteMock).toHaveBeenCalledWith('opp-1', expect.anything())
  })
})
