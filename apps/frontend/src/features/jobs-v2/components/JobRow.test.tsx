import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { JobRow } from './JobRow'
import type { JobListItem } from '@/entities/job/types'

function makeJob(overrides: Partial<JobListItem> = {}): JobListItem {
  return {
    id: 'job-1',
    title: 'Engineer',
    company_name: 'Acme',
    location: 'Berlin',
    remote: false,
    visa_sponsorship: false,
    job_status: 'imported',
    latest_processing_execution: null,
    scores: { overall: null, fit: null, success: null },
    recommendation: null,
    pinned: false,
    dismissed: false,
    tags: [],
    rank: null,
    tracking_status: null,
    easy_apply: null,
    updated_at: null,
    created_at: '2026-08-01T00:00:00Z',
    ...overrides,
  }
}

function renderRow(job: JobListItem, overrides: Record<string, unknown> = {}) {
  const props = {
    job,
    onProcessV2: vi.fn(),
    onViewDetails: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    onToggleDismissed: vi.fn(),
    ...overrides,
  }
  return render(<JobRow {...(props as any)} />)
}

describe('JobRow row-number column', () => {
  it('renders no row number when the column is off', () => {
    renderRow(makeJob())
    expect(screen.queryByText('3')).not.toBeInTheDocument()
  })

  it('renders the row number when the column is shown', () => {
    renderRow(makeJob(), { showRowNumberColumn: true, rowNumber: 3 })
    expect(screen.getByText('3')).toBeInTheDocument()
  })
})

describe('JobRow recommendation', () => {
  it('renders the recommendation badge', () => {
    renderRow(makeJob({ recommendation: 'apply' }))
    expect(screen.getByText('Apply')).toBeInTheDocument()
  })

  it('renders an em dash when there is no recommendation', () => {
    const { container } = renderRow(makeJob({ recommendation: null }))
    expect(container.textContent).toContain('—')
  })
})

describe('JobRow tracking status', () => {
  it('renders the tracking badge', () => {
    renderRow(makeJob({ tracking_status: 'interview' }))
    expect(screen.getByText('Interview')).toBeInTheDocument()
  })

  it('renders Not Applied when there is no tracking status', () => {
    renderRow(makeJob({ tracking_status: null }))
    expect(screen.getByText('Not Applied')).toBeInTheDocument()
  })
})

describe('JobRow grade', () => {
  it('renders a grade badge derived from the overall score', () => {
    renderRow(makeJob({ scores: { overall: 92, fit: 90, success: 85 } }))
    expect(screen.getByText('A++')).toBeInTheDocument()
  })

  it('renders score badges in Overall, Success, Fit order', () => {
    const { container } = renderRow(makeJob({ scores: { overall: 92, fit: 90, success: 85 } }))
    const text = container.textContent ?? ''
    const overall = text.indexOf('92')
    const success = text.indexOf('85')
    const fit = text.indexOf('90')
    expect(overall).toBeGreaterThan(-1)
    expect(success).toBeGreaterThan(overall)
    expect(fit).toBeGreaterThan(success)
  })

  it('renders a compact rank badge at the start of the score group when present', () => {
    const { container } = renderRow(makeJob({ rank: 7, scores: { overall: 92, fit: 90, success: 85 } }))
    expect(screen.getByTestId('job-rank')).toBeInTheDocument()
    const text = container.textContent ?? ''
    const rank = text.indexOf('#7')
    const overall = text.indexOf('92')
    expect(rank).toBeGreaterThan(-1)
    expect(overall).toBeGreaterThan(rank)
  })

  it('does not render the rank badge when rank is absent', () => {
    renderRow(makeJob({ rank: null }))
    expect(screen.queryByTestId('job-rank')).not.toBeInTheDocument()
  })

  it('renders an em dash when there is no overall score', () => {
    const { container } = renderRow(makeJob())
    expect(container.textContent).toContain('—')
  })
})

describe('JobRow hover actions', () => {
  it('wraps the actions in a hover-revealed overlay (hidden by default)', () => {
    const { container } = renderRow(makeJob())
    expect(container.querySelector('[class*="group-hover:opacity-100"]')).not.toBeNull()
    expect(container.querySelector('[class*="group-hover:opacity-100"]')?.classList.contains('opacity-0')).toBe(true)
  })

  it('calls the delete handler and does not open details when an action is clicked', () => {
    const onDelete = vi.fn()
    const onViewDetails = vi.fn()
    renderRow(makeJob({
      job_status: 'completed',
      latest_processing_execution: { id: 'e1', status: 'completed', started_at: '2026-08-01T00:00:00Z', finished_at: '2026-08-01T00:00:00Z' },
    }), { onDelete, onViewDetails })

    fireEvent.click(screen.getByLabelText('Delete'))

    expect(onDelete).toHaveBeenCalled()
    expect(onViewDetails).not.toHaveBeenCalled()
  })
})
