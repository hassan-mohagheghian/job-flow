import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SkillsPage } from './SkillsPage'
import type { SkillListItem } from '@/entities/skill/types'

vi.mock('@/entities/skill/hooks', () => ({
  useCreateSkill: () => ({
    createSkill: vi.fn().mockResolvedValue(true),
    submitting: false,
    error: null,
    clearError: vi.fn(),
  }),
  useMergeSkills: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ status: 'merged' }),
    isPending: false,
  }),
  useBreakdownSkill: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ status: 'broken_down' }),
    isPending: false,
  }),
  usePromoteAliasToCanonical: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ status: 'promoted' }),
    isPending: false,
  }),
  useSkillCategories: () => ({
    categories: [],
    isLoading: false,
    createMutation: { mutateAsync: vi.fn().mockResolvedValue({ id: 9, name: 'data', created: true }) },
    deleteMutation: { mutateAsync: vi.fn() },
  }),
  useSkillReferencedJobs: () => ({
    data: { jobs: [], total: 0 },
    isLoading: false,
    isError: false,
  }),
}))

vi.mock('@/entities/skill/api', () => ({
  skillApi: {
    listInfinite: vi.fn().mockResolvedValue({
      items: [{ id: 9, name: 'React', mention_count: 3, categories: [] }],
      next_cursor: null,
      has_more: false,
      total_items: 1,
    }),
    merge: vi.fn().mockResolvedValue({ status: 'merged' }),
  },
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

function makeSkill(id: number, name: string): SkillListItem {
  return {
    id,
    name,
    level: 3,
    roles: '',
    path: '',
    category: 'technical',
    categories: ['technical'],
    confidence: 0.8,
    market_relevance: 0.9,
    evidence: null,
    tags: [],
    aliases: [],
    source_type: 'user_input',
    mention_count: 0,
    pinned: false,
    created_at: '2026-08-01T00:00:00Z',
  }
}

function baseProps(overrides: Partial<Parameters<typeof SkillsPage>[0]> = {}): Parameters<typeof SkillsPage>[0] {
  return {
    items: [],
    total: 0,
    loadedCount: 0,
    isLoading: false,
    isFetchingNextPage: false,
    hasNextPage: false,
    onFetchNextPage: vi.fn(),
    isError: false,
    error: null,
    onRefetch: vi.fn(),
    query: '',
    onQueryChange: vi.fn(),
    sort: 'mention_count',
    onSortChange: vi.fn(),
    order: 'desc',
    filterCategories: [],
    onFilterCategoriesChange: vi.fn(),
    categoryOptions: [],
    activeFilterCount: 0,
    onClearFilters: vi.fn(),
    onViewDetails: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    addSkillDrawerOpen: false,
    onAddSkillDrawerOpenChange: vi.fn(),
    detailSkillId: null,
    onDetailSkillIdChange: vi.fn(),
    editSkillId: null,
    onEditSkillIdChange: vi.fn(),
    ...overrides,
  }
}

function renderPage(props: Parameters<typeof SkillsPage>[0]) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <SkillsPage {...props} />
    </QueryClientProvider>
  )
}

describe('SkillsPage', () => {
  it('renders the header with total count', () => {
    renderPage(baseProps({ total: 12 }))
    expect(screen.getByText(/Skills \(12\)/)).toBeInTheDocument()
  })

  it('shows empty state when there are no skills', () => {
    renderPage(baseProps())
    expect(screen.getByText(/No skills yet/)).toBeInTheDocument()
  })

  it('renders the toolbar and rows are rendered via the virtualized table', () => {
    renderPage(baseProps({
      items: [makeSkill(1, 'Kubernetes'), makeSkill(2, 'Python')],
      total: 2,
      loadedCount: 2,
    }))
    expect(screen.getByText(/Skills \(2\)/)).toBeInTheDocument()
  })

  it('shows the error state with a retry button', () => {
    renderPage(baseProps({
      isError: true,
      error: new Error('boom'),
    }))
    expect(screen.getByText('Unable to load skills')).toBeInTheDocument()
    expect(screen.getByText('Retry')).toBeInTheDocument()
  })

  it('triggers onRefetch when the refresh button is clicked', () => {
    const onRefetch = vi.fn()
    renderPage(baseProps({ onRefetch }))
    fireEvent.click(screen.getByRole('button', { name: 'Refresh skills' }))
    expect(onRefetch).toHaveBeenCalledTimes(1)
  })

  it('disables the refresh button while refreshing', () => {
    renderPage(baseProps({ isRefetching: true }))
    expect(screen.getByRole('button', { name: 'Refresh skills' })).toBeDisabled()
  })

  it('focuses the search input when F is pressed', () => {
    renderPage(baseProps())
    const search = screen.getByLabelText('Search skills')

    fireEvent.keyDown(window, { key: 'f' })

    expect(search).toHaveFocus()
  })

  it('does not expose a Pinned option in the Columns dropdown', async () => {
    const user = userEvent.setup()
    renderPage(baseProps({ showRowNumberColumn: true, onToggleRowNumberColumn: vi.fn() }))
    await user.click(screen.getByText('Columns'))
    const menu = await screen.findByRole('menu')
    expect(within(menu).queryByText('Pinned')).not.toBeInTheDocument()
  })

  it('reports a column toggle when the Select option is clicked', async () => {
    const user = userEvent.setup()
    const onToggleSelectColumn = vi.fn()
    renderPage(baseProps({ showSelectColumn: false, onToggleSelectColumn }))
    await user.click(screen.getByText('Columns'))
    const option = await screen.findByText('Select')
    await user.click(option)
    expect(onToggleSelectColumn).toHaveBeenCalledWith(true)
  })

  it('renders the row-number header when the row-number column is shown', () => {
    renderPage(baseProps({
      items: [makeSkill(1, 'Kubernetes')],
      total: 1,
      loadedCount: 1,
      showRowNumberColumn: true,
      onToggleRowNumberColumn: vi.fn(),
    }))
    expect(screen.getByText('#')).toBeInTheDocument()
  })

  it('reports a column toggle when the Row number option is clicked', async () => {
    const user = userEvent.setup()
    const onToggleRowNumberColumn = vi.fn()
    renderPage(baseProps({ showRowNumberColumn: false, onToggleRowNumberColumn }))
    await user.click(screen.getByText('Columns'))
    const option = await screen.findByText('Row number')
    await user.click(option)
    expect(onToggleRowNumberColumn).toHaveBeenCalledWith(true)
  })

  it('renders the pinned filter button', () => {
    renderPage(baseProps({ onFilterPinnedChange: vi.fn() }))
    expect(screen.getByLabelText('Show pinned skills only')).toBeInTheDocument()
  })

  it('toggles the pinned filter on click', () => {
    const onFilterPinnedChange = vi.fn()
    renderPage(baseProps({ onFilterPinnedChange }))
    fireEvent.click(screen.getByLabelText('Show pinned skills only'))
    expect(onFilterPinnedChange).toHaveBeenCalledWith(true)
  })

  it('toggles the pinned filter off when active', () => {
    const onFilterPinnedChange = vi.fn()
    renderPage(baseProps({ filterPinned: true, onFilterPinnedChange }))
    fireEvent.click(screen.getByLabelText('Show pinned skills only'))
    expect(onFilterPinnedChange).toHaveBeenCalledWith(false)
  })

  it('does not show the bulk bar when nothing is selected', () => {
    renderPage(baseProps({
      items: [makeSkill(1, 'Kubernetes'), makeSkill(2, 'Python')],
      total: 2,
      loadedCount: 2,
      showSelectColumn: true,
    }))
    expect(screen.queryByText(/selected/)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Merge/ })).not.toBeInTheDocument()
  })

  it('selects all loaded skills via the header checkbox and shows the bulk bar', async () => {
    const user = userEvent.setup()
    renderPage(baseProps({
      items: [makeSkill(1, 'Kubernetes'), makeSkill(2, 'Python')],
      total: 2,
      loadedCount: 2,
      showSelectColumn: true,
    }))

    await user.click(screen.getByLabelText('Select all skills'))

    expect(screen.getByText('2 selected')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Merge 2 into/ })).toBeInTheDocument()
  })

  it('clears the selection with the bulk bar Clear button', async () => {
    const user = userEvent.setup()
    renderPage(baseProps({
      items: [makeSkill(1, 'Kubernetes')],
      total: 1,
      loadedCount: 1,
      showSelectColumn: true,
    }))

    await user.click(screen.getByLabelText('Select all skills'))
    expect(screen.getByText('1 selected')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Clear/ }))
    expect(screen.queryByText(/selected/)).not.toBeInTheDocument()
  })

  it('merges all selected skills into the picked target', async () => {
    const user = userEvent.setup()
    renderPage(baseProps({
      items: [makeSkill(1, 'Kubernetes'), makeSkill(2, 'Python')],
      total: 2,
      loadedCount: 2,
      showSelectColumn: true,
    }))

    await user.click(screen.getByLabelText('Select all skills'))
    await user.click(screen.getByRole('button', { name: /Merge 2 into/ }))

    const target = await screen.findByText('React')
    await user.click(target)
    await user.click(screen.getByRole('button', { name: /Merge 2 into selected/ }))

    const { toast } = await import('sonner')
    expect(toast.success).toHaveBeenCalledWith('Merged 2 skills')
    await waitFor(() => {
      expect(screen.queryByText(/selected/)).not.toBeInTheDocument()
    })
  })
})
