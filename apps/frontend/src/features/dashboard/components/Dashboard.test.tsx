import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { SourceDistributionChart, buildSlices } from './SourceDistributionChart'
import { buildRecommendationSlices, RecommendationChart } from './RecommendationChart'
import {
  ApplicationStatusChart,
  buildApplicationStatusSlices,
} from './ApplicationStatusChart'
import { MetricCard } from './MetricCard'
import { SourcesTable } from './SourcesTable'
import { DashboardPage } from './DashboardPage'
import type {
  JobApplicationStatusDistribution,
  RecommendationDistribution,
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

const recommendations: RecommendationDistribution = {
  items: [
    { recommendation: 'apply', count: 12 },
    { recommendation: 'consider', count: 7 },
    { recommendation: 'skip', count: 3 },
  ],
  total: 29,
}

describe('buildRecommendationSlices', () => {
  it('keeps bucket order and hides zero/missing buckets', () => {
    const { slices, total, pct } = buildRecommendationSlices(recommendations)
    expect(total).toBe(22)
    expect(slices.map((s) => s.label)).toEqual(['Apply', 'Consider', 'Skip'])
    expect(slices[0].color).not.toBe(slices[1].color)
    expect(pct(12)).toBe('55%')
  })

  it('maps jobs without analysis to No analysis', () => {
    const { slices } = buildRecommendationSlices({
      items: [{ recommendation: 'none', count: 4 }],
      total: 4,
    })
    expect(slices.map((s) => s.label)).toEqual(['No analysis'])
  })

  it('is empty-safe', () => {
    const { slices, total } = buildRecommendationSlices({ items: [], total: 0 })
    expect(slices).toEqual([])
    expect(total).toBe(0)
  })
})

describe('RecommendationChart', () => {
  it('renders the legend, total and chart role', () => {
    render(<RecommendationChart distribution={recommendations} />)
    expect(screen.getByTestId('recommendation-chart')).toBeInTheDocument()
    expect(screen.getByText('Apply')).toBeInTheDocument()
    expect(screen.queryByText('No analysis')).not.toBeInTheDocument()
    expect(screen.getByRole('img', { name: /jobs per recommendation/i })).toBeInTheDocument()
    expect(screen.getByText(/22 total listings/)).toBeInTheDocument()
  })

  it('empty and loading states', () => {
    const { unmount } = render(
      <RecommendationChart distribution={{ items: [], total: 0 }} />,
    )
    expect(screen.getByText(/No recommendations yet/i)).toBeInTheDocument()
    unmount()
    const { container } = render(<RecommendationChart distribution={recommendations} isLoading />)
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })
})

const applicationStatuses: JobApplicationStatusDistribution = {
  items: [
    { status: 'not_applied', count: 20 },
    { status: 'seen', count: 5 },
    { status: 'applied', count: 12 },
    { status: 'interview', count: 4 },
    { status: 'offer', count: 1 },
    { status: 'accepted', count: 2 },
    { status: 'rejected', count: 3 },
    { status: 'withdrawn', count: 1 },
  ],
  total: 48,
}

describe('buildApplicationStatusSlices', () => {
  it('keeps the important funnel order and folds the terminal leftovers into Other statuses', () => {
    const { slices, total, pct } = buildApplicationStatusSlices(applicationStatuses)

    expect(total).toBe(48)
    expect(slices.map((slice) => slice.label)).toEqual([
      'Not applied',
      'Applied',
      'Interview',
      'Offer',
      'Accepted',
      'Rejected',
      'Other statuses',
    ])
    expect(slices[0]?.job_count).toBe(25)
    expect(slices.at(-1)?.job_count).toBe(1)
    expect(pct(12)).toBe('25%')
  })

  it('counts jobs without an application and pre-application statuses as Not applied', () => {
    const { slices } = buildApplicationStatusSlices({
      items: [
        { status: 'not_applied', count: 4 },
        { status: 'seen', count: 2 },
        { status: 'preparing', count: 3 },
        { status: 'ready_to_apply', count: 1 },
        { status: 'applied', count: 4 },
      ],
      total: 14,
    })

    expect(slices[0]?.label).toBe('Not applied')
    expect(slices[0]?.job_count).toBe(10)
    expect(slices.map((slice) => slice.label)).toEqual([
      'Not applied',
      'Applied',
    ])
  })

  it('shows every job as Not applied when no application exists yet', () => {
    const { slices, total } = buildApplicationStatusSlices({
      items: [{ status: 'not_applied', count: 9 }],
      total: 9,
    })

    expect(total).toBe(9)
    expect(slices).toEqual([
      expect.objectContaining({ key: 'not_applied', job_count: 9 }),
    ])
  })

  it('hides zero-count slices and has no Other bucket when every status is important', () => {
    const { slices } = buildApplicationStatusSlices({
      items: [
        { status: 'applied', count: 2 },
        { status: 'rejected', count: 1 },
      ],
      total: 3,
    })

    expect(slices.map((slice) => slice.label)).toEqual(['Applied', 'Rejected'])
  })

  it('is empty-safe', () => {
    const { slices, total } = buildApplicationStatusSlices({ items: [], total: 0 })
    expect(slices).toEqual([])
    expect(total).toBe(0)
  })
})

describe('ApplicationStatusChart', () => {
  it('renders the legend, total and chart role', () => {
    render(<ApplicationStatusChart distribution={applicationStatuses} />)

    expect(screen.getByTestId('application-status-chart')).toBeInTheDocument()
    expect(screen.getByText('Not applied')).toBeInTheDocument()
    expect(screen.getByText('Applied')).toBeInTheDocument()
    expect(screen.getByText('Other statuses')).toBeInTheDocument()
    expect(
      screen.getByRole('img', { name: /applications per status/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/48 total jobs/)).toBeInTheDocument()
  })

  it('empty and loading states', () => {
    const { unmount } = render(
      <ApplicationStatusChart distribution={{ items: [], total: 0 }} />,
    )
    expect(screen.getByText(/No jobs yet/i)).toBeInTheDocument()
    unmount()
    const { container } = render(
      <ApplicationStatusChart distribution={applicationStatuses} isLoading />,
    )
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })
})

describe('MetricCard', () => {  it('renders value and label with an accessible label', () => {
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
    pageSize: 10,
    totalPages: 1,
    totalItems: 2,
    sortField: 'job_count' as const,
    sortOrder: 'desc' as const,
    searchValue: '',
    onSearchChange: vi.fn(),
    onSortChange: vi.fn(),
    onPageChange: vi.fn(),
    onPageSizeChange: vi.fn(),
    ...overrides,
  }
  return { props, ...render(<SourcesTable {...props} />) }
}

describe('SourcesTable', () => {
  // jsdom lacks pointer-capture APIs that Radix Select relies on.
  beforeAll(() => {
    Element.prototype.hasPointerCapture = () => false
    Element.prototype.setPointerCapture = () => {}
    Element.prototype.releasePointerCapture = () => {}
    Element.prototype.scrollIntoView = () => {}
  })
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

  it('changes page size via the per-page select', async () => {
    const user = userEvent.setup()
    const onPageSizeChange = vi.fn()
    renderTable({ onPageSizeChange })
    await user.click(screen.getByRole('combobox', { name: 'Rows per page' }))
    await user.keyboard('{ArrowDown}{Enter}') // 10 → 20
    expect(onPageSizeChange).toHaveBeenCalledWith(20)
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

  const baseProps = {
    stats,
    distribution,
    recommendations,
    applicationStatuses,
    statsLoading: false,
    distributionLoading: false,
    recommendationsLoading: false,
    applicationStatusesLoading: false,
    sources: [],
    sourcesLoading: false,
    sourcesEmpty: false,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    totalItems: 0,
    sortField: 'job_count' as const,
    sortOrder: 'desc' as const,
    searchValue: '',
    onSearchChange: () => {},
    onSortChange: () => {},
    onPageChange: () => {},
    onPageSizeChange: () => {},
  }

  it('renders metric cards, chart panels, recommendation panel and table', () => {
    render(<DashboardPage {...baseProps} />)
    expect(screen.getByTestId('dashboard-page')).toBeInTheDocument()
    expect(screen.getByText('1,258')).toBeInTheDocument()
    expect(screen.getByLabelText('Total listings: 1258')).toBeInTheDocument()
    expect(screen.getByText('Unknown source')).toBeInTheDocument()
    expect(screen.getByTestId('distribution-panel')).toBeInTheDocument()
    expect(screen.getByText('Listings by source')).toBeInTheDocument()
    expect(screen.getByTestId('recommendation-panel')).toBeInTheDocument()
    expect(screen.getByText('Jobs by recommendation')).toBeInTheDocument()
    expect(screen.getByText('Apply')).toBeInTheDocument()
    expect(screen.getByText('Consider')).toBeInTheDocument()
    expect(screen.getByTestId('application-status-panel')).toBeInTheDocument()
    expect(screen.getByText('Applications by status')).toBeInTheDocument()
    expect(screen.getByText('Applied')).toBeInTheDocument()
    expect(screen.getByTestId('sources-table')).toBeInTheDocument()
  })

  it('shows application status errors with retry', async () => {
    const user = userEvent.setup()
    const onRetryApplicationStatuses = vi.fn()
    render(
      <DashboardPage
        {...baseProps}
        applicationStatusesError="boom"
        onRetryApplicationStatuses={onRetryApplicationStatuses}
      />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Unable to load application statuses.')
    await user.click(screen.getByText('Retry'))
    expect(onRetryApplicationStatuses).toHaveBeenCalledOnce()
  })

  it('shows recommendation errors with retry', async () => {
    const user = userEvent.setup()
    const onRetryRecommendations = vi.fn()
    render(
      <DashboardPage
        {...baseProps}
        recommendationsError="boom"
        onRetryRecommendations={onRetryRecommendations}
      />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Unable to load recommendations.')
    await user.click(screen.getByText('Retry'))
    expect(onRetryRecommendations).toHaveBeenCalledOnce()
  })

  it('metrics are zero-safe while loading', () => {
    render(
      <DashboardPage
        {...baseProps}
        stats={undefined}
        recommendations={undefined}
        applicationStatuses={undefined}
        statsLoading
        distributionLoading
        recommendationsLoading
        applicationStatusesLoading
        sources={[]}
        sourcesLoading
        sourcesEmpty={false}
      />,
    )
    expect(screen.getAllByTestId('metric-card')).toHaveLength(4)
    expect(screen.getAllByText('0').length).toBeGreaterThanOrEqual(4)
  })
})
