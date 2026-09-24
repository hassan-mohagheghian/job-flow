import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useJobsInfiniteQuery } from './useJobsInfiniteQuery'
import { jobApi } from '@/entities/job/api'
import type { JobListItem, InfiniteJobSearchResult } from '@/entities/job/types'

vi.mock('@/entities/job/api', () => ({
  jobApi: {
    searchInfinite: vi.fn(),
    deleteJob: vi.fn(),
    setPinned: vi.fn(),
  },
}))

function makeJob(id: string): JobListItem {
  return {
    id,
    title: `Job ${id}`,
    company_name: 'Acme',
    location: 'Berlin',
    remote: false,
    visa_sponsorship: true,
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
  }
}

function page(items: JobListItem[], total_items: number, has_more = false, next_cursor: string | null = null): InfiniteJobSearchResult {
  return { items, total_items, has_more, next_cursor }
}

function wrapper(qc: QueryClient) {
  return function QueryClientWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe('useJobsInfiniteQuery.deleteMutation', () => {
  let qc: QueryClient
  let firstPage: JobListItem[]
  let secondPage: JobListItem[]

  beforeEach(() => {
    vi.clearAllMocks()
    qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    firstPage = [makeJob('job-1'), makeJob('job-2')]
    secondPage = [makeJob('job-3')]
    vi.mocked(jobApi.searchInfinite).mockImplementation((_q) =>
      Promise.resolve(_q?.cursor ? page(secondPage, 3, false) : page(firstPage, 3, true, 'cursor-2'))
    )
  })

  it('optimistically removes the job and decrements the total before the request resolves', async () => {
    let resolveDelete!: () => void
    vi.mocked(jobApi.deleteJob).mockImplementation(() => new Promise<void>((resolve) => { resolveDelete = resolve }))

    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(result.current.items).toHaveLength(2)
    })

    act(() => {
      result.current.deleteMutation.mutate('job-1')
    })

    await waitFor(() => {
      const cached = qc.getQueriesData<{ pages: { items: JobListItem[]; total_items: number }[] }>({ queryKey: ['jobs-v2-infinite'] })
      const pages = cached[0]?.[1]?.pages ?? []
      expect(pages[0].items.map(i => i.id)).not.toContain('job-1')
      expect(pages[0].total_items).toBe(2)
    })

    act(() => { resolveDelete() })
    await waitFor(() => {
      expect(result.current.deleteMutation.isSuccess).toBe(true)
    })
  })

  it('restores the removed job when the delete request fails', async () => {
    vi.mocked(jobApi.deleteJob).mockRejectedValue(new Error('boom'))

    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(result.current.items).toHaveLength(2)
    })

    await act(async () => {
      result.current.deleteMutation.mutate('job-1')
    })

    await waitFor(() => {
      expect(result.current.deleteMutation.isError).toBe(true)
    })

    const cached = qc.getQueriesData<{ pages: { items: JobListItem[]; total_items: number }[] }>({ queryKey: ['jobs-v2-infinite'] })
    const pages = cached[0]?.[1]?.pages ?? []
    expect(pages[0].items.map(i => i.id)).toContain('job-1')
    expect(pages[0].total_items).toBe(3)
  })
})

describe('useJobsInfiniteQuery.filterProcessingStatus', () => {
  let qc: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    vi.mocked(jobApi.searchInfinite).mockResolvedValue(page([makeJob('job-1')], 1))
  })

  it('sends processing_status=none when the Not processed filter is selected', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalled()
    })

    act(() => {
      result.current.setFilterProcessingStatus('none')
    })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalledWith(
        expect.objectContaining({ processing_status: 'none' })
      )
    })
  })

  it('counts the Not processed filter as an active filter', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(result.current.activeFilterCount).toBe(0)
    })

    act(() => {
      result.current.setFilterProcessingStatus('none')
    })

    expect(result.current.activeFilterCount).toBe(1)
  })

  it('clears the Not processed filter alongside the others', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(result.current.activeFilterCount).toBe(0)
    })

    act(() => {
      result.current.setFilterProcessingStatus('none')
      result.current.setFilterRemote(true)
    })
    expect(result.current.activeFilterCount).toBe(2)

    act(() => {
      result.current.clearFilters()
    })
    expect(result.current.activeFilterCount).toBe(0)
  })
})

describe('useJobsInfiniteQuery.filterLocation', () => {
  let qc: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    vi.mocked(jobApi.searchInfinite).mockResolvedValue(page([makeJob('job-1')], 1))
  })

  it('sends the location filter to the API', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalled()
    })

    act(() => {
      result.current.setFilterLocation('Berlin')
    })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalledWith(
        expect.objectContaining({ location: 'Berlin' })
      )
    })
  })

  it('omits the location param when the filter is empty', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalled()
    })

    const lastCall = vi.mocked(jobApi.searchInfinite).mock.calls.at(-1)![0]
    expect(lastCall.location).toBeUndefined()
  })

  it('counts the location filter as an active filter and clears it', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(result.current.activeFilterCount).toBe(0)
    })

    act(() => {
      result.current.setFilterLocation('Amsterdam')
    })
    expect(result.current.activeFilterCount).toBe(1)

    act(() => {
      result.current.clearFilters()
    })
    expect(result.current.activeFilterCount).toBe(0)
    expect(result.current.filterLocation).toBe('')
  })
})

describe("useJobsInfiniteQuery.filterPinned", () => {
  let qc: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    vi.mocked(jobApi.searchInfinite).mockResolvedValue(page([makeJob('job-1')], 1))
  })

  it('sends pinned=true when the pinned filter is enabled', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalled()
    })

    act(() => {
      result.current.setFilterPinned(true)
    })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalledWith(
        expect.objectContaining({ pinned: true })
      )
    })
  })

  it('omits the pinned param when the filter is off', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalled()
    })

    const lastCall = vi.mocked(jobApi.searchInfinite).mock.calls.at(-1)![0]
    expect(lastCall.pinned).toBeUndefined()
  })

  it('counts the pinned filter as an active filter and clears it', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(result.current.activeFilterCount).toBe(0)
    })

    act(() => {
      result.current.setFilterPinned(true)
    })
    expect(result.current.activeFilterCount).toBe(1)

    act(() => {
      result.current.clearFilters()
    })
    expect(result.current.activeFilterCount).toBe(0)
    expect(result.current.filterPinned).toBe(false)
  })
})

describe('useJobsInfiniteQuery.filterRecommendation', () => {
  let qc: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    vi.mocked(jobApi.searchInfinite).mockResolvedValue(page([makeJob('job-1')], 1))
  })

  it('sends the recommendation filter to the API', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalled()
    })

    act(() => {
      result.current.setFilterRecommendation(['apply'])
    })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalledWith(
        expect.objectContaining({ recommendation: ['apply'] })
      )
    })
  })

  it('omits the recommendation param when the filter is empty', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalled()
    })

    const lastCall = vi.mocked(jobApi.searchInfinite).mock.calls.at(-1)![0]
    expect(lastCall.recommendation).toBeUndefined()
  })

  it('sends multiple recommendation values to the API (OR)', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalled()
    })

    act(() => {
      result.current.setFilterRecommendation(['apply', 'consider'])
    })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalledWith(
        expect.objectContaining({ recommendation: ['apply', 'consider'] })
      )
    })
  })

  it('counts the recommendation filter as an active filter and clears it', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(result.current.activeFilterCount).toBe(0)
    })

    act(() => {
      result.current.setFilterRecommendation(['skip'])
    })
    expect(result.current.activeFilterCount).toBe(1)

    act(() => {
      result.current.clearFilters()
    })
    expect(result.current.activeFilterCount).toBe(0)
    expect(result.current.filterRecommendation).toEqual([])
  })
})

describe('useJobsInfiniteQuery.filterTrackingStatus', () => {
  let qc: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    vi.mocked(jobApi.searchInfinite).mockResolvedValue(page([makeJob('job-1')], 1))
  })

  it('sends the tracking filter to the API', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalled()
    })

    act(() => {
      result.current.setFilterTrackingStatus(['interview'])
    })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalledWith(
        expect.objectContaining({ tracking_status: ['interview'] })
      )
    })
  })

  it('omits the tracking param when the filter is empty', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalled()
    })

    const lastCall = vi.mocked(jobApi.searchInfinite).mock.calls.at(-1)![0]
    expect(lastCall.tracking_status).toBeUndefined()
  })

  it('counts the tracking filter as an active filter and clears it', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(result.current.activeFilterCount).toBe(0)
    })

    act(() => {
      result.current.setFilterTrackingStatus(['accepted'])
    })
    expect(result.current.activeFilterCount).toBe(1)

    act(() => {
      result.current.clearFilters()
    })
    expect(result.current.activeFilterCount).toBe(0)
    expect(result.current.filterTrackingStatus).toEqual([])
  })
})

describe('useJobsInfiniteQuery.filterCreatedDate', () => {
  let qc: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    vi.mocked(jobApi.searchInfinite).mockResolvedValue(page([makeJob('job-1')], 1))
  })

  it('sends the created-date filter to the API', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalled()
    })

    act(() => {
      result.current.setFilterCreatedDate('week')
    })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalledWith(
        expect.objectContaining({ created_date: 'week' })
      )
    })
  })

  it('omits the created-date param when the filter is empty', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(jobApi.searchInfinite).toHaveBeenCalled()
    })

    const lastCall = vi.mocked(jobApi.searchInfinite).mock.calls.at(-1)![0]
    expect(lastCall.created_date).toBeUndefined()
  })

  it('counts the created-date filter as an active filter and clears it', async () => {
    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(result.current.activeFilterCount).toBe(0)
    })

    act(() => {
      result.current.setFilterCreatedDate('today')
    })
    expect(result.current.activeFilterCount).toBe(1)

    act(() => {
      result.current.clearFilters()
    })
    expect(result.current.activeFilterCount).toBe(0)
    expect(result.current.filterCreatedDate).toBe('')
  })
})

describe('useJobsInfiniteQuery.pinnedMutation', () => {
  let qc: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    vi.mocked(jobApi.searchInfinite).mockResolvedValue(page([makeJob('job-1')], 1))
  })

  it('optimistically toggles the pinned flag before the request resolves', async () => {
    let resolvePinned!: (v: { pinned: boolean }) => void
    vi.mocked(jobApi.setPinned).mockImplementation(
      () => new Promise((resolve) => { resolvePinned = resolve })
    )

    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(result.current.items).toHaveLength(1)
    })

    qc.setQueryData(['job-detail', 'job-1'], { id: 'job-1', pinned: false } as any)

    act(() => {
      result.current.pinnedMutation.mutate({ jobId: 'job-1', pinned: true })
    })

    await waitFor(() => {
      const cached = qc.getQueriesData<{ pages: { items: JobListItem[] }[] }>({ queryKey: ['jobs-v2-infinite'] })
      const pages = cached[0]?.[1]?.pages ?? []
      expect(pages[0].items[0].pinned).toBe(true)
    })

    expect(qc.getQueryData(['job-detail', 'job-1'])).toMatchObject({ pinned: true })

    act(() => { resolvePinned({ pinned: true }) })
    await waitFor(() => {
      expect(result.current.pinnedMutation.isSuccess).toBe(true)
    })
  })

  it('restores the previous pinned state when the request fails', async () => {
    vi.mocked(jobApi.setPinned).mockRejectedValue(new Error('boom'))

    const { result } = renderHook(() => useJobsInfiniteQuery(), { wrapper: wrapper(qc) })

    await waitFor(() => {
      expect(result.current.items).toHaveLength(1)
    })

    qc.setQueryData(['job-detail', 'job-1'], { id: 'job-1', pinned: false } as any)

    await act(async () => {
      result.current.pinnedMutation.mutate({ jobId: 'job-1', pinned: true })
    })

    await waitFor(() => {
      expect(result.current.pinnedMutation.isError).toBe(true)
    })

    const cached = qc.getQueriesData<{ pages: { items: JobListItem[] }[] }>({ queryKey: ['jobs-v2-infinite'] })
    const pages = cached[0]?.[1]?.pages ?? []
    expect(pages[0].items[0].pinned).toBe(false)

    expect(qc.getQueryData(['job-detail', 'job-1'])).toMatchObject({ pinned: false })
  })
})
