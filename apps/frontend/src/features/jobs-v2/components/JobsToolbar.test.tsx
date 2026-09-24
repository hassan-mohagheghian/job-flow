import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { JobsToolbar } from './JobsToolbar'

function renderToolbar(overrides: Record<string, unknown> = {}) {
  const props = {
    query: '',
    onQueryChange: vi.fn(),
    filterProcessingStatus: '',
    onFilterProcessingStatusChange: vi.fn(),
    filterLocation: '',
    onFilterLocationChange: vi.fn(),
    filterRemote: '',
    onFilterRemoteChange: vi.fn(),
    filterVisa: '',
    onFilterVisaChange: vi.fn(),
    filterPinned: false,
    onFilterPinnedChange: vi.fn(),
    filterRecommendation: [],
    onFilterRecommendationChange: vi.fn(),
    filterTrackingStatus: [],
    onFilterTrackingStatusChange: vi.fn(),
    filterCreatedDate: '',
    onFilterCreatedDateChange: vi.fn(),
    activeFilterCount: 0,
    onClearFilters: vi.fn(),
    ...overrides,
  }
  return render(<JobsToolbar {...(props as any)} />)
}

describe('JobsToolbar search shortcut', () => {
  it('focuses the search input when F is pressed', () => {
    renderToolbar()
    const search = screen.getByLabelText('Search jobs')

    fireEvent.keyDown(window, { key: 'f' })

    expect(search).toHaveFocus()
  })

  it('does not steal focus when typing inside the search input', () => {
    renderToolbar()
    const search = screen.getByLabelText('Search jobs')

    fireEvent.keyDown(search, { key: 'f' })

    expect(search).not.toHaveFocus()
  })
})

describe('JobsToolbar location filter', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders a location input', () => {
    renderToolbar()
    expect(screen.getByLabelText('Filter by location')).toBeInTheDocument()
  })

  it('debounces typed locations before reporting them', () => {
    const onFilterLocationChange = vi.fn()
    renderToolbar({ onFilterLocationChange })

    fireEvent.change(screen.getByLabelText('Filter by location'), { target: { value: 'Berlin' } })

    expect(onFilterLocationChange).not.toHaveBeenCalled()

    act(() => {
      vi.advanceTimersByTime(300)
    })

    expect(onFilterLocationChange).toHaveBeenCalledWith('Berlin')
  })

  it('shows a clear button and clears the filter on click', () => {
    const onFilterLocationChange = vi.fn()
    renderToolbar({ filterLocation: 'Berlin', onFilterLocationChange })

    fireEvent.click(screen.getByLabelText('Clear location filter'))

    expect(onFilterLocationChange).toHaveBeenCalledWith('')
  })
})

describe('JobsToolbar pinned filter', () => {
  it('renders the pinned toggle', () => {
    renderToolbar()
    expect(screen.getByLabelText('Show pinned only')).toBeInTheDocument()
  })

  it('toggles the pinned filter on click', () => {
    const onFilterPinnedChange = vi.fn()
    renderToolbar({ onFilterPinnedChange })

    fireEvent.click(screen.getByLabelText('Show pinned only'))

    expect(onFilterPinnedChange).toHaveBeenCalledWith(true)
  })

  it('toggles the pinned filter off when active', () => {
    const onFilterPinnedChange = vi.fn()
    renderToolbar({ filterPinned: true, onFilterPinnedChange })

    fireEvent.click(screen.getByLabelText('Show pinned only'))

    expect(onFilterPinnedChange).toHaveBeenCalledWith(false)
  })
})

describe('JobsToolbar recommendation filter', () => {
  it('renders a recommendation filter', () => {
    renderToolbar()
    expect(screen.getByText('Recommendation')).toBeInTheDocument()
  })

  it('reports the selected recommendation (multi-select)', async () => {
    const user = userEvent.setup()
    const onFilterRecommendationChange = vi.fn()
    renderToolbar({ onFilterRecommendationChange })

    await user.click(screen.getByText('Recommendation'))
    await user.click(screen.getByText('Apply'))

    expect(onFilterRecommendationChange).toHaveBeenCalledWith(['apply'])
  })

  it('shows a selection count badge for recommendation', () => {
    renderToolbar({ filterRecommendation: ['consider'] })
    expect(screen.getByText('Recommendation')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
  })
})

describe('JobsToolbar tracking filter', () => {
  it('renders a tracking filter', () => {
    renderToolbar()
    expect(screen.getByText('Tracking')).toBeInTheDocument()
  })

  it('reports the selected tracking status (multi-select)', async () => {
    const user = userEvent.setup()
    const onFilterTrackingStatusChange = vi.fn()
    renderToolbar({ onFilterTrackingStatusChange })

    await user.click(screen.getByText('Tracking'))
    await user.click(screen.getByText('Applied'))

    expect(onFilterTrackingStatusChange).toHaveBeenCalledWith(['applied'])
  })

  it('shows a selection count badge for tracking', () => {
    renderToolbar({ filterTrackingStatus: ['interview'] })
    expect(screen.getByText('Tracking')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
  })
})

describe('JobsToolbar created-date filter', () => {
  it('renders a date select', () => {
    renderToolbar()
    expect(screen.getByText('Date')).toBeInTheDocument()
  })

  it('reports the selected created-date preset', () => {
    const onFilterCreatedDateChange = vi.fn()
    renderToolbar({ onFilterCreatedDateChange })

    fireEvent.click(screen.getByText('Date'))
    fireEvent.click(screen.getByText('Yesterday'))

    expect(onFilterCreatedDateChange).toHaveBeenCalledWith('yesterday')
  })

  it('shows the selected created-date label when active', () => {
    renderToolbar({ filterCreatedDate: 'week' })
    expect(screen.getByText('Last Week')).toBeInTheDocument()
  })
})

describe('JobsToolbar columns toggle', () => {
  it('renders a Columns dropdown when a row-number toggle handler is provided', () => {
    renderToolbar({ onToggleRowNumberColumn: vi.fn() })
    expect(screen.getByText('Columns')).toBeInTheDocument()
  })

  it('does not render the Columns dropdown without a toggle handler', () => {
    renderToolbar()
    expect(screen.queryByText('Columns')).not.toBeInTheDocument()
  })

  it('shows the Row number option and reports its toggle', async () => {
    const user = userEvent.setup()
    const onToggleRowNumberColumn = vi.fn()
    renderToolbar({ showRowNumberColumn: false, onToggleRowNumberColumn })
    await user.click(screen.getByText('Columns'))
    const option = within(await screen.findByRole('menu')).getByText('Row number')
    await user.click(option)
    expect(onToggleRowNumberColumn).toHaveBeenCalledWith(true)
  })

  it('does not list a Pinned option in the Columns dropdown', async () => {
    const user = userEvent.setup()
    renderToolbar({ showRowNumberColumn: true, onToggleRowNumberColumn: vi.fn() })
    await user.click(screen.getByText('Columns'))
    const menu = await screen.findByRole('menu')
    expect(within(menu).queryByText('Pinned')).not.toBeInTheDocument()
  })
})
