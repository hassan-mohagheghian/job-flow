'use client'

import { useState, useMemo, useCallback } from 'react'
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobApi } from '@/entities/job/api'
import type { JobListItem, ProcessingStatus, ProcessingStatusFilter, RecommendationFilter, TrackingStatusFilter, CreatedDateFilter, InfiniteJobSearchResult } from '@/entities/job/types'
import { PAGE_SIZE } from '@/shared/config/constants'
const JOBS_KEY = 'jobs-v2-infinite'

export function useJobsInfiniteQuery() {
  const queryClient = useQueryClient()
  const [query, setQuery] = useState('')
  const [sortState, setSortState] = useState<{ sort: string; order: 'asc' | 'desc' }>({ sort: 'created_at', order: 'desc' })
  const { sort, order } = sortState
  const [filterProcessingStatus, setFilterProcessingStatus] = useState<ProcessingStatusFilter>('')
  const [filterLocation, setFilterLocation] = useState('')
  const [filterRemote, setFilterRemote] = useState<boolean | ''>('')
  const [filterVisa, setFilterVisa] = useState<boolean | ''>('')
  const [filterPinned, setFilterPinned] = useState(false)
  const [filterTags, setFilterTags] = useState<string[]>([])
  const [filterRecommendation, setFilterRecommendation] = useState<RecommendationFilter[]>([])
  const [filterTrackingStatus, setFilterTrackingStatus] = useState<TrackingStatusFilter[]>([])
  const [filterCreatedDate, setFilterCreatedDate] = useState<CreatedDateFilter>('')

  const filterKey = useMemo(() => ({
    query,
    sort,
    order,
    processing_status: filterProcessingStatus || undefined,
    location: filterLocation || undefined,
    remote: filterRemote === '' ? undefined : filterRemote,
    visa: filterVisa === '' ? undefined : filterVisa,
    pinned: filterPinned || undefined,
    tags: filterTags.length ? filterTags.join(',') : undefined,
    recommendation: filterRecommendation.length ? filterRecommendation : undefined,
    tracking_status: filterTrackingStatus.length ? filterTrackingStatus : undefined,
    created_date: filterCreatedDate || undefined,
  }), [query, sort, order, filterProcessingStatus, filterLocation, filterRemote, filterVisa, filterPinned, filterTags, filterRecommendation, filterTrackingStatus, filterCreatedDate])

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isRefetching,
  } = useInfiniteQuery<InfiniteJobSearchResult>({
    queryKey: [JOBS_KEY, filterKey],
    queryFn: ({ pageParam }) => jobApi.searchInfinite({
      page_size: PAGE_SIZE,
      cursor: pageParam as string | undefined,
      query: filterKey.query || undefined,
      sort: filterKey.sort,
      order: filterKey.order as 'asc' | 'desc',
      processing_status: filterKey.processing_status as ProcessingStatus | 'none' | undefined,
      location: filterKey.location as string | undefined,
      remote: filterKey.remote as boolean | undefined,
      visa: filterKey.visa as boolean | undefined,
      pinned: filterKey.pinned as boolean | undefined,
      recommendation: filterKey.recommendation as RecommendationFilter[] | undefined,
      tracking_status: filterKey.tracking_status as TrackingStatusFilter[] | undefined,
      created_date: filterKey.created_date as CreatedDateFilter | undefined,
    }),
    initialPageParam: undefined,
    getNextPageParam: (lastPage) => lastPage.has_more ? lastPage.next_cursor : undefined,
  })

  const items = useMemo(() => {
    return data?.pages.flatMap(p => p.items) ?? []
  }, [data])

  const total = data?.pages[0]?.total_items ?? 0
  const loadedCount = items.length

  const activeFilterCount = [
    filterProcessingStatus,
    filterLocation,
    filterRemote !== '',
    filterVisa !== '',
    filterPinned,
    filterRecommendation.length > 0,
    filterTrackingStatus.length > 0,
    filterCreatedDate,
  ].filter(Boolean).length

  const clearFilters = useCallback(() => {
    setFilterProcessingStatus('')
    setFilterLocation('')
    setFilterRemote('')
    setFilterVisa('')
    setFilterPinned(false)
    setFilterRecommendation([])
    setFilterTrackingStatus([])
    setFilterCreatedDate('')
  }, [])

  const handleHeaderSort = useCallback((field: string) => {
    setSortState(prev => {
      if (prev.sort === field) {
        return { sort: field, order: prev.order === 'desc' ? 'asc' : 'desc' }
      }
      return { sort: field, order: 'desc' }
    })
  }, [])
  const processMutation = useMutation({
    mutationFn: (jobId: string) => jobApi.processJob(jobId),
    onMutate: async (jobId) => {
      await queryClient.cancelQueries({ queryKey: [JOBS_KEY] })
      const previousData = queryClient.getQueriesData<{ pages: { items: JobListItem[] }[] }>({ queryKey: [JOBS_KEY] })
      queryClient.setQueriesData<{ pages: { items: JobListItem[] }[] }>(
        { queryKey: [JOBS_KEY] },
        (old) => {
          if (!old) return old
          return {
            ...old,
            pages: old.pages.map(page => ({
              ...page,
              items: page.items.map((item) =>
                item.id === jobId
                  ? {
                      ...item,
                      latest_processing_execution: {
                        id: 'optimistic',
                        status: 'queued' as ProcessingStatus,
                        started_at: new Date().toISOString(),
                        finished_at: null,
                      },
                    }
                  : item
              ),
            })),
          }
        }
      )
      return { previousData }
    },
    onError: (_err, jobId, context) => {
      if (context?.previousData) {
        for (const [key, data] of context.previousData) {
          queryClient.setQueryData(key, data)
        }
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: [JOBS_KEY] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (jobId: string) => jobApi.deleteJob(jobId),
    onMutate: async (jobId) => {
      await queryClient.cancelQueries({ queryKey: [JOBS_KEY] })
      const previousData = queryClient.getQueriesData<{ pages: { items: JobListItem[]; total_items?: number }[] }>({ queryKey: [JOBS_KEY] })
      queryClient.setQueriesData<{ pages: { items: JobListItem[]; total_items?: number }[] }>(
        { queryKey: [JOBS_KEY] },
        (old) => {
          if (!old) return old
          return {
            ...old,
            pages: old.pages.map(page => ({
              ...page,
              total_items: page.total_items !== undefined ? Math.max(0, page.total_items - 1) : page.total_items,
              items: page.items.filter((item) => item.id !== jobId),
            })),
          }
        }
      )
      return { previousData }
    },
    onError: (_err, _jobId, context) => {
      if (context?.previousData) {
        for (const [key, data] of context.previousData) {
          queryClient.setQueryData(key, data)
        }
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: [JOBS_KEY] })
    },
  })

  const pinnedMutation = useMutation({
    mutationFn: ({ jobId, pinned }: { jobId: string; pinned: boolean }) => jobApi.setPinned(jobId, pinned),
    onMutate: async ({ jobId, pinned }) => {
      await queryClient.cancelQueries({ queryKey: [JOBS_KEY] })
      const previousData = queryClient.getQueriesData<{ pages: { items: JobListItem[] }[] }>({ queryKey: [JOBS_KEY] })
      queryClient.setQueriesData<{ pages: { items: JobListItem[] }[] }>(
        { queryKey: [JOBS_KEY] },
        (old) => {
          if (!old) return old
          return {
            ...old,
            pages: old.pages.map(page => ({
              ...page,
              items: page.items.map((item) =>
                item.id === jobId ? { ...item, pinned } : item
              ),
            })),
          }
        }
      )
      return { previousData }
    },
    onError: (_err, _vars, context) => {
      if (context?.previousData) {
        for (const [key, data] of context.previousData) {
          queryClient.setQueryData(key, data)
        }
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: [JOBS_KEY] })
    },
  })

  const dismissedMutation = useMutation({
    mutationFn: ({ jobId, dismissed, note }: { jobId: string; dismissed: boolean; note?: string }) => jobApi.setDismissed(jobId, dismissed, note),
    onMutate: async ({ jobId, dismissed }) => {
      await queryClient.cancelQueries({ queryKey: [JOBS_KEY] })
      const previousData = queryClient.getQueriesData<{ pages: { items: JobListItem[] }[] }>({ queryKey: [JOBS_KEY] })
      queryClient.setQueriesData<{ pages: { items: JobListItem[] }[] }>(
        { queryKey: [JOBS_KEY] },
        (old) => {
          if (!old) return old
          return {
            ...old,
            pages: old.pages.map(page => ({
              ...page,
              items: page.items.map((item) =>
                item.id === jobId ? { ...item, dismissed } : item
              ),
            })),
          }
        }
      )
      return { previousData }
    },
    onError: (_err, _vars, context) => {
      if (context?.previousData) {
        for (const [key, data] of context.previousData) {
          queryClient.setQueryData(key, data)
        }
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: [JOBS_KEY] })
    },
  })

  return {
    items,
    total,
    loadedCount,
    isLoading,
    isFetchingNextPage,
    isRefetching,
    isError,
    error,
    refetch,
    query,
    setQuery: useCallback((v: string) => { setQuery(v) }, []),
    sort,
    order,
    handleHeaderSort,
    hasNextPage: !!hasNextPage,
    fetchNextPage,
    filterProcessingStatus,
    setFilterProcessingStatus: useCallback((v: ProcessingStatusFilter) => { setFilterProcessingStatus(v) }, []),
    filterLocation,
    setFilterLocation: useCallback((v: string) => { setFilterLocation(v) }, []),
    filterRemote,
    setFilterRemote: useCallback((v: boolean | '') => { setFilterRemote(v) }, []),
    filterVisa,
    setFilterVisa: useCallback((v: boolean | '') => { setFilterVisa(v) }, []),
    filterPinned,
    setFilterPinned: useCallback((v: boolean) => { setFilterPinned(v) }, []),
    filterRecommendation,
    setFilterRecommendation: useCallback((v: RecommendationFilter[]) => { setFilterRecommendation(v) }, []),
    filterTrackingStatus,
    setFilterTrackingStatus: useCallback((v: TrackingStatusFilter[]) => { setFilterTrackingStatus(v) }, []),
    filterCreatedDate,
    setFilterCreatedDate: useCallback((v: CreatedDateFilter) => { setFilterCreatedDate(v) }, []),
    filterTags,
    setFilterTags: useCallback((v: string[]) => { setFilterTags(v) }, []),
    activeFilterCount,
    clearFilters,
    processMutation,
    deleteMutation,
    pinnedMutation,
    dismissedMutation,
    tagsMutation: useMutation({
      mutationFn: ({ jobId, tags }: { jobId: string; tags: string[] }) => jobApi.setTags(jobId, tags),
      onMutate: async ({ jobId, tags }) => {
        await queryClient.cancelQueries({ queryKey: [JOBS_KEY] })
        const previousData = queryClient.getQueriesData<{ pages: { items: JobListItem[] }[] }>({ queryKey: [JOBS_KEY] })
        queryClient.setQueriesData<{ pages: { items: JobListItem[] }[] }>(
          { queryKey: [JOBS_KEY] },
          (old) => {
            if (!old) return old
            return {
              ...old,
              pages: old.pages.map(page => ({
                ...page,
                items: page.items.map((item) =>
                  item.id === jobId ? { ...item, tags } : item
                ),
              })),
            }
          }
        )
        return { previousData }
      },
      onError: (_err, _vars, context) => {
        if (context?.previousData) {
          for (const [key, data] of context.previousData) {
            queryClient.setQueryData(key, data)
          }
        }
      },
      onSettled: () => {
        queryClient.invalidateQueries({ queryKey: [JOBS_KEY] })
      },
    }),
  }
}
