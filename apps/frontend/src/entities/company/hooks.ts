'use client'

import { useState, useMemo, useCallback } from 'react'
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { companyApi } from './api'
import type {
  CompanyDetail,
  CompanyListItem,
  CompanyEditInput,
  InfiniteCompanySearchResult,
} from './types'
import { PAGE_SIZE_SMALL } from '@/shared/config/constants'

const PAGE_SIZE = PAGE_SIZE_SMALL
const COMPANIES_KEY = 'companies-v2-infinite'
const COMPANY_DETAIL_KEY = 'company-detail'

export function useCompaniesInfiniteQuery() {
  const queryClient = useQueryClient()
  const [query, setQuery] = useState('')
  const [sortState, setSortState] = useState<{ sort: string; order: 'asc' | 'desc' }>({
    sort: 'created_at',
    order: 'desc',
  })
  const { sort, order } = sortState
  const [filterIndustry, setFilterIndustry] = useState('')
  const [filterCompanyType, setFilterCompanyType] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterPinned, setFilterPinned] = useState(false)

  const filterKey = useMemo(
    () => ({
      query,
      sort,
      order,
      industry: filterIndustry || undefined,
      company_type: filterCompanyType || undefined,
      status: filterStatus || undefined,
      pinned: filterPinned || undefined,
    }),
    [query, sort, order, filterIndustry, filterCompanyType, filterStatus, filterPinned]
  )

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
  } = useInfiniteQuery<InfiniteCompanySearchResult>({
    queryKey: [COMPANIES_KEY, filterKey],
    queryFn: ({ pageParam }) =>
      companyApi.listInfinite({
        page_size: PAGE_SIZE,
        cursor: pageParam as string | undefined,
        query: filterKey.query || undefined,
        industry: filterKey.industry,
        company_type: filterKey.company_type,
        status: filterKey.status,
        pinned: filterKey.pinned,
        sort: filterKey.sort,
        order: filterKey.order as 'asc' | 'desc',
      }),
    initialPageParam: undefined,
    getNextPageParam: (lastPage) => (lastPage.has_more ? lastPage.next_cursor : undefined),
  })

  const items = useMemo(() => data?.pages.flatMap((p) => p.items) ?? [], [data])
  const total = data?.pages[0]?.total_items ?? 0
  const loadedCount = items.length

  const activeFilterCount = [query, filterIndustry, filterCompanyType, filterStatus, filterPinned].filter(Boolean).length

  const clearFilters = useCallback(() => {
    setQuery('')
    setFilterIndustry('')
    setFilterCompanyType('')
    setFilterStatus('')
    setFilterPinned(false)
  }, [])

  const handleHeaderSort = useCallback((field: string) => {
    setSortState((prev) => {
      if (prev.sort === field) {
        return { sort: field, order: prev.order === 'desc' ? 'asc' : 'desc' }
      }
      return { sort: field, order: 'desc' }
    })
  }, [])

  const deleteMutation = useMutation({
    mutationFn: (id: string) => companyApi.delete(id),
    onSettled: () => queryClient.invalidateQueries({ queryKey: [COMPANIES_KEY] }),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: CompanyEditInput }) => companyApi.update(id, data),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: [COMPANIES_KEY] })
      queryClient.invalidateQueries({ queryKey: [COMPANY_DETAIL_KEY] })
    },
  })

  const reprocessMutation = useMutation({
    mutationFn: (id: string) => companyApi.reprocess(id),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: [COMPANIES_KEY] })
      queryClient.invalidateQueries({ queryKey: [COMPANY_DETAIL_KEY] })
    },
  })

  const setMainMutation = useMutation({
    mutationFn: ({ id, mainCompanyId }: { id: string; mainCompanyId: string | null }) =>
      companyApi.setMain(id, mainCompanyId),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: [COMPANIES_KEY] })
      queryClient.invalidateQueries({ queryKey: [COMPANY_DETAIL_KEY] })
    },
  })

  const pinnedMutation = useMutation({
    mutationFn: ({ id, pinned }: { id: string; pinned: boolean }) => companyApi.setPinned(id, pinned),
    onMutate: async ({ id, pinned }) => {
      await queryClient.cancelQueries({ queryKey: [COMPANIES_KEY] })
      await queryClient.cancelQueries({ queryKey: [COMPANY_DETAIL_KEY, id] })
      const previousData = queryClient.getQueriesData<{ pages: { items: CompanyListItem[] }[] }>({ queryKey: [COMPANIES_KEY] })
      const previousDetail = queryClient.getQueryData<CompanyDetail>([COMPANY_DETAIL_KEY, id])
      queryClient.setQueriesData<{ pages: { items: CompanyListItem[] }[] }>(
        { queryKey: [COMPANIES_KEY] },
        (old) => {
          if (!old) return old
          return {
            ...old,
            pages: old.pages.map((page) => ({
              ...page,
              items: page.items.map((item) =>
                item.id === id ? { ...item, pinned } : item
              ),
            })),
          }
        }
      )
      queryClient.setQueryData<CompanyDetail>([COMPANY_DETAIL_KEY, id], (old) =>
        old ? { ...old, pinned } : old
      )
      return { previousData, previousDetail }
    },
    onError: (_err, _vars, context) => {
      if (context?.previousData) {
        for (const [key, data] of context.previousData) {
          queryClient.setQueryData(key, data)
        }
      }
      if (context?.previousDetail) {
        queryClient.setQueryData([COMPANY_DETAIL_KEY, _vars.id], context.previousDetail)
      }
    },
    onSettled: (_data, _error, vars) => {
      queryClient.invalidateQueries({ queryKey: [COMPANIES_KEY] })
      queryClient.invalidateQueries({ queryKey: [COMPANY_DETAIL_KEY, vars.id] })
    },
  })

  return {
    items,
    total,
    loadedCount,
    isLoading,
    isFetchingNextPage,
    isRefetching,
    hasNextPage: !!hasNextPage,
    fetchNextPage,
    isError,
    error,
    refetch,
    query,
    setQuery: useCallback((v: string) => setQuery(v), []),
    sort,
    order,
    handleHeaderSort,
    filterIndustry,
    setFilterIndustry: useCallback((v: string) => setFilterIndustry(v), []),
    filterCompanyType,
    setFilterCompanyType: useCallback((v: string) => setFilterCompanyType(v), []),
    filterStatus,
    setFilterStatus: useCallback((v: string) => setFilterStatus(v), []),
    filterPinned,
    setFilterPinned: useCallback((v: boolean) => setFilterPinned(v), []),
    activeFilterCount,
    clearFilters,
    deleteMutation,
    updateMutation,
    reprocessMutation,
    setMainMutation,
    pinnedMutation,
  }
}

export function useCompanyQuery(id: number | string | null) {
  return useQuery<CompanyDetail>({
    queryKey: [COMPANY_DETAIL_KEY, id],
    queryFn: () => companyApi.get(id as string),
    enabled: !!id,
  })
}
