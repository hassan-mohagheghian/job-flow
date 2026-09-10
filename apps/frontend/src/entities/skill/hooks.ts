'use client'

import { useState, useMemo, useCallback } from 'react'
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { skillApi } from './api'
import type { InfiniteSkillSearchResult, SkillCreateInput, SkillUpdateInput, SkillListItem } from './types'
import { PAGE_SIZE_SMALL, DEFAULT_STALE_TIME } from '@/shared/config/constants'

const PAGE_SIZE = PAGE_SIZE_SMALL
const SKILLS_KEY = 'skills-v2-infinite'
const CATEGORIES_KEY = 'skills-categories'

export function useSkillCategories() {
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: [CATEGORIES_KEY],
    queryFn: () => skillApi.getCategories(),
    staleTime: DEFAULT_STALE_TIME,
  })

  const categories = useMemo(() => query.data ?? [], [query.data])

  const createMutation = useMutation({
    mutationFn: (name: string) => skillApi.createCategory(name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CATEGORIES_KEY] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (name: string) => skillApi.deleteCategory(name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CATEGORIES_KEY] }),
  })

  return { categories, isLoading: query.isLoading, createMutation, deleteMutation }
}

export function useSkillsInfiniteQuery() {
  const queryClient = useQueryClient()
  const [query, setQuery] = useState('')
  const [sortState, setSortState] = useState<{ sort: string; order: 'asc' | 'desc' }>({
    sort: 'mention_count',
    order: 'desc',
  })
  const { sort, order } = sortState
  const [filterCategories, setFilterCategories] = useState<string[]>([])
  const [filterPinned, setFilterPinned] = useState(false)

  const filterKey = useMemo(
    () => ({
      query,
      sort,
      order,
      categories: filterCategories.length > 0 ? [...filterCategories].sort() : undefined,
      pinned: filterPinned || undefined,
    }),
    [query, sort, order, filterCategories, filterPinned]
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
  } = useInfiniteQuery<InfiniteSkillSearchResult>({
    queryKey: [SKILLS_KEY, filterKey],
    queryFn: ({ pageParam }) =>
      skillApi.listInfinite({
        page_size: PAGE_SIZE,
        cursor: pageParam as string | undefined,
        query: filterKey.query || undefined,
        categories: filterKey.categories,
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

  const activeFilterCount = [query, filterCategories.length > 0 ? filterCategories.length : '', filterPinned ? 'pinned' : ''].filter(Boolean).length

  const clearFilters = useCallback(() => {
    setQuery('')
    setFilterCategories([])
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
    mutationFn: (id: number | string) => skillApi.delete(id),
    onSettled: () => queryClient.invalidateQueries({ queryKey: [SKILLS_KEY] }),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number | string; data: SkillUpdateInput }) => skillApi.update(id, data),
    onSettled: () => queryClient.invalidateQueries({ queryKey: [SKILLS_KEY] }),
  })

  const pinnedMutation = useMutation({
    mutationFn: ({ id, pinned }: { id: number | string; pinned: boolean }) => skillApi.setPinned(id, pinned),
    onMutate: async ({ id, pinned }) => {
      await queryClient.cancelQueries({ queryKey: [SKILLS_KEY] })
      const previousData = queryClient.getQueriesData<{ pages: { items: SkillListItem[] }[] }>({ queryKey: [SKILLS_KEY] })
      queryClient.setQueriesData<{ pages: { items: SkillListItem[] }[] }>(
        { queryKey: [SKILLS_KEY] },
        (old) => {
          if (!old) return old
          return {
            ...old,
            pages: old.pages.map(page => ({
              ...page,
              items: page.items.map((item) =>
                item.id === id ? { ...item, pinned } : item
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
      queryClient.invalidateQueries({ queryKey: [SKILLS_KEY] })
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
    filterCategories,
    setFilterCategories: useCallback((v: string[]) => setFilterCategories(v), []),
    filterPinned,
    setFilterPinned: useCallback((v: boolean) => setFilterPinned(v), []),
    activeFilterCount,
    clearFilters,
    deleteMutation,
    updateMutation,
    pinnedMutation,
  }
}

export function useCreateSkill() {
  const queryClient = useQueryClient()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (data: SkillCreateInput) => skillApi.create(data),
    onError: (e: unknown) => {
      setError((e as { message?: string })?.message || 'Failed to add skill')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: [SKILLS_KEY] })
    },
  })

  const createSkill = async (data: SkillCreateInput): Promise<boolean> => {
    setSubmitting(true)
    setError(null)
    try {
      await mutation.mutateAsync(data)
      return true
    } catch {
      return false
    } finally {
      setSubmitting(false)
    }
  }

  const clearError = () => setError(null)

  return { createSkill, submitting, error, clearError }
}

export function useMergeSkills() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ targetId, sourceIds }: { targetId: number; sourceIds: number[] }) =>
      skillApi.merge(targetId, sourceIds),
    onSettled: () => queryClient.invalidateQueries({ queryKey: [SKILLS_KEY] }),
  })
}

export function useBreakdownSkill() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, childNames }: { id: number; childNames: string[] }) =>
      skillApi.breakDown(id, childNames),
    onSettled: () => queryClient.invalidateQueries({ queryKey: [SKILLS_KEY] }),
  })
}

export function usePromoteAliasToCanonical() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, aliasName }: { id: number; aliasName: string }) =>
      skillApi.promoteAliasToCanonical(id, aliasName),
    onSettled: () => queryClient.invalidateQueries({ queryKey: [SKILLS_KEY] }),
  })
}

export function useSkillReferencedJobs(skillId: number | null) {
  return useQuery({
    queryKey: ['skills-referenced-jobs', skillId],
    queryFn: () => skillApi.referencedJobs(skillId as number),
    enabled: skillId != null,
  })
}

export function useAddSkillNoteMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ skillId, content }: { skillId: number; content: string }) =>
      skillApi.addNote(skillId, content),
    onSettled: () => queryClient.invalidateQueries({ queryKey: [SKILLS_KEY] }),
  })
}

export function useDeleteSkillNoteMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (noteId: number) => skillApi.deleteNote(noteId),
    onSettled: () => queryClient.invalidateQueries({ queryKey: [SKILLS_KEY] }),
  })
}

export function useAddSkillLinkMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ skillId, title, url }: { skillId: number; title: string; url: string }) =>
      skillApi.addLink(skillId, title, url),
    onSettled: () => queryClient.invalidateQueries({ queryKey: [SKILLS_KEY] }),
  })
}

export function useDeleteSkillLinkMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (linkId: number) => skillApi.deleteLink(linkId),
    onSettled: () => queryClient.invalidateQueries({ queryKey: [SKILLS_KEY] }),
  })
}
