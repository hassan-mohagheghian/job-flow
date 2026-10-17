import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SourceDistributionChart, buildSlices } from './SourceDistributionChart'
import { MetricCard } from './MetricCard'
import { SourcesTable } from './SourcesTable'
import { DashboardPage } from './DashboardPage'
import type {
  SourceDistribution,
  SourceListItem,
  SourceStats,
} from '@/entities/job/sources'

const distribution: SourceDistribution = {
  items: [
    { id: '1', name: 'Indeed.com', domain: 'indeed.com', job_count: 412 },
    { id: '2', name: 'LinkedIn.com', domain: 'linkedin.com', job_count: 284 },
    { id: '3', name: 'StepStone.com', domain: 'stepstone.com', job_count: 190 },
    { id: '4', name: 'Jobinja.ir', domain: 'jobinja.ir', job_count: 60 },
    { id: '5', name: 'Staff.am', domain: 'staff.am', job_count: 40 },
  ],
  other_count: 40,
  unknown_count: 23,
}

const totalListings = 412 + 284 + 190 + 60 + 40 + 40 + 23

describe('buildSlices', () => {
  it('aggregates top 5 plus Other and Unknown with a percent helper', () => {
    const { slices, total, pct } = buildSlices(distribution)
    expect(total).toBe(totalListings)
    expect(slices.map((s) => s.label)).toEqual([
      'Indeed.com',
      'LinkedIn.com',
      'StepStone.com',
      'Jobinja.ir',
      'Staff.am',
      'Other',
      'Unknown',
    ])
    expect(slices[0].job_count).toBe(412)
    expect(slices.at(-2)?.job_count).toBe(40)
    expect(slices.at(-1)?.job_count).toBe(23)
    expect(pct(412)).toBe('39%')
  })

  it('handles an empty dataset', () => {
    const { slices, pct } = buildSlices({
      items: [],
      other_count: 0,
      unknown_count: 0,
    })
    expect(slices).toEqual([])
    expect(pct(10)).toBe('0%')
  })
})

describe('MetricCard', () => {
  it('renders value and label with an accessible label', () => {
    render(<MetricCard label="Total sources" value={14} />)
    expect(screen.getByText('14')).toBeInTheDocument()
    expect(screen.getByText('Total sources')).toBeInTheDocument()
    expect(screen.getByLabelText('Total sources: 14')).toBeInTheDocument()
  })
})

describe('SourceDistributionChart', () => {
  it('shows the alternative textual legend and total', () => {
    render(<SourceDistributionChart distribution={distribution} />)
    expect(screen.getByText('Indeed.com')).toBeInTheDocument()
    expect(screen.getByText('Unknown')).toBeInTheDocument()
    expect(screen.getByText(/total listings/i)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /doughnut chart/i })).toBeInTheDocument()
  })

  it('renders the empty state', () => {
    render(
      <SourceDistributionChart distribution={{ items: [], other_count: 0, unknown_count: 0 }} />,
    )
    expect(screen.getByText(/No sources yet/i)).toBeInTheDocument()
  })

  it('renders the loading state', () => {
    const { container } = render(<SourceDistributionChart distribution={distribution} isLoading />)
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })
})

const sources: SourceListItem[] = [
  {
    id: 'a',
    name: 'Indeed.com',
    canonical_url: 'https://indeed.com',
    domain: 'indeed.com',
    is_active: true,
    job_count: 412,
    last_activity: '2026-10-14T08:25:00.000Z',
  },
  {
    id: 'b',
    name: 'Empty Source',
    canonical_url: 'https://empty.io',
    domain: 'empty.io',
    is_active: false,
    job_count: 0,
    last_activity: null,
  },
]

function renderTable(overrides: Partial<Parameters<typeof SourcesTable>[0]> = {}) {
  const props = {
    items: sources,
    isLoading: false,
    isEmpty: false,
    page: 1,
    pageSize: 25,
    totalPages: 1,
    totalItems: 2,
    sortField: 'job_count' as const,
    sortOrder: 'desc' as const,
    searchValue: '',
    onSearchChange: vi.fn(),
    onSortChange: vi.fn(),
    onPageChange: vi.fn(),
    ...overrides,
  }
  return { props, ...render(<SourcesTable {...props} />) }
}

describe('SourcesTable', () => {
  it('renders rows with links, counts and activity', () => {
    renderTable()
    expect(screen.getByText('Indeed.com')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'indeed.com' })).toHaveAttribute(
      'href',
      'https://indeed.com',
    )
    expect(screen.getByText('412')).toBeInTheDocument()
    expect(screen.getByText('Empty Source')).toBeInTheDocument()
    expect(screen.getByText('Inactive')).toBeInTheDocument()
  })

  it('shows loading, empty and error states', () => {
    const first = renderTable({ items: [], isLoading: true, isEmpty: false })
    expect(screen.getByTestId('sources-table-loading')).toBeInTheDocument()
    first.unmount()

    renderTable({ items: [], isEmpty: true })
    expect(screen.getByText(/No sources yet/i)).toBeInTheDocument()
  })

  it('shows an error with retry', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    renderTable({ items: [], isError: true, errorMessage: 'boom', onRetry })
    expect(screen.getByRole('alert')).toHaveTextContent('Unable to load sources.')
    expect(screen.getByText('boom')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('paginates and disables edges', () => {
    const onPageChange = vi.fn()
    renderTable({ page: 2, totalPages: 3, onPageChange })
    expect(screen.getByText(/Page 2 of 3/)).toBeInTheDocument()
    screen.getByRole('button', { name: 'Previous page' }).click()
    screen.getByRole('button', { name: 'Next page' }).click()
    expect(onPageChange).toHaveBeenCalledWith(1)
    expect(onPageChange).toHaveBeenCalledWith(3)
  })

  it('disables Prev on first page and shows totals', () => {
    renderTable({ page: 1, totalPages: 1 })
    expect(screen.getByRole('button', { name: 'Previous page' })).toBeDisabled()
    expect(screen.getByText(/2 sources/)).toBeInTheDocument()
  })

  it('search input forwards changes', async () => {
    const user = userEvent.setup()
    const onSearchChange = vi.fn()
    renderTable({ onSearchChange })
    const input = screen.getByLabelText('Search sources')
    await user.type(input, 'inde')
    await waitFor(() => expect(onSearchChange).toHaveBeenCalled())
  })

  it('sort headers trigger onSortChange', () => {
    const onSortChange = vi.fn()
    renderTable({ onSortChange })
    screen.getByText('Source').click()
    screen.getByText('Jobs').click()
    screen.getByText('Last activity').click()
    expect(onSortChange).toHaveBeenCalledWith('name')
    expect(onSortChange).toHaveBeenCalledWith('job_count')
    expect(onSortChange).toHaveBeenCalledWith('last_activity')
  })
})

describe('DashboardPage', () => {
  const stats: SourceStats = {
    total_jobs: 1258,
    total_sources: 14,
    active_sources: 12,
    unknown_jobs: 23,
  }

  it('renders metric cards, chart panel and table from real props', () => {
    render(
      <DashboardPage
        stats={stats}
        distribution={distribution}
        statsLoading={false}
        distributionLoading={false}
        sources={[]}
        sourcesLoading={false}
        sourcesEmpty={false}
        page={1}
        pageSize={25}
        totalPages={1}
        totalItems={0}
        sortField="job_count"
        sortOrder="desc"
        searchValue=""
        onSearchChange={() => {}}
        onSortChange={() => {}}
        onPageChange={() => {}}
      />,
    )
    expect(screen.getByTestId('dashboard-page')).toBeInTheDocument()
    expect(screen.getByText('1,258')).toBeInTheDocument()
    expect(screen.getByLabelText('Total listings: 1258')).toBeInTheDocument()
    expect(screen.getByText('Unknown source')).toBeInTheDocument()
    expect(screen.getByTestId('distribution-panel')).toBeInTheDocument()
    expect(screen.getByText('Listings by source')).toBeInTheDocument()
  })

  it('metrics are zero-safe while loading', () => {
    render(
      <DashboardPage
        stats={undefined}
        statsLoading
        distributionLoading
        sources={[]}
        sourcesLoading
        sourcesEmpty={false}
        page={1}
        pageSize={25}
        totalPages={1}
        totalItems={0}
        sortField="job_count"
        sortOrder="desc"
        searchValue=""
        onSearchChange={() => {}}
        onSortChange={() => {}}
        onPageChange={() => {}}
      />,
    )
    expect(screen.getAllByTestId('metric-card')).toHaveLength(4)
    expect(screen.getAllByText('0')).toHaveLength(4)
  })
})
