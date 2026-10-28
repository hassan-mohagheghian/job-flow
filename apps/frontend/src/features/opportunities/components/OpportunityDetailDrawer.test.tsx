import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import '@testing-library/jest-dom'
import { OpportunityDetailDrawer } from './OpportunityDetailDrawer'

const processMock = vi.fn()
const moveMock = vi.fn()
const statusMock = vi.fn()
const deleteMock = vi.fn()
const addNoteMock = vi.fn()
const deleteNoteMock = vi.fn()
const dismissMock = vi.fn()
const addLinkMock = vi.fn()
const deleteLinkMock = vi.fn()
const setBaseUrlMock = vi.fn()

const baseDetail = {
  id: 'opp-1',
  title: 'Senior Backend Engineer',
  company_name: 'Acme GmbH',
  source: 'manual',
  status: 'evaluated',
  evaluation_status: 'complete',
  job_id: null,
  job_title: null,
  dismissed: false,
  overall_score: 79,
  recommendation: 'consider',
  sender: 'Jane',
  raw_content: 'Hi Hassan, we are hiring a Senior Backend Engineer.',
  base_url: 'https://www.linkedin.com/posts/jane-hiring-123',
  extracted: { role_title: 'Senior Backend Engineer' },
  evaluation: { concerns: ['Sponsorship is unclear'], missing_requirements: ['Job location'] },
  application_path: { kind: 'reply_sender', label: 'Reply to the sender' },
  next_action: 'Ask the recruiter for the location and JD',
  evaluations: [{ id: 'eval-1', status: 'evaluated', overall_score: 79 }],
  notes: [
    {
      id: 'note-1',
      opportunity_id: 'opp-1',
      title: 'Recruiter replied',
      content: 'They sent the JD.',
      author: 'Hassan',
      created_at: '2026-10-08T10:00:00+00:00',
      updated_at: '2026-10-08T10:00:00+00:00',
    },
  ],
  links: [
    {
      id: 'link-1',
      opportunity_id: 'opp-1',
      title: 'Recruiter post',
      url: 'https://acme.example/careers',
      created_at: '2026-10-08T10:00:00+00:00',
      updated_at: '2026-10-08T10:00:00+00:00',
    },
  ],
}

// Mutable override so tests can render different opportunity states; read at
// render time because vi.mock factories are hoisted above module initializers.
let detailOverride: Record<string, unknown> | null = null

vi.mock('@/entities/opportunity/hooks', () => ({
  useOpportunityDetailQuery: () => ({
    data: detailOverride ?? baseDetail,
    isLoading: false,
    isError: false,
  }),
  useProcessOpportunity: () => ({ mutate: processMock, isPending: false }),
  useMoveOpportunityToJob: () => ({ mutate: moveMock, isPending: false }),
  useUpdateOpportunityStatus: () => ({ mutate: statusMock, isPending: false }),
  useDeleteOpportunity: () => ({ mutate: deleteMock, isPending: false }),
  useAddOpportunityNote: () => ({ mutate: addNoteMock, isPending: false }),
  useDeleteOpportunityNote: () => ({ mutate: deleteNoteMock, isPending: false }),
  useDismissOpportunity: () => ({ mutate: dismissMock, isPending: false }),
  useAddOpportunityLink: () => ({ mutate: addLinkMock, isPending: false }),
  useDeleteOpportunityLink: () => ({ mutate: deleteLinkMock, isPending: false }),
  useSetOpportunityBaseUrl: () => ({ mutate: setBaseUrlMock, isPending: false }),
}))

describe('OpportunityDetailDrawer', () => {
  beforeEach(() => {
    processMock.mockClear()
    moveMock.mockClear()
    statusMock.mockClear()
    deleteMock.mockClear()
    addNoteMock.mockClear()
    deleteNoteMock.mockClear()
    dismissMock.mockClear()
    addLinkMock.mockClear()
    deleteLinkMock.mockClear()
    setBaseUrlMock.mockClear()
    detailOverride = null
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

  it('enables Move to Jobs for an evaluated opportunity', () => {
    render(<OpportunityDetailDrawer opportunityId="opp-1" onClose={vi.fn()} />)

    const button = screen.getByRole('button', { name: /move to jobs/i })
    expect(button).toBeEnabled()
    fireEvent.click(button)
    expect(moveMock).toHaveBeenCalledWith('opp-1', expect.anything())
  })

  it('disables Move to Jobs before evaluation and hides it once linked', () => {
    detailOverride = { ...baseDetail, evaluation_status: 'pending' }
    const { unmount } = render(<OpportunityDetailDrawer opportunityId="opp-1" onClose={vi.fn()} />)
    expect(screen.getByRole('button', { name: /move to jobs/i })).toBeDisabled()
    unmount()

    detailOverride = { ...baseDetail, job_id: 'job-1', job_title: 'Senior Backend Engineer' }
    render(<OpportunityDetailDrawer opportunityId="opp-1" onClose={vi.fn()} />)
    expect(screen.queryByRole('button', { name: /move to jobs/i })).not.toBeInTheDocument()
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

  it('shows follow-up notes and adds a new one', () => {
    render(<OpportunityDetailDrawer opportunityId="opp-1" onClose={vi.fn()} />)

    expect(screen.getByText('Recruiter replied')).toBeInTheDocument()
    expect(screen.getByText('They sent the JD.')).toBeInTheDocument()
    expect(screen.getByText(/Hassan ·/)).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/note title/i), { target: { value: 'Second reply' } })
    fireEvent.change(screen.getByLabelText(/new follow-up note/i), { target: { value: 'New salary info.' } })
    fireEvent.click(screen.getByRole('button', { name: /add follow-up/i }))

    expect(addNoteMock).toHaveBeenCalledWith(
      { id: 'opp-1', data: { title: 'Second reply', content: 'New salary info.' } },
      expect.anything(),
    )
  })

  it('deletes a follow-up note', () => {
    render(<OpportunityDetailDrawer opportunityId="opp-1" onClose={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: /delete note recruiter replied/i }))
    expect(deleteNoteMock).toHaveBeenCalledWith({ id: 'opp-1', noteId: 'note-1' })
  })

  it('shows, adds and deletes links', () => {
    render(<OpportunityDetailDrawer opportunityId="opp-1" onClose={vi.fn()} />)

    expect(screen.getByText('https://acme.example/careers')).toBeInTheDocument()
    expect(screen.getByText(/Recruiter post/)).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/new link title/i), { target: { value: 'Company site' } })
    fireEvent.change(screen.getByLabelText(/new link url/i), { target: { value: 'https://acme.example' } })
    fireEvent.click(screen.getByRole('button', { name: /add link/i }))
    expect(addLinkMock).toHaveBeenCalledWith(
      { id: 'opp-1', data: { title: 'Company site', url: 'https://acme.example' } },
      expect.anything(),
    )

    fireEvent.click(screen.getByRole('button', { name: /delete link recruiter post/i }))
    expect(deleteLinkMock).toHaveBeenCalledWith({ id: 'opp-1', linkId: 'link-1' })
  })

  it('shows and edits the base URL', () => {
    render(<OpportunityDetailDrawer opportunityId="opp-1" onClose={vi.fn()} />)

    expect(screen.getByText('https://www.linkedin.com/posts/jane-hiring-123')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /edit base url/i }))
    const input = screen.getByLabelText(/edit base url/i)
    expect(input).toHaveValue('https://www.linkedin.com/posts/jane-hiring-123')
    fireEvent.change(input, { target: { value: 'https://acme.example/hiring-9' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
    expect(setBaseUrlMock).toHaveBeenCalledWith(
      { id: 'opp-1', baseUrl: 'https://acme.example/hiring-9' },
      expect.anything(),
    )
  })

  it('shows the empty base URL state and clears it by saving an empty edit', () => {
    detailOverride = { ...baseDetail, base_url: null }
    render(<OpportunityDetailDrawer opportunityId="opp-1" onClose={vi.fn()} />)

    expect(screen.getByText(/no source page set/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /edit base url/i }))
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
    expect(setBaseUrlMock).toHaveBeenCalledWith(
      { id: 'opp-1', baseUrl: null },
      expect.anything(),
    )
  })

  it('dismisses with a reason through the dialog', () => {
    render(<OpportunityDetailDrawer opportunityId="opp-1" onClose={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: /^dismiss$/i }))
    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByText('Dismiss opportunity')).toBeInTheDocument()
    fireEvent.change(within(dialog).getByPlaceholderText(/why are you dismissing/i), {
      target: { value: 'Wrong seniority' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: /^dismiss$/i }))
    expect(dismissMock).toHaveBeenCalledWith(
      { id: 'opp-1', dismissed: true, note: 'Wrong seniority' },
      expect.anything(),
    )
  })
})
