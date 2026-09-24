import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { CompanyRow } from './CompanyRow'
import type { CompanyListItem } from '@/entities/company/types'

function makeCompany(overrides: Partial<CompanyListItem> = {}): CompanyListItem {
  return {
    id: 'company-1',
    name: 'Acme GmbH',
    industry: 'Software',
    city: 'Berlin',
    country: 'Germany',
    company_size: '50-200',
    company_type: 'PRODUCT_COMPANY',
    logo_url: null,
    website: null,
    description: null,
    job_count: 3,
    recruiter_job_count: 0,
    scores: { overall: null, fit: null, success: null, overall_grade: null },
    processing: { status: null, current_node: null, progress_pct: null, error: null },
    latest_processing_execution: null,
    parent_company_id: null,
    main_company: null,
    alias_count: 0,
    is_alias: false,
    pinned: false,
    updated_at: null,
    created_at: '2026-08-01T00:00:00Z',
    ...overrides,
  }
}

function renderRow(company: CompanyListItem) {
  return render(
    <CompanyRow
      company={company}
      onViewDetails={vi.fn()}
      onReprocess={vi.fn()}
      onEdit={vi.fn()}
      onDelete={vi.fn()}
    />
  )
}

describe('CompanyRow scores', () => {
  it('renders the processing-computed fit, success and overall values', () => {
    renderRow(makeCompany({ scores: { overall: 80, fit: 88, success: 72, overall_grade: 'A+' } }))

    expect(screen.getByText('88')).toBeInTheDocument()
    expect(screen.getByText('72')).toBeInTheDocument()
    expect(screen.getByText('80')).toBeInTheDocument()
    expect(screen.getByText('A+')).toBeInTheDocument()
  })

  it('renders score values in Overall, Success, Fit order', () => {
    const { container } = renderRow(makeCompany({ scores: { overall: 80, fit: 88, success: 72, overall_grade: 'A+' } }))
    const text = container.textContent ?? ''
    const overall = text.indexOf('80')
    const success = text.indexOf('72')
    const fit = text.indexOf('88')
    expect(overall).toBeGreaterThan(-1)
    expect(success).toBeGreaterThan(overall)
    expect(fit).toBeGreaterThan(success)
  })

  it('shows the overall_grade computed by processing when present', () => {
    renderRow(makeCompany({ scores: { overall: 80, fit: 88, success: 72, overall_grade: 'A+' } }))
    expect(screen.getByText('A+')).toBeInTheDocument()
  })

  it('falls back to deriving the grade from the overall score', () => {
    renderRow(makeCompany({ scores: { overall: 85, fit: 88, success: 72, overall_grade: null } }))
    expect(screen.getByText('A+')).toBeInTheDocument()
  })

  it('renders placeholders when there is no processing score', () => {
    renderRow(makeCompany({ scores: { overall: null, fit: null, success: null, overall_grade: null } }))

    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
    expect(screen.queryByText('A+')).not.toBeInTheDocument()
  })

  it('shows the alias badge for alias companies', () => {
    renderRow(makeCompany({
      scores: { overall: 80, fit: 88, success: 72, overall_grade: 'A+' },
      is_alias: true,
      main_company: { id: 'company-2', name: 'Acme SE' },
      parent_company_id: 'company-2',
    }))
    expect(screen.getByText('alias')).toBeInTheDocument()
  })
})

describe('CompanyRow status', () => {
  it('renders the shared StatusBadge for the execution status', () => {
    renderRow(makeCompany({ processing: { status: 'running', current_node: null, progress_pct: 40, error: null } }))
    expect(screen.getByText('Running')).toBeInTheDocument()
  })

  it('renders a dash when there is no execution status', () => {
    renderRow(makeCompany())
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })
})

describe('CompanyRow jobs column', () => {
  it('shows job_count for product companies', () => {
    renderRow(makeCompany({ company_type: 'PRODUCT_COMPANY', job_count: 3, recruiter_job_count: 0 }))
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('shows recruiter_job_count for recruiter companies', () => {
    renderRow(makeCompany({
      company_type: 'RECRUITING_AGENCY',
      job_count: 0,
      recruiter_job_count: 7,
    }))
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByTitle('7 jobs listed for clients')).toBeInTheDocument()
  })

  it('shows a dash when a recruiter has no listed jobs', () => {
    renderRow(makeCompany({ company_type: 'STAFFING_COMPANY', job_count: 0, recruiter_job_count: 0 }))
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })
})

describe('CompanyRow recruiter tint', () => {
  it('marks recruiter rows with the purple tint attribute', () => {
    const { container } = renderRow(makeCompany({
      company_type: 'RECRUITING_AGENCY',
      recruiter_job_count: 3,
    }))
    expect(container.querySelector('[data-recruiter="true"]')).toBeInTheDocument()
  })

  it('does not tint product company rows', () => {
    const { container } = renderRow(makeCompany({
      company_type: 'PRODUCT_COMPANY',
      recruiter_job_count: 0,
    }))
    expect(container.querySelector('[data-recruiter="false"]')).toBeInTheDocument()
  })

  it('tints companies detected as recruiters by listed job count', () => {
    const { container } = renderRow(makeCompany({
      company_type: 'PRODUCT_COMPANY',
      recruiter_job_count: 2,
    }))
    expect(container.querySelector('[data-recruiter="true"]')).toBeInTheDocument()
  })
})

describe('CompanyRow row-number column', () => {
  it('renders no row number when the column is off', () => {
    renderRow(makeCompany())
    expect(screen.queryByText('5')).not.toBeInTheDocument()
  })

  it('renders the row number when the column is shown', () => {
    render(
      <CompanyRow
        company={makeCompany()}
        onViewDetails={vi.fn()}
        onReprocess={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        showRowNumberColumn
        rowNumber={5}
      />
    )
    expect(screen.getByText('5')).toBeInTheDocument()
  })
})

describe('CompanyRow hover actions', () => {
  it('wraps the actions in a hover-revealed overlay (hidden by default)', () => {
    const { container } = renderRow(makeCompany())
    const overlay = container.querySelector('[class*="group-hover:opacity-100"]')
    expect(overlay).not.toBeNull()
    expect(overlay?.classList.contains('opacity-0')).toBe(true)
  })

  it('calls the delete handler and does not open details when an action is clicked', () => {
    const onDelete = vi.fn()
    const onViewDetails = vi.fn()
    render(
      <CompanyRow
        company={makeCompany()}
        onViewDetails={onViewDetails}
        onReprocess={vi.fn()}
        onEdit={vi.fn()}
        onDelete={onDelete}
      />
    )

    fireEvent.click(screen.getByLabelText('Delete'))

    expect(onDelete).toHaveBeenCalled()
    expect(onViewDetails).not.toHaveBeenCalled()
  })
})

describe('CompanyRow company type column', () => {
  it('renders the formatted company type as a badge without the "Company" suffix', () => {
    renderRow(makeCompany({ company_type: 'CONSULTING_COMPANY' }))
    expect(screen.getByText('Consulting')).toBeInTheDocument()
    expect(screen.queryByText('Consulting Company')).not.toBeInTheDocument()
  })

  it('renders Unknown for a null company type', () => {
    renderRow(makeCompany({ company_type: null }))
    expect(screen.getByText('Unknown')).toBeInTheDocument()
  })
})

describe('CompanyRow company type row colors', () => {
  it('leaves product companies white (no tint class)', () => {
    const { container } = renderRow(makeCompany({ company_type: 'PRODUCT_COMPANY' }))
    const row = container.querySelector('[data-recruiter]')
    const tinted = ['bg-blue-500/5', 'bg-purple-500/5', 'bg-orange-500/5', 'bg-teal-500/5', 'bg-muted/40']
    for (const cls of tinted) {
      expect(row?.className).not.toContain(cls)
    }
  })

  it('gives each non-product type a unique row tint', () => {
    const cases: Array<[string, string]> = [
      ['RECRUITING_AGENCY', 'bg-purple-500/5'],
      ['STAFFING_COMPANY', 'bg-orange-500/5'],
      ['CONSULTING_COMPANY', 'bg-teal-500/5'],
      ['UNKNOWN', 'bg-muted/40'],
    ]
    for (const [type, cls] of cases) {
      const { container } = renderRow(makeCompany({ company_type: type }))
      expect(container.querySelector('[class*="bg-"]')?.className).toContain(cls)
    }
  })

  it('falls back to the recruiter purple tint when no type but recruiter job count', () => {
    const { container } = renderRow(makeCompany({ company_type: null, recruiter_job_count: 3 }))
    expect(container.querySelector('[class*="bg-purple-500/5"]')).not.toBeNull()
  })
})
