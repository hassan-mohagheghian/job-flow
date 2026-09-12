import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { JobDetailDrawer } from './JobDetailDrawer'
import { jobApi } from '@/entities/job/api'
import { applicationApi } from '@/entities/application/api'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/entities/job/api', () => ({
  jobApi: {
    getDetail: vi.fn(),
  },
}))

vi.mock('@/entities/application/api', () => ({
  applicationApi: {
    getByJob: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
  },
}))

const sampleDetail = {
  id: 'job-1',
  title: 'Staff Engineer',
  company_name: 'Acme GmbH',
  company_id: 'company-1',
  company_type: 'PRODUCT_COMPANY',
  role: 'Staff',
  location: 'Berlin',
  work_types: ['Hybrid'],
  employment_types: ['Full-time'],
  salary: '100k',
  visa: 'Strong',
  url: 'https://example.com/job',
  status: 'imported',
  scores: { overall: 90, fit: 85, success: 88, overall_grade: 'A+' },
  rank: 3,
  latest_processing_execution: null,
  description: 'A great role.',
  notes: [],
  links: [],
  analysis: null,
  related_companies: [],
  workflow: [],
  tracking_status: 'applied',
  updated_at: null,
  created_at: null,
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(jobApi.getDetail).mockResolvedValue(sampleDetail as any)
  vi.mocked(applicationApi.getByJob).mockResolvedValue({
    id: 'app-1',
    job_id: 'job-1',
    status: 'applied',
  } as any)
})

function renderDrawer(
  jobId: string | null,
  onEdit: (id: string) => void = vi.fn(),
  onReprocess: (id: string) => void = vi.fn(),
) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <JobDetailDrawer
        jobId={jobId}
        onOpenChange={vi.fn()}
        onEdit={onEdit}
        onReprocess={onReprocess}
      />
    </QueryClientProvider>
  )
}

describe('JobDetailDrawer edit', () => {
  it('opens the edit drawer when Edit is clicked', async () => {
    const onEdit = vi.fn()
    renderDrawer('job-1', onEdit)

    await waitFor(() => expect(screen.getByText('Staff Engineer')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Edit job' }))
    expect(onEdit).toHaveBeenCalledWith('job-1')
  })

  it('does not render the Edit button without an onEdit handler', () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    render(
      <QueryClientProvider client={qc}>
        <JobDetailDrawer jobId="job-1" onOpenChange={vi.fn()} />
      </QueryClientProvider>
    )
    expect(screen.queryByRole('button', { name: 'Edit job' })).not.toBeInTheDocument()
  })

  it('calls onReprocess when the header Reprocess button is clicked', async () => {
    const onReprocess = vi.fn()
    renderDrawer('job-1', vi.fn(), onReprocess)

    await waitFor(() => expect(screen.getByText('Staff Engineer')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Reprocess job' }))
    expect(onReprocess).toHaveBeenCalledWith('job-1')
  })

  it('does not render the Reprocess button without an onReprocess handler', () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    render(
      <QueryClientProvider client={qc}>
        <JobDetailDrawer jobId="job-1" onOpenChange={vi.fn()} />
      </QueryClientProvider>
    )
    expect(
      screen.queryByRole('button', { name: 'Reprocess job' }),
    ).not.toBeInTheDocument()
  })

  it('links the company name to the companies page detail drawer', async () => {
    renderDrawer('job-1')

    await waitFor(() => expect(screen.getByText('Staff Engineer')).toBeInTheDocument())
    const link = screen.getByRole('link', { name: 'Acme GmbH' })
    expect(link).toHaveAttribute('href', '/companies?company=company-1')
    expect(screen.getByRole('button', { name: 'Change company' })).toBeInTheDocument()
  })

  it('offers a company picker in the Details section', async () => {
    renderDrawer('job-1')

    await waitFor(() => expect(screen.getByText('Staff Engineer')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Change company' })).toBeInTheDocument()
  })

  it('shows the company type when it is set', async () => {
    renderDrawer('job-1')

    await waitFor(() => expect(screen.getByText('Staff Engineer')).toBeInTheDocument())
    expect(screen.getByText('Product Company')).toBeInTheDocument()
  })
})

describe('JobDetailDrawer published by', () => {
  it('shows the recruiters as Published by', async () => {
    vi.mocked(jobApi.getDetail).mockResolvedValue({
      ...sampleDetail,
      related_companies: [
        {
          company_id: 'recruiter-1',
          name: 'RecruitCo',
          role: 'recruiter',
          company_type: 'recruiting_agency',
          confidence: 0.9,
          reason: 'listed as the recruiting partner',
        },
      ],
    } as any)
    renderDrawer('job-1')

    await waitFor(() => expect(screen.getByText('Staff Engineer')).toBeInTheDocument())
    expect(screen.getByText('Published by')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Published by'))
    const link = screen.getByRole('link', { name: 'RecruitCo' })
    expect(link).toHaveAttribute('href', '/companies?company=recruiter-1')
    expect(screen.getByText('recruiting agency')).toBeInTheDocument()
    expect(screen.getByText('listed as the recruiting partner')).toBeInTheDocument()
  })

  it('does not render Published by without recruiters', async () => {
    renderDrawer('job-1')

    await waitFor(() => expect(screen.getByText('Staff Engineer')).toBeInTheDocument())
    expect(screen.queryByText('Published by')).not.toBeInTheDocument()
  })
})

describe('JobDetailDrawer tracking', () => {
  it('renders an editable tracking status select with the current status', async () => {
    renderDrawer('job-1')

    const trigger = await screen.findByRole('combobox', { name: 'Tracking status' })
    expect(trigger).toHaveTextContent('applied')
  })
})

describe('JobDetailDrawer rank', () => {
  it('renders the overall-score rank', async () => {
    renderDrawer('job-1')

    await waitFor(() => expect(screen.getByText('Staff Engineer')).toBeInTheDocument())
    expect(screen.getByText('#3')).toBeInTheDocument()
    expect(screen.getByText('Rank')).toBeInTheDocument()
  })

  it('does not render a rank when it is absent', async () => {
    vi.mocked(jobApi.getDetail).mockResolvedValue({ ...sampleDetail, rank: null } as any)
    renderDrawer('job-1')

    await waitFor(() => expect(screen.getByText('Staff Engineer')).toBeInTheDocument())
    expect(screen.queryByText('Rank')).not.toBeInTheDocument()
  })
})

describe('JobDetailDrawer score order', () => {
  it('renders score cards in Overall, Success, Fit order before the rank', async () => {
    renderDrawer('job-1')

    await waitFor(() => expect(screen.getByText('Staff Engineer')).toBeInTheDocument())
    const text = document.body.textContent ?? ''
    const overall = text.indexOf('90')
    const success = text.indexOf('88')
    const fit = text.indexOf('85')
    const rank = text.indexOf('#3')
    expect(overall).toBeGreaterThan(-1)
    expect(success).toBeGreaterThan(overall)
    expect(fit).toBeGreaterThan(success)
    expect(rank).toBeGreaterThan(fit)
  })
})

describe('JobDetailDrawer scores explanation', () => {
  it('opens the scores explanation popover when clicked and shows the factors', async () => {
    vi.mocked(jobApi.getDetail).mockResolvedValue({
      ...sampleDetail,
      analysis: {
        recommendation: null,
        apply_reason: null,
        generated_at: null,
        insights: [],
        skills: [],
        summary: null,
        scores_explanation: {
          fit_factors: ['Strong Python background'],
          success_factors: ['Senior level role'],
          concerns: ['No Kafka experience'],
        },
      },
    } as any)
    renderDrawer('job-1')

    await waitFor(() => expect(screen.getByText('Staff Engineer')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Show scores explanation' }))
    expect(screen.getByText('Scores Explanation')).toBeInTheDocument()
    expect(screen.getByText('Strong Python background')).toBeInTheDocument()
    expect(screen.getByText('Senior level role')).toBeInTheDocument()
    expect(screen.getByText('No Kafka experience')).toBeInTheDocument()
  })

  it('does not render the scores explanation button without an analysis', async () => {
    renderDrawer('job-1')

    await waitFor(() => expect(screen.getByText('Staff Engineer')).toBeInTheDocument())
    expect(
      screen.queryByRole('button', { name: 'Show scores explanation' }),
    ).not.toBeInTheDocument()
  })
})

describe('JobDetailDrawer processing failure', () => {
  const failedDetail = {
    ...sampleDetail,
    latest_processing_execution: {
      id: 'exec-1',
      status: 'failed',
      error: {
        message: 'Execution timed out after 600s (worker stopped responding).',
      },
      started_at: null,
      finished_at: null,
      current_step: null,
      workflow: { steps: [] },
    },
  }

  it('shows a fade-in error banner with the failure message', async () => {
    vi.mocked(jobApi.getDetail).mockResolvedValue(failedDetail as any)
    renderDrawer('job-1')

    await waitFor(() => expect(screen.getByText('Staff Engineer')).toBeInTheDocument())
    expect(screen.getByText('Processing failed')).toBeInTheDocument()
    expect(
      screen.getByText(
        'Execution timed out after 600s (worker stopped responding).',
      ),
    ).toBeInTheDocument()
    expect(screen.getByTestId('processing-error-banner').className).toContain(
      'animate-in',
    )
  })

  it('calls onReprocess when Retry is clicked', async () => {
    const onReprocess = vi.fn()
    vi.mocked(jobApi.getDetail).mockResolvedValue(failedDetail as any)
    renderDrawer('job-1', vi.fn(), onReprocess)

    await waitFor(() => expect(screen.getByText('Staff Engineer')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onReprocess).toHaveBeenCalledWith('job-1')
  })

  it('refetches the detail when Check status is clicked', async () => {
    vi.mocked(jobApi.getDetail).mockReset()
    vi.mocked(jobApi.getDetail).mockResolvedValue({
      ...sampleDetail,
      latest_processing_execution: {
        id: 'exec-1',
        status: 'failed',
        error: {
          message: 'Execution timed out after 600s (worker stopped responding).',
        },
        started_at: null,
        finished_at: null,
        current_step: null,
        workflow: { steps: [] },
      },
    } as any)
    renderDrawer('job-1')

    await waitFor(() =>
      expect(screen.getByTestId('processing-error-banner')).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByRole('button', { name: 'Check processing status' }))
    await waitFor(() => expect(jobApi.getDetail).toHaveBeenCalledTimes(2))
  })
})
