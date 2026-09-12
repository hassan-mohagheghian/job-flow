import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TrackingStatusSelect } from './TrackingStatusSelect'
import { applicationApi } from '@/entities/application/api'

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
  status: 'applied',
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

function renderSelect(jobId = 'job-1') {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <TrackingStatusSelect jobId={jobId} />
    </QueryClientProvider>
  )
}

describe('TrackingStatusSelect', () => {
  it('updates the status when a new option is picked', async () => {
    vi.mocked(applicationApi.getByJob).mockResolvedValue(sampleApplication as never)
    vi.mocked(applicationApi.update).mockResolvedValue({ ...sampleApplication, status: 'expired' } as never)
    const user = userEvent.setup()
    renderSelect()

    const trigger = await screen.findByRole('combobox')
    trigger.focus()
    await user.keyboard('{ArrowDown}')
    await user.click(await screen.findByRole('option', { name: 'expired' }))

    await waitFor(() => {
      expect(applicationApi.update).toHaveBeenCalledWith('app-1', { status: 'expired' })
    })
  })

  it('creates an application and marks it expired when none exists', async () => {
    vi.mocked(applicationApi.getByJob).mockRejectedValue(new Error('Not found'))
    vi.mocked(applicationApi.create).mockResolvedValue(sampleApplication as never)
    vi.mocked(applicationApi.update).mockResolvedValue({ ...sampleApplication, status: 'expired' } as never)
    const user = userEvent.setup()
    renderSelect()

    await user.click(await screen.findByRole('button', { name: /mark expired/i }))

    await waitFor(() => {
      expect(applicationApi.create).toHaveBeenCalledWith('job-1', undefined)
    })
    await waitFor(() => {
      expect(applicationApi.update).toHaveBeenCalledWith('app-1', { status: 'expired' })
    })
  })

  it('shows a loading placeholder while resolving the application', () => {
    vi.mocked(applicationApi.getByJob).mockReturnValue(new Promise(() => {}) as never)
    renderSelect()
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })
})
