import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TrackingActions } from './TrackingActions'
import { applicationApi } from '@/entities/application/api'
import type { ApplicationStatus } from '@/entities/application/types'

vi.mock('@/entities/application/api', () => ({
  applicationApi: {
    getByJob: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
  },
}))

const sampleApplication = {
  id: 'app-1',
  job_id: 'job-1',
  status: 'seen',
  applied_at: null,
  created_at: null,
  updated_at: null,
  status_timeline: [],
  follow_ups: [],
  notes: [],
  documents: [],
}

beforeEach(() => {
  vi.clearAllMocks()
})

function renderActions(jobId = 'job-1', statuses?: ApplicationStatus[]) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <TrackingActions jobId={jobId} statuses={statuses} />
    </QueryClientProvider>,
  )
}

describe('TrackingActions', () => {
  it('renders the Mark applied and Mark expired quick actions', async () => {
    vi.mocked(applicationApi.getByJob).mockResolvedValue(sampleApplication as never)
    renderActions()

    expect(await screen.findByRole('button', { name: 'Mark applied' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mark expired' })).toBeInTheDocument()
  })

  it('renders only the requested statuses when the statuses prop is set', async () => {
    vi.mocked(applicationApi.getByJob).mockResolvedValue(sampleApplication as never)
    renderActions('job-1', ['expired'])

    expect(await screen.findByRole('button', { name: 'Mark expired' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Mark applied' })).not.toBeInTheDocument()
  })

  it('marks an existing application as applied', async () => {
    vi.mocked(applicationApi.getByJob).mockResolvedValue(sampleApplication as never)
    vi.mocked(applicationApi.update).mockResolvedValue({ ...sampleApplication, status: 'applied' } as never)
    const user = userEvent.setup()
    renderActions()

    await user.click(await screen.findByRole('button', { name: 'Mark applied' }))

    await waitFor(() => {
      expect(applicationApi.update).toHaveBeenCalledWith('app-1', { status: 'applied' })
    })
    expect(applicationApi.create).not.toHaveBeenCalled()
  })

  it('creates an application and marks it applied when none exists', async () => {
    vi.mocked(applicationApi.getByJob).mockRejectedValue(new Error('Not found'))
    vi.mocked(applicationApi.create).mockResolvedValue(sampleApplication as never)
    vi.mocked(applicationApi.update).mockResolvedValue({ ...sampleApplication, status: 'applied' } as never)
    const user = userEvent.setup()
    renderActions()

    await user.click(await screen.findByRole('button', { name: 'Mark applied' }))

    await waitFor(() => {
      expect(applicationApi.create).toHaveBeenCalledWith('job-1', undefined)
    })
    await waitFor(() => {
      expect(applicationApi.update).toHaveBeenCalledWith('app-1', { status: 'applied' })
    })
  })

  it('marks an existing application as expired', async () => {
    vi.mocked(applicationApi.getByJob).mockResolvedValue(sampleApplication as never)
    vi.mocked(applicationApi.update).mockResolvedValue({ ...sampleApplication, status: 'expired' } as never)
    const user = userEvent.setup()
    renderActions()

    await user.click(await screen.findByRole('button', { name: 'Mark expired' }))

    await waitFor(() => {
      expect(applicationApi.update).toHaveBeenCalledWith('app-1', { status: 'expired' })
    })
    expect(applicationApi.create).not.toHaveBeenCalled()
  })

  it('disables both actions while a mutation is pending', async () => {
    vi.mocked(applicationApi.getByJob).mockResolvedValue(sampleApplication as never)
    let resolveUpdate: (value: unknown) => void = () => {}
    vi.mocked(applicationApi.update).mockReturnValue(
      new Promise((resolve) => {
        resolveUpdate = resolve
      }) as never,
    )
    const user = userEvent.setup()
    renderActions()

    await user.click(await screen.findByRole('button', { name: 'Mark applied' }))

    const pendingButtons = await screen.findAllByRole('button', { name: 'Saving…' })
    expect(pendingButtons).toHaveLength(2)
    pendingButtons.forEach((button) => expect(button).toBeDisabled())

    resolveUpdate({ ...sampleApplication, status: 'applied' })
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Mark applied' })).toBeEnabled()
    })
    expect(screen.getByRole('button', { name: 'Mark expired' })).toBeEnabled()
  })
})
