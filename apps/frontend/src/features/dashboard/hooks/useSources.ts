'use client'

import { useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { sourceApi, type SourcesQuery } from '@/entities/job/sources'
import { DEFAULT_STALE_TIME } from '@/shared/config/constants'

export function useSourceStats() {
  return useQuery({
    queryKey: ['job-source-stats'],
    queryFn: sourceApi.stats,
    staleTime: DEFAULT_STALE_TIME,
  })
}

export function useSourceDistribution() {
  return useQuery({
    queryKey: ['job-source-distribution'],
    queryFn: () => sourceApi.distribution(),
    staleTime: DEFAULT_STALE_TIME,
  })
}

export function useRecommendationDistribution() {
  return useQuery({
    queryKey: ['job-recommendation-distribution'],
    queryFn: sourceApi.recommendationDistribution,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/** Debounces anything typed into `query` before it becomes part of a queryKey. */
export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(timer)
  }, [value, delay])
  return debounced
}

const DEFAULT_QUERY: SourcesQuery = {
  page: 1,
  page_size: 25,
  query: '',
  field: 'job_count',
  order: 'desc',
}

export function useSourcesList() {
  const [query, setQuery] = useState<SourcesQuery>(DEFAULT_QUERY)
  const debouncedSearch = useDebouncedValue(query.query)

  // Page reset when the visible inputs (search/sort) change.
  const effectiveQuery = useMemo<SourcesQuery>(
    () => ({ ...query, query: debouncedSearch }),
    [query, debouncedSearch],
  )

  const result = useQuery({
    queryKey: ['job-sources', effectiveQuery],
    queryFn: () => sourceApi.sources(effectiveQuery),
    staleTime: DEFAULT_STALE_TIME,
  })

  const setPage = useCallback(
    (page: number) => setQuery((q) => ({ ...q, page })),
    [],
  )
  const setPageSize = useCallback(
    (pageSize: number) => setQuery((q) => ({ ...q, page_size: pageSize, page: 1 })),
    [],
  )
  const setSearch = useCallback(
    (search: string) => setQuery((q) => ({ ...q, query: search, page: 1 })),
    [],
  )
  const onSortChange = useCallback((field: SourcesQuery['field']) => {
    setQuery((q) =>
      q.field === field
        ? { ...q, order: q.order === 'asc' ? 'desc' : 'asc', page: 1 }
        : { ...q, field, order: 'desc', page: 1 },
    )
  }, [])

  return {
    query: effectiveQuery,
    rawSearch: query.query,
    setPage,
    setPageSize,
    setSearch,
    onSortChange,
    ...result,
  }
}
